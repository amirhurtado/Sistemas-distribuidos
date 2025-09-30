import threading
from common import protocol
from common import security  
import base64 

class ClientHandler(threading.Thread):
    # MODIFICADO: El constructor ahora recibe las claves del servidor
    def __init__(self, connection, address, server, rsa_public_pem):
        super().__init__(daemon=True)
        self.conn = connection
        self.addr = address
        self.server = server
        self.nickname = f"user_{address[1]}"
        
        # Atributos de seguridad
        self.server_rsa_public_pem = rsa_public_pem
        self.client_rsa_public_pem = None # Para guardar la clave del cliente
        self.session_key = None 


    def run(self):
        self.server.logger(f"[NUEVA CONEXIÓN] {self.addr} iniciando Fase 1.")
        try:
            # Fase 1: Intercambio de claves RSA
            if not self.perform_rsa_exchange():
                self.server.logger(f"[ERROR FASE 1] Falló el intercambio de claves con {self.addr}.")
                return

            # Por ahora, dejamos el hilo aquí. Las Fases 2 y 3 irán a continuación.
            self.server.logger(f"[FASE 1 COMPLETADA] Intercambio de claves con {self.addr} exitoso.")
            
            # --- Aquí iría la lógica para las Fases 2, 3 y 4 ---
            # --- Por ahora, lo dejamos pendiente ---

        except (ConnectionResetError, ConnectionAbortedError):
            self.server.logger(f"[CONEXIÓN PERDIDA] {self.nickname} se desconectó.")
        finally:
            self.cleanup()

    
    def perform_rsa_exchange(self):
        try:
            # 1. El Servidor espera recibir la clave pública del Cliente.
            self.server.logger(f"Esperando clave pública de {self.addr}...")
            client_msg = protocol.parse_message_from_socket(self.conn)
            if not client_msg or client_msg.get("type") != "client_public_key":
                self.server.logger("Mensaje de cliente no válido.")
                return False
            
            self.client_rsa_public_pem = client_msg["payload"]["public_key"].encode('ascii')
            self.server.logger(f"Clave pública de {self.addr} recibida.")

            # 2. El Servidor responde con su propia clave pública.
            self.server.logger(f"Enviando clave pública del servidor a {self.addr}...")
            server_key_msg = protocol.create_message(
                "server_public_key", 
                public_key=self.server_rsa_public_pem.decode('ascii')
            )
            self.send(server_key_msg)
            return True
        except Exception as e:
            self.server.logger(f"Error durante el intercambio de claves RSA con {self.addr}: {e}")
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
