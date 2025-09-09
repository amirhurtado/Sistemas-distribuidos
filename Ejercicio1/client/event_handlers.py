# event_handlers.py

"""
Manejadores de Eventos (Controlador).

Este módulo actúa como el "pegamento" entre la interfaz de usuario (GUI) y la
lógica de la aplicación (red). Contiene las funciones que se ejecutan como
respuesta a las interacciones del usuario, como clics de botones, selección en
listas o el cierre de la ventana.
"""

from tkinter import filedialog, messagebox

# Importamos los módulos necesarios
import app_state
import gui_manager
import network_handler

def manejar_envio_mensaje(event=None):
    """
    Se ejecuta al presionar Enter en el campo de texto o al hacer clic
    en el botón de enviar.
    """
    msg = app_state.gui_widgets.get('entry_msg').get().strip()
    if msg:
        network_handler.enviar_mensaje_publico(msg)
        app_state.gui_widgets.get('entry_msg').delete(0, 'end')

def manejar_envio_privado(destinatario, entry_widget):
    """
    Se ejecuta al enviar un mensaje desde una ventana de chat privado.
    :param destinatario: El apodo del receptor.
    :param entry_widget: El widget de entrada de texto de la ventana privada.
    """
    msg = entry_widget.get().strip()
    if msg:
        network_handler.enviar_mensaje_privado(destinatario, msg)
        entry_widget.delete(0, 'end')

def manejar_envio_archivo():
    """
    Abre un diálogo para seleccionar un archivo y llama a la función de red
    para enviarlo.
    """
    ruta_archivo = filedialog.askopenfilename(parent=app_state.root)
    if ruta_archivo:
        network_handler.enviar_archivo(ruta_archivo)

def manejar_inicio_chat_privado(event=None):
    """
    Se ejecuta al hacer doble clic en un usuario o al usar el botón de
    "Iniciar Privado".
    """
    seleccion = app_state.gui_widgets.get('usuarios_listbox').curselection()
    if not seleccion:
        messagebox.showinfo("Chat Privado", "Por favor, selecciona un usuario de la lista.", parent=app_state.root)
        return
    
    destinatario_display = app_state.gui_widgets.get('usuarios_listbox').get(seleccion[0])
    # Limpiamos el "(tú)" para obtener el nombre real
    destinatario = destinatario_display.replace(" (tú)", "")
    
    if destinatario == app_state.apodo:
        messagebox.showwarning("Acción no permitida", "No puedes iniciar un chat privado contigo mismo.", parent=app_state.root)
        return
    
    gui_manager.obtener_o_crear_ventana_privada(destinatario)

def manejar_cierre_ventana():
    """
    Se ejecuta cuando el usuario cierra la ventana principal.
    Cierra la conexión del socket y destruye la ventana.
    """
    if app_state.cliente_socket:
        try:
            app_state.cliente_socket.close()
        except Exception as e:
            print(f"Error al cerrar el socket: {e}")
    if app_state.root:
        app_state.root.destroy()