from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()


@app.get("/")
async def index():
    return FileResponse("web.html")


class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.discard(websocket)

    async def send_personal(self, websocket: WebSocket, message: str):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        to_remove = []
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except Exception:
                to_remove.append(ws)
        for r in to_remove:
            self.active.discard(r)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            await manager.send_personal(ws, f"eco: {data}")
            await manager.broadcast(f"user dijo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(ws)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
