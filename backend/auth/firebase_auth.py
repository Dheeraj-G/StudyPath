"""
Firebase Authentication module
"""

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, status
from typing import Optional, Dict
import json
import os

class FirebaseAuth:
    def __init__(self):
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        if not firebase_admin._apps:
            # Try to get credentials from environment variables
            if os.getenv("FIREBASE_PRIVATE_KEY"):
                cred_dict = {
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
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
            else:
                # Use default credentials (for local development)
                cred = credentials.ApplicationDefault()
            
            firebase_admin.initialize_app(cred)
    
    async def verify_token(self, token: str) -> Dict:
        """Verify Firebase ID token and return user info"""
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
