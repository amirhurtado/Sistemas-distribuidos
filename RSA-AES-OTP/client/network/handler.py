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

        print("Generando par de claves RSA para el cliente...")
        self.rsa_private_key = security.generate_rsa_keys()
        self.rsa_public_pem = security.get_public_key_pem(self.rsa_private_key)
        self.server_rsa_public_pem = None # Para guardar la clave del servidor
        print("Claves de cliente generadas.")

    def connect(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            
            # El handshake sigue siendo el primer paso
            if not self.perform_rsa_exchange():
                self.on_server_disconnect("Fallo en el intercambio de claves RSA.")
                return False

            # El resto de la lógica de conexión no cambia
            # NOTA: Por ahora, el hilo de escucha NO se inicia aquí. Lo haremos después del OTP.
            print("Fase 1 (Intercambio RSA) completada con éxito.")
            return True # La conexión fue exitosa
        except Exception as e:
            print(f"Error de conexión: {e}")
            return False
     

    def perform_rsa_exchange(self):
        try:
            # 1. El Cliente envía su clave pública PRIMERO.
            print("Enviando clave pública del cliente al servidor...")
            client_key_msg = protocol.create_message(
                "client_public_key",
                public_key=self.rsa_public_pem.decode('ascii')
            )
            self.socket.sendall(client_key_msg)

            # 2. El Cliente espera recibir la clave pública del Servidor.
            print("Esperando clave pública del servidor...")
            server_msg = protocol.parse_message_from_socket(self.socket)
            if not server_msg or server_msg.get("type") != "server_public_key":
                print("No se recibió una respuesta válida del servidor.")
                return False
            
            self.server_rsa_public_pem = server_msg["payload"]["public_key"].encode('ascii')
            print("Clave pública del servidor recibida.")
            return True

        except Exception as e:
            print(f"Error durante el intercambio de claves RSA: {e}")
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
