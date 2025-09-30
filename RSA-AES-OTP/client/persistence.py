import os
import json
from common import security

LOGS_DIR = "chat_logs"


class LogManager:
    def __init__(self, owner_nickname):
        self.owner = owner_nickname
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR)

    def _get_log_path(self, contact_name):
        """Genera una ruta de archivo segura para el log."""
        safe_filename = "".join(
            c for c in contact_name if c.isalnum() or c in ("-", "_")
        ).rstrip()
        return os.path.join(LOGS_DIR, f"log_{self.owner}_with_{safe_filename}.json.enc")

    def load_conversation(self, contact_name):
        """Carga, descifra y devuelve la lista de mensajes de una conversación."""
        log_path = self._get_log_path(contact_name)
        if not os.path.exists(log_path):
            return []

        with open(log_path, "rb") as f:
            encrypted_data = f.read()

        decrypted_json_string = security.decrypt_message(encrypted_data)
        return json.loads(decrypted_json_string)

    def save_conversation(self, contact_name, messages):
        """Cifra y guarda la lista de mensajes de una conversación."""
        log_path = self._get_log_path(contact_name)

        json_string = json.dumps(messages, indent=2)
        encrypted_data = security.encrypt_message(json_string)

        with open(log_path, "wb") as f:
            f.write(encrypted_data)
