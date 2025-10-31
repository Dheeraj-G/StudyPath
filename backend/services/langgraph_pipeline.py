"""
LangGraph pipeline that coordinates PDF, Image, and Audio parsers and
consolidates parsed information, then stores it in Firestore.
"""

from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from datetime import datetime

from services.parsers.pdf_parser import PDFParserAgent
from services.parsers.image_parser import ImageParserAgent
from services.parsers.audio_parser import AudioParserAgent
from services.firestore_service import firestore_service

# Global WebSocket manager reference (set by orchestrator)
_ws_manager = None

def set_ws_manager(manager):
    """Set the WebSocket manager for progress updates"""
    global _ws_manager
    _ws_manager = manager


class ParseInput(BaseModel):
    user_id: str
    pdf_paths: List[str] = []
    image_paths: List[str] = []
    audio_paths: List[str] = []


"""
The graph state uses TypedDict. Each key can be updated independently,
allowing concurrent updates from multiple nodes (pdf, image, audio) running in parallel.
"""


class GraphState(TypedDict, total=False):
    input: ParseInput
    pdf_result: Dict[str, Any] | None
    image_result: Dict[str, Any] | None
    audio_result: Dict[str, Any] | None
    consolidated: Dict[str, Any] | None


"""
Agents are instantiated lazily inside nodes to avoid initializing Groq/LLM
clients before the learning session starts.
"""


async def pdf_node(state: GraphState) -> Dict[str, Any]:
    input_data: ParseInput = state.get("input")
    if input_data and input_data.pdf_paths:
        total_files = len(input_data.pdf_paths)
        # Send progress update via WebSocket if available
        # Access manager from global context (set by orchestrator)
        try:
            if _ws_manager:
                await _ws_manager.send_personal_message({
                "type": "parsing_progress",
                "data": {
                    "file_type": "pdf",
                    "parsed": 0,
                    "total": total_files,
                    "percentage": 0
                },
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }, input_data.user_id)
        except:
            pass  # WebSocket not critical for parsing
        
        agent = PDFParserAgent()
        result = await agent.parse(input_data.user_id, input_data.pdf_paths)
        
        # Send completion update
        try:
            await ws_manager.send_personal_message({
                "type": "parsing_progress",
                "data": {
                    "file_type": "pdf",
                    "parsed": total_files,
                    "total": total_files,
                    "percentage": 100
                },
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }, input_data.user_id)
        except:
            pass
        
        return {"pdf_result": result}
    return {}


async def image_node(state: GraphState) -> Dict[str, Any]:
    input_data: ParseInput = state.get("input")
    image_inputs: List[str] = []
    if input_data and input_data.image_paths:
        image_inputs.extend(input_data.image_paths)
    pdf_result = state.get("pdf_result")
    if pdf_result and pdf_result.get("derived_image_urls"):
        image_inputs.extend(pdf_result.get("derived_image_urls", []))
    if image_inputs and input_data:
        total_images = len(image_inputs)
        # Send progress update
        try:
            if _ws_manager:
                await _ws_manager.send_personal_message({
                "type": "parsing_progress",
                "data": {
                    "file_type": "image",
                    "parsed": 0,
                    "total": total_images,
                    "percentage": 0
                },
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }, input_data.user_id)
        except:
            pass
        
        agent = ImageParserAgent()
        result = await agent.parse(input_data.user_id, image_inputs)
        
        # Send completion update
        try:
            await ws_manager.send_personal_message({
                "type": "parsing_progress",
                "data": {
                    "file_type": "image",
                    "parsed": total_images,
                    "total": total_images,
                    "percentage": 100
                },
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }, input_data.user_id)
        except:
            pass
        
        return {"image_result": result}
    return {}


async def audio_node(state: GraphState) -> Dict[str, Any]:
    input_data: ParseInput = state.get("input")
    if input_data and input_data.audio_paths:
        total_files = len(input_data.audio_paths)
        # Send progress update
        try:
            if _ws_manager:
                await _ws_manager.send_personal_message({
                "type": "parsing_progress",
                "data": {
                    "file_type": "audio",
                    "parsed": 0,
                    "total": total_files,
                    "percentage": 0
                },
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }, input_data.user_id)
        except:
            pass
        
        agent = AudioParserAgent()
        result = await agent.parse(input_data.audio_paths)
        
        # Send completion update
        try:
            await ws_manager.send_personal_message({
                "type": "parsing_progress",
                "data": {
                    "file_type": "audio",
                    "parsed": total_files,
                    "total": total_files,
                    "percentage": 100
                },
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }, input_data.user_id)
        except:
            pass
        
        return {"audio_result": result}
    return {}


async def wait_for_results_node(state: GraphState) -> Dict[str, Any]:
    """
    Wait node that collects results from all parsing nodes.
    This node is called by all three parsing nodes and only proceeds when all are done.
    Returns empty dict to just pass through state.
    """
    # This node just passes state through, no modification needed
    # The conditional edge will route to consolidate when all results are ready
    return {}

async def consolidate_node(state: GraphState) -> Dict[str, Any]:
    """
    Consolidate results from pdf, image, and audio nodes.
    Extract results directly from state.
    """
    # Extract results from state
    pdf_res = state.get("pdf_result") or {}
    image_res = state.get("image_result") or {}
    audio_res = state.get("audio_result") or {}
    
    consolidated: Dict[str, Any] = {
        "pdf": pdf_res,
        "image": image_res,
        "audio": audio_res,
    }
    
    # Return consolidated result and preserve all state keys needed by downstream nodes
    result: Dict[str, Any] = {"consolidated": consolidated}
    
    # Preserve individual results and input for store_node
    if pdf_res:
        result["pdf_result"] = pdf_res
    if image_res:
        result["image_result"] = image_res
    if audio_res:
        result["audio_result"] = audio_res
    if state.get("input"):
        result["input"] = state["input"]
    
    return result


async def store_node(state: GraphState) -> Dict[str, Any]:
    data = {
        "pdf": state.get("pdf_result"),
        "image": state.get("image_result"),
        "audio": state.get("audio_result"),
        "created_at": None,
    }
    # Store in Firestore under users/{uid}/parsed_content
    try:
        await firestore_service._ensure_initialized()  # type: ignore[attr-defined]
    except Exception:
        pass
    # Use generic write via Firestore client available on service
    if firestore_service.db:
        input_data: ParseInput = state.get("input")
        user_id = input_data.user_id if input_data else "unknown"
        
        # Store file paths that were processed for this parsed content
        file_paths: List[str] = []
        if input_data:
            file_paths.extend(input_data.pdf_paths or [])
            file_paths.extend(input_data.image_paths or [])
            file_paths.extend(input_data.audio_paths or [])
        
        data["file_paths"] = file_paths
        data["processed_at"] = datetime.utcnow().isoformat()
        
        col = firestore_service.db.collection("users").document(user_id).collection("parsed_content")
        doc = col.document()
        doc.set(data)
    return {}


def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("pdf", pdf_node)
    graph.add_node("image", image_node)
    graph.add_node("audio", audio_node)
    graph.add_node("wait_for_results", wait_for_results_node)
    graph.add_node("consolidate", consolidate_node)
    graph.add_node("store", store_node)

    graph.add_edge(START, "pdf")
    graph.add_edge(START, "image")
    graph.add_edge(START, "audio")

    # Option 1: Avoid fan-in by routing all three nodes to a wait node first
    # Then only one edge goes from wait node to consolidate
    # This prevents multiple edges converging on consolidate
    graph.add_edge("pdf", "wait_for_results")
    graph.add_edge("image", "wait_for_results")
    graph.add_edge("audio", "wait_for_results")
    
    # Wait node routes to consolidate only when all results are ready
    def should_consolidate(state: GraphState) -> str:
        """Check if all parsing nodes have completed and route to consolidate"""
        # Check which results exist in state
        has_pdf = "pdf_result" in state
        has_image = "image_result" in state
        has_audio = "audio_result" in state
        
        # Check if we have input to determine if work was expected
        input_data = state.get("input")
        if not input_data:
            return "consolidate"  # No input, just consolidate
        
        # Check if all expected results are present
        # ParseInput is a Pydantic model, so access attributes directly
        pdf_expected = input_data.pdf_paths or []
        image_expected = input_data.image_paths or []
        audio_expected = input_data.audio_paths or []
        
        pdf_done = not pdf_expected or has_pdf
        image_done = not image_expected or has_image
        audio_done = not audio_expected or has_audio
        
        # Route to consolidate only when all expected work is done
        if pdf_done and image_done and audio_done:
            return "consolidate"
        # Otherwise, end (wait node will be called again when other nodes complete)
        return END
    
    graph.add_conditional_edges("wait_for_results", should_consolidate, {
        "consolidate": "consolidate",
        END: END
    })
    
    graph.add_edge("consolidate", "store")
    graph.add_edge("store", END)
    return graph


graph_app = build_graph().compile()


async def run_pipeline(user_id: str, pdf_paths: List[str], image_paths: List[str], audio_paths: List[str]) -> Dict[str, Any]:
    state: GraphState = {
        "input": ParseInput(user_id=user_id, pdf_paths=pdf_paths, image_paths=image_paths, audio_paths=audio_paths),
        "pdf_result": None,
        "image_result": None,
        "audio_result": None,
        "consolidated": None
    }
    final_state: GraphState = await graph_app.ainvoke(state)
    return {
        "consolidated": final_state.get("consolidated"),
        "pdf": final_state.get("pdf_result"),
        "image": final_state.get("image_result"),
        "audio": final_state.get("audio_result"),
    }

async def run_learning_session_pipeline(user_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    pdf_paths: List[str] = []
    image_paths: List[str] = []
    audio_paths: List[str] = []
    for f in files:
        path = f.get("file_path") or f.get("path")
        ftype = f.get("file_type") or f.get("content_type", "")
        if not path:
            continue
        lower = (ftype or "").lower()
        if path.lower().endswith(".pdf") or "pdf" in lower:
            pdf_paths.append(path)
        elif any(path.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"] ) or "image" in lower:
            image_paths.append(path)
        elif any(path.lower().endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".aac"] ) or "audio" in lower:
            audio_paths.append(path)

    return await run_pipeline(user_id, pdf_paths, image_paths, audio_paths)


