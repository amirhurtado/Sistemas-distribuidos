import socket
import threading
import os
import tkinter as tk
from tkinter import filedialog, simpledialog, scrolledtext, messagebox

HOST = "10.253.23.135"
PORT = 5000

cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cliente.connect((HOST, PORT))

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

# ---- Ventanas privadas ----
private_windows = {}  # {apodo_contraparte: {'win': Toplevel, 'text': ScrolledText, 'entry': Entry}}

def get_private_window(contraparte):
    if contraparte in private_windows:
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
            # Protocolo 'P' = destinatario(64) + len + msg
            destinatario = contraparte
            cliente.sendall(b'P' + destinatario.ljust(64).encode('utf-8') + len(msg.encode('utf-8')).to_bytes(4, 'big') + msg.encode('utf-8'))
            entry.delete(0, tk.END)
            # Importante: NO escribimos aquí; esperamos el eco del servidor para evitar duplicados
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar privado: {e}")

    btn = tk.Button(win, text="Enviar", command=enviar_privado_cmd)
    btn.pack(side=tk.LEFT, padx=6, pady=8)

    def write_private_line(s):
        txt.config(state="normal")
        txt.insert(tk.END, s + "\n")
        txt.yview(tk.END)
        txt.config(state="disabled")

    private_windows[contraparte] = {'win': win, 'text': txt, 'entry': entry, 'write': write_private_line}
    return private_windows[contraparte]

# ---- Apodo ----
apodo = simpledialog.askstring("Apodo", "Escribe tu apodo:", parent=root)
if not apodo:
    messagebox.showerror("Error", "Debes ingresar un apodo.")
    root.destroy()
    cliente.close()
    raise SystemExit

cliente.sendall(b'A' + apodo.encode('utf-8'))

# ---- Recepción ----
def escuchar_servidor():
    while True:
        try:
            tipo_b = cliente.recv(1)
            if not tipo_b:
                break
            tipo = tipo_b.decode('utf-8')

            if tipo == 'M':
                data = cliente.recv(1024).decode('utf-8')
                if not data:
                    break
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
                        if not chunk:
                            break
                        f.write(chunk)
                        leidos += len(chunk)
                escribir_en_chat(f"[ARCHIVO] Descarga completada: {nombre_archivo}")

            elif tipo == 'P':
                # formato recibido: contraparte(64) + len + msg
                contraparte = cliente.recv(64).decode('utf-8').strip()
                ln = int.from_bytes(cliente.recv(4), 'big')
                msg = cliente.recv(ln).decode('utf-8') if ln > 0 else ""
                # Abrir/obtener ventana privada y mostrar
                pv = get_private_window(contraparte)
                pv['write'](f"[{contraparte}] {msg}")

        except Exception as e:
            escribir_en_chat(f"[ERROR] {e}")
            break

threading.Thread(target=escuchar_servidor, daemon=True).start()

# ---- Envío público ----
def enviar_mensaje():
    msg = entry_msg.get().strip()
    if msg:
        try:
            cliente.sendall(b'M' + msg.encode('utf-8'))
            entry_msg.delete(0, tk.END)
            # Si prefieres verlo de inmediato localmente: escribir_en_chat(f"[Tú] {msg}")
        except:
            escribir_en_chat("[ERROR] No se pudo enviar el mensaje")

btn_enviar = tk.Button(root, text="Enviar", command=enviar_mensaje)
btn_enviar.pack(side=tk.LEFT, padx=5, pady=5)

# Botón para iniciar un chat privado (elige apodo destino)
def iniciar_privado():
    dest = simpledialog.askstring("Privado", "Apodo del destinatario:", parent=root)
    if dest:
        get_private_window(dest)  # solo abre la ventana; el envío se hace desde esa ventana

btn_priv = tk.Button(root, text="Privado...", command=iniciar_privado)
btn_priv.pack(side=tk.LEFT, padx=5, pady=5)

# Enviar archivo público (no privados en esta versión)
def enviar_archivo():
    ruta = filedialog.askopenfilename()
    if not ruta:
        return
    try:
        nombre = os.path.basename(ruta)
        tam = os.path.getsize(ruta)
        cliente.sendall(b'F')
        cliente.sendall(nombre.ljust(256).encode('utf-8'))
        cliente.sendall(tam.to_bytes(8, 'big'))
        with open(ruta, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                cliente.sendall(chunk)
        escribir_en_chat(f"[ARCHIVO] Enviado: {nombre}")
    except Exception as e:
        escribir_en_chat(f"[ERROR] {e}")

btn_archivo = tk.Button(root, text="Enviar archivo", command=enviar_archivo)
btn_archivo.pack(side=tk.LEFT, padx=5, pady=5)

def on_closing():
    try:
        cliente.close()
    except:
        pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
