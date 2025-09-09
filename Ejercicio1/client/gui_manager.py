"""
Gestor de la Interfaz de Usuario (GUI).

Este módulo es responsable de crear, configurar y manipular todos los elementos
gráficos de la aplicación usando Tkinter. Contiene funciones para construir la
ventana principal, las ventanas de chat privado y para actualizar el contenido
de los widgets, como el área de chat y la lista de usuarios.
"""

import tkinter as tk
from tkinter import scrolledtext, Listbox
from datetime import datetime

# Importamos la configuración y el estado de la aplicación
import config
import app_state
import event_handlers # Necesario para asignar comandos a los botones

def crear_interfaz_principal():
    """
    Construye la ventana principal de la aplicación con todos sus widgets.
    """
    # Configuración de la ventana raíz
    app_state.root.title("Chat Sirius")
    app_state.root.geometry("800x600")
    app_state.root.configure(bg=config.COLOR_FONDO)
    app_state.root.minsize(600, 400)

    # Frame principal
    main_frame = tk.Frame(app_state.root, bg=config.COLOR_FONDO)
    main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    main_frame.grid_columnconfigure(1, weight=1)
    main_frame.grid_rowconfigure(0, weight=1)

    # --- Barra Lateral (Sidebar) ---
    sidebar_frame = tk.Frame(main_frame, bg=config.COLOR_BARRA_LATERAL, width=200)
    sidebar_frame.grid(row=0, column=0, sticky="nswe", padx=(0, 10))

    tk.Label(sidebar_frame, text="Usuarios Conectados", font=config.FONT_BOLD, bg=config.COLOR_BARRA_LATERAL, fg=config.COLOR_TEXTO).pack(pady=10)
    
    app_state.gui_widgets['usuarios_listbox'] = Listbox(
        sidebar_frame, bg=config.COLOR_BARRA_LATERAL, fg=config.COLOR_TEXTO,
        font=config.FONT_NORMAL, borderwidth=0, highlightthickness=0,
        selectbackground=config.COLOR_PRIMARIO, selectforeground=config.COLOR_TEXTO_MI_MENSAJE,
        activestyle="none"
    )
    app_state.gui_widgets['usuarios_listbox'].pack(expand=True, fill=tk.BOTH, padx=5)
    app_state.gui_widgets['usuarios_listbox'].bind("<Double-Button-1>", event_handlers.manejar_inicio_chat_privado)

    # --- Contenedor del Chat ---
    chat_container_frame = tk.Frame(main_frame, bg=config.COLOR_FONDO_SECUNDARIO)
    chat_container_frame.grid(row=0, column=1, sticky="nswe")
    chat_container_frame.grid_rowconfigure(0, weight=1)
    chat_container_frame.grid_columnconfigure(0, weight=1)

    app_state.gui_widgets['chat_area'] = tk.Text(
        chat_container_frame, wrap=tk.WORD, state="disabled", bg=config.COLOR_FONDO_SECUNDARIO,
        font=config.FONT_NORMAL, borderwidth=0, highlightthickness=0, padx=10, pady=10
    )
    app_state.gui_widgets['chat_area'].grid(row=0, column=0, sticky="nswe")

    scrollbar = tk.Scrollbar(chat_container_frame, command=app_state.gui_widgets['chat_area'].yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    app_state.gui_widgets['chat_area']['yscrollcommand'] = scrollbar.set

    # --- Frame de Entrada de Texto ---
    input_frame = tk.Frame(app_state.root, bg=config.COLOR_FONDO_SECUNDARIO, height=50)
    input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
    input_frame.grid_columnconfigure(1, weight=1)

    app_state.gui_widgets['entry_msg'] = tk.Entry(
        input_frame, font=config.FONT_NORMAL, bg=config.COLOR_FONDO, fg=config.COLOR_TEXTO,
        borderwidth=0, highlightthickness=1, highlightbackground="#CCCCCC",
        highlightcolor=config.COLOR_PRIMARIO, insertbackground=config.COLOR_TEXTO
    )
    app_state.gui_widgets['entry_msg'].grid(row=0, column=1, sticky="we", padx=10, pady=10, ipady=5)
    app_state.gui_widgets['entry_msg'].bind("<Return>", event_handlers.manejar_envio_mensaje)

    # --- Botones ---
    btn_privado = _crear_boton_con_icono(sidebar_frame, "👤 Iniciar Privado", event_handlers.manejar_inicio_chat_privado)
    btn_privado.pack(fill=tk.X, padx=5, pady=5)
    
    btn_archivo = _crear_boton_con_icono(input_frame, "📎", event_handlers.manejar_envio_archivo)
    btn_archivo.grid(row=0, column=0, padx=5, pady=10)

    btn_enviar = _crear_boton_con_icono(input_frame, "➤", event_handlers.manejar_envio_mensaje)
    btn_enviar.grid(row=0, column=2, padx=5, pady=10)
    
    # --- Configuración de Estilos (Tags) ---
    _configurar_estilos_chat()

    # --- Protocolo de Cierre ---
    app_state.root.protocol("WM_DELETE_WINDOW", event_handlers.manejar_cierre_ventana)

def _crear_boton_con_icono(parent, texto_icono, comando):
    """Función auxiliar para crear botones con un estilo consistente."""
    btn = tk.Button(
        parent, text=texto_icono, font=("Segoe UI Symbol", 14), command=comando,
        bg=config.COLOR_FONDO_SECUNDARIO, fg=config.COLOR_PRIMARIO,
        activebackground=config.COLOR_FONDO_SECUNDARIO, activeforeground=config.COLOR_PRIMARIO_ACTIVO,
        relief="flat", cursor="hand2"
    )
    return btn

def _configurar_estilos_chat():
    """Configura los tags de estilo para el área de chat."""
    chat_area = app_state.gui_widgets['chat_area']
    chat_area.tag_configure("info", foreground=config.COLOR_TEXTO_SECUNDARIO, justify='center', font=config.FONT_ITALIC_PEQUEÑA)
    chat_area.tag_configure("nombre_otro_linea", font=config.FONT_BOLD, foreground=config.COLOR_PRIMARIO, justify='left')
    chat_area.tag_configure("nombre_mio_linea", font=config.FONT_BOLD, foreground=config.COLOR_TEXTO_SECUNDARIO, justify='right')
    chat_area.tag_configure("tag_tu", font=config.FONT_TU, foreground=config.COLOR_PRIMARIO, justify='right')
    chat_area.tag_configure("otro_usuario_burbuja", background=config.COLOR_BARRA_LATERAL, foreground=config.COLOR_TEXTO, justify='left', lmargin1=15, lmargin2=15, rmargin=120, spacing3=5, relief="groove", borderwidth=2, wrap="word")
    chat_area.tag_configure("mi_burbuja", background=config.COLOR_MI_BURBUJA, foreground=config.COLOR_TEXTO_MI_MENSAJE, justify='right', lmargin1=120, lmargin2=120, rmargin=15, spacing3=5, relief="groove", borderwidth=2, wrap="word")

def escribir_en_chat(mensaje_completo, tipo_mensaje="info"):
    """
    Añade un mensaje al área de chat principal con el formato adecuado.
    (VERSIÓN CORREGIDA para manejar mensajes de sistema de forma segura)
    """
    chat_area = app_state.gui_widgets['chat_area']
    chat_area.config(state="normal")
    
    timestamp = datetime.now().strftime("%H:%M")
    
    # --- INICIO DE LA CORRECCIÓN ---
    # Ahora, solo intentamos parsear el mensaje si es de un usuario.
    # Los mensajes de tipo "info" se tratan de forma separada y segura.
    if tipo_mensaje == "yo" or tipo_mensaje == "otro":
        # Esta lógica de parseo solo se aplica a mensajes de usuario reales.
        if "] " in mensaje_completo:
            partes = mensaje_completo.split("] ", 1)
            remitente = partes[0][1:]
            mensaje = partes[1]

            if tipo_mensaje == "yo":
                chat_area.insert(tk.END, f"{remitente} ", "nombre_mio_linea")
                chat_area.insert(tk.END, "(tú) ", "tag_tu")
                chat_area.insert(tk.END, f"({timestamp})\n", "nombre_mio_linea")
                chat_area.insert(tk.END, f"{mensaje}\n\n", "mi_burbuja")
            else:  # tipo_mensaje == "otro"
                chat_area.insert(tk.END, f"{remitente} ({timestamp})\n", "nombre_otro_linea")
                chat_area.insert(tk.END, f"{mensaje}\n\n", "otro_usuario_burbuja")
        else:
            # Si un mensaje de usuario llega con mal formato, lo mostramos como info.
            chat_area.insert(tk.END, f"{mensaje_completo}\n", "info")

    else:  # tipo_mensaje == "info"
        # Los mensajes del sistema como "[Enviando archivo...]" y los errores
        # entrarán directamente aquí, evitando el error de parseo.
        chat_area.insert(tk.END, f"{mensaje_completo}\n", "info")
    # --- FIN DE LA CORRECCIÓN ---
        
    chat_area.config(state="disabled")
    chat_area.yview(tk.END)

def actualizar_lista_usuarios(lista_nombres):
    """
    Limpia y actualiza la lista de usuarios en la barra lateral.
    :param lista_nombres: Una lista de strings con los apodos de los usuarios.
    """
    usuarios_listbox = app_state.gui_widgets['usuarios_listbox']
    usuarios_listbox.delete(0, tk.END)
    for nombre in sorted(lista_nombres):
        if nombre:
            display_name = nombre
            if nombre == app_state.apodo:
                display_name += " (tú)"
            usuarios_listbox.insert(tk.END, display_name)

def obtener_o_crear_ventana_privada(contraparte):
    """
    Busca una ventana de chat privado existente con un usuario o crea una nueva.
    :param contraparte: El apodo del otro usuario.
    :return: Un diccionario con la referencia a la ventana y su función de escritura.
    """
    if contraparte in app_state.private_windows and app_state.private_windows[contraparte]['win'].winfo_exists():
        app_state.private_windows[contraparte]['win'].lift()
        return app_state.private_windows[contraparte]

    win = tk.Toplevel(app_state.root)
    win.title(f"Chat privado con {contraparte}")
    txt = scrolledtext.ScrolledText(win, wrap=tk.WORD, state="disabled", width=50, height=18)
    txt.pack(padx=8, pady=8)
    entry = tk.Entry(win, width=40)
    entry.pack(side=tk.LEFT, padx=8, pady=8, expand=True, fill=tk.X)

    # El comando del botón llama a un event handler, pasando los widgets necesarios
    btn = tk.Button(win, text="Enviar", command=lambda: event_handlers.manejar_envio_privado(contraparte, entry))
    btn.pack(side=tk.LEFT, padx=6, pady=8)
    
    def on_private_close():
        del app_state.private_windows[contraparte]
        win.destroy()
    win.protocol("WM_DELETE_WINDOW", on_private_close)

    def write_private_line(texto_formateado):
        txt.config(state="normal")
        txt.insert(tk.END, texto_formateado + "\n")
        txt.yview(tk.END)
        txt.config(state="disabled")

    app_state.private_windows[contraparte] = {'win': win, 'write': write_private_line}
    return app_state.private_windows[contraparte]