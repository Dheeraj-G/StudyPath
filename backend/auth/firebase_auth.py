"""
Firebase Authentication module
"""

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, status
from typing import Optional, Dict
import json
import os

from config.settings import get_settings

class FirebaseAuth:
    def __init__(self):
        self.settings = get_settings()
        self._initialize_firebase()
    
    def _get_service_account_path(self):
        """Get absolute path to service account file"""
        cred_path = self.settings.GOOGLE_APPLICATION_CREDENTIALS
        # If path is relative, make it relative to backend directory
        if not os.path.isabs(cred_path):
            # Get backend directory (where this file is located)
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cred_path = os.path.join(backend_dir, cred_path)
        return cred_path
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        if not firebase_admin._apps:
            try:
                cred = None
                project_id = self.settings.GOOGLE_CLOUD_PROJECT
                service_account_path = self._get_service_account_path()
                
                # Priority 1: Use service account JSON file (recommended)
                if os.path.exists(service_account_path):
                    try:
                        cred = credentials.Certificate(service_account_path)
                        # Read project_id from service account file to ensure it matches
                        with open(service_account_path, "r") as f:
                            cred_data = json.load(f)
                            project_id = cred_data.get("project_id", project_id)
                        print(f"Firebase Admin SDK initialized using service account: {service_account_path}")
                    except Exception as e:
                        print(f"Warning: Could not load service account file: {e}")
                
                # Priority 2: Use environment variables (if service account file not found)
                if not cred and os.getenv("FIREBASE_PRIVATE_KEY"):
                    cred_dict = {
                        "type": "service_account",
                        "project_id": os.getenv("FIREBASE_PROJECT_ID", project_id),
                        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
                        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL')}"
                    }
                    cred = credentials.Certificate(cred_dict)
                    print("Firebase Admin SDK initialized using environment variables")
                
                # Priority 3: Fall back to Application Default Credentials (for production/Cloud Run)
                if not cred:
                    try:
                        # Set GOOGLE_APPLICATION_CREDENTIALS if service account file exists
                        if os.path.exists(service_account_path):
                            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path
                        cred = credentials.ApplicationDefault()
                        print("Firebase Admin SDK initialized using Application Default Credentials")
                    except Exception as e:
                        print(f"Warning: Application Default Credentials not available: {e}")
                
                if cred:
                    firebase_admin.initialize_app(cred, {
                        'projectId': project_id
                    })
                else:
                    raise Exception("No valid credentials found for Firebase Admin SDK")
                    
            except Exception as e:
                print(f"Firebase initialization failed: {e}")
                print("Firebase authentication will not work. Please check your credentials.")
                raise
    
    async def verify_token(self, token: str) -> Dict:
        """Verify Firebase ID token and return user info"""
        # Check if Firebase Admin SDK is initialized
        if not firebase_admin._apps:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Firebase Admin SDK is not initialized. Please check your service account credentials."
            )
        
        try:
            decoded_token = auth.verify_id_token(token)
            return {
                "uid": decoded_token["uid"],
                "email": decoded_token.get("email"),
                "name": decoded_token.get("name"),
                "picture": decoded_token.get("picture"),
                "email_verified": decoded_token.get("email_verified", False)
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}"
            )
    
    async def get_user_by_uid(self, uid: str) -> Optional[Dict]:
        """Get user information by UID"""
        try:
            user = auth.get_user(uid)
            return {
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "photo_url": user.photo_url,
                "email_verified": user.email_verified,
                "disabled": user.disabled,
                "created_at": user.user_metadata.get("creation_timestamp"),
                "last_sign_in": user.user_metadata.get("last_sign_in_timestamp")
            }
        except Exception as e:
            print(f"Error getting user {uid}: {str(e)}")
            return None

# Global Firebase auth instance
firebase_auth = FirebaseAuth()

async def verify_firebase_token(token: str) -> Dict:
    """Verify Firebase token and return user info"""
    return await firebase_auth.verify_token(token)

async def get_user_info(uid: str) -> Optional[Dict]:
    """Get user information by UID"""
    return await firebase_auth.get_user_by_uid(uid)
