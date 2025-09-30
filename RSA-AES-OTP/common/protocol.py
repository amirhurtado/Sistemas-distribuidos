import json
import base64

def create_message(msg_type, **payload):
    """
    Crea un mensaje JSON estandarizado, lo codifica a bytes y le prefija su longitud.
    """
    message = {
        "type": msg_type,
        "payload": payload
    }
    json_message = json.dumps(message)
    return len(json_message).to_bytes(4, 'big') + json_message.encode('utf-8')

def parse_message_from_socket(sock):
    """
    Lee un mensaje completo desde un socket, usando el prefijo de longitud.
    """
    raw_msglen = sock.recv(4)
    if not raw_msglen:
        return None
    msg_len = int.from_bytes(raw_msglen, 'big')
    
    data = bytearray()
    while len(data) < msg_len:
        packet = sock.recv(min(4096, msg_len - len(data)))
        if not packet:
            return None
        data.extend(packet)
        
    return json.loads(data.decode('utf-8'))

def create_login_message(nickname):
    return create_message("login", nickname=nickname)

def create_public_message(text):
    return create_message("public_message", content=text)

def create_private_message(recipient, text):
    return create_message("private_message", recipient=recipient, content=text)

def create_file_message(recipient, filename, file_content_bytes):
    """
    Crea un mensaje para enviar un archivo.
    El contenido del archivo se codifica en Base64 para que sea seguro para JSON.
    """
    encoded_content = base64.b64encode(file_content_bytes).decode('ascii')
    return create_message(
        "file_transfer",
        recipient=recipient,
        filename=filename,
        content=encoded_content
    )
