import tkinter as tk
from tkinter import simpledialog, messagebox
import os
import base64
from client.gui.manager import GuiManager
from client.network.handler import NetworkHandler
from client.persistence import LogManager

from common import protocol
from common import security


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
        
        # Ocultamos la ventana hasta que todo el proceso termine
        self.root.withdraw()
        
        # --- NUEVO: Inicia la Fase 2 de Autenticación OTP ---
        if not self.perform_otp_authentication():
            messagebox.showerror("Error de Autenticación", "No se pudo verificar la identidad con el servidor.")
            self.shutdown()
            return
            
        print("¡Autenticación OTP exitosa! Listo para la Fase 3.")

    def perform_otp_authentication(self):
        try:
            # 1. Espera el reto del servidor
            print("Esperando reto OTP del servidor...")
            challenge_msg = protocol.parse_message_from_socket(self.network.socket)
            if not challenge_msg or challenge_msg.get("type") != "otp_challenge":
                return False

            # 2. Descifra el reto con la CLAVE PRIVADA DEL CLIENTE
            encrypted_challenge = base64.b64decode(challenge_msg["payload"]["challenge"])
            decrypted_otp = security.decrypt_with_rsa(self.network.rsa_private_key, encrypted_challenge).decode('utf-8')

            # 3. Muestra el código al usuario y le pide que lo re-ingrese
            messagebox.showinfo("Reto de Seguridad (OTP)", f"El servidor te ha enviado un código: {decrypted_otp}\n\nIntrodúcelo a continuación para verificar tu identidad.")
            user_response = simpledialog.askstring("Respuesta de Seguridad", "Escribe el código que acabas de ver:", parent=self.root)

            if not user_response:
                return False

            # 4. Cifra la respuesta del usuario con la CLAVE PÚBLICA DEL SERVIDOR
            encrypted_response = security.encrypt_with_rsa(self.network.server_rsa_public_pem, user_response.encode('utf-8'))
            
            # 5. Envía la respuesta cifrada al servidor
            response_msg = protocol.create_message(
                "otp_response",
                response=base64.b64encode(encrypted_response).decode('ascii')
            )
            self.network.socket.sendall(response_msg)

            # 6. Espera la confirmación final del servidor
            final_msg = protocol.parse_message_from_socket(self.network.socket)
            return final_msg and final_msg.get("type") == "auth_success"

        except Exception as e:
            print(f"Excepción durante la autenticación OTP: {e}")
            return False

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
        # MODIFICADO: Ahora ciframos el mensaje antes de enviarlo
        if self.network.session_key:
            content_bytes = content.encode('utf-8')
            
            # 1. Cifrar el contenido
            nonce, tag, ciphertext = security.encrypt_with_aes(self.network.session_key, content_bytes)
            
            # 2. Empaquetar todo en un diccionario, codificado en Base64
            encrypted_payload = {
                'nonce': base64.b64encode(nonce).decode('ascii'),
                'tag': base64.b64encode(tag).decode('ascii'),
                'ciphertext': base64.b64encode(ciphertext).decode('ascii')
            }
            
            if recipient == "public":
                self.network.send("public_message", content=encrypted_payload)
                # La lógica para mostrar tu propio mensaje no cambia
                msg = {"type": "message", "sender": self.nickname, "content": content}
                self.conversations.setdefault("public", []).append(msg)
                if self.gui.active_chat == "public":
                    self.gui.add_message_to_view(msg)
            else:
                self.network.send("private_message", recipient=recipient, content=encrypted_payload)
        else:
            messagebox.showerror("Error", "No se ha establecido una sesión segura.")

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
        # --- INICIO DE LA SECCIÓN MODIFICADA ---
        # Si el mensaje es de texto, primero debemos descifrarlo.
        if msg_type in ["public_message", "private_message", "private_message_echo"]:
            # Determinar quién envía y quién recibe
            sender = payload.get("sender", self.nickname if msg_type == "private_message_echo" else "Anónimo")
            recipient = payload.get("recipient", "public")
            
            
            encrypted_content = payload.get("content")
            print(f"DEBUG: Mensaje CIFRADO recibido de {sender}: {encrypted_content}")
            
            content = "" # Variable para guardar el texto descifrado
            
            try:
                # 1. Decodificar las partes del mensaje desde Base64
                nonce = base64.b64decode(encrypted_content['nonce'])
                tag = base64.b64decode(encrypted_content['tag'])
                ciphertext = base64.b64decode(encrypted_content['ciphertext'])
                
                # 2. Intentar descifrar con la clave de sesión
                decrypted_bytes = security.decrypt_with_aes(self.network.session_key, nonce, tag, ciphertext)
                content = decrypted_bytes.decode('utf-8')

            except (ValueError, KeyError, TypeError):
                # Si algo falla (mensaje manipulado, error de formato), mostramos un error.
                content = "[Mensaje corrupto o ilegible]"
            
            # Ahora que tenemos el 'content' en texto plano, continuamos con la lógica original
            msg = {"type": "message", "sender": sender, "content": content}

            if msg_type == "public_message":
                self.conversations.setdefault("public", []).append(msg)
                if self.gui.active_chat == "public":
                    self.gui.add_message_to_view(msg)
            
            elif msg_type == "private_message":
                self.start_private_chat(sender)
                self.conversations.setdefault(sender, []).append(msg)
                if self.gui.active_chat == sender:
                    self.gui.add_message_to_view(msg)

            elif msg_type == "private_message_echo":
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
        # MODIFICADO: Envolvemos las llamadas a la GUI en un try-except
        try:
            # Esto funcionará si la desconexión ocurre después de que la GUI esté corriendo
            self.root.after(0, self.gui._add_system_message, f"[DESCONECTADO] {reason}")
            self.root.after(0, messagebox.showwarning, "Desconectado", reason)
        except RuntimeError:
            # Esto se ejecutará si la desconexión ocurre ANTES de que inicie el mainloop
            print(f"!!! Error de GUI manejado: La desconexión ocurrió antes de que la ventana principal estuviera activa.")
            print(f"[DESCONECTADO] {reason}")


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
