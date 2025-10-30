"""
File Upload Routes with Google Cloud Storage Signed URLs
Secure file upload with user namespacing and Firebase authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid
import json

from services.gcs_service import gcs_service
from services.firestore_service import firestore_service
from auth.firebase_auth import verify_firebase_token
from config.settings import get_settings

router = APIRouter()
security = HTTPBearer()
settings = get_settings()

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
    file_size: int
    # We no longer require clients to send file_path
    file_path: Optional[str] = None

class FileDownloadRequest(BaseModel):
    file_path: str

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
    """Generate signed URL for secure file upload with user namespacing"""
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
            "audio/wav",
            "audio/mp3",
            "video/mpeg",
            "video/quicktime"
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
        
        # Generate signed URL with user namespacing
        upload_info = gcs_service.create_signed_upload_url(
            filename=request.file_name,
            content_type=request.content_type,
            user_id=current_user["uid"],
            file_type=request.file_type,
            expires_minutes=10  # Short expiration for security
        )
        
        # Do not include raw file_path in API response
        safe_response = {
            "upload_url": upload_info["upload_url"],
            "file_id": upload_info["file_id"],
            "expires_at": upload_info["expires_at"],
            "fields": upload_info["fields"],
        }
        return FileUploadResponse(**safe_response)
        
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
        # Resolve file_path server-side if not provided (to avoid exposing raw paths)
        resolved_file_path = request.file_path
        if not resolved_file_path:
            user_files = gcs_service.list_user_files(current_user["uid"]) or []
            # Find by file_id
            match = next((f for f in user_files if f.get("file_id") == request.file_id), None)
            if not match:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file not found for given file_id"
                )
            resolved_file_path = match["file_path"]

        # Verify file was uploaded successfully
        if not gcs_service.verify_file_upload(resolved_file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File upload verification failed"
            )
        
        # Get file information
        file_info = gcs_service.get_file_info(resolved_file_path)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File not found"
            )
        
        # Verify the file belongs to the current user
        uploads_dir = settings.UPLOADS_DIR_NAME.strip("/")
        user_prefix = f"users/{current_user['uid']}/" + (uploads_dir + "/" if uploads_dir else "")
        if not resolved_file_path.startswith(user_prefix):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: File does not belong to user"
            )
        
        file_name = file_info["name"].split("/")[-1]
        file_size = file_info["size"]
        
        # Check for duplicate file (same name and size for this user)
        existing_file = await firestore_service.find_file_by_name_and_size(
            current_user["uid"], 
            file_name, 
            file_size
        )
        
        if existing_file:
            # Delete the old file from GCS and Firestore
            try:
                # Delete old file from GCS
                if existing_file.get("file_path"):
                    gcs_service.delete_file(existing_file["file_path"])
                
                # Delete old file from Firestore
                await firestore_service.delete_file_metadata(
                    current_user["uid"], 
                    existing_file["file_id"]
                )
            except Exception as e:
                print(f"Warning: Error deleting duplicate file: {str(e)}")
                # Continue with new upload even if old deletion fails
        
        # Store file metadata in Firestore
        file_metadata = {
            "file_id": request.file_id,
            "user_id": current_user["uid"],
            "file_path": resolved_file_path,
            "file_name": file_name,
            "file_size": file_size,
            "content_type": file_info["content_type"],
            "uploaded_at": datetime.utcnow().isoformat(),
            "status": "uploaded",
            "gcs_metadata": file_info
        }
        
        # Store in Firestore
        await firestore_service.store_file_metadata(file_metadata)
        
        # TODO: Trigger LangGraph orchestrator to process the file
        # await trigger_file_processing(request.file_id, current_user["uid"])
        
        return {
            "message": "File upload completed successfully",
            "file_id": request.file_id,
            "status": "processing",
            "file_info": file_info
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
    """Get list of user's uploaded files from Firestore"""
    try:
        files = await firestore_service.list_user_files(current_user["uid"])
        # Remove direct file paths from the response to avoid exposing raw URLs
        redacted_files = []
        for f in files:
            f_copy = {k: v for k, v in f.items() if k != "file_path"}
            redacted_files.append(f_copy)
        return {
            "files": redacted_files,
            "total": len(redacted_files)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving files: {str(e)}"
        )

@router.post("/download-url")
async def generate_download_url(
    request: FileDownloadRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Generate signed URL for file download"""
    try:
        # Verify the file belongs to the current user
        uploads_dir = settings.UPLOADS_DIR_NAME.strip("/")
        user_prefix = f"users/{current_user['uid']}/" + (uploads_dir + "/" if uploads_dir else "")
        if not request.file_path.startswith(user_prefix):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: File does not belong to user"
            )
        
        # Generate signed download URL
        download_url = gcs_service.create_signed_download_url(request.file_path)
        
        return {
            "download_url": download_url,
            "expires_at": (datetime.utcnow() + timedelta(minutes=60)).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating download URL: {str(e)}"
        )

@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete a file from both GCS and Firestore"""
    try:
        # Get file metadata from Firestore
        file_metadata = await firestore_service.get_file_metadata(current_user["uid"], file_id)
        
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete from GCS
        success = gcs_service.delete_file(file_metadata["file_path"])
        
        if success:
            # Delete from Firestore
            await firestore_service.delete_file_metadata(current_user["uid"], file_id)
            
            return {
                "message": f"File {file_id} deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file from storage"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )
