from cryptography.fernet import Fernet
import os

# NUEVO: Importaciones para RSA y AES
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Random import get_random_bytes

KEY_FILE = "client_secret.key"

# --- Funciones existentes de Fernet (las dejamos como estaban) ---

def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)
    return key

def load_key():
    if not os.path.exists(KEY_FILE):
        return generate_key()
    with open(KEY_FILE, "rb") as key_file:
        return key_file.read()

_key = load_key()
_cipher_suite = Fernet(_key)

def encrypt_message(message: str) -> bytes:
    return _cipher_suite.encrypt(message.encode('utf-8'))

def decrypt_message(encrypted_message: bytes) -> str:
    try:
        return _cipher_suite.decrypt(encrypted_message).decode('utf-8')
    except Exception:
        return "[Mensaje ilegible]"

# ---Funciones para el handshake RSA ---
# Implementar RSA para el Intercambio de Claves: 
# Primero, necesitamos una forma segura para que el cliente y el servidor se pongan de acuerdo en una clave secreta sin
# que un posible espía pueda descubrirla. RSA (un sistema de criptografía asimétrica) es ideal para esto. El servidor
# tendrá un "candado" (clave pública) que le dará al cliente. El cliente creará una clave secreta para los mensajes, 
# la meterá en una "caja", la cerrará con el candado del servidor y se la enviará. Solo el servidor, con su "llave" (clave privada), 
# podrá abrir la caja y ver la clave secreta.

def generate_rsa_keys():
    """Genera un nuevo par de claves RSA de 2048 bits."""
    return RSA.generate(2048)

def get_public_key_pem(rsa_key):
    """Exporta la parte pública de una clave RSA a formato PEM."""
    return rsa_key.publickey().export_key()

def encrypt_with_rsa(public_key_pem, data):
    """Cifra datos usando una clave pública RSA en formato PEM."""
    recipient_key = RSA.import_key(public_key_pem)
    cipher_rsa = PKCS1_OAEP.new(recipient_key)
    return cipher_rsa.encrypt(data)

def decrypt_with_rsa(rsa_private_key, encrypted_data):
    """Descifra datos usando un objeto de clave privada RSA."""
    cipher_rsa = PKCS1_OAEP.new(rsa_private_key)
    return cipher_rsa.decrypt(encrypted_data)

# --- NUEVO: Función para generar la clave de sesión (que usaremos con AES) ---

def generate_session_key():
    """Genera una clave aleatoria de 256 bits (32 bytes) para usar con AES."""
    return get_random_bytes(32)





#AES

def encrypt_with_aes(session_key, data_bytes):
    """
    Cifra datos usando la clave de sesión AES en modo GCM.
    Devuelve nonce, tag y ciphertext, necesarios para descifrar.
    """
    # Creamos un nuevo objeto de cifrado AES con la clave de sesión
    cipher = AES.new(session_key, AES.MODE_GCM)
    
    # Ciframos los datos. El modo GCM también genera una "etiqueta" de autenticación.
    ciphertext, tag = cipher.encrypt_and_digest(data_bytes)
    
    # El "nonce" es un número único que usa el cifrador, también debemos guardarlo.
    nonce = cipher.nonce
    
    return nonce, tag, ciphertext

def decrypt_with_aes(session_key, nonce, tag, ciphertext):
    """
    Descifra datos usando la clave de sesión, el nonce y el tag.
    Si el tag no coincide (mensaje corrupto/clave incorrecta), lanzará un error.
    """
    # Creamos el objeto de cifrado con la misma clave y el mismo nonce que se usó para cifrar
    cipher = AES.new(session_key, AES.MODE_GCM, nonce=nonce)
    
    # Desciframos y verificamos. Si el tag no es correcto, esta línea fallará.
    decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)
    
    return decrypted_bytes