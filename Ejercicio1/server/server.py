import socket
import threading
from .client_handler import ClientHandler
from common import protocol

class ChatServer:
    def __init__(self, host, port, logger=print):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.nicknames = {}  # {nickname: client_handler_instance}
        self.lock = threading.Lock()
        self.logger = logger

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.logger(f"Servidor escuchando en {self.host}:{self.port}...")
        while True:
            conn, addr = self.server_socket.accept()
            client_handler = ClientHandler(conn, addr, self)
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
        with self.lock:
            for client in list(self.clients):
                if client is not source_client:
                    client.send(message_bytes)

    def broadcast_user_list(self):
        with self.lock:
            user_list = list(self.nicknames.keys())
        self.logger(f"Enviando lista de usuarios: {user_list}")
        user_list_message = protocol.create_message("user_list_update", users=user_list)
        self.broadcast(user_list_message)

    def send_private_message(self, recipient_nick, sender_nick, content):
        with self.lock:
            recipient_client = self.nicknames.get(recipient_nick)
            sender_client = self.nicknames.get(sender_nick)
        if recipient_client:
            msg_to_recipient = protocol.create_message("private_message", sender=sender_nick, content=content)
            recipient_client.send(msg_to_recipient)
        if sender_client:
            echo_to_sender = protocol.create_message("private_message_echo", recipient=recipient_nick, content=content)
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
