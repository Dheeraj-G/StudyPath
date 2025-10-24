"""
Simple FastAPI Backend for StudyPath Application (Test Version)
This version works without Firebase configuration for basic testing
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json
import asyncio
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title="StudyPath Backend API",
    description="Backend API for StudyPath learning platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple WebSocket connection manager
class SimpleConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        print(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict, user_id: str):
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending message to {user_id}: {str(e)}")
                self.disconnect(user_id)

# Global connection manager
manager = SimpleConnectionManager()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "StudyPath Backend API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "connections": len(manager.active_connections)
    }

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat communication"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Echo the message back (for testing)
            response = {
                "type": "response",
                "content": f"Echo: {message_data.get('content', 'Hello!')}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send response back to client
            await manager.send_personal_message(response, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint that doesn't require authentication"""
    return {
        "message": "Backend is working!",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
