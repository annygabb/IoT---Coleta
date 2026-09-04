import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from apps.api.app.api.v1.endpoints import get_engine

ws_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@ws_router.websocket("/ws/scenarios/{scenario_id}")
async def websocket_scenario_endpoint(websocket: WebSocket, scenario_id: str):
    await manager.connect(websocket)
    engine = get_engine()
    try:
        # Envia estado inicial imediatamente
        await websocket.send_json({"type": "FULL_SNAPSHOT", "data": engine.get_full_state()})

        # Loop bidirecional
        while True:
            # Envia deltas e escuta comandos do cliente com timeout curto
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
                # Trata comando vindo do front
                action = data.get("action")
                if action == "PAUSE":
                    engine.clock.pause()
                elif action == "RESUME":
                    engine.clock.resume()
                elif action == "SET_SPEED":
                    engine.clock.set_speed(float(data.get("speed", 60)))
            except asyncio.TimeoutError:
                pass

            # Envia estado atualizado periodicamente
            await websocket.send_json({"type": "DELTA_UPDATE", "data": engine.get_full_state()})
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
