"""
LangGraph Learning Session Pipeline
Coordinates parsing, knowledge extraction, and learning insights
"""

from langgraph.graph import StateGraph, START, END
from typing import List, Dict, Any
import traceback
from datetime import datetime

from services.firestore_service import firestore_service
from services.parsers.pdf_parser import PDFParserAgent
from services.parsers.image_parser import ImageParserAgent
from services.parsers.audio_parser import AudioParserAgent


async def parse_user_files(user_id: str, user_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse user files into text chunks"""
    pdf_paths: List[str] = []
    image_paths: List[str] = []
    audio_paths: List[str] = []
    
    for f in user_files:
        try:
            file_path = f.get("file_path") or f.get("path")
            file_type = f.get("file_type") or f.get("content_type", "").lower()
            
            if not file_path:
                continue
                
            if file_path.lower().endswith(".pdf") or "pdf" in file_type:
                pdf_paths.append(file_path)
            elif any(file_path.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]) or "image" in file_type:
                image_paths.append(file_path)
            elif any(file_path.lower().endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".aac"]) or "audio" in file_type:
                audio_paths.append(file_path)
        except Exception as e:
            print(f"⚠️ Error processing file {f.get('file_path', 'unknown')}: {e}")
    
    result: Dict[str, Any] = {}
    
    # Parse PDFs
    if pdf_paths:
        try:
            pdf_agent = PDFParserAgent()
            result["pdf_result"] = await pdf_agent.parse(user_id, pdf_paths)
        except Exception as e:
            print(f"⚠️ Error parsing PDFs: {e}")
    
    # Parse Images
    if image_paths:
        try:
            image_agent = ImageParserAgent()
            result["image_result"] = await image_agent.parse(user_id, image_paths)
        except Exception as e:
            print(f"⚠️ Error parsing images: {e}")
    
    # Parse Audio
    if audio_paths:
        try:
            audio_agent = AudioParserAgent()
            result["audio_result"] = await audio_agent.parse(audio_paths)
        except Exception as e:
            print(f"⚠️ Error parsing audio: {e}")
    
    return result


async def embed_parsed_docs(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Embed parsed documents for retrieval - placeholder for future implementation"""
    # TODO: Implement embedding service
    return {"embeddings": parsed_data}


async def generate_learning_summary(embedded_data: Dict[str, Any]) -> Dict[str, Any]:
    """Use LLM to generate learning summary - placeholder for future implementation"""
    # TODO: Implement LLM summarization service
    return {"summary": embedded_data}


async def run_learning_session_pipeline(user_id: str, user_files: List[Dict[str, Any]]):
    """
    Run the end-to-end learning session pipeline:
    1. Parse files
    2. Embed documents
    3. Generate learning summary
    4. Save progress to Firestore
    """

    try:
        # Define LangGraph pipeline
        graph = StateGraph(dict)

        async def step_parse(state: Dict[str, Any]) -> Dict[str, Any]:
            parsed_data = await parse_user_files(user_id, user_files)
            return {"parsed_docs": parsed_data}

        async def step_embed(state: Dict[str, Any]) -> Dict[str, Any]:
            parsed_docs = state.get("parsed_docs", {})
            embeddings = await embed_parsed_docs(parsed_docs)
            return {"embeddings": embeddings}

        async def step_summarize(state: Dict[str, Any]) -> Dict[str, Any]:
            embeddings = state.get("embeddings", {})
            summary = await generate_learning_summary(embeddings)
            return {"summary": summary}

        async def step_save(state: Dict[str, Any]) -> Dict[str, Any]:
            summary = state.get("summary", {})
            # Store the summary in Firestore
            try:
                if firestore_service.db:
                    # Store under users/{user_id}/learning_sessions
                    col = firestore_service.db.collection("users").document(user_id).collection("learning_sessions")
                    doc = col.document()
                    doc.set({
                        "latest_summary": summary,
                        "created_at": None  # Will be set by Firestore server timestamp
                    })
            except Exception as e:
                print(f"⚠️ Error saving to Firestore: {e}")
            return {"status": "completed"}

        # Add steps in a single, linear flow
        graph.add_node("parse", step_parse)
        graph.add_node("embed", step_embed)
        graph.add_node("summarize", step_summarize)
        graph.add_node("save", step_save)

        # Define flow connections
        graph.add_edge(START, "parse")
        graph.add_edge("parse", "embed")
        graph.add_edge("embed", "summarize")
        graph.add_edge("summarize", "save")
        graph.add_edge("save", END)

        # Compile the graph
        compiled = graph.compile()

        # Run the pipeline with a single input key — avoids "__root__" collision
        result = await compiled.ainvoke({"user_id": user_id})

        print(f"✅ Learning session complete for {user_id}: {result}")
        return result

    except Exception as e:
        print(f"Learning session pipeline error: {e}")
        traceback.print_exc()
        raise e


# Export router for main.py with endpoints
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

from auth.firebase_auth import verify_firebase_token

router = APIRouter()
security = HTTPBearer()


class StartLearningSessionRequest(BaseModel):
    topic: str
    goals: list[str] = []


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    user_info = await verify_firebase_token(token)
    return user_info


@router.post("/learning-session")
async def start_learning_session(
    request: StartLearningSessionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Start a new learning session and process user files"""
    try:
        user_id = current_user["uid"]
        
        # Store learning session in Firestore
        session_data = {
            "user_id": user_id,
            "topic": request.topic,
            "goals": request.goals,
            "session_type": "learning",
            "status": "active"
        }
        session_id = await firestore_service.store_learning_session(user_id, session_data)
        
        # Get user's files from Firestore
        all_user_files = await firestore_service.list_user_files(user_id)
        
        # Filter out files that have already been processed
        user_files = []
        for file in all_user_files:
            file_status = file.get('status', 'uploaded')
            # Only process files that are uploaded or not yet processed
            # Skip files with status 'processed' or 'processing'
            if file_status not in ['processed', 'processing']:
                user_files.append(file)
            else:
                print(f"⏭️  Skipping already processed file: {file.get('file_name', 'unknown')} (status: {file_status})")
        
        if not user_files:
            # All files have already been processed
            # Send notification via WebSocket
            try:
                from main import manager as ws_manager
                await ws_manager.send_personal_message({
                    "type": "processing_complete",
                    "content": "ℹ️ All documents have already been processed. No new documents to process.",
                    "data": {
                        "session_id": session_id,
                        "status": "skipped"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }, user_id)
            except Exception as ws_error:
                print(f"Warning: Could not send skip notification: {ws_error}")
            
            return {
                "session_id": session_id,
                "status": "skipped",
                "message": "All documents have already been processed."
            }
        
        # Run the learning session pipeline in background
        # Import here to avoid circular dependency
        from services.langgraph_pipeline import run_learning_session_pipeline, set_ws_manager
        from main import manager as ws_manager
        
        # Set WebSocket manager for progress updates
        set_ws_manager(ws_manager)
        
        async def run_pipeline_background():
            try:
                # Mark files as processing before starting
                for file in user_files:
                    file_id = file.get('file_id')
                    if file_id:
                        try:
                            await firestore_service.update_file_status(
                                user_id, 
                                file_id, 
                                'processing'
                            )
                        except Exception as e:
                            print(f"Warning: Could not update file status to processing: {e}")
                
                await run_learning_session_pipeline(user_id, user_files)
                
                # Mark files as processed after successful completion
                for file in user_files:
                    file_id = file.get('file_id')
                    if file_id:
                        try:
                            await firestore_service.update_file_status(
                                user_id,
                                file_id,
                                'processed',
                                {'processed_at': datetime.utcnow().isoformat()}
                            )
                        except Exception as e:
                            print(f"Warning: Could not update file status to processed: {e}")
                
                # Update session status to completed
                # Firestore update() is synchronous, not async
                if firestore_service.db:
                    firestore_service.db.collection('users').document(user_id)\
                        .collection('learning_sessions').document(session_id).update({
                            'status': 'completed',
                            'updated_at': None  # Firestore will set timestamp
                        })
                
                # Send completion notification via WebSocket
                try:
                    await ws_manager.send_personal_message({
                        "type": "processing_complete",
                        "content": "✅ Document processing completed successfully! Your documents are now ready.",
                        "data": {
                            "session_id": session_id,
                            "status": "completed"
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }, user_id)
                except Exception as ws_error:
                    print(f"Warning: Could not send completion notification: {ws_error}")
                    
            except Exception as e:
                print(f"Learning session pipeline error: {e}")
                traceback.print_exc()
                
                # Mark files as uploaded (revert from processing) on error so they can be retried
                for file in user_files:
                    file_id = file.get('file_id')
                    if file_id:
                        try:
                            await firestore_service.update_file_status(
                                user_id,
                                file_id,
                                'uploaded'  # Revert to uploaded so it can be retried
                            )
                        except Exception as update_error:
                            print(f"Warning: Could not revert file status: {update_error}")
                
                # Update session status to error
                try:
                    if firestore_service.db:
                        firestore_service.db.collection('users').document(user_id)\
                            .collection('learning_sessions').document(session_id).update({
                                'status': 'error',
                                'error': str(e),
                                'updated_at': None
                            })
                except:
                    pass
                
                # Send error notification via WebSocket
                try:
                    await ws_manager.send_personal_message({
                        "type": "processing_error",
                        "content": f"❌ Document processing failed: {str(e)}",
                        "data": {
                            "session_id": session_id,
                            "status": "error",
                            "error": str(e)
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }, user_id)
                except Exception as ws_error:
                    print(f"Warning: Could not send error notification: {ws_error}")
        
        background_tasks.add_task(run_pipeline_background)

        return {
            "session_id": session_id,
            "status": "active"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting learning session: {str(e)}"
        )
