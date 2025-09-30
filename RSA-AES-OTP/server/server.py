import socket
import threading
from .client_handler import ClientHandler
from common import protocol
from common import security  
import base64 

class ChatServer:
    def __init__(self, host, port, logger=print):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.nicknames = {}  # {nickname: client_handler_instance}
        self.lock = threading.Lock()
        self.logger = logger
        
        # NUEVO: Generar par de claves RSA para el servidor al iniciar
        self.logger("Generando par de claves RSA para el servidor...")
        self.rsa_private_key = security.generate_rsa_keys()
        self.rsa_public_pem = security.get_public_key_pem(self.rsa_private_key)
        self.logger("Claves RSA generadas correctamente.")

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.logger(f"Servidor escuchando en {self.host}:{self.port}...")
        while True:
            conn, addr = self.server_socket.accept()
            # MODIFICADO: Ya no pasamos la clave privada, solo la pública.
            client_handler = ClientHandler(conn, addr, self, self.rsa_public_pem)
            self.add_client(client_handler)
            client_handler.start()

    def start_in_thread(self):
        server_thread = threading.Thread(target=self.start, daemon=True)
        server_thread.start()

    def add_client(self, client):
        with self.lock:
            self.clients.append(client)

    def remove_client(self, client):
        with self.lock:
            if client in self.clients:
                self.clients.remove(client)
            try:
                if client.nickname in self.nicknames and self.nicknames[client.nickname] == client:
                    del self.nicknames[client.nickname]
            except (AttributeError, KeyError):
                pass

    def register_client(self, client, nickname):
        with self.lock:
            if client.nickname in self.nicknames and self.nicknames[client.nickname] == client:
                del self.nicknames[client.nickname]
            self.nicknames[nickname] = client

    def broadcast(self, message_bytes, source_client=None):
        # Esta función ahora solo la usaremos para mensajes que no necesitan cifrado por cliente (como la lista de usuarios)
        with self.lock:
            for client in list(self.clients):
                if client is not source_client:
                    client.send(message_bytes)
    
    def broadcast_message(self, sender_nick, content_text, source_client):
        with self.lock:
            # Iteramos sobre una copia de la lista de clientes
            for client in list(self.clients):
                # Nos aseguramos de no enviarle el mensaje a quien lo originó y de que el cliente tenga una clave de sesión
                if client is not source_client and client.session_key:
                    content_bytes = content_text.encode('utf-8')
                    # Ciframos el mensaje CON LA CLAVE DE SESIÓN DE CADA CLIENTE DESTINATARIO
                    nonce, tag, ciphertext = security.encrypt_with_aes(client.session_key, content_bytes)
                    
                    encrypted_payload = {
                        'nonce': base64.b64encode(nonce).decode('ascii'),
                        'tag': base64.b64encode(tag).decode('ascii'),
                        'ciphertext': base64.b64encode(ciphertext).decode('ascii')
                    }
                    
                    msg = protocol.create_message("public_message", sender=sender_nick, content=encrypted_payload)
                    client.send(msg)


    def broadcast_user_list(self):
        with self.lock:
            user_list = list(self.nicknames.keys())
        self.logger(f"Enviando lista de usuarios: {user_list}")
        user_list_message = protocol.create_message("user_list_update", users=user_list)
        self.broadcast(user_list_message)

    def send_private_message(self, recipient_nick, sender_nick, content_text):
        recipient_client = None
        sender_client = None
        with self.lock:
            recipient_client = self.nicknames.get(recipient_nick)
            sender_client = self.nicknames.get(sender_nick)

        content_bytes = content_text.encode('utf-8')

        # Cifrar para el destinatario
        if recipient_client and recipient_client.session_key:
            nonce, tag, ciphertext = security.encrypt_with_aes(recipient_client.session_key, content_bytes)
            encrypted_payload = {
                'nonce': base64.b64encode(nonce).decode('ascii'),
                'tag': base64.b64encode(tag).decode('ascii'),
                'ciphertext': base64.b64encode(ciphertext).decode('ascii')
            }
            msg_to_recipient = protocol.create_message("private_message", sender=sender_nick, content=encrypted_payload)
            recipient_client.send(msg_to_recipient)
            
        # Cifrar el "eco" para el que envía
        if sender_client and sender_client.session_key:
            nonce, tag, ciphertext = security.encrypt_with_aes(sender_client.session_key, content_bytes)
            encrypted_payload = {
                'nonce': base64.b64encode(nonce).decode('ascii'),
                'tag': base64.b64encode(tag).decode('ascii'),
                'ciphertext': base64.b64encode(ciphertext).decode('ascii')
            }
            echo_to_sender = protocol.create_message("private_message_echo", recipient=recipient_nick, content=encrypted_payload)
            sender_client.send(echo_to_sender)

    def relay_file(self, sender_nick, payload, source_client):
        """
        Reenvía un mensaje de archivo al destinatario correcto (público o privado).
        """
        recipient = payload.get("recipient")
        
        file_msg = protocol.create_message(
            "file_transfer",
            sender=sender_nick,
            recipient=recipient,
            filename=payload.get("filename"),
            content=payload.get("content")
        )

        if recipient == "public":
            self.broadcast(file_msg, source_client=source_client)
        else:
            with self.lock:
                recipient_client = self.nicknames.get(recipient)
            
            if recipient_client:
                recipient_client.send(file_msg)
