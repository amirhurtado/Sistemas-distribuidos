import socket
import threading
from common import protocol
from common import security  
import base64

class NetworkHandler:
    def __init__(self, on_message_received, on_server_disconnect):
        self.socket = None
        self.on_message_received = on_message_received
        self.on_server_disconnect = on_server_disconnect
        self.is_listening = False
        self.session_key = None  # NUEVO: Para guardar la clave de sesión AES

    def connect(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            
            # MODIFICADO: Realizar handshake ANTES de empezar a escuchar
            if not self.perform_handshake():
                self.on_server_disconnect("Fallo en el handshake de seguridad.")
                return False

            self.is_listening = True
            listen_thread = threading.Thread(target=self.listen, daemon=True)
            listen_thread.start()
            return True
        except Exception as e:
            print(f"Error de conexión: {e}")
            return False

    # NUEVO: Lógica del cliente para el handshake
    def perform_handshake(self):
        try:
            # 1. Esperar la clave pública del servidor
            server_msg = protocol.parse_message_from_socket(self.socket)
            if not server_msg or server_msg.get("type") != "key_exchange_init":
                return False
            
            server_public_key_pem = server_msg["payload"]["public_key"].encode('ascii')

            # 2. Generar una clave de sesión (para AES)
            self.session_key = security.generate_session_key()

            # 3. Cifrar la clave de sesión con la pública del servidor
            encrypted_session_key_bytes = security.encrypt_with_rsa(server_public_key_pem, self.session_key)

            # MODIFICADO: Codificar los bytes cifrados en Base64 para un transporte seguro
            encrypted_session_key_b64 = base64.b64encode(encrypted_session_key_bytes).decode('ascii')

            # 4. Enviar la clave de sesión cifrada (ahora como string Base64) de vuelta al servidor
            response_msg = protocol.create_message(
                "key_exchange_finish",
                session_key=encrypted_session_key_b64 # Enviar el string Base64
            )
            self.socket.sendall(response_msg)
            print("Handshake completado, canal seguro establecido.")
            return True
        except Exception as e:
            print(f"Error durante el handshake: {e}")
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
