import socket
import threading
import os
import tkinter as tk
from tkinter import filedialog, simpledialog, scrolledtext, messagebox, Listbox

HOST = "192.168.1.105" # Asegúrate que esta sea la IP del servidor
PORT = 5000

# ---- Variables Globales ----
apodo = ""
lista_usuarios_conectados = []

# ---- Configuración del Socket ----
try:
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.connect((HOST, PORT))
except ConnectionRefusedError:
    messagebox.showerror("Error de Conexión", f"No se pudo conectar al servidor en {HOST}:{PORT}. ¿Está el servidor en línea?")
    raise SystemExit

# ---- Configuración de la GUI Principal ----
root = tk.Tk()
root.title("Cliente Chat")

chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state="disabled", width=60, height=20)
chat_area.pack(padx=10, pady=10)

entry_msg = tk.Entry(root, width=50)
entry_msg.pack(side=tk.LEFT, padx=10, pady=5, expand=True, fill=tk.X)

def escribir_en_chat(texto):
    chat_area.config(state="normal")
    chat_area.insert(tk.END, texto + "\n")
    chat_area.yview(tk.END)
    chat_area.config(state="disabled")

# ---- Ventanas de Chat Privado ----
private_windows = {}  # {apodo_contraparte: {'win': Toplevel, ...}}

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
        if not msg:
            return
        try:
            destinatario = contraparte
            cliente.sendall(b'P' + destinatario.ljust(64).encode('utf-8') + len(msg.encode('utf-8')).to_bytes(4, 'big') + msg.encode('utf-8'))
            entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar privado: {e}")

    btn = tk.Button(win, text="Enviar", command=enviar_privado_cmd)
    btn.pack(side=tk.LEFT, padx=6, pady=8)

    def on_private_close():
        del private_windows[contraparte]
        win.destroy()
    win.protocol("WM_DELETE_WINDOW", on_private_close)

    def write_private_line(s):
        txt.config(state="normal")
        txt.insert(tk.END, s + "\n")
        txt.yview(tk.END)
        txt.config(state="disabled")

    private_windows[contraparte] = {'win': win, 'text': txt, 'entry': entry, 'write': write_private_line}
    return private_windows[contraparte]

# ---- Lógica de Conexión y Recepción ----
apodo = simpledialog.askstring("Apodo", "Escribe tu apodo:", parent=root)
if not apodo:
    messagebox.showerror("Error", "Debes ingresar un apodo.")
    root.destroy()
    cliente.close()
    raise SystemExit
root.title(f"Cliente Chat - {apodo}")
cliente.sendall(b'A' + apodo.encode('utf--8'))

def escuchar_servidor():
    global lista_usuarios_conectados
    while True:
        try:
            tipo_b = cliente.recv(1)
            if not tipo_b:
                break
            tipo = tipo_b.decode('utf-8')

            if tipo == 'M':
                data = cliente.recv(1024).decode('utf-8')
                if not data: break
                escribir_en_chat(data)

            elif tipo == 'F':
                nombre_archivo = cliente.recv(256).decode('utf-8').strip()
                tamaño = int.from_bytes(cliente.recv(8), 'big')
                escribir_en_chat(f"[ARCHIVO] Recibiendo: {nombre_archivo} ({tamaño} bytes)")
                if not os.path.exists("descargas"):
                    os.makedirs("descargas")
                ruta = os.path.join("descargas", nombre_archivo)
                with open(ruta, 'wb') as f:
                    leidos = 0
                    while leidos < tamaño:
                        chunk = cliente.recv(min(4096, tamaño - leidos))
                        if not chunk: break
                        f.write(chunk)
                        leidos += len(chunk)
                escribir_en_chat(f"[ARCHIVO] Descarga completada: {nombre_archivo}")

            elif tipo == 'P':
                contraparte = cliente.recv(64).decode('utf-8').strip()
                ln = int.from_bytes(cliente.recv(4), 'big')
                msg = cliente.recv(ln).decode('utf-8') if ln > 0 else ""
                pv = get_private_window(contraparte)
                pv['write'](f"[{contraparte}] {msg}")

            elif tipo == 'L':
                data = cliente.recv(4096).decode('utf-8')
                lista_usuarios_conectados = data.split(',')
                escribir_en_chat(f"[SISTEMA] Usuarios conectados: {', '.join(lista_usuarios_conectados)}")

        except Exception as e:
            escribir_en_chat(f"[ERROR DE CONEXIÓN] {e}")
            break
    cliente.close()

threading.Thread(target=escuchar_servidor, daemon=True).start()

# ---- Lógica de Envío ----
def enviar_mensaje():
    msg = entry_msg.get().strip()
    if msg:
        try:
            cliente.sendall(b'M' + msg.encode('utf-8'))
            entry_msg.delete(0, tk.END)
        except:
            escribir_en_chat("[ERROR] No se pudo enviar el mensaje")

def iniciar_privado():
    lista_filtrada = [u for u in lista_usuarios_conectados if u != apodo and u]
    if not lista_filtrada:
        messagebox.showinfo("Chat Privado", "No hay otros usuarios conectados para iniciar un chat.")
        return

    win_seleccion = tk.Toplevel(root)
    win_seleccion.title("Iniciar Chat Privado")
    win_seleccion.geometry("250x300")
    win_seleccion.resizable(False, False)

    tk.Label(win_seleccion, text="Selecciona un usuario:").pack(pady=10)

    listbox = Listbox(win_seleccion, selectmode=tk.SINGLE)
    listbox.pack(expand=True, fill=tk.BOTH, padx=10)
    for usuario in lista_filtrada:
        listbox.insert(tk.END, usuario)

    def on_select():
        seleccion = listbox.curselection()
        if not seleccion:
            messagebox.showwarning("Selección", "Por favor, selecciona un usuario.", parent=win_seleccion)
            return
        
        destinatario = listbox.get(seleccion[0])
        win_seleccion.destroy()
        get_private_window(destinatario)

    btn_seleccionar = tk.Button(win_seleccion, text="Chatear", command=on_select)
    btn_seleccionar.pack(pady=10)
    win_seleccion.transient(root)
    win_seleccion.grab_set()
    root.wait_window(win_seleccion)

def enviar_archivo():
    ruta = filedialog.askopenfilename()
    if not ruta: return
    try:
        nombre = os.path.basename(ruta)
        tam = os.path.getsize(ruta)
        cliente.sendall(b'F' + nombre.ljust(256).encode('utf-8') + tam.to_bytes(8, 'big'))
        with open(ruta, 'rb') as f:
            cliente.sendfile(f)
        escribir_en_chat(f"[ARCHIVO] Enviado: {nombre}")
    except Exception as e:
        escribir_en_chat(f"[ERROR] No se pudo enviar el archivo: {e}")

# ---- Configuración de Botones y Cierre ----
btn_enviar = tk.Button(root, text="Enviar", command=enviar_mensaje)
btn_enviar.pack(side=tk.LEFT, padx=5, pady=5)
entry_msg.bind("<Return>", lambda event: enviar_mensaje())

btn_priv = tk.Button(root, text="Privado...", command=iniciar_privado)
btn_priv.pack(side=tk.LEFT, padx=5, pady=5)

btn_archivo = tk.Button(root, text="Adjuntar", command=enviar_archivo)
btn_archivo.pack(side=tk.LEFT, padx=5, pady=5)

def on_closing():
    try:
        cliente.close()
    except:
        pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()