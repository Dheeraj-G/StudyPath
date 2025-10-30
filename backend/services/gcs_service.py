"""
Google Cloud Storage Service
Handles file uploads, downloads, and management with user namespacing
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from google.cloud import storage
from google.cloud.exceptions import NotFound
from fastapi import HTTPException, status
import uuid
import json

from config.settings import get_settings

class GCSService:
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.bucket = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Initialize GCS client only when needed"""
        if self._initialized:
            return
            
        try:
            # Set credentials if service account file exists
            project_id = self.settings.GOOGLE_CLOUD_PROJECT
            bucket_name = self.settings.GCS_BUCKET_NAME
            
            if os.path.exists(self.settings.GOOGLE_APPLICATION_CREDENTIALS):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.settings.GOOGLE_APPLICATION_CREDENTIALS
                # Read project_id from service account file to ensure it matches
                try:
                    with open(self.settings.GOOGLE_APPLICATION_CREDENTIALS, "r") as f:
                        cred_data = json.load(f)
                        project_id = cred_data.get("project_id", project_id)
                except Exception as e:
                    print(f"Warning: Could not read project_id from service account: {e}")
            
            # Initialize storage client with project ID (following user's example pattern)
            self.client = storage.Client(project=project_id)
            self.bucket = self.client.bucket(bucket_name)
            
            # Verify bucket exists
            if not self.bucket.exists():
                print(f"Warning: GCS bucket '{bucket_name}' does not exist")
                print(f"Please create the bucket '{bucket_name}' in project '{project_id}'")
                # Don't raise exception, just log warning
                
            self._initialized = True
            
        except Exception as e:
            print(f"Warning: Failed to initialize GCS client: {str(e)}")
            print("GCS operations will be disabled. Please set up credentials to enable file uploads.")
            # Don't raise exception, just log warning
            self._initialized = True
    
    def create_signed_upload_url(self, filename: str, content_type: str, user_id: str, file_type: str, expires_minutes: int = 15) -> Dict:
        """
        Create a signed URL for direct file upload to GCS
        Files are namespaced per user and type: users/{user_id}/uploads/{file_type}/{file_id}/{filename}
        """
        self._ensure_initialized()
        
        if not self.client or not self.bucket:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GCS service is not available. Please check your Google Cloud credentials."
            )
            
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Build file path using configurable uploads directory name
            uploads_dir = self.settings.UPLOADS_DIR_NAME.strip("/")
            # Join non-empty segments to avoid double slashes when uploads_dir is empty
            path_segments = ["users", user_id]
            if uploads_dir:
                path_segments.append(uploads_dir)
            path_segments.extend([file_type, file_id, filename])
            file_path = "/".join(path_segments)
            
            # Create blob reference
            blob = self.bucket.blob(file_path)
            
            # Calculate expiration datetime
            expiration_datetime = datetime.utcnow() + timedelta(minutes=expires_minutes)
            
            # Generate signed URL for PUT request
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=expiration_datetime,
                method="PUT",
                content_type=content_type
            )
            
            return {
                "upload_url": signed_url,
                "file_id": file_id,
                "file_path": file_path,
                "expires_at": expiration_datetime.isoformat(),
                "fields": {
                    "Content-Type": content_type
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating signed upload URL: {str(e)}"
            )
    
    def create_signed_download_url(self, file_path: str, expires_minutes: int = 60) -> str:
        """
        Create a signed URL for file download
        """
        self._ensure_initialized()
        
        if not self.client or not self.bucket:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GCS service is not available. Please check your Google Cloud credentials."
            )
            
        try:
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )
            
            expiration = datetime.utcnow() + timedelta(minutes=expires_minutes)
            
            signed_url = blob.generate_signed_url(
                version="v4",
                method="GET",
                expiration=expiration
            )
            
            return signed_url
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating signed download URL: {str(e)}"
            )
    
    def verify_file_upload(self, file_path: str) -> bool:
        """Verify that file was uploaded successfully"""
        self._ensure_initialized()
        
        if not self.client or not self.bucket:
            return False
            
        try:
            blob = self.bucket.blob(file_path)
            return blob.exists()
        except Exception as e:
            print(f"Error verifying file upload: {str(e)}")
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """Get file information from GCS"""
        self._ensure_initialized()
        
        if not self.client or not self.bucket:
            return None
            
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
                    "md5_hash": blob.md5_hash,
                    "etag": blob.etag
                }
            return None
        except Exception as e:
            print(f"Error getting file info: {str(e)}")
            return None
    
    def list_user_files(self, user_id: str) -> List[Dict]:
        """List all files for a specific user"""
        self._ensure_initialized()
        
        if not self.client or not self.bucket:
            return []
            
        try:
            uploads_dir = self.settings.UPLOADS_DIR_NAME.strip("/")
            prefix = f"users/{user_id}/" + (uploads_dir + "/" if uploads_dir else "")
            blobs = self.client.list_blobs(self.settings.GCS_BUCKET_NAME, prefix=prefix)
            
            files = []
            for blob in blobs:
                # Only include files, not directories
                if not blob.name.endswith('/'):
                    file_info = {
                        "file_path": blob.name,
                        "file_name": blob.name.split('/')[-1],
                        "file_id": blob.name.split('/')[-2],  # Extract file_id from path
                        "size": blob.size,
                        "content_type": blob.content_type,
                        "created": blob.time_created.isoformat() if blob.time_created else None,
                        "updated": blob.updated.isoformat() if blob.updated else None
                    }
                    files.append(file_info)
            
            return files
            
        except Exception as e:
            print(f"Error listing user files: {str(e)}")
            return []
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from GCS"""
        self._ensure_initialized()
        
        if not self.client or not self.bucket:
            return False
            
        try:
            blob = self.bucket.blob(file_path)
            blob.delete()

            # After deleting the file, attempt to clean up empty parent prefixes
            try:
                self._cleanup_empty_prefixes(file_path)
            except Exception as e:
                # Non-fatal: log and continue
                print(f"Warning: Failed to cleanup empty prefixes for {file_path}: {str(e)}")

            return True
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
            return False

    def _cleanup_empty_prefixes(self, file_path: str) -> None:
        """
        Recursively delete empty parent "folders" (prefix placeholders) up to the user's uploads root.
        This only removes zero-byte placeholder blobs that exactly match the prefix (ending with '/'),
        and only if there are no other blobs under that prefix.
        """
        parts = file_path.split('/')
        if len(parts) < 3:
            return

        uploads_dir = self.settings.UPLOADS_DIR_NAME.strip('/')
        # Determine stop index for cleanup (inclusive index of the uploads root)
        # Path format with uploads_dir: users/{uid}/{uploads_dir}/{file_type}/{file_id}/{filename}
        # Stop at: users/{uid}/{uploads_dir}/ (index 2)
        # Without uploads_dir: users/{uid}/{file_type}/{file_id}/{filename}
        # Stop at: users/{uid}/ (index 1)
        stop_index = 2 if uploads_dir else 1

        # Start from parent of the file (exclude filename)
        # Iterate downwards: file_id/, file_type/, uploads_dir/
        for i in range(len(parts) - 1, stop_index, -1):
            # Standard GCS "folder" prefix representation ends with '/'
            prefix_with_slash = '/'.join(parts[:i]) + '/'
            # Some tools may create a marker object without trailing '/'
            prefix_no_slash = '/'.join(parts[:i])

            # Check for any children under this prefix besides an optional placeholder blob
            has_children = False
            placeholder_with_slash = False
            placeholder_no_slash = False

            for b in self.client.list_blobs(self.settings.GCS_BUCKET_NAME, prefix=prefix_with_slash):
                if b.name == prefix_with_slash:
                    placeholder_with_slash = True
                    continue
                # Any object that is not the exact placeholder counts as a child
                has_children = True
                break

            if not has_children:
                # Also check if a no-slash marker exists explicitly
                marker_blob_no_slash = self.bucket.blob(prefix_no_slash)
                try:
                    if marker_blob_no_slash.exists():
                        placeholder_no_slash = True
                except Exception:
                    pass

                # Delete placeholder blobs if they exist
                if placeholder_with_slash:
                    try:
                        self.bucket.blob(prefix_with_slash).delete()
                    except Exception:
                        pass
                if placeholder_no_slash:
                    try:
                        marker_blob_no_slash.delete()
                    except Exception:
                        pass
                # continue checking next parent level
                continue
            else:
                # This prefix has other children; stop cleanup
                break
    
    def delete_user_files(self, user_id: str) -> int:
        """Delete all files and placeholder blobs for a specific user"""
        self._ensure_initialized()
        
        if not self.client or not self.bucket:
            return 0
            
        try:
            uploads_dir = self.settings.UPLOADS_DIR_NAME.strip("/")
            prefix = f"users/{user_id}/" + (uploads_dir + "/" if uploads_dir else "")
            blobs = list(self.client.list_blobs(self.settings.GCS_BUCKET_NAME, prefix=prefix))
            
            deleted_count = 0
            for blob in blobs:
                try:
                    blob.delete()
                    deleted_count += 1
                except Exception as e:
                    # Continue with best-effort deletion
                    print(f"Warning: failed to delete blob {blob.name}: {e}")

            # Cleanup folder markers (empty prefixes) inferred from deleted blobs
            marker_prefixes = set()
            for blob in blobs:
                parts = blob.name.split("/")
                # accumulate all parent prefixes as potential markers
                for i in range(1, len(parts)):
                    prefix_path = "/".join(parts[:i]) + "/"
                    marker_prefixes.add(prefix_path)

            user_root_prefix = f"users/{user_id}/"
            for prefix_marker in marker_prefixes:
                # Never delete above the user root; keep user-level info intact
                if prefix_marker == user_root_prefix or prefix_marker == "users/":
                    continue
                marker_blob = self.bucket.blob(prefix_marker)
                try:
                    # exists() is cheap; only delete zero-byte markers
                    if marker_blob.exists():
                        try:
                            # reload to access size safely
                            marker_blob.reload()
                            if not marker_blob.size:
                                marker_blob.delete()
                        except Exception:
                            # If reload not available, attempt delete best-effort
                            marker_blob.delete()
                except Exception:
                    # Best-effort cleanup; ignore errors
                    pass

            return deleted_count
            
        except Exception as e:
            print(f"Error deleting user files: {str(e)}")
            return 0
    
    def upload_file_directly(self, file_path: str, file_content: bytes, content_type: str) -> bool:
        """Upload file directly from backend (for server-side uploads)"""
        self._ensure_initialized()
        
        if not self.client or not self.bucket:
            return False
            
        try:
            blob = self.bucket.blob(file_path)
            blob.upload_from_string(file_content, content_type=content_type)
            return True
        except Exception as e:
            print(f"Error uploading file directly: {str(e)}")
            return False

# Global GCS service instance
gcs_service = GCSService()
