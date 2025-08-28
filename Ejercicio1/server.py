import socket
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

clientes = {}           # {conn: apodo}
apodos_a_conn = {}      # {apodo: conn}

# --- Utilidades ---
def send_all_file_chunked(dest_conn_list, nombre_archivo, contenido):
    try:
        size = len(contenido)
        for c in dest_conn_list:
            try:
                c.sendall(b'F')
                c.sendall(nombre_archivo.ljust(256).encode('utf-8'))
                c.sendall(size.to_bytes(8, 'big'))
                c.sendall(contenido)
            except:
                pass
    except:
        pass

def enviar_lista_clientes(gui_log):
    """
    Envía a todos los clientes conectados la lista actual de apodos.
    Mensaje: b'L' + apodo1,apodo2,apodo3...
    """
    try:
        lista = ",".join(apodos_a_conn.keys())
        payload = b'L' + lista.encode('utf-8')
        # iteramos sobre una copia de las conexiones para evitar modificaciones simultáneas
        for c in list(clientes.keys()):
            try:
                c.sendall(payload)
            except:
                # si falla el envío, se ignora aquí; el manejador del cliente limpiará en su momento
                pass
        gui_log(f"[#] Lista enviada a clientes: {lista}")
    except Exception as e:
        gui_log(f"[x] Error enviando lista de clientes: {e}")

def manejar_cliente(conn, addr, gui_log):
    apodo = None
    try:
        while True:
            tipo = conn.recv(1).decode("utf-8")
            if not tipo:
                break

            if tipo == 'A':  # Apodo
                apodo = conn.recv(1024).decode("utf-8").strip() or str(addr)
                clientes[conn] = apodo
                apodos_a_conn[apodo] = conn
                gui_log(f"[+] {apodo} se ha conectado desde {addr}")
                # Enviamos la lista actualizada a todos
                enviar_lista_clientes(gui_log)

            elif tipo == 'M':  # Mensaje público
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    break
                apodo_actual = clientes.get(conn, "Desconocido")
                mensaje = f"[{apodo_actual}] {data}"
                gui_log(mensaje)
                # reenviar a todos (incluido emisor si quieres eco uniforme)
                for c in list(clientes.keys()):
                    try:
                        c.sendall(b'M' + mensaje.encode('utf-8'))
                    except:
                        pass

            elif tipo == 'F':  # Archivo público
                nombre_archivo = conn.recv(256).decode("utf-8").strip()
                tamaño = int.from_bytes(conn.recv(8), 'big')
                apodo_actual = clientes.get(conn, "Desconocido")
                gui_log(f"[{apodo_actual}] envió archivo: {nombre_archivo} ({tamaño} bytes)")

                contenido = b''
                leidos = 0
                while leidos < tamaño:
                    chunk = conn.recv(min(4096, tamaño - leidos))
                    if not chunk:
                        break
                    contenido += chunk
                    leidos += len(chunk)

                try:
                    with open(f"recibido_{nombre_archivo}", "wb") as f:
                        f.write(contenido)
                    gui_log(f"[✔] Guardado como recibido_{nombre_archivo}")
                except Exception as e:
                    gui_log(f"[x] Error guardando archivo: {e}")

                # reenviar a todos (excepto emisor)
                dests = [c for c in list(clientes.keys()) if c != conn]
                send_all_file_chunked(dests, nombre_archivo, contenido)

            elif tipo == 'P':  # Mensaje privado
                # formato: destinatario(64) + len(4) + msg
                dest_raw = conn.recv(64)
                if not dest_raw:
                    break
                destinatario = dest_raw.decode('utf-8').strip()
                ln = int.from_bytes(conn.recv(4), 'big')
                msg = conn.recv(ln).decode('utf-8') if ln > 0 else ""

                remitente = clientes.get(conn, "Desconocido")
                gui_log(f"[Privado] {remitente} -> {destinatario}: {msg}")

                dest_conn = apodos_a_conn.get(destinatario)
                # payload al receptor: contraparte = remitente
                payload_receptor = b'P' + remitente.ljust(64).encode('utf-8') + ln.to_bytes(4, 'big') + msg.encode('utf-8')
                # eco al emisor: contraparte = destinatario
                payload_emisor = b'E' + destinatario.ljust(64).encode('utf-8') + ln.to_bytes(4, 'big') + msg.encode('utf-8')

                # enviar al receptor si existe y está conectado
                if dest_conn:
                    try:
                        dest_conn.sendall(payload_receptor)
                    except:
                        pass
                # eco al emisor para que vea su propio dm en su ventana privada
                try:
                    conn.sendall(payload_emisor)
                except:
                    pass

            elif tipo == 'L_REQ':  # si quisieras manejar peticiones puntuales (opcional)
                # ejemplo de implementación si el cliente pide explícitamente la lista
                enviar_lista_clientes(gui_log)

            else:
                # tipo desconocido: puedes loguearlo para depuración
                gui_log(f"[?] Tipo desconocido recibido: {repr(tipo)} de {addr}")

    except Exception as e:
        gui_log(f"[x] Error con {addr}: {e}")
    finally:
        try:
            conn.close()
        except:
            pass
        if conn in clientes:
            ap = clientes.pop(conn)
            apodos_a_conn.pop(ap, None)
            gui_log(f"[-] {ap} se ha desconectado")
            # actualizar lista al resto
            enviar_lista_clientes(gui_log)

def iniciar_servidor(gui_log):
    HOST = "192.168.1.105"
    PORT = 5000
    MAX_CLIENTES = 10

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(MAX_CLIENTES)
    gui_log(f"Servidor escuchando en {HOST}:{PORT}...")

    def aceptar_clientes():
        while True:
            conn, addr = server.accept()
            hilo = threading.Thread(target=manejar_cliente, args=(conn, addr, gui_log), daemon=True)
            hilo.start()
            gui_log(f"[#] Clientes activos: {threading.active_count()-2}")

    threading.Thread(target=aceptar_clientes, daemon=True).start()

# --- GUI ---
def main():
    root = tk.Tk()
    root.title("Servidor de Chat")

    text_area = ScrolledText(root, wrap=tk.WORD, width=80, height=25, state="disabled")
    text_area.pack(padx=10, pady=10)

    def gui_log(msg):
        text_area.config(state="normal")
        text_area.insert(tk.END, msg + "\n")
        text_area.see(tk.END)
        text_area.config(state="disabled")

    threading.Thread(target=iniciar_servidor, args=(gui_log,), daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()
