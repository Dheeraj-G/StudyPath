"""
Knowledge Tree API Routes
Handles requests for knowledge tree generation
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import traceback

from auth.firebase_auth import verify_firebase_token
from services.knowledge_tree_pipeline import run_knowledge_tree_pipeline, set_ws_manager
from services.firestore_service import firestore_service

router = APIRouter()
security = HTTPBearer()


class GenerateKnowledgeTreeRequest(BaseModel):
    session_id: Optional[str] = None  # Optional: specific session, otherwise use all parsed content


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    user_info = await verify_firebase_token(token)
    return user_info


@router.post("/generate")
async def generate_knowledge_trees(
    request: GenerateKnowledgeTreeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Generate knowledge trees from parsed content"""
    print("="*80)
    print("🌳 KNOWLEDGE_TREE.PY: /generate endpoint called")
    print("="*80)
    try:
        user_id = current_user["uid"]
        print(f"🌳 KNOWLEDGE_TREE.PY: Generating knowledge trees for user: {user_id}")
        print(f"🌳 KNOWLEDGE_TREE.PY: Session ID: {request.session_id}")
        
        # Import here to avoid circular dependency
        from main import manager as ws_manager
        
        # Set WebSocket manager for progress updates
        set_ws_manager(ws_manager)
        print("🌳 KNOWLEDGE_TREE.PY: WebSocket manager set")
        
        # Run the knowledge tree pipeline in background
        async def run_pipeline_background():
            print("🌳 KNOWLEDGE_TREE.PY: Background task started")
            try:
                print("🌳 KNOWLEDGE_TREE.PY: Calling run_knowledge_tree_pipeline...")
                result = await run_knowledge_tree_pipeline(
                    user_id=user_id,
                    session_id=request.session_id
                )
                print(f"🌳 KNOWLEDGE_TREE.PY: Pipeline completed. Result keys: {list(result.keys()) if result else 'None'}")
                
                # Send completion notification via WebSocket
                try:
                    if result.get("error"):
                        await ws_manager.send_personal_message({
                            "type": "knowledge_tree_complete",
                            "content": f"❌ Knowledge tree generation failed: {result.get('error')}",
                            "data": {
                                "tree_id": result.get("tree_id"),
                                "status": "error",
                                "error": result.get("error")
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }, user_id)
                    else:
                        await ws_manager.send_personal_message({
                            "type": "knowledge_tree_complete",
                            "content": "✅ Knowledge trees generated successfully!",
                            "data": {
                                "tree_id": result.get("tree_id"),
                                "status": "completed",
                                "total_nodes": result.get("knowledge_trees", {}).get("total_nodes", 0)
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }, user_id)
                except Exception as ws_error:
                    print(f"Warning: Could not send completion notification: {ws_error}")
                    
            except Exception as e:
                print(f"Knowledge tree pipeline error: {e}")
                traceback.print_exc()
                
                # Send error notification via WebSocket
                try:
                    await ws_manager.send_personal_message({
                        "type": "knowledge_tree_complete",
                        "content": f"❌ Knowledge tree generation failed: {str(e)}",
                        "data": {
                            "status": "error",
                            "error": str(e)
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }, user_id)
                except Exception as ws_error:
                    print(f"Warning: Could not send error notification: {ws_error}")
        
        background_tasks.add_task(run_pipeline_background)
        
        return {
            "status": "processing",
            "message": "Knowledge tree generation started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting knowledge tree generation: {str(e)}"
        )


@router.get("/")
async def get_knowledge_trees(
    tree_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get knowledge trees for the current user"""
    try:
        user_id = current_user["uid"]
        
        if tree_id:
            tree = await firestore_service.get_knowledge_trees(user_id, tree_id)
            if not tree:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Knowledge tree not found"
                )
            return tree
        else:
            # Get latest knowledge tree
            tree = await firestore_service.get_knowledge_trees(user_id)
            if not tree:
                return {"message": "No knowledge trees found"}
            return tree
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting knowledge trees: {str(e)}"
        )


@router.get("/list")
async def list_knowledge_trees(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List all knowledge trees for the current user"""
    try:
        user_id = current_user["uid"]
        trees = await firestore_service.list_knowledge_trees(user_id, limit=limit)
        return {
            "trees": trees,
            "total": len(trees)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing knowledge trees: {str(e)}"
        )


@router.post("/quiz-results")
async def store_quiz_results(
    quiz_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Store quiz results for the current user"""
    try:
        user_id = current_user["uid"]
        result_id = await firestore_service.store_quiz_results(user_id, quiz_data)
        return {
            "result_id": result_id,
            "status": "stored"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error storing quiz results: {str(e)}"
        )


@router.get("/quiz-results/last")
async def get_last_quiz_results(
    current_user: dict = Depends(get_current_user)
):
    """Get the last quiz results for the current user"""
    try:
        user_id = current_user["uid"]
        results = await firestore_service.get_last_quiz_results(user_id)
        
        if not results:
            return {
                "message": "No quiz results found"
            }
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting last quiz results: {str(e)}"
        )

