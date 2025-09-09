import socket
import threading
from common import protocol


class NetworkHandler:
    def __init__(self, on_message_received, on_server_disconnect):
        self.socket = None
        self.on_message_received = on_message_received
        self.on_server_disconnect = on_server_disconnect
        self.is_listening = False

    def connect(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.is_listening = True

            listen_thread = threading.Thread(target=self.listen, daemon=True)
            listen_thread.start()
            return True
        except Exception as e:
            print(f"Error de conexión: {e}")
            return False

    def listen(self):
        while self.is_listening:
            try:
                message = protocol.parse_message_from_socket(self.socket)
                if message is None:
                    self.is_listening = False
                    self.on_server_disconnect("El servidor cerró la conexión.")
                    break

                self.on_message_received(
                    message.get("type"), message.get("payload", {})
                )
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                self.is_listening = False
                self.on_server_disconnect("Se perdió la conexión con el servidor.")
                break

    def send(self, msg_type, **payload):
        if self.socket and self.is_listening:
            try:
                message_bytes = protocol.create_message(msg_type, **payload)
                self.socket.sendall(message_bytes)
            except OSError:
                self.is_listening = False
                self.on_server_disconnect("Error al enviar, conexión perdida.")

    def disconnect(self):
        self.is_listening = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except OSError:
                pass
            self.socket = None
