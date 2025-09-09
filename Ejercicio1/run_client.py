import tkinter as tk
from tkinter import simpledialog, messagebox
import os
import base64
from client.gui.manager import GuiManager
from client.network.handler import NetworkHandler
from client.persistence import LogManager


class ChatApplication:
    def __init__(self, root):
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.nickname = ""

        self.conversations = {"public": []}
        self.log_manager = None

        gui_callbacks = {
            "send_message": self.send_message,
            "send_file": self.send_file,
            "start_private_chat": self.start_private_chat,
            "switch_chat_view": self.switch_chat_view,
        }

        self.gui = GuiManager(root, gui_callbacks)
        self.network = NetworkHandler(
            self.handle_server_message, self.handle_disconnect
        )

    def start(self):
        if not self.network.connect("127.0.0.1", 5000):
            messagebox.showerror("Error", "No se pudo conectar al servidor.")
            self.shutdown()
            return

        self.prompt_for_nickname()

        if self.nickname:
            self.log_manager = LogManager(self.nickname)
            self.conversations["public"] = self.log_manager.load_conversation("public")
            self.root.deiconify()
            self.switch_chat_view("public")
            self.root.mainloop()
        else:
            self.shutdown()

    def prompt_for_nickname(self):
        self.root.withdraw()
        nickname = simpledialog.askstring(
            "Bienvenido", "Elige tu nombre de usuario:", parent=self.root
        )
        if nickname:
            self.nickname = nickname
            self.gui.nickname = nickname
            self.root.title(f"Sirius Chat - Conectado como {self.nickname}")
            self.network.send("login", nickname=self.nickname)
            self._add_system_message(
                "public", f"¡Bienvenido, {self.nickname}! Conectado al servidor."
            )
        else:
            self.nickname = ""

    def send_message(self, recipient, content):
        if recipient == "public":
            self.network.send("public_message", recipient="public", content=content)
            msg = {"type": "message", "sender": self.nickname, "content": content}
            self.conversations.setdefault("public", []).append(msg)
            if self.gui.active_chat == "public":
                self.gui.add_message_to_view(msg)
        else:
            self.network.send("private_message", recipient=recipient, content=content)

    def send_file(self, recipient, filepath):
        try:
            filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                content_bytes = f.read()
            
            b64_content = base64.b64encode(content_bytes).decode("ascii")

            self.network.send(
                "file_transfer",
                recipient=recipient,
                filename=filename,
                content=b64_content,
            )

            contact = recipient
            msg = {
                "type": "file",
                "sender": self.nickname,
                "filename": filename,
                "content": b64_content,
            }
            self.conversations.setdefault(contact, []).append(msg)

            if self.gui.active_chat == contact:
                self.gui.add_message_to_view(msg)

        except Exception as e:
            messagebox.showerror("Error de Envío", f"No se pudo enviar el archivo: {e}")

    def start_private_chat(self, contact_name):
        if contact_name not in self.conversations:
            self.conversations[contact_name] = self.log_manager.load_conversation(
                contact_name
            )
        self.gui.add_conversation_to_list(contact_name)
        self.switch_chat_view(contact_name)

    def switch_chat_view(self, contact_name):
        self.gui.active_chat = contact_name
        messages = self.conversations.get(contact_name, [])
        self.gui.display_conversation(messages)

    def handle_server_message(self, msg_type, payload):
        self.root.after(0, self._process_message, msg_type, payload)

    def _process_message(self, msg_type, payload):
        if msg_type == "public_message":
            sender = payload.get("sender", "Anónimo")
            content = payload.get("content", "")
            msg = {"type": "message", "sender": sender, "content": content}
            self.conversations.setdefault("public", []).append(msg)
            if self.gui.active_chat == "public":
                self.gui.add_message_to_view(msg)

        elif msg_type == "private_message":
            sender = payload["sender"]
            content = payload["content"]
            msg = {"type": "message", "sender": sender, "content": content}
            self.start_private_chat(sender)
            self.conversations.setdefault(sender, []).append(msg)
            if self.gui.active_chat == sender:
                self.gui.add_message_to_view(msg)

        elif msg_type == "private_message_echo":
            recipient = payload["recipient"]
            content = payload["content"]
            msg = {"type": "message", "sender": self.nickname, "content": content}
            self.start_private_chat(recipient)
            self.conversations.setdefault(recipient, []).append(msg)
            if self.gui.active_chat == recipient:
                self.gui.add_message_to_view(msg)

        elif msg_type == "file_transfer":
            sender = payload["sender"]
            recipient = payload.get("recipient", "public")
            filename = payload["filename"]
            b64_content = payload["content"]

            contact = "public"
            if recipient != "public":
                contact = sender if recipient == self.nickname else recipient
            
            self.start_private_chat(contact)

            msg = {
                "type": "file",
                "sender": sender,
                "filename": filename,
                "content": b64_content,
            }
            self.conversations.setdefault(contact, []).append(msg)

            if self.gui.active_chat == contact:
                self.gui.add_message_to_view(msg)

        elif msg_type == "user_list_update":
            self.gui.update_user_list(payload["users"])

    def handle_disconnect(self, reason):
        self.root.after(0, self.gui.add_system_message, f"[DESCONECTADO] {reason}")
        self.root.after(0, messagebox.showwarning, "Desconectado", reason)

    def shutdown(self):
        if self.log_manager:
            for contact, messages in self.conversations.items():
                self.log_manager.save_conversation(contact, messages)
        self.network.disconnect()
        self.root.destroy()

    def _add_system_message(self, contact, content):
        self.conversations.setdefault(contact, []).append(
            {"type": "system", "content": content, "recipient": contact}
        )


if __name__ == "__main__":
    main_root = tk.Tk()
    app = ChatApplication(main_root)
    app.start()
