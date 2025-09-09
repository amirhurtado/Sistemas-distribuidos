import threading
from common import protocol

class ClientHandler(threading.Thread):
    def __init__(self, connection, address, server):
        super().__init__(daemon=True)
        self.conn = connection
        self.addr = address
        self.server = server
        self.nickname = f"user_{address[1]}"

    def run(self):
        self.server.logger(f"[NUEVA CONEXIÓN] {self.addr} conectado.")
        try:
            while True:
                message = protocol.parse_message_from_socket(self.conn)
                if message is None: break
                self.handle_message(message)
        except (ConnectionResetError, ConnectionAbortedError):
            self.server.logger(f"[CONEXIÓN PERDIDA] {self.nickname} se desconectó.")
        finally:
            self.cleanup()

    def handle_message(self, message):
        msg_type = message.get("type")
        payload = message.get("payload", {})

        if msg_type == "login":
            self.nickname = payload.get("nickname", self.nickname)
            self.server.register_client(self, self.nickname)
            self.server.logger(f"'{self.addr}' se identificó como '{self.nickname}'.")
            self.server.broadcast_user_list()

        elif msg_type == "public_message":
            content = payload.get("content")
            msg = protocol.create_message("public_message", sender=self.nickname, content=content)
            self.server.broadcast(msg, source_client=self)
            self.server.logger(f"[{self.nickname}] Mensaje público: {content}")

        elif msg_type == "private_message":
            recipient = payload.get("recipient")
            content = payload.get("content")
            self.server.send_private_message(recipient, self.nickname, content)
            self.server.logger(f"[{self.nickname} -> {recipient}] Mensaje privado.")
        
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
