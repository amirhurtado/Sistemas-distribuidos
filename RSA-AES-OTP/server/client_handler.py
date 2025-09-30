import threading
from common import protocol
from common import security  
import base64 

class ClientHandler(threading.Thread):
    # MODIFICADO: El constructor ahora recibe las claves del servidor
    def __init__(self, connection, address, server, rsa_private, rsa_public_pem):
        super().__init__(daemon=True)
        self.conn = connection
        self.addr = address
        self.server = server
        self.nickname = f"user_{address[1]}"
        # NUEVO: Atributos para la seguridad
        self.server_rsa_private_key = rsa_private
        self.server_rsa_public_pem = rsa_public_pem
        self.session_key = None # Aquí guardaremos la clave AES del cliente

    def run(self):
        self.server.logger(f"[NUEVA CONEXIÓN] {self.addr} conectado.")
        try:
            # Realizar el handshake de seguridad
            if not self.perform_handshake():
                self.server.logger(f"[ERROR HANDSHAKE] Falló el intercambio de claves con {self.addr}.")
                # Si el handshake falla, la conexión se cerrará en el bloque 'finally'
                return

            # MODIFICADO: El bucle para escuchar mensajes ahora va aquí,
            # DESPUÉS de un handshake exitoso.
            while True:
                message = protocol.parse_message_from_socket(self.conn)
                if message is None:
                    break  # El cliente cerró la conexión
                self.handle_message(message)
                
        except (ConnectionResetError, ConnectionAbortedError):
            self.server.logger(f"[CONEXIÓN PERDIDA] {self.nickname} se desconectó.")
        finally:
            self.cleanup()

    
    # NUEVO: Método para gestionar el intercambio de claves RSA
    def perform_handshake(self):
        try:
            # 1. Enviar la clave pública del servidor al cliente
            self.server.logger(f"Enviando clave pública RSA a {self.addr}...")
            key_exchange_msg = protocol.create_message(
                "key_exchange_init", 
                public_key=self.server_rsa_public_pem.decode('ascii')
            )
            self.send(key_exchange_msg)

            # 2. Esperar la respuesta del cliente con la clave de sesión cifrada
            response = protocol.parse_message_from_socket(self.conn)
            if not response or response.get("type") != "key_exchange_finish":
                return False

            # MODIFICADO: Decodificar el string Base64 para obtener los bytes cifrados originales
            encrypted_key_b64 = response["payload"]["session_key"]
            encrypted_key_bytes = base64.b64decode(encrypted_key_b64)
            
            # 3. Descifrar la clave de sesión usando la clave privada del servidor
            self.session_key = security.decrypt_with_rsa(self.server_rsa_private_key, encrypted_key_bytes)
            
            self.server.logger(f"Handshake con {self.addr} completado. Clave de sesión recibida.")
            return True
        except Exception as e:
            self.server.logger(f"Error durante el handshake con {self.addr}: {e}")
            return False
        
        
    def handle_message(self, message):
        msg_type = message.get("type")
        payload = message.get("payload", {})

        if msg_type == "login":
            self.nickname = payload.get("nickname", self.nickname)
            self.server.register_client(self, self.nickname)
            self.server.logger(f"'{self.addr}' se identificó como '{self.nickname}'.")
            self.server.broadcast_user_list()

        elif msg_type in ["public_message", "private_message"]:
            # MODIFICADO: Desciframos el mensaje del cliente
            encrypted_content = payload.get("content")
            try:
                nonce = base64.b64decode(encrypted_content['nonce'])
                tag = base64.b64decode(encrypted_content['tag'])
                ciphertext = base64.b64decode(encrypted_content['ciphertext'])
                
                decrypted_bytes = security.decrypt_with_aes(self.session_key, nonce, tag, ciphertext)
                content = decrypted_bytes.decode('utf-8')
            except (ValueError, KeyError):
                self.server.logger(f"Error al descifrar mensaje de {self.nickname}.")
                return
            
            # Ahora que tenemos el texto plano, se lo pasamos al servidor para que lo reenvíe
            if msg_type == "public_message":
                self.server.broadcast_message(self.nickname, content, source_client=self)
                self.server.logger(f"[{self.nickname}] Mensaje público: {content}")
            
            elif msg_type == "private_message":
                recipient = payload.get("recipient")
                self.server.send_private_message(recipient, self.nickname, content)
                self.server.logger(f"[{self.nickname} -> {recipient}] Mensaje privado: {content}")
        
        
        elif msg_type == "file_transfer":
            recipient = payload.get("recipient")
            filename = payload.get("filename")
            self.server.logger(f"[{self.nickname} -> {recipient}] Archivo: {filename}")
            self.server.relay_file(self.nickname, payload, source_client=self)

    def send(self, message_bytes):
        try:
            self.conn.sendall(message_bytes)
        except OSError:
            self.cleanup()

    def cleanup(self):
        self.server.remove_client(self)
        try:
            self.conn.close()
        except Exception: pass
        self.server.logger(f"[DESCONEXIÓN] {self.nickname} se ha desconectado.")
        self.server.broadcast_user_list()
