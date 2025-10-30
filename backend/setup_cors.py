"""
Script to configure CORS for Firebase Storage / GCS bucket
"""

import json
import os
from google.cloud import storage
from config.settings import get_settings

def setup_cors():
    """Configure CORS for the GCS bucket"""
    settings = get_settings()
    
    # Set credentials from service account file
    if os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
        print(f"Using service account: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
    else:
        print(f"Warning: Service account file not found: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
        # Try relative path from backend directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        cred_path = os.path.join(backend_dir, "service-account.json")
        if os.path.exists(cred_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
            print(f"Using service account: {cred_path}")
        else:
            raise FileNotFoundError(f"Service account file not found at {settings.GOOGLE_APPLICATION_CREDENTIALS} or {cred_path}")
    
    # CORS configuration
    cors_config = [
        {
            "origin": ["http://localhost:3000"],
            "method": ["GET", "PUT", "POST", "HEAD"],
            "responseHeader": ["Content-Type", "Content-Length", "x-goog-resumable"],
            "maxAgeSeconds": 3600
        }
    ]
    
    try:
        # Initialize GCS client
        client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        
        # Get current CORS configuration
        try:
            current_cors = bucket.cors
            print(f"Current CORS configuration: {current_cors}")
        except Exception as e:
            print(f"No existing CORS configuration: {e}")
        
        # Set CORS configuration
        bucket.cors = cors_config
        bucket.patch()
        
        print(f"✅ CORS configuration successfully applied to bucket: {settings.GCS_BUCKET_NAME}")
        print(f"CORS configuration:")
        print(json.dumps(cors_config, indent=2))
        
        # Verify
        bucket.reload()
        print(f"\n✅ Verified - Current CORS configuration:")
        print(json.dumps(bucket.cors, indent=2))
        
    except Exception as e:
        print(f"❌ Error setting CORS: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure service-account.json exists in the backend directory")
        print("2. Verify the bucket name in your .env file matches your Firebase Storage bucket")
        print("3. Ensure your service account has Storage Admin permissions")
        raise

if __name__ == "__main__":
    print("Setting up CORS for Firebase Storage bucket...")
    print("=" * 60)
    setup_cors()
    print("=" * 60)
    print("\n🎉 CORS setup complete!")
    print("Note: CORS changes can take a few minutes to propagate.")

