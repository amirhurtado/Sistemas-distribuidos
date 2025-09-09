
"""
Estado Global de la Aplicación.

Este módulo contiene las variables que necesitan ser accesibles desde diferentes
partes de la aplicación (GUI, red, manejadores de eventos).
Centralizar el estado aquí ayuda a evitar el desorden de variables globales y
previene problemas de importaciones circulares entre módulos.
"""

# Variable para la conexión del socket con el servidor.
cliente_socket = None

# El apodo (nombre de usuario) del cliente.
apodo = ""

# La ventana principal de la aplicación (Tkinter root).
root = None

# Diccionario para gestionar las ventanas de chat privado activas.
# La clave es el apodo de la contraparte y el valor es un diccionario
# con la ventana y la función para escribir en ella.
private_windows = {}

# Diccionario para almacenar las referencias a los widgets importantes de la GUI.
gui_widgets = {}