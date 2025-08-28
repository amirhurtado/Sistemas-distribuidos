import socket
import threading
import os
import tkinter as tk
from tkinter import filedialog, simpledialog, scrolledtext, messagebox, Listbox
from datetime import datetime

# --- CONFIGURACIÓN INICIAL ---
HOST = "192.168.1.105" 
PORT = 5000

# --- PALETA DE COLORES Y FUENTES (Estilo Red Social) ---
COLOR_FONDO = "#F0F2F5"
COLOR_FONDO_SECUNDARIO = "#FFFFFF"
COLOR_BARRA_LATERAL = "#E4E6EB"
COLOR_PRIMARIO = "#0084FF" 
COLOR_PRIMARIO_ACTIVO = "#0062CC"
COLOR_TEXTO = "#050505"
COLOR_TEXTO_SECUNDARIO = "#65676B"
COLOR_MI_BURBUJA = "#0084FF" 
COLOR_TEXTO_MI_MENSAJE = "#FFFFFF" 

FONT_NORMAL = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_ITALIC_PEQUEÑA = ("Segoe UI", 8, "italic")
FONT_TITULO = ("Segoe UI", 12, "bold")
# --- NUEVA FUENTE AÑADIDA ---
FONT_TU = ("Segoe UI", 8, "normal")

# ---- Variables Globales ----
apodo = ""
cliente = None 

# ---- Configuración de la Ventana Principal ----
root = tk.Tk()
root.title("Chat Sirius")
root.geometry("800x600")
root.configure(bg=COLOR_FONDO)
root.minsize(600, 400)

# ---- Conexión con el Servidor ----
try:
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.connect((HOST, PORT))
except Exception as e:
    messagebox.showerror("Error de Conexión", f"No se pudo conectar al servidor en {HOST}:{PORT}.\n{e}")
    root.destroy()
    raise SystemExit

# ---- Estructura de la GUI con Frames ----
main_frame = tk.Frame(root, bg=COLOR_FONDO)
main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
main_frame.grid_columnconfigure(1, weight=1) 
main_frame.grid_rowconfigure(0, weight=1)

sidebar_frame = tk.Frame(main_frame, bg=COLOR_BARRA_LATERAL, width=200)
sidebar_frame.grid(row=0, column=0, sticky="nswe", padx=(0, 10))

tk.Label(sidebar_frame, text="Usuarios Conectados", font=FONT_BOLD, bg=COLOR_BARRA_LATERAL, fg=COLOR_TEXTO).pack(pady=10)
usuarios_listbox = Listbox(
    sidebar_frame, 
    bg=COLOR_BARRA_LATERAL, 
    fg=COLOR_TEXTO, 
    font=FONT_NORMAL, 
    borderwidth=0, 
    highlightthickness=0,
    selectbackground=COLOR_PRIMARIO,
    selectforeground=COLOR_TEXTO_MI_MENSAJE,
    activestyle="none"
)
usuarios_listbox.pack(expand=True, fill=tk.BOTH, padx=5)

chat_container_frame = tk.Frame(main_frame, bg=COLOR_FONDO_SECUNDARIO)
chat_container_frame.grid(row=0, column=1, sticky="nswe")
chat_container_frame.grid_rowconfigure(0, weight=1)
chat_container_frame.grid_columnconfigure(0, weight=1)

chat_area = tk.Text(
    chat_container_frame, 
    wrap=tk.WORD, 
    state="disabled", 
    bg=COLOR_FONDO_SECUNDARIO, 
    font=FONT_NORMAL,
    borderwidth=0,
    highlightthickness=0,
    padx=10,
    pady=10
)
chat_area.grid(row=0, column=0, sticky="nswe")

scrollbar = tk.Scrollbar(chat_container_frame, command=chat_area.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
chat_area['yscrollcommand'] = scrollbar.set

input_frame = tk.Frame(root, bg=COLOR_FONDO_SECUNDARIO, height=50)
input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
input_frame.grid_columnconfigure(1, weight=1)

entry_msg = tk.Entry(
    input_frame, 
    font=FONT_NORMAL, 
    bg=COLOR_FONDO, 
    fg=COLOR_TEXTO,
    borderwidth=0,
    highlightthickness=1,
    highlightbackground="#CCCCCC",
    highlightcolor=COLOR_PRIMARIO,
    insertbackground=COLOR_TEXTO
)
entry_msg.grid(row=0, column=1, sticky="we", padx=10, pady=10, ipady=5)

# --------------------------------------------------------------------------
# --- FUNCIONES DE LÓGICA (Definidas aquí, antes de ser usadas por los botones) ---
# --------------------------------------------------------------------------
private_windows = {}

def escribir_en_chat(mensaje_completo, tipo_mensaje="info"):
    chat_area.config(state="normal")
    
    remitente = ""
    mensaje = mensaje_completo
    
    if mensaje_completo.startswith("[") and "]" in mensaje_completo:
        partes = mensaje_completo.split("] ", 1)
        remitente = partes[0][1:]
        mensaje = partes[1]

    timestamp = datetime.now().strftime("%H:%M")
    
    if tipo_mensaje == "yo":
        # --- MODIFICACIÓN AQUÍ para añadir "(tú)" con su propio estilo ---
        # Se inserta en tres partes para poder aplicar diferentes estilos a cada una
        chat_area.insert(tk.END, f"{remitente} ", "nombre_mio_linea")
        chat_area.insert(tk.END, "(tú) ", "tag_tu")
        chat_area.insert(tk.END, f"({timestamp})\n", "nombre_mio_linea")
        
        chat_area.insert(tk.END, f"{mensaje}\n\n", "mi_burbuja")
        
    elif tipo_mensaje == "otro":
        chat_area.insert(tk.END, f"{remitente} ({timestamp})\n", "nombre_otro_linea")
        chat_area.insert(tk.END, f"{mensaje}\n\n", "otro_usuario_burbuja")
    else: 
        chat_area.insert(tk.END, f"{mensaje_completo}\n", "info")
        
    chat_area.config(state="disabled")
    chat_area.yview(tk.END)

def actualizar_lista_usuarios(lista_nombres):
    # --- MODIFICACIÓN AQUÍ para añadir "(tú)" en la lista de usuarios ---
    usuarios_listbox.delete(0, tk.END)
    for nombre in sorted(lista_nombres):
        if nombre:
            display_name = nombre
            if nombre == apodo:
                display_name += " (tú)"
            usuarios_listbox.insert(tk.END, display_name)

def get_private_window(contraparte):
    if contraparte in private_windows and private_windows[contraparte]['win'].winfo_exists():
        private_windows[contraparte]['win'].lift()
        return private_windows[contraparte]

    win = tk.Toplevel(root)
    win.title(f"Chat privado con {contraparte}")
    txt = scrolledtext.ScrolledText(win, wrap=tk.WORD, state="disabled", width=50, height=18)
    txt.pack(padx=8, pady=8)
    entry = tk.Entry(win, width=40)
    entry.pack(side=tk.LEFT, padx=8, pady=8, expand=True, fill=tk.X)

    def enviar_privado_cmd():
        msg = entry.get().strip()
        if not msg: return
        try:
            cliente.sendall(b'P' + contraparte.ljust(64).encode('utf-8') + len(msg.encode('utf-8')).to_bytes(4, 'big') + msg.encode('utf-8'))
            entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar privado: {e}", parent=win)

    btn = tk.Button(win, text="Enviar", command=enviar_privado_cmd)
    btn.pack(side=tk.LEFT, padx=6, pady=8)
    
    def on_private_close():
        del private_windows[contraparte]
        win.destroy()
    win.protocol("WM_DELETE_WINDOW", on_private_close)

    def write_private_line(texto_formateado):
        txt.config(state="normal")
        txt.insert(tk.END, texto_formateado + "\n")
        txt.yview(tk.END)
        txt.config(state="disabled")

    private_windows[contraparte] = {'win': win, 'write': write_private_line}
    return private_windows[contraparte]

def escuchar_servidor():
    while True:
        try:
            tipo_b = cliente.recv(1)
            if not tipo_b: break
            tipo = tipo_b.decode('utf-8')

            if tipo == 'M':
                data = cliente.recv(1024).decode('utf-8')
                if not data: break
                remitente = data.split("]")[0][1:]
                if remitente == apodo:
                    escribir_en_chat(data, "yo")
                else:
                    escribir_en_chat(data, "otro")
            
            elif tipo == 'L':
                data = cliente.recv(4096).decode('utf-8')
                actualizar_lista_usuarios(data.split(','))

            elif tipo == 'P':
                remitente = cliente.recv(64).decode('utf-8').strip()
                ln = int.from_bytes(cliente.recv(4), 'big')
                msg = cliente.recv(ln).decode('utf-8') if ln > 0 else ""
                pv = get_private_window(remitente)
                timestamp = datetime.now().strftime("%H:%M")
                pv['write'](f"[{remitente}] ({timestamp}): {msg}")

            elif tipo == 'E': 
                destinatario = cliente.recv(64).decode('utf-8').strip()
                ln = int.from_bytes(cliente.recv(4), 'big')
                msg = cliente.recv(ln).decode('utf-8') if ln > 0 else ""
                pv = get_private_window(destinatario)
                timestamp = datetime.now().strftime("%H:%M")
                # --- MODIFICACIÓN AQUÍ para añadir "(tú)" en el chat privado ---
                pv['write'](f"[{apodo} (tú)] ({timestamp}): {msg}")
            
            elif tipo == 'F':
                nombre_archivo = cliente.recv(256).decode('utf-8').strip()
                tamaño = int.from_bytes(cliente.recv(8), 'big')
                escribir_en_chat(f"[Recibiendo archivo: {nombre_archivo}]")
                if not os.path.exists("descargas"): os.makedirs("descargas")
                ruta = os.path.join("descargas", nombre_archivo)
                with open(ruta, 'wb') as f:
                    leidos = 0
                    while leidos < tamaño:
                        chunk = cliente.recv(min(4096, tamaño - leidos))
                        if not chunk: break
                        f.write(chunk)
                        leidos += len(chunk)
                escribir_en_chat(f"[Archivo '{nombre_archivo}' guardado en 'descargas']")

        except Exception as e:
            print(e)
            escribir_en_chat("[ERROR: Se ha perdido la conexión con el servidor.]")
            break

def enviar_mensaje(event=None):
    msg = entry_msg.get().strip()
    if msg:
        try:
            cliente.sendall(b'M' + msg.encode('utf-8'))
            entry_msg.delete(0, tk.END)
        except:
            escribir_en_chat("[No se pudo enviar el mensaje]")

def iniciar_privado(event=None):
    seleccion = usuarios_listbox.curselection()
    if not seleccion:
        messagebox.showinfo("Chat Privado", "Por favor, selecciona un usuario de la lista para chatear.", parent=root)
        return
    
    destinatario_display = usuarios_listbox.get(seleccion[0])
    # Limpiamos el "(tú)" si existe, para obtener el nombre real
    destinatario = destinatario_display.replace(" (tú)", "")
    
    if destinatario == apodo:
        messagebox.showwarning("Acción no permitida", "No puedes iniciar un chat privado contigo mismo.", parent=root)
        return
    
    get_private_window(destinatario)

def enviar_archivo():
    ruta = filedialog.askopenfilename()
    if not ruta: return
    try:
        nombre = os.path.basename(ruta)
        escribir_en_chat(f"[Enviando archivo: {nombre}]")
        cliente.sendall(b'F')
        cliente.sendall(nombre.ljust(256).encode('utf-8'))
        cliente.sendall(os.path.getsize(ruta).to_bytes(8, 'big'))
        with open(ruta, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk: break
                cliente.sendall(chunk)
    except Exception as e:
        escribir_en_chat(f"[ERROR al enviar archivo: {e}]")

def on_closing():
    if cliente:
        cliente.close()
    root.destroy()

# ------------------------------------------------------------------
# --- CREACIÓN DE BOTONES Y ASIGNACIÓN DE ESTILOS (TAGS) ---
# ------------------------------------------------------------------
chat_area.tag_configure("info", foreground=COLOR_TEXTO_SECUNDARIO, justify='center', font=FONT_ITALIC_PEQUEÑA)
chat_area.tag_configure("nombre_otro_linea", font=FONT_BOLD, foreground=COLOR_PRIMARIO, justify='left')
chat_area.tag_configure("nombre_mio_linea", font=FONT_BOLD, foreground=COLOR_TEXTO_SECUNDARIO, justify='right')
# --- NUEVO TAG AÑADIDO ---
chat_area.tag_configure("tag_tu", font=FONT_TU, foreground=COLOR_PRIMARIO, justify='right')

chat_area.tag_configure("otro_usuario_burbuja", background=COLOR_BARRA_LATERAL, foreground=COLOR_TEXTO, justify='left', lmargin1=15, lmargin2=15, rmargin=120, spacing3=5, relief="groove", borderwidth=2, wrap="word")
chat_area.tag_configure("mi_burbuja", background=COLOR_MI_BURBUJA, foreground=COLOR_TEXTO_MI_MENSAJE, justify='right', lmargin1=120, lmargin2=120, rmargin=15, spacing3=5, relief="groove", borderwidth=2, wrap="word")

def crear_boton_con_icono(parent, texto_icono, comando):
    btn = tk.Button(
        parent,
        text=texto_icono,
        font=("Segoe UI Symbol", 14),
        command=comando,
        bg=COLOR_FONDO_SECUNDARIO,
        fg=COLOR_PRIMARIO,
        activebackground=COLOR_FONDO_SECUNDARIO,
        activeforeground=COLOR_PRIMARIO_ACTIVO,
        relief="flat",
        cursor="hand2"
    )
    return btn

btn_privado = crear_boton_con_icono(sidebar_frame, "👤 Iniciar Privado", lambda: iniciar_privado(None))
btn_privado.pack(fill=tk.X, padx=5, pady=5)
usuarios_listbox.bind("<Double-Button-1>", iniciar_privado) 

btn_archivo = crear_boton_con_icono(input_frame, "📎", enviar_archivo)
btn_archivo.grid(row=0, column=0, padx=5, pady=10)

btn_enviar = crear_boton_con_icono(input_frame, "➤", enviar_mensaje)
btn_enviar.grid(row=0, column=2, padx=5, pady=10)

entry_msg.bind("<Return>", enviar_mensaje)
root.protocol("WM_DELETE_WINDOW", on_closing)

# ---- Bucle de Inicio y Ejecución ----
apodo_valido = False
while not apodo_valido:
    apodo = simpledialog.askstring("Bienvenido a Sirius Chat", "Para empezar, elige tu nombre de usuario:", parent=root)
    if apodo:
        apodo_valido = True
        root.title(f"Sirius Chat - Conectado como {apodo}")
        cliente.sendall(b'A' + apodo.encode('utf-8'))
        escribir_en_chat(f"¡Bienvenido, {apodo}! Conectado al servidor.")
        threading.Thread(target=escuchar_servidor, daemon=True).start()
        root.mainloop()
    else:
        if messagebox.askokcancel("Salir", "¿Seguro que quieres salir?"):
            on_closing()
            break