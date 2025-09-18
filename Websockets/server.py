import asyncio
import websockets

# No hemos cambiado el handler, el problema no está aquí.
async def handler(websocket, path):
    print(f"¡Cliente conectado desde {websocket.remote_address}!")
    try:
        async for message in websocket:
            print(f"<-- Mensaje recibido: {message}")
            response = f"El servidor recibió tu mensaje: '{message}'"
            await websocket.send(response)
            print(f"--> Mensaje enviado: {response}")
    except websockets.exceptions.ConnectionClosedOK:
        print(f"Cliente {websocket.remote_address} se desconectó.")

async def main():
    # --- ¡AQUÍ ESTÁ EL CAMBIO IMPORTANTE! ---
    # Hemos envuelto el inicio del servidor en un bloque try...except
    # para capturar CUALQUIER error que ocurra al intentar iniciarlo.
    try:
        print("Intentando iniciar el servidor en 0.0.0.0:8765...")
        
        async with websockets.serve(handler, "0.0.0.0", 8765):
            print("¡ÉXITO! Servidor WebSocket iniciado correctamente.")
            await asyncio.Future()  # Mantiene el servidor corriendo

    except Exception as e:
        # Si algo falla al intentar iniciar, este código se ejecutará.
        print("\n" + "="*50)
        print(f"          ERROR CRÍTICO AL INICIAR EL SERVIDOR")
        print("="*50)
        print(f"El error es: {e}")
        print("\nPosibles causas:")
        print("1. Otro programa ya está usando el puerto 8765.")
        print("2. Un problema de permisos o de red en el sistema operativo.")
        print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
