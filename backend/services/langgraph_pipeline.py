"""
LangGraph pipeline that coordinates PDF, Image, and Audio parsers and
consolidates parsed information, then stores it in Firestore.
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from services.parsers.pdf_parser import PDFParserAgent
from services.parsers.image_parser import ImageParserAgent
from services.parsers.audio_parser import AudioParserAgent
from services.firestore_service import firestore_service


class ParseInput(BaseModel):
    user_id: str
    pdf_paths: List[str] = []
    image_paths: List[str] = []
    audio_paths: List[str] = []


"""
The graph state is a plain dict. Each node returns only the keys it updates to
avoid concurrent writes to the same key (e.g., 'input').
"""

# State keys:
# - input: ParseInput
# - pdf_result: dict | None
# - image_result: dict | None
# - audio_result: dict | None
# - consolidated: dict | None


"""
Agents are instantiated lazily inside nodes to avoid initializing Groq/LLM
clients before the learning session starts.
"""


async def pdf_node(state: Dict[str, Any]) -> Dict[str, Any]:
    input_data: ParseInput = state.get("input")
    if input_data and input_data.pdf_paths:
        agent = PDFParserAgent()
        result = await agent.parse(input_data.user_id, input_data.pdf_paths)
        return {"pdf_result": result}
    return {}


async def image_node(state: Dict[str, Any]) -> Dict[str, Any]:
    input_data: ParseInput = state.get("input")
    image_inputs: List[str] = []
    if input_data and input_data.image_paths:
        image_inputs.extend(input_data.image_paths)
    pdf_result = state.get("pdf_result")
    if pdf_result and pdf_result.get("derived_image_urls"):
        image_inputs.extend(pdf_result.get("derived_image_urls", []))
    if image_inputs and input_data:
        agent = ImageParserAgent()
        result = await agent.parse(input_data.user_id, image_inputs)
        return {"image_result": result}
    return {}


async def audio_node(state: Dict[str, Any]) -> Dict[str, Any]:
    input_data: ParseInput = state.get("input")
    if input_data and input_data.audio_paths:
        agent = AudioParserAgent()
        result = await agent.parse(input_data.audio_paths)
        return {"audio_result": result}
    return {}


async def consolidate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    consolidated: Dict[str, Any] = {
        "pdf": state.get("pdf_result") or {},
        "image": state.get("image_result") or {},
        "audio": state.get("audio_result") or {},
    }
    return {"consolidated": consolidated}


async def store_node(state: Dict[str, Any]) -> Dict[str, Any]:
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
        col = firestore_service.db.collection("users").document(user_id).collection("parsed_content")
        doc = col.document()
        doc.set(data)
    return {}


def build_graph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("pdf", pdf_node)
    graph.add_node("image", image_node)
    graph.add_node("audio", audio_node)
    graph.add_node("consolidate", consolidate_node)
    graph.add_node("store", store_node)

    graph.add_edge(START, "pdf")
    graph.add_edge(START, "image")
    graph.add_edge(START, "audio")

    # Fan-in to consolidation after parallel nodes
    graph.add_edge("pdf", "consolidate")
    graph.add_edge("image", "consolidate")
    graph.add_edge("audio", "consolidate")
    graph.add_edge("consolidate", "store")
    graph.add_edge("store", END)
    return graph


graph_app = build_graph().compile()


async def run_pipeline(user_id: str, pdf_paths: List[str], image_paths: List[str], audio_paths: List[str]) -> Dict[str, Any]:
    state: Dict[str, Any] = {"input": ParseInput(user_id=user_id, pdf_paths=pdf_paths, image_paths=image_paths, audio_paths=audio_paths)}
    final_state: Dict[str, Any] = await graph_app.ainvoke(state)
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


