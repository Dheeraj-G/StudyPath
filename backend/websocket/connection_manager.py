"""
WebSocket Connection Manager
Handles WebSocket connections and message broadcasting
"""

from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        # Dictionary to store active connections: {user_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Dictionary to store user sessions: {user_id: session_data}
        self.user_sessions: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection and store it"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_sessions[user_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "message_count": 0
        }
        print(f"User {user_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, user_id: str):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        print(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_text(json.dumps(message))
                
                # Update session activity
                if user_id in self.user_sessions:
                    self.user_sessions[user_id]["last_activity"] = datetime.utcnow().isoformat()
                    self.user_sessions[user_id]["message_count"] += 1
                    
            except Exception as e:
                print(f"Error sending message to {user_id}: {str(e)}")
                # Remove broken connection
                self.disconnect(user_id)
    
    async def broadcast_message(self, message: Dict, exclude_user: str = None):
        """Broadcast message to all connected users"""
        disconnected_users = []
        
        for user_id, websocket in self.active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue
                
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to {user_id}: {str(e)}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)
    
    async def send_to_group(self, message: Dict, group_users: List[str]):
        """Send message to specific group of users"""
        for user_id in group_users:
            if user_id in self.active_connections:
                await self.send_personal_message(message, user_id)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    def get_user_session(self, user_id: str) -> Dict:
        """Get user session information"""
        return self.user_sessions.get(user_id, {})
    
    def get_all_sessions(self) -> Dict[str, Dict]:
        """Get all user sessions"""
        return self.user_sessions.copy()
    
    async def ping_all_connections(self):
        """Send ping to all connections to check if they're alive"""
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_message(ping_message)
