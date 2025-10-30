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
from services.firestore_service import firestore_service
from models.study_models import (
    ChatMessage, ProcessingRequest, AgentResponse,
    StudyPlanRequest, LearningSession, ProcessingStatus
)

router = APIRouter()
security = HTTPBearer()

# Note: Using models from models.study_models instead of defining here

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
    """Send chat message to LangGraph orchestrator and store in Firestore"""
    try:
        # Store user message in Firestore
        user_message_data = {
            "user_id": current_user["uid"],
            "role": "user",
            "content": request.message,
            "context": request.context,
            "file_references": request.file_ids or []
        }
        await firestore_service.store_chat_message(current_user["uid"], user_message_data)
        
        # Send to LangGraph orchestrator
        response = await orchestrator.send_message(
            current_user["uid"],
            request.message,
            request.context
        )
        
        # Store assistant response in Firestore
        assistant_message_data = {
            "user_id": current_user["uid"],
            "role": "assistant",
            "content": response.get("message", ""),
            "context": {"orchestrator_response": response}
        }
        await firestore_service.store_chat_message(current_user["uid"], assistant_message_data)
        
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
    """Trigger file processing by LangGraph orchestrator and track in Firestore"""
    try:
        # Store processing task in Firestore
        task_data = {
            "user_id": current_user["uid"],
            "task_type": request.processing_type,
            "file_ids": request.file_ids,
            "status": ProcessingStatus.PENDING,
            "progress_percentage": 0.0
        }
        task_id = await firestore_service.store_processing_task(current_user["uid"], task_data)
        
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
            "task_id": task_id,
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

@router.post("/study-plan/create")
async def create_study_plan(
    request: StudyPlanRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new study plan based on uploaded files"""
    try:
        # Store processing task for study plan generation
        task_data = {
            "user_id": current_user["uid"],
            "task_type": "study_plan_generation",
            "file_ids": request.file_ids,
            "status": ProcessingStatus.PENDING,
            "progress_percentage": 0.0,
            "options": {
                "title": request.title,
                "description": request.description,
                "learning_goals": request.learning_goals,
                "time_constraints": request.time_constraints
            }
        }
        task_id = await firestore_service.store_processing_task(current_user["uid"], task_data)
        
        # Trigger study plan generation
        response = await orchestrator.process_files(
            current_user["uid"],
            request.file_ids,
            "study_plan"
        )
        
        return {
            "message": "Study plan generation started",
            "task_id": task_id,
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating study plan: {str(e)}"
        )

@router.get("/study-plan")
async def get_user_study_plan(current_user: Dict = Depends(get_current_user)):
    """Get user's current study plan"""
    try:
        study_plan = await firestore_service.get_study_plan(current_user["uid"])
        
        if study_plan:
            return study_plan
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No study plan found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting study plan: {str(e)}"
        )

@router.post("/learning-session")
async def start_learning_session(
    session_data: LearningSession,
    current_user: Dict = Depends(get_current_user)
):
    """Start a new learning session"""
    try:
        session_dict = session_data.dict()
        session_dict["user_id"] = current_user["uid"]
        session_id = await firestore_service.store_learning_session(current_user["uid"], session_dict)
        
        return {
            "message": "Learning session started",
            "session_id": session_id,
            "status": "active"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting learning session: {str(e)}"
        )

@router.get("/learning-sessions")
async def get_learning_sessions(
    limit: int = 50,
    current_user: Dict = Depends(get_current_user)
):
    """Get user's learning sessions"""
    try:
        sessions = await firestore_service.get_learning_sessions(current_user["uid"], limit)
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting learning sessions: {str(e)}"
        )

@router.get("/learning-progress")
async def get_learning_progress(current_user: Dict = Depends(get_current_user)):
    """Get user's learning progress"""
    try:
        user_profile = await firestore_service.get_user_profile(current_user["uid"])
        
        if user_profile and "learning_progress" in user_profile:
            return user_profile["learning_progress"]
        else:
            return {
                "total_study_time": 0,
                "sessions_completed": 0,
                "topics_completed": 0,
                "current_streak": 0,
                "longest_streak": 0,
                "accuracy_percentage": 0.0,
                "last_activity": None
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting learning progress: {str(e)}"
        )

@router.get("/chat-history")
async def get_chat_history(
    limit: int = 100,
    current_user: Dict = Depends(get_current_user)
):
    """Get user's chat history"""
    try:
        messages = await firestore_service.get_chat_history(current_user["uid"], limit)
        
        return {
            "messages": messages,
            "total": len(messages)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting chat history: {str(e)}"
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
