from fastapi import WebSocket
from typing import Dict, List, Set, Any
import json
import logging

logger = logging.getLogger("quizarena.ws")

class WebSocketManager:
    def __init__(self):
        # Maps quiz_id -> Dict[participant_id, WebSocket]
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Maps quiz_id -> Set[WebSocket] for admin connections
        self.admin_connections: Dict[str, Set[WebSocket]] = {}

    async def connect_player(self, quiz_id: str, participant_id: str, websocket: WebSocket):
        await websocket.accept()
        if quiz_id not in self.active_connections:
            self.active_connections[quiz_id] = {}
        self.active_connections[quiz_id][participant_id] = websocket
        logger.info(f"Player connected: {participant_id} in quiz {quiz_id}")
        
        # Broadcast player joined event to admin clients
        await self.broadcast_to_admin(quiz_id, {
            "type": "PLAYER_JOINED",
            "participant_id": participant_id
        })

    async def connect_admin(self, quiz_id: str, websocket: WebSocket):
        await websocket.accept()
        if quiz_id not in self.admin_connections:
            self.admin_connections[quiz_id] = set()
        self.admin_connections[quiz_id].add(websocket)
        logger.info(f"Admin connected to quiz {quiz_id}")

    def disconnect_player(self, quiz_id: str, participant_id: str):
        if quiz_id in self.active_connections:
            if participant_id in self.active_connections[quiz_id]:
                del self.active_connections[quiz_id][participant_id]
                logger.info(f"Player disconnected: {participant_id} from quiz {quiz_id}")

    def disconnect_admin(self, quiz_id: str, websocket: WebSocket):
        if quiz_id in self.admin_connections:
            self.admin_connections[quiz_id].discard(websocket)
            logger.info(f"Admin disconnected from quiz {quiz_id}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_admin(self, quiz_id: str, message: dict):
        if quiz_id in self.admin_connections:
            disconnected_admin = []
            for ws in list(self.admin_connections[quiz_id]):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send to admin: {e}")
                    disconnected_admin.append(ws)
            for ws in disconnected_admin:
                self.disconnect_admin(quiz_id, ws)

    async def broadcast_to_quiz(self, quiz_id: str, message: dict):
        # Broadcast to all players in the room
        if quiz_id in self.active_connections:
            disconnected = []
            for p_id, ws in list(self.active_connections[quiz_id].items()):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send to player {p_id}: {e}")
                    disconnected.append(p_id)
            for p_id in disconnected:
                self.disconnect_player(quiz_id, p_id)

        # Broadcast to all admin observer connections
        await self.broadcast_to_admin(quiz_id, message)

    def get_connected_player_ids(self, quiz_id: str) -> List[str]:
        if quiz_id in self.active_connections:
            return list(self.active_connections[quiz_id].keys())
        return []

manager = WebSocketManager()
