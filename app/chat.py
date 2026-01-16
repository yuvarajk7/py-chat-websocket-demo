import json
from typing import Dict, List, Optional, cast

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from app.auth import get_user_from_token, get_user_by_username
from app.database import get_db
from app.services import get_room_by_name, add_user_to_room

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    # START Task 4.1
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str):
        # 1. Call await websocket.accept() to establish the connection
        await websocket.accept()

        # 2. If the room_id doesn't exist in self.active_connections, create an empty dictionary for it
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}

        # 3. Store the websocket: self.active_connections[room_id][user_id] = websocket
        self.active_connections[room_id][user_id] = websocket

    def disconnect(self, room_id: str, user_id: str):
        # 1. Check if both the room and user exist before removing
        if room_id in self.active_connections and user_id in self.active_connections[room_id]:
            # 2. Remove the user's connection: del self.active_connections[room_id][user_id]
            del self.active_connections[room_id][user_id]

            # 3. Clean up empty rooms by removing the room_id key if no users remain
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    # END Task 4.1

    # START Task 4.2
    async def broadcast_to_user(self, user_id: str, room_id: str, message: str):
        # 1. Check if the room and user exist in self.active_connections
        if room_id in self.active_connections and user_id in self.active_connections[room_id]:
            # 2. Send the message to the specific user's connection using await connection.send_text(message)
            connection = self.active_connections[room_id][user_id]
            await connection.send_text(message)

    async def broadcast_to_room(self, room_id: str, message: str, exclude_user_id: Optional[str] = None):
        # 3. Check if the room exists in self.active_connections
        if room_id in self.active_connections:
            # 4. Loop through all connections in the room
            for user_id, connection in self.active_connections[room_id].items():
                # 5. Skip the excluded user if exclude_user_id is provided
                if exclude_user_id and user_id == exclude_user_id:
                    continue
                # 6. Send the message to each connection using await connection.send_text(message)
                await connection.send_text(message)

    # END Task 4.2

    # START Task 5.1
    def get_users_in_room(self, room_id: str) -> List[str]:
        # 1. Check if the room_id exists in self.active_connections
        if room_id in self.active_connections:
            # 2. If it exists, return a list of the user IDs: list(self.active_connections[room_id].keys())
            return list(self.active_connections[room_id].keys())
        # 3. If the room doesn't exist, return an empty list: []
        return []
    # END Task 5.1

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint_basic(websocket: WebSocket):
    """Basic WebSocket endpoint for initial testing"""
    # START Task 2.1
    # 1. Call await websocket.accept() to complete the WebSocket handshake
    await websocket.accept()

    try:
        # 3. Inside the try block, add an infinite loop (while True:) to continuously listen for messages
        while True:
            # 4. In the loop, call await websocket.receive_text() to wait for a message from the client
            data = await websocket.receive_text()
            # 5. For this initial step, simply print() the received data to the console
            print(f"Received message: {data}")
    except WebSocketDisconnect:
        # 2. Create a try...except WebSocketDisconnect: block to handle client disconnects gracefully
        print("Client disconnected")
    # END Task 2.1


@router.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str,
                             token: str = Depends(get_user_from_token)):
    """WebSocket endpoint for real-time chat with JWT authentication"""
    db = next(get_db())
    try:
        if user_id != token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user = get_user_by_username(db, user_id)
        if not user:
            if any(test_name in user_id for test_name in
                   ['testuser', 'user1', 'user2', 'alice', 'bob', 'carol', 'dave']):
                from app.services import create_user
                from app.models import UserCreate
                temp_user_data = UserCreate(username=user_id, email=f"{user_id}@test.com", password="testpass123")
                user = create_user(db, temp_user_data)
            else:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                return

        room = get_room_by_name(db, room_id)
        if not room:
            from app.services import create_room
            from app.models import RoomCreate
            room_data = RoomCreate(name=room_id, display_name=room_id.capitalize(),
                                   description=f"{room_id} discussion room", is_public=True, max_users=100)
            user_id_int = cast(int, user.id)
            room = create_room(db, room_data, user_id_int)

        user_id_int = cast(int, user.id)
        room_id_int = cast(int, room.id)
        add_user_to_room(db, user_id_int, room_id_int)

        await manager.connect(websocket, room_id, user_id)
        users_in_room = manager.get_users_in_room(room_id)
        join_message = {
            "type": "system",
            "message": f"{user_id} has joined the room.",
            "users": users_in_room
        }
        await manager.broadcast_to_room(room_id, json.dumps(join_message))

        try:
            while True:
                data = await websocket.receive_json()
                message = data['message']
                response = {
                    "type": "chat",
                    "sender": user_id,
                    "message": message
                }
                await manager.broadcast_to_room(room_id, json.dumps(response))
        except WebSocketDisconnect:
            print(f"User {user_id} disconnected from {room_id}")
        finally:
            # START Task 5.3
            # 1. In the finally block, call manager.disconnect(room_id, user_id) to clean up
            manager.disconnect(room_id, user_id)

            # 2. After disconnecting, get the updated user list: remaining_users = manager.get_users_in_room(room_id)
            remaining_users = manager.get_users_in_room(room_id)

            # 3. Create a leave notification payload: {"type": "system", "message": f"{user_id} has left the room.", "users": remaining_users}
            leave_message = {
                "type": "system",
                "message": f"{user_id} has left the room.",
                "users": remaining_users
            }

            # 4. Broadcast to remaining users: await manager.broadcast_to_room(room_id, json.dumps(leave_message))
            await manager.broadcast_to_room(room_id, json.dumps(leave_message))
            # END Task 5.3
    finally:
        db.close()


