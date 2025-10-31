"""
LangGraph Pipeline for Knowledge Tree Generation
Orchestrates the creation of knowledge trees from parsed content
"""

from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from datetime import datetime

from services.knowledge_tree_agent import KnowledgeTreeAgent
from services.firestore_service import firestore_service

# Global WebSocket manager reference (set by orchestrator)
_ws_manager = None

def set_ws_manager(manager):
    """Set the WebSocket manager for progress updates"""
    global _ws_manager
    _ws_manager = manager


class KnowledgeTreeInput(BaseModel):
    user_id: str
    session_id: Optional[str] = None  # Optional: specific session, otherwise use all


class KnowledgeTreeState(TypedDict, total=False):
    input: KnowledgeTreeInput
    parsed_content: Dict[str, Any] | None
    knowledge_trees: Dict[str, Any] | None
    error: str | None


async def retrieve_parsed_content_node(state: KnowledgeTreeState) -> Dict[str, Any]:
    """Retrieve all parsed content from Firestore for the user"""
    input_data: KnowledgeTreeInput = state.get("input")
    user_id = input_data.user_id if input_data else "unknown"
    
    try:
        # Send progress update
        if _ws_manager:
            await _ws_manager.send_personal_message({
                "type": "knowledge_tree_progress",
                "data": {
                    "step": "retrieving_content",
                    "percentage": 10,
                    "message": "Retrieving parsed content from learning session..."
                },
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
        
        # Ensure Firestore is initialized
        firestore_service._ensure_initialized()
        
        if not firestore_service.db:
            raise Exception("Firestore not initialized")
        
        # Get all parsed content for the user
        parsed_content_col = firestore_service.db.collection("users").document(user_id).collection("parsed_content")
        parsed_docs = parsed_content_col.stream()
        
        # Aggregate all parsed content
        all_parsed_content = {
            "pdf": {"results": []},
            "image": {"results": []},
            "audio": {"results": []},
            "file_paths": []
        }
        
        for doc in parsed_docs:
            doc_data = doc.to_dict()
            
            # Merge PDF results
            pdf_data = doc_data.get("pdf", {})
            if pdf_data and isinstance(pdf_data, dict):
                pdf_results = pdf_data.get("results", [])
                if pdf_results:
                    all_parsed_content["pdf"]["results"].extend(pdf_results)
            
            # Merge image results
            image_data = doc_data.get("image", {})
            if image_data and isinstance(image_data, dict):
                image_results = image_data.get("results", [])
                if image_results:
                    all_parsed_content["image"]["results"].extend(image_results)
            
            # Merge audio results
            audio_data = doc_data.get("audio", {})
            if audio_data and isinstance(audio_data, dict):
                audio_results = audio_data.get("results", [])
                if audio_results:
                    all_parsed_content["audio"]["results"].extend(audio_results)
            
            # Collect file paths
            file_paths = doc_data.get("file_paths", [])
            if file_paths:
                all_parsed_content["file_paths"].extend(file_paths)
        
        if not all_parsed_content["pdf"]["results"] and \
           not all_parsed_content["image"]["results"] and \
           not all_parsed_content["audio"]["results"]:
            return {
                "parsed_content": None,
                "error": "No parsed content found for this user"
            }
        
        return {"parsed_content": all_parsed_content}
        
    except Exception as e:
        error_msg = f"Error retrieving parsed content: {str(e)}"
        print(f"⚠️ {error_msg}")
        return {
            "parsed_content": None,
            "error": error_msg
        }


async def generate_trees_node(state: KnowledgeTreeState) -> Dict[str, Any]:
    """Generate knowledge trees from parsed content"""
    input_data: KnowledgeTreeInput = state.get("input")
    parsed_content = state.get("parsed_content")
    user_id = input_data.user_id if input_data else "unknown"
    
    if not parsed_content:
        print("⚠️ No parsed content available to generate trees")
        return {
            "knowledge_trees": None,
            "error": "No parsed content available to generate trees"
        }
    
    try:
        print(f"📊 Starting knowledge tree generation for user: {user_id}")
        print(f"📊 Parsed content structure: {list(parsed_content.keys())}")
        print(f"📊 PDF results count: {len(parsed_content.get('pdf', {}).get('results', []))}")
        print(f"📊 Image results count: {len(parsed_content.get('image', {}).get('results', []))}")
        print(f"📊 Audio results count: {len(parsed_content.get('audio', {}).get('results', []))}")
        
        # Send progress update
        if _ws_manager:
            await _ws_manager.send_personal_message({
                "type": "knowledge_tree_progress",
                "data": {
                    "step": "generating_trees",
                    "percentage": 30,
                    "message": "Creating knowledge tree structure..."
                },
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
        
        # Create knowledge tree agent
        print("🤖 Creating KnowledgeTreeAgent instance...")
        agent = KnowledgeTreeAgent()
        print("✅ KnowledgeTreeAgent created successfully")
        
        # Process parsed data to create trees
        print("🔄 Starting to process parsed data...")
        result = await agent.process_parsed_data(parsed_content)
        print(f"✅ Processed parsed data, result keys: {list(result.keys())}")
        
        if "error" in result:
            return {
                "knowledge_trees": None,
                "error": result["error"]
            }
        
        # Send progress update
        if _ws_manager:
            await _ws_manager.send_personal_message({
                "type": "knowledge_tree_progress",
                "data": {
                    "step": "generating_questions",
                    "percentage": 60,
                    "message": "Generating questions for tree nodes..."
                },
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
        
        # Questions are already generated in the process_parsed_data method
        # So we can return the result directly
        
        return {"knowledge_trees": result}
        
    except Exception as e:
        error_msg = f"Error generating knowledge trees: {str(e)}"
        print(f"⚠️ {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "knowledge_trees": None,
            "error": error_msg
        }


async def store_trees_node(state: KnowledgeTreeState) -> Dict[str, Any]:
    """Store knowledge trees in Firestore"""
    input_data: KnowledgeTreeInput = state.get("input")
    knowledge_trees = state.get("knowledge_trees")
    user_id = input_data.user_id if input_data else "unknown"
    
    if not knowledge_trees:
        return {"error": "No knowledge trees to store"}
    
    try:
        # Send progress update
        if _ws_manager:
            await _ws_manager.send_personal_message({
                "type": "knowledge_tree_progress",
                "data": {
                    "step": "storing_trees",
                    "percentage": 90,
                    "message": "Storing knowledge trees..."
                },
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
        
        # Ensure Firestore is initialized
        firestore_service._ensure_initialized()
        
        if not firestore_service.db:
            raise Exception("Firestore not initialized")
        
        # Store knowledge trees
        trees_col = firestore_service.db.collection("users").document(user_id).collection("knowledge_trees")
        doc_ref = trees_col.document()
        
        data = {
            **knowledge_trees,
            "user_id": user_id,
            "session_id": input_data.session_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "completed"
        }
        
        doc_ref.set(data)
        
        tree_id = doc_ref.id
        
        # Send completion update
        if _ws_manager:
            await _ws_manager.send_personal_message({
                "type": "knowledge_tree_progress",
                "data": {
                    "step": "completed",
                    "percentage": 100,
                    "message": "Knowledge trees generated successfully!",
                    "tree_id": tree_id,
                    "total_nodes": knowledge_trees.get("total_nodes", 0)
                },
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
        
        return {
            "tree_id": tree_id,
            "status": "completed"
        }
        
    except Exception as e:
        error_msg = f"Error storing knowledge trees: {str(e)}"
        print(f"⚠️ {error_msg}")
        return {"error": error_msg}


def build_knowledge_tree_graph() -> StateGraph:
    """Build the LangGraph pipeline for knowledge tree generation"""
    graph = StateGraph(KnowledgeTreeState)
    
    # Add nodes
    graph.add_node("retrieve_content", retrieve_parsed_content_node)
    graph.add_node("generate_trees", generate_trees_node)
    graph.add_node("store_trees", store_trees_node)
    
    # Define flow
    graph.add_edge(START, "retrieve_content")
    graph.add_edge("retrieve_content", "generate_trees")
    graph.add_edge("generate_trees", "store_trees")
    graph.add_edge("store_trees", END)
    
    return graph


# Compile the graph
knowledge_tree_graph_app = build_knowledge_tree_graph().compile()


async def run_knowledge_tree_pipeline(
    user_id: str, 
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Run the knowledge tree generation pipeline"""
    state: KnowledgeTreeState = {
        "input": KnowledgeTreeInput(user_id=user_id, session_id=session_id),
        "parsed_content": None,
        "knowledge_trees": None,
        "error": None
    }
    
    try:
        final_state: KnowledgeTreeState = await knowledge_tree_graph_app.ainvoke(state)
        
        return {
            "tree_id": final_state.get("tree_id"),
            "knowledge_trees": final_state.get("knowledge_trees"),
            "error": final_state.get("error"),
            "status": final_state.get("status", "completed" if not final_state.get("error") else "failed")
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "status": "failed"
        }

