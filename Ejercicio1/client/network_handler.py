# network_handler.py

"""
Gestor de Red.

Este módulo encapsula toda la lógica de comunicación con el servidor a través de sockets.
Incluye funciones para conectar, enviar diferentes tipos de mensajes (público, privado,
archivo, apodo) y un bucle principal que escucha continuamente los mensajes
entrantes del servidor en un hilo separado.
"""

import socket
import os
from datetime import datetime
from tkinter import messagebox

import config
import app_state
import gui_manager

def conectar_al_servidor():
    """
    Intenta establecer la conexión del socket con el servidor.
    En caso de error, muestra un mensaje y cierra la aplicación.
    """
    try:
        app_state.cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        app_state.cliente_socket.connect((config.HOST, config.PORT))
    except Exception as e:
        messagebox.showerror("Error de Conexión", f"No se pudo conectar al servidor en {config.HOST}:{config.PORT}.\n{e}")
        if app_state.root:
            app_state.root.destroy()
        raise SystemExit

def enviar_apodo():
    """Envía el apodo elegido al servidor."""
    if app_state.cliente_socket and app_state.apodo:
        app_state.cliente_socket.sendall(b'A' + app_state.apodo.encode('utf-8'))

def enviar_mensaje_publico(mensaje):
    """
    Envía un mensaje público al servidor.
    :param mensaje: El texto del mensaje a enviar.
    """
    try:
        app_state.cliente_socket.sendall(b'M' + mensaje.encode('utf-8'))
    except Exception as e:
        gui_manager.escribir_en_chat(f"[No se pudo enviar el mensaje: {e}]")

def enviar_mensaje_privado(destinatario, mensaje):
    """
    Envía un mensaje privado a un destinatario específico.
    :param destinatario: El apodo del usuario de destino.
    :param mensaje: El texto del mensaje.
    """
    try:
        payload = (b'P' + destinatario.ljust(64).encode('utf-8') +
                   len(mensaje.encode('utf-8')).to_bytes(4, 'big') +
                   mensaje.encode('utf-8'))
        app_state.cliente_socket.sendall(payload)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo enviar el mensaje privado: {e}")

def enviar_archivo(ruta_archivo):
    """
    Envía un archivo al servidor.
    :param ruta_archivo: La ruta completa del archivo a enviar.
    """
    try:
        nombre = os.path.basename(ruta_archivo)
        tamaño = os.path.getsize(ruta_archivo)
        gui_manager.escribir_en_chat(f"[Enviando archivo: {nombre}]")
        
        # Enviar metadatos
        app_state.cliente_socket.sendall(b'F')
        app_state.cliente_socket.sendall(nombre.ljust(256).encode('utf-8'))
        app_state.cliente_socket.sendall(tamaño.to_bytes(8, 'big'))
        
        # Enviar contenido del archivo en chunks
        with open(ruta_archivo, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                app_state.cliente_socket.sendall(chunk)
    except Exception as e:
        gui_manager.escribir_en_chat(f"[ERROR al enviar archivo: {e}]")

def escuchar_servidor():
    """
    Bucle principal que se ejecuta en un hilo para recibir y procesar
    constantemente los mensajes del servidor.
    """
    while True:
        try:
            tipo_b = app_state.cliente_socket.recv(1)
            if not tipo_b: break
            tipo = tipo_b.decode('utf-8')

            if tipo == 'M': # Mensaje público
                data = app_state.cliente_socket.recv(1024).decode('utf-8')
                if not data: break
                remitente = data.split("]")[0][1:]
                tipo_msg = "yo" if remitente == app_state.apodo else "otro"
                gui_manager.escribir_en_chat(data, tipo_msg)
            
            elif tipo == 'L': # Lista de usuarios
                data = app_state.cliente_socket.recv(4096).decode('utf-8')
                gui_manager.actualizar_lista_usuarios(data.split(','))

            elif tipo == 'P': # Mensaje privado recibido
                remitente = app_state.cliente_socket.recv(64).decode('utf-8').strip()
                ln = int.from_bytes(app_state.cliente_socket.recv(4), 'big')
                msg = app_state.cliente_socket.recv(ln).decode('utf-8') if ln > 0 else ""
                pv = gui_manager.obtener_o_crear_ventana_privada(remitente)
                timestamp = datetime.now().strftime("%H:%M")
                pv['write'](f"[{remitente}] ({timestamp}): {msg}")

            elif tipo == 'E': # Eco de mensaje privado enviado
                destinatario = app_state.cliente_socket.recv(64).decode('utf-8').strip()
                ln = int.from_bytes(app_state.cliente_socket.recv(4), 'big')
                msg = app_state.cliente_socket.recv(ln).decode('utf-8') if ln > 0 else ""
                pv = gui_manager.obtener_o_crear_ventana_privada(destinatario)
                timestamp = datetime.now().strftime("%H:%M")
                pv['write'](f"[{app_state.apodo} (tú)] ({timestamp}): {msg}")
            
            elif tipo == 'F': # Archivo
                nombre_archivo = app_state.cliente_socket.recv(256).decode('utf-8').strip()
                tamaño = int.from_bytes(app_state.cliente_socket.recv(8), 'big')
                gui_manager.escribir_en_chat(f"[Recibiendo archivo: {nombre_archivo}]")
                if not os.path.exists("descargas"): os.makedirs("descargas")
                ruta = os.path.join("descargas", nombre_archivo)
                with open(ruta, 'wb') as f:
                    leidos = 0
                    while leidos < tamaño:
                        chunk = app_state.cliente_socket.recv(min(4096, tamaño - leidos))
                        if not chunk: break
                        f.write(chunk)
                        leidos += len(chunk)
                gui_manager.escribir_en_chat(f"[Archivo '{nombre_archivo}' guardado en 'descargas']")

        except (ConnectionAbortedError, ConnectionResetError, OSError) as e:
            gui_manager.escribir_en_chat(f"[ERROR: Se ha perdido la conexión con el servidor: {e}]")
            break
        except Exception as e:
            print(f"Error inesperado en escuchar_servidor: {e}")
            gui_manager.escribir_en_chat(f"[ERROR: {e}]")
            break