"""
Firestore Service
Handles all Firestore database operations for StudyPath application
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from fastapi import HTTPException, status
import json

from config.settings import get_settings

class FirestoreService:
    def __init__(self):
        self.settings = get_settings()
        self.db = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Initialize Firestore client only when needed"""
        if self._initialized:
            return
            
        try:
            # Set credentials if service account file exists
            project_id = self.settings.GOOGLE_CLOUD_PROJECT
            
            if os.path.exists(self.settings.GOOGLE_APPLICATION_CREDENTIALS):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.settings.GOOGLE_APPLICATION_CREDENTIALS
                # Read project_id from service account file to ensure it matches
                try:
                    with open(self.settings.GOOGLE_APPLICATION_CREDENTIALS, "r") as f:
                        cred_data = json.load(f)
                        project_id = cred_data.get("project_id", project_id)
                except Exception as e:
                    print(f"Warning: Could not read project_id from service account: {e}")
            
            # Initialize Firestore client (uses same service account as GCS)
            self.db = firestore.Client(project=project_id)
            self._initialized = True
            
        except Exception as e:
            print(f"Warning: Failed to initialize Firestore client: {str(e)}")
            print("Firestore operations will be disabled. Please set up credentials to enable database operations.")
            self._initialized = True
    
    # File Upload Metadata Operations
    async def store_file_metadata(self, file_metadata: Dict) -> str:
        """Store file upload metadata in Firestore"""
        self._ensure_initialized()
        
        if not self.db:
            print("Warning: Firestore not available, skipping metadata storage")
            return file_metadata.get('file_id', 'unknown')
            
        try:
            doc_ref = self.db.collection('users').document(file_metadata['user_id'])\
                .collection('uploads').document(file_metadata['file_id'])
            
            # Add timestamp fields
            file_metadata['created_at'] = datetime.utcnow()
            file_metadata['updated_at'] = datetime.utcnow()
            
            doc_ref.set(file_metadata)
            return file_metadata['file_id']
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error storing file metadata: {str(e)}"
            )
    
    async def get_file_metadata(self, user_id: str, file_id: str) -> Optional[Dict]:
        """Get file metadata from Firestore"""
        self._ensure_initialized()
        
        if not self.db:
            print("Warning: Firestore not available, returning None")
            return None
        
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('uploads').document(file_id)
            
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting file metadata: {str(e)}"
            )
    
    async def find_file_by_name_and_size(self, user_id: str, file_name: str, file_size: int) -> Optional[Dict]:
        """Find a file by name and size for a user (used for duplicate detection)"""
        self._ensure_initialized()
        
        if not self.db:
            return None
            
        try:
            files_ref = self.db.collection('users').document(user_id).collection('uploads')
            # Query for files with matching name and size
            query = files_ref.where(filter=FieldFilter('file_name', '==', file_name)).where(filter=FieldFilter('file_size', '==', file_size))
            docs = query.limit(1).stream()
            
            for doc in docs:
                file_data = doc.to_dict()
                file_data['file_id'] = doc.id
                return file_data
            
            return None
            
        except Exception as e:
            print(f"Error finding file by name and size: {str(e)}")
            return None
    
    async def list_user_files(self, user_id: str) -> List[Dict]:
        """List all files for a user"""
        self._ensure_initialized()
        
        if not self.db:
            print("Warning: Firestore not available, returning empty file list")
            return []
            
        try:
            files_ref = self.db.collection('users').document(user_id).collection('uploads')
            docs = files_ref.order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            
            files = []
            for doc in docs:
                file_data = doc.to_dict()
                file_data['file_id'] = doc.id
                files.append(file_data)
            
            return files
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error listing user files: {str(e)}"
            )
    
    async def update_file_status(self, user_id: str, file_id: str, status: str, additional_data: Dict = None) -> bool:
        """Update file processing status"""
        self._ensure_initialized()
        
        if not self.db:
            print("Warning: Firestore not available, skipping status update")
            return False
        
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('uploads').document(file_id)
            
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow()
            }
            
            if additional_data:
                update_data.update(additional_data)
            
            doc_ref.update(update_data)
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating file status: {str(e)}"
            )
    
    async def delete_file_metadata(self, user_id: str, file_id: str) -> bool:
        """Delete file metadata from Firestore"""
        self._ensure_initialized()
        
        if not self.db:
            print("Warning: Firestore not available, skipping metadata deletion")
            return False
        
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('uploads').document(file_id)
            
            # Recursively delete any nested subcollections before deleting the doc
            self._delete_document_recursively(doc_ref)
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting file metadata: {str(e)}"
            )

    async def add_derived_asset(self, user_id: str, file_id: str, asset_data: Dict) -> str:
        """Add a derived asset (e.g., processed image from a PDF) under an upload.
        Stored under users/{user_id}/uploads/{file_id}/derived_assets/{asset_id}.
        """
        self._ensure_initialized()
        if not self.db:
            return ""
        try:
            col_ref = self.db.collection('users').document(user_id)\
                .collection('uploads').document(file_id)\
                .collection('derived_assets')
            doc_ref = col_ref.document()
            payload = {
                **asset_data,
                'user_id': user_id,
                'file_id': file_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
            doc_ref.set(payload)
            return doc_ref.id
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error adding derived asset: {str(e)}"
            )

    async def list_derived_assets(self, user_id: str, file_id: str) -> List[Dict]:
        """List derived assets for a given upload."""
        self._ensure_initialized()
        if not self.db:
            return []
        try:
            col_ref = self.db.collection('users').document(user_id)\
                .collection('uploads').document(file_id)\
                .collection('derived_assets')
            docs = col_ref.stream()
            assets: List[Dict] = []
            for doc in docs:
                d = doc.to_dict()
                d['asset_id'] = doc.id
                assets.append(d)
            return assets
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error listing derived assets: {str(e)}"
            )

    def _delete_document_recursively(self, doc_ref) -> None:
        """Recursively delete a document and all nested subcollection documents.
        Firestore does not delete subcollections with a single delete call.
        """
        try:
            # Delete all documents in all subcollections recursively
            for subcollection in doc_ref.collections():
                for sub_doc in subcollection.stream():
                    self._delete_document_recursively(sub_doc.reference)
            # Delete the parent document last
            doc_ref.delete()
        except Exception as e:
            # Surface errors to caller for HTTP handling
            raise e
    
    # Study Plan Operations
    async def store_study_plan(self, user_id: str, study_plan: Dict) -> str:
        """Store generated study plan"""
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('study_plans').document()
            
            study_plan_data = {
                **study_plan,
                'user_id': user_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'status': 'active'
            }
            
            doc_ref.set(study_plan_data)
            return doc_ref.id
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error storing study plan: {str(e)}"
            )
    
    async def get_study_plan(self, user_id: str, plan_id: str = None) -> Optional[Dict]:
        """Get study plan for user"""
        try:
            if plan_id:
                # Get specific study plan
                doc_ref = self.db.collection('users').document(user_id)\
                    .collection('study_plans').document(plan_id)
                doc = doc_ref.get()
                if doc.exists:
                    return doc.to_dict()
            else:
                # Get latest active study plan
                plans_ref = self.db.collection('users').document(user_id)\
                    .collection('study_plans')
                docs = plans_ref.where(filter=FieldFilter('status', '==', 'active'))\
                    .order_by('created_at', direction=firestore.Query.DESCENDING)\
                    .limit(1).stream()
                
                for doc in docs:
                    plan_data = doc.to_dict()
                    plan_data['plan_id'] = doc.id
                    return plan_data
            
            return None
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting study plan: {str(e)}"
            )
    
    async def update_study_plan(self, user_id: str, plan_id: str, updates: Dict) -> bool:
        """Update study plan"""
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('study_plans').document(plan_id)
            
            updates['updated_at'] = datetime.utcnow()
            doc_ref.update(updates)
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating study plan: {str(e)}"
            )
    
    # Learning Progress Operations
    async def store_learning_session(self, user_id: str, session_data: Dict) -> str:
        """Store learning session data"""
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('learning_sessions').document()
            
            session_data['user_id'] = user_id
            session_data['created_at'] = datetime.utcnow()
            session_data['updated_at'] = datetime.utcnow()
            
            doc_ref.set(session_data)
            return doc_ref.id
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error storing learning session: {str(e)}"
            )
    
    async def get_learning_sessions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user's learning sessions"""
        try:
            sessions_ref = self.db.collection('users').document(user_id)\
                .collection('learning_sessions')
            docs = sessions_ref.order_by('created_at', direction=firestore.Query.DESCENDING)\
                .limit(limit).stream()
            
            sessions = []
            for doc in docs:
                session_data = doc.to_dict()
                session_data['session_id'] = doc.id
                sessions.append(session_data)
            
            return sessions
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting learning sessions: {str(e)}"
            )
    
    async def update_learning_progress(self, user_id: str, progress_data: Dict) -> bool:
        """Update user's learning progress"""
        try:
            doc_ref = self.db.collection('users').document(user_id)
            
            progress_data['updated_at'] = datetime.utcnow()
            doc_ref.update({
                'learning_progress': progress_data,
                'last_activity': datetime.utcnow()
            })
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating learning progress: {str(e)}"
            )
    
    # Chat History Operations
    async def store_chat_message(self, user_id: str, message_data: Dict) -> str:
        """Store chat message"""
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('chat_history').document()
            
            message_data['user_id'] = user_id
            message_data['created_at'] = datetime.utcnow()
            
            doc_ref.set(message_data)
            return doc_ref.id
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error storing chat message: {str(e)}"
            )
    
    async def get_chat_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get user's chat history"""
        try:
            chat_ref = self.db.collection('users').document(user_id)\
                .collection('chat_history')
            docs = chat_ref.order_by('created_at', direction=firestore.Query.DESCENDING)\
                .limit(limit).stream()
            
            messages = []
            for doc in docs:
                message_data = doc.to_dict()
                message_data['message_id'] = doc.id
                messages.append(message_data)
            
            return messages
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting chat history: {str(e)}"
            )
    
    # Processing Task Operations
    async def store_processing_task(self, user_id: str, task_data: Dict) -> str:
        """Store processing task information"""
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('processing_tasks').document()
            
            task_data['user_id'] = user_id
            task_data['created_at'] = datetime.utcnow()
            task_data['updated_at'] = datetime.utcnow()
            task_data['status'] = 'pending'
            
            doc_ref.set(task_data)
            return doc_ref.id
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error storing processing task: {str(e)}"
            )
    
    async def update_processing_task(self, user_id: str, task_id: str, updates: Dict) -> bool:
        """Update processing task status"""
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('processing_tasks').document(task_id)
            
            updates['updated_at'] = datetime.utcnow()
            doc_ref.update(updates)
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating processing task: {str(e)}"
            )
    
    async def get_processing_task(self, user_id: str, task_id: str) -> Optional[Dict]:
        """Get processing task"""
        try:
            doc_ref = self.db.collection('users').document(user_id)\
                .collection('processing_tasks').document(task_id)
            
            doc = doc_ref.get()
            if doc.exists:
                task_data = doc.to_dict()
                task_data['task_id'] = doc.id
                return task_data
            return None
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting processing task: {str(e)}"
            )
    
    # User Profile Operations
    async def create_user_profile(self, user_id: str, user_data: Dict) -> bool:
        """Create user profile"""
        try:
            doc_ref = self.db.collection('users').document(user_id)
            
            profile_data = {
                **user_data,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'last_login': datetime.utcnow()
            }
            
            doc_ref.set(profile_data)
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating user profile: {str(e)}"
            )
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile"""
        try:
            doc_ref = self.db.collection('users').document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting user profile: {str(e)}"
            )
    
    async def update_user_profile(self, user_id: str, updates: Dict) -> bool:
        """Update user profile"""
        try:
            doc_ref = self.db.collection('users').document(user_id)
            
            updates['updated_at'] = datetime.utcnow()
            doc_ref.update(updates)
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating user profile: {str(e)}"
            )
    
    async def delete_parsed_content_for_file(self, user_id: str, file_path: str) -> bool:
        """Delete parsed content entries that reference a specific file path"""
        self._ensure_initialized()
        
        if not self.db:
            print("Warning: Firestore not available, skipping parsed content deletion")
            return False
            
        try:
            parsed_content_ref = self.db.collection('users').document(user_id)\
                .collection('parsed_content')
            
            # Query all parsed content documents
            docs = parsed_content_ref.stream()
            
            deleted_count = 0
            for doc in docs:
                doc_data = doc.to_dict()
                # Check if this parsed content references the file_path
                file_paths = doc_data.get('file_paths', [])
                if file_path in file_paths:
                    # Delete this parsed content document
                    doc.reference.delete()
                    deleted_count += 1
            
            if deleted_count > 0:
                print(f"Deleted {deleted_count} parsed content entries for file: {file_path}")
            
            return deleted_count > 0
            
        except Exception as e:
            print(f"Error deleting parsed content for file {file_path}: {str(e)}")
            return False

# Global Firestore service instance
firestore_service = FirestoreService()
