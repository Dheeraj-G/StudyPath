"""
FastAPI Backend for StudyPath Application
Handles authentication, WebSocket communication, and routes to LangGraph orchestrator
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import os
from typing import Dict, List
import json
import asyncio
from datetime import datetime, timedelta

from auth.firebase_auth import verify_firebase_token, get_user_info
from websocket.connection_manager import ConnectionManager
from routes.file_upload import router as file_router
from routes.langgraph_orchestrator import router as orchestrator_router
from config.settings import get_settings

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

# Security
security = HTTPBearer()

# WebSocket connection manager
manager = ConnectionManager()

# Include routers
app.include_router(file_router, prefix="/api/files", tags=["files"])
app.include_router(orchestrator_router, prefix="/api/orchestrator", tags=["orchestrator"])

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
        "version": "1.0.0"
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
            
            # Process message and route to LangGraph orchestrator
            response = await process_chat_message(user_id, message_data)
            
            # Send response back to client
            await manager.send_personal_message(response, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)

async def process_chat_message(user_id: str, message_data: Dict) -> Dict:
    """Process chat message and route to LangGraph orchestrator"""
    try:
        # Extract message content
        message_content = message_data.get("content", "")
        message_type = message_data.get("type", "chat")
        
        # Route to appropriate handler based on message type
        if message_type == "chat":
            # Route to LangGraph orchestrator
            response = await route_to_langgraph(user_id, message_content)
        elif message_type == "file_upload":
            # Handle file upload completion
            response = await handle_file_upload_completion(user_id, message_data)
        else:
            response = {"error": "Unknown message type"}
            
        return {
            "type": "response",
            "content": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "type": "error",
            "content": f"Error processing message: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

async def route_to_langgraph(user_id: str, message: str) -> Dict:
    """Route message to LangGraph orchestrator"""
    # This will be implemented in the orchestrator router
    # For now, return a placeholder response
    return {
        "message": f"Processing message for user {user_id}: {message}",
        "status": "processing"
    }

async def handle_file_upload_completion(user_id: str, message_data: Dict) -> Dict:
    """Handle file upload completion notification"""
    # This will trigger the LangGraph orchestrator to process uploaded files
    return {
        "message": "File upload completed, starting processing...",
        "status": "processing"
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(settings.PORT),
        reload=settings.DEBUG
    )
