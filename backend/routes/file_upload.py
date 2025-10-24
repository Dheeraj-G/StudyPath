"""
File Upload Routes with Google Cloud Storage Signed URLs
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid
import json

from google.cloud import storage
from google.cloud.exceptions import NotFound
from auth.firebase_auth import verify_firebase_token
from config.settings import get_settings

router = APIRouter()
security = HTTPBearer()

class FileUploadRequest(BaseModel):
    file_name: str
    file_type: str
    file_size: int
    content_type: str

class FileUploadResponse(BaseModel):
    upload_url: str
    file_id: str
    expires_at: str
    fields: Dict[str, str]

class FileUploadComplete(BaseModel):
    file_id: str
    file_path: str
    file_size: int

class GCSFileManager:
    def __init__(self):
        self.settings = get_settings()
        self.client = storage.Client(project=self.settings.GOOGLE_CLOUD_PROJECT)
        self.bucket = self.client.bucket(self.settings.GCS_BUCKET_NAME)
    
    def generate_signed_url(self, file_name: str, content_type: str, expires_in_minutes: int = 60) -> Dict:
        """Generate signed URL for file upload"""
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            file_path = f"uploads/{file_id}/{file_name}"
            
            # Generate signed URL for upload
            blob = self.bucket.blob(file_path)
            
            # Set expiration time
            expiration = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
            
            # Generate signed URL with specific fields
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="PUT",
                content_type=content_type,
                headers={
                    "x-goog-content-length-range": "1,104857600"  # 1 byte to 100MB
                }
            )
            
            return {
                "upload_url": url,
                "file_id": file_id,
                "file_path": file_path,
                "expires_at": expiration.isoformat(),
                "fields": {
                    "Content-Type": content_type
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating signed URL: {str(e)}"
            )
    
    def verify_file_upload(self, file_path: str) -> bool:
        """Verify that file was uploaded successfully"""
        try:
            blob = self.bucket.blob(file_path)
            return blob.exists()
        except Exception as e:
            print(f"Error verifying file upload: {str(e)}")
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """Get file information from GCS"""
        try:
            blob = self.bucket.blob(file_path)
            if blob.exists():
                blob.reload()
                return {
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "created": blob.time_created.isoformat() if blob.time_created else None,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "md5_hash": blob.md5_hash
                }
            return None
        except Exception as e:
            print(f"Error getting file info: {str(e)}")
            return None

# Global file manager instance
file_manager = GCSFileManager()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    user_info = await verify_firebase_token(token)
    return user_info

@router.post("/upload-url", response_model=FileUploadResponse)
async def generate_upload_url(
    request: FileUploadRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Generate signed URL for file upload"""
    try:
        # Validate file type and size
        allowed_types = [
            "application/pdf",
            "text/plain",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/jpeg",
            "image/png",
            "image/gif",
            "video/mp4",
            "audio/mpeg",
            "audio/wav"
        ]
        
        if request.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {request.content_type} not supported"
            )
        
        # Check file size (100MB limit)
        max_size = 100 * 1024 * 1024  # 100MB
        if request.file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 100MB limit"
            )
        
        # Generate signed URL
        upload_info = file_manager.generate_signed_url(
            request.file_name,
            request.content_type,
            expires_in_minutes=60
        )
        
        return FileUploadResponse(**upload_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating upload URL: {str(e)}"
        )

@router.post("/complete")
async def complete_file_upload(
    request: FileUploadComplete,
    current_user: Dict = Depends(get_current_user)
):
    """Mark file upload as complete and trigger processing"""
    try:
        # Verify file was uploaded successfully
        if not file_manager.verify_file_upload(request.file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File upload verification failed"
            )
        
        # Get file information
        file_info = file_manager.get_file_info(request.file_path)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File not found"
            )
        
        # Store file metadata in database (you can implement this)
        file_metadata = {
            "file_id": request.file_id,
            "user_id": current_user["uid"],
            "file_path": request.file_path,
            "file_name": file_info["name"].split("/")[-1],
            "file_size": file_info["size"],
            "content_type": file_info["content_type"],
            "uploaded_at": datetime.utcnow().isoformat(),
            "status": "uploaded"
        }
        
        # TODO: Store in database (Firestore/PostgreSQL)
        # await store_file_metadata(file_metadata)
        
        # TODO: Trigger LangGraph orchestrator to process the file
        # await trigger_file_processing(request.file_id, current_user["uid"])
        
        return {
            "message": "File upload completed successfully",
            "file_id": request.file_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing file upload: {str(e)}"
        )

@router.get("/files")
async def get_user_files(current_user: Dict = Depends(get_current_user)):
    """Get list of user's uploaded files"""
    try:
        # TODO: Implement database query to get user files
        # For now, return empty list
        return {
            "files": [],
            "total": 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving files: {str(e)}"
        )

@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete a file"""
    try:
        # TODO: Implement file deletion from GCS and database
        return {
            "message": f"File {file_id} deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )
