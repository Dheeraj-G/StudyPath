"""
LangGraph Orchestrator Routes
Handles communication with LangGraph orchestrator and AI agents
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import httpx
import json
from datetime import datetime

from auth.firebase_auth import verify_firebase_token
from config.settings import get_settings
from websocket.connection_manager import ConnectionManager

router = APIRouter()
security = HTTPBearer()

class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    file_ids: Optional[List[str]] = None

class ProcessingRequest(BaseModel):
    file_ids: List[str]
    user_id: str
    processing_type: str = "study_plan"

class AgentResponse(BaseModel):
    agent_type: str
    response: Dict[str, Any]
    timestamp: str

class LangGraphOrchestrator:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.LANGGRAPH_API_URL
        self.connection_manager = ConnectionManager()
    
    async def send_message(self, user_id: str, message: str, context: Dict = None) -> Dict:
        """Send message to LangGraph orchestrator"""
        try:
            payload = {
                "user_id": user_id,
                "message": message,
                "context": context or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat",
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"LangGraph orchestrator error: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="LangGraph orchestrator timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error communicating with orchestrator: {str(e)}"
            )
    
    async def process_files(self, user_id: str, file_ids: List[str], processing_type: str = "study_plan") -> Dict:
        """Trigger file processing by LangGraph orchestrator"""
        try:
            payload = {
                "user_id": user_id,
                "file_ids": file_ids,
                "processing_type": processing_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/process-files",
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"File processing error: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="File processing timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing files: {str(e)}"
            )
    
    async def get_processing_status(self, user_id: str, task_id: str) -> Dict:
        """Get processing status from LangGraph orchestrator"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/status/{user_id}/{task_id}",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Status check error: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Status check timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error checking status: {str(e)}"
            )
    
    async def get_study_plan(self, user_id: str) -> Dict:
        """Get generated study plan for user"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/study-plan/{user_id}",
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Study plan error: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Study plan timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting study plan: {str(e)}"
            )

# Global orchestrator instance
orchestrator = LangGraphOrchestrator()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    user_info = await verify_firebase_token(token)
    return user_info

@router.post("/chat")
async def send_chat_message(
    request: ChatMessage,
    current_user: Dict = Depends(get_current_user)
):
    """Send chat message to LangGraph orchestrator"""
    try:
        response = await orchestrator.send_message(
            current_user["uid"],
            request.message,
            request.context
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )

@router.post("/process-files")
async def process_files(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """Trigger file processing by LangGraph orchestrator"""
    try:
        # Start file processing in background
        background_tasks.add_task(
            orchestrator.process_files,
            current_user["uid"],
            request.file_ids,
            request.processing_type
        )
        
        return {
            "message": "File processing started",
            "user_id": current_user["uid"],
            "file_ids": request.file_ids,
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting file processing: {str(e)}"
        )

@router.get("/status/{task_id}")
async def get_processing_status(
    task_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get processing status for a task"""
    try:
        status_info = await orchestrator.get_processing_status(
            current_user["uid"],
            task_id
        )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting processing status: {str(e)}"
        )

@router.get("/study-plan")
async def get_study_plan(current_user: Dict = Depends(get_current_user)):
    """Get user's study plan"""
    try:
        study_plan = await orchestrator.get_study_plan(current_user["uid"])
        
        return study_plan
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting study plan: {str(e)}"
        )

@router.post("/agent-response")
async def receive_agent_response(
    response: AgentResponse,
    current_user: Dict = Depends(get_current_user)
):
    """Receive response from AI agents (called by LangGraph orchestrator)"""
    try:
        # Send agent response to user via WebSocket
        await orchestrator.connection_manager.send_personal_message(
            {
                "type": "agent_response",
                "agent_type": response.agent_type,
                "response": response.response,
                "timestamp": response.timestamp
            },
            current_user["uid"]
        )
        
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing agent response: {str(e)}"
        )

@router.get("/health")
async def orchestrator_health():
    """Check LangGraph orchestrator health"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{orchestrator.base_url}/health",
                timeout=5.0
            )
            
            if response.status_code == 200:
                return {"status": "healthy", "orchestrator": "connected"}
            else:
                return {"status": "unhealthy", "orchestrator": "disconnected"}
                
    except Exception as e:
        return {"status": "unhealthy", "orchestrator": "error", "error": str(e)}
