#CORRER ESTE PROGRAMA, Y ABRIR EL HTML
import asyncio
import websockets

USERS = set()

async def handler(websocket, path=None):
    # obtener path de forma robusta (según versión de websockets)
    ws_path = path if path is not None else getattr(websocket, "path", "/")
    client = websocket.remote_address  # tupla (ip, port) o None
    print("Cliente conectado:", client, "path:", ws_path)
    USERS.add(websocket)
    try:
        async for message in websocket:
            print("Recibido de", client, ":", message)
            # respuesta simple
            await websocket.send(f"server-echo: {message}")
    except websockets.exceptions.ConnectionClosedOK:
        print("Conexión cerrada correctamente:", client)
    except Exception as e:
        print("Error:", e)
    finally:
        USERS.discard(websocket)
        print("Cliente desconectado:", client)

async def main():
    host = "0.0.0.0"
    port = 8765
    print(f"WebSocket server escuchando en {host}:{port}")
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # se queda esperando indefinidamente

if __name__ == "__main__":
    asyncio.run(main())
