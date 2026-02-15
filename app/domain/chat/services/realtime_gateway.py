"""채팅 실시간 게이트웨이 (WebSocket 연결 관리자)"""
from collections import defaultdict
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket


class ChatRealtimeGateway:
    """채팅방별 WebSocket 연결 관리자"""

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, room_id: UUID, websocket: WebSocket) -> None:
        """채팅방에 소켓 연결 추가"""
        await websocket.accept()
        self._connections[str(room_id)].add(websocket)

    def disconnect(self, room_id: UUID, websocket: WebSocket) -> None:
        """채팅방에서 소켓 연결 제거"""
        room_key = str(room_id)
        clients = self._connections.get(room_key)
        if not clients:
            return
        clients.discard(websocket)
        if not clients:
            self._connections.pop(room_key, None)

    async def broadcast_json(self, room_id: UUID, payload: dict) -> None:
        """채팅방 전체에 JSON 브로드캐스트"""
        room_key = str(room_id)
        clients = list(self._connections.get(room_key, set()))
        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                self.disconnect(room_id, client)


chat_realtime_gateway = ChatRealtimeGateway()
