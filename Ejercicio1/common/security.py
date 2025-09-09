from cryptography.fernet import Fernet
import os

KEY_FILE = "client_secret.key"

def generate_key():
    """Genera una clave para el cifrado y la guarda en un archivo."""
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)
    return key

def load_key():
    """
    Carga la clave desde el archivo. Si no existe, la crea.
    NOTA: En una aplicación real, la gestión de claves es un tema de seguridad
    crítico. Esto es una simplificación.
    """
    if not os.path.exists(KEY_FILE):
        return generate_key()
    with open(KEY_FILE, "rb") as key_file:
        return key_file.read()

_key = load_key()
_cipher_suite = Fernet(_key)

def encrypt_message(message: str) -> bytes:
    """Cifra un mensaje string y devuelve bytes."""
    return _cipher_suite.encrypt(message.encode('utf-8'))

def decrypt_message(encrypted_message: bytes) -> str:
    """Descifra un mensaje en bytes y devuelve un string."""
    try:
        return _cipher_suite.decrypt(encrypted_message).decode('utf-8')
    except Exception:
        return "[Mensaje ilegible]"
