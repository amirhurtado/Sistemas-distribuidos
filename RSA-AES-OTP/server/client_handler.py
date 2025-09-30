import threading
from common import protocol
from common import security  
import base64 
import random

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
        try:
            # Fase 1: Intercambio de claves RSA
            if not self.perform_rsa_exchange():
                self.server.logger(f"[ERROR FASE 1] Falló el intercambio de claves con {self.addr}.")
                return
            self.server.logger(f"[FASE 1 COMPLETADA] Intercambio de claves con {self.addr} exitoso.")

            # Fase 2: Autenticación OTP
            if not self.perform_otp_authentication():
                self.server.logger(f"[ERROR FASE 2] Falló la autenticación OTP con {self.addr}.")
                return
            self.server.logger(f"[FASE 2 COMPLETADA] Autenticación OTP con {self.addr} exitosa.")

            # --- NUEVO: Fase 3, Esperar la clave AES ---
            if not self.receive_aes_key():
                self.server.logger(f"[ERROR FASE 3] Falló la recepción de la clave AES de {self.addr}.")
                return
            self.server.logger(f"[FASE 3 COMPLETADA] Clave AES de {self.addr} recibida y establecida.")
            
            # --- NUEVO: Fase 4, Iniciar el bucle de mensajes ---
            self.server.logger(f"Canal seguro con {self.addr} establecido. Esperando mensajes...")
            while True:
                message = protocol.parse_message_from_socket(self.conn)
                if message is None: break
                self.handle_message(message)

        except (ConnectionResetError, ConnectionAbortedError):
            self.server.logger(f"[CONEXIÓN PERDIDA] {self.nickname} se desconectó.")
        finally:
            self.cleanup()

    def receive_aes_key(self):
        try:
            # 1. Espera el mensaje con la clave AES
            aes_msg = protocol.parse_message_from_socket(self.conn)
            if not aes_msg or aes_msg.get("type") != "aes_key_exchange":
                return False

            # 2. Descifra la clave AES con la CLAVE PRIVADA DEL SERVIDOR
            encrypted_key = base64.b64decode(aes_msg["payload"]["key"])
            decrypted_key = security.decrypt_with_rsa(self.server.rsa_private_key, encrypted_key)
            
            # 3. La guarda y confirma al cliente
            self.session_key = decrypted_key
            ready_msg = protocol.create_message("secure_channel_ready")
            self.send(ready_msg)
            return True
        except Exception as e:
            self.server.logger(f"Excepción en la recepción de AES: {e}")
            return False

    
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


    def perform_otp_authentication(self):
        try:
            # 1. El Servidor genera un código OTP aleatorio (el reto)
            otp_code = str(random.randint(100000, 999999))
            self.server.logger(f"Generando reto OTP '{otp_code}' para {self.addr}.")

            # 2. Cifra el reto con la CLAVE PÚBLICA DEL CLIENTE
            encrypted_otp = security.encrypt_with_rsa(self.client_rsa_public_pem, otp_code.encode('utf-8'))
            
            # 3. Envía el reto cifrado al cliente
            challenge_msg = protocol.create_message(
                "otp_challenge",
                challenge=base64.b64encode(encrypted_otp).decode('ascii')
            )
            self.send(challenge_msg)

            # 4. Espera la respuesta del cliente
            response_msg = protocol.parse_message_from_socket(self.conn)
            if not response_msg or response_msg.get("type") != "otp_response":
                return False

            # 5. Descifra la respuesta con la CLAVE PRIVADA DEL SERVIDOR
            encrypted_response = base64.b64decode(response_msg["payload"]["response"])
            # Necesitamos la clave privada del servidor, que no pasamos antes. La obtenemos del objeto server.
            decrypted_response = security.decrypt_with_rsa(self.server.rsa_private_key, encrypted_response).decode('utf-8')
            
            # 6. Compara el reto original con la respuesta descifrada
            if decrypted_response == otp_code:
                # ¡Éxito! Enviamos la confirmación.
                success_msg = protocol.create_message("auth_success")
                self.send(success_msg)
                return True
            else:
                # ¡Fallo! Enviamos el rechazo.
                fail_msg = protocol.create_message("auth_fail")
                self.send(fail_msg)
                return False

        except Exception as e:
            self.server.logger(f"Excepción en la autenticación OTP: {e}")
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
