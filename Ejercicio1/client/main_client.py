# main_client.py

"""
Punto de Entrada Principal de la Aplicación Cliente.

Este script es el responsable de iniciar la aplicación. Orquesta la creación
de la interfaz de usuario, establece la conexión de red, solicita el apodo
al usuario, e inicia el hilo para escuchar al servidor. Finalmente,
inicia el bucle principal de la GUI de Tkinter.
"""

import threading
import tkinter as tk
from tkinter import simpledialog, messagebox

# Importamos todos nuestros módulos refactorizados
import app_state
import gui_manager
import network_handler
import event_handlers

def main():
    """Función principal que inicializa y ejecuta la aplicación."""
    # 1. Inicializar la ventana principal de la GUI
    app_state.root = tk.Tk()
    # Ocultamos la ventana temporalmente mientras pedimos el apodo
    app_state.root.withdraw() 
    
    # 2. Conectar al servidor
    # (Maneja su propio error y salida si falla)
    network_handler.conectar_al_servidor()

    # 3. Solicitar apodo al usuario
    apodo_valido = False
    while not apodo_valido:
        apodo = simpledialog.askstring(
            "Bienvenido a Sirius Chat",
            "Para empezar, elige tu nombre de usuario:",
            parent=app_state.root
        )
        if apodo:
            app_state.apodo = apodo
            apodo_valido = True
        else:
            if messagebox.askokcancel("Salir", "¿Seguro que quieres salir?"):
                event_handlers.manejar_cierre_ventana()
                return # Salimos de la función main

    # 4. Una vez tenemos el apodo, construimos la GUI y la mostramos
    app_state.root.deiconify() # Mostramos la ventana
    gui_manager.crear_interfaz_principal()
    app_state.root.title(f"Sirius Chat - Conectado como {app_state.apodo}")

    # 5. Enviar el apodo al servidor
    network_handler.enviar_apodo()
    gui_manager.escribir_en_chat(f"¡Bienvenido, {app_state.apodo}! Conectado al servidor.")
    
    # 6. Iniciar el hilo para escuchar al servidor
    hilo_escucha = threading.Thread(target=network_handler.escuchar_servidor, daemon=True)
    hilo_escucha.start()

    # 7. Iniciar el bucle principal de la aplicación
    app_state.root.mainloop()

if __name__ == "__main__":
    main()