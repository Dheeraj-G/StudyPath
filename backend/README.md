# StudyPath Backend

FastAPI backend for the StudyPath learning platform with Firebase authentication, WebSocket communication, and Google Cloud Storage integration.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Firebase Authentication**: Secure user authentication and authorization
- **WebSocket Support**: Real-time communication for chat functionality
- **Google Cloud Storage**: Signed URL file uploads for secure file handling
- **LangGraph Integration**: Routes to AI orchestrator for intelligent processing
- **Cloud Run Ready**: Containerized for easy deployment to Google Cloud Run

## Architecture

```
Frontend (Next.js) → Backend (FastAPI) → LangGraph Orchestrator → AI Agents
                    ↓
                Google Cloud Storage (File Uploads)
                    ↓
                Firebase Auth (User Management)
```

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud SDK
- Firebase project
- Docker (for containerization)

### Installation

1. **Clone and setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

3. **Run locally**:
   ```bash
   python main.py
   ```

4. **Run with Docker**:
   ```bash
   docker build -t studypath-backend .
   docker run -p 8000:8000 studypath-backend
   ```

### Environment Variables

Required environment variables:

```bash
# Server
PORT=8000
DEBUG=true

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----..."
FIREBASE_CLIENT_EMAIL=service-account@project.iam.gserviceaccount.com

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-gcp-project
GCS_BUCKET_NAME=studypath-uploads

# LangGraph
LANGGRAPH_API_URL=http://localhost:8001
```

## API Endpoints

### Authentication
- All endpoints require Firebase ID token in Authorization header
- `Bearer <firebase-id-token>`

### File Upload
- `POST /api/files/upload-url` - Generate signed URL for file upload
- `POST /api/files/complete` - Mark file upload as complete
- `GET /api/files/files` - Get user's uploaded files
- `DELETE /api/files/files/{file_id}` - Delete a file

### LangGraph Orchestrator
- `POST /api/orchestrator/chat` - Send chat message
- `POST /api/orchestrator/process-files` - Trigger file processing
- `GET /api/orchestrator/status/{task_id}` - Get processing status
- `GET /api/orchestrator/study-plan` - Get user's study plan

### WebSocket
- `WS /ws/{user_id}` - Real-time chat communication

## Deployment

### Google Cloud Run

1. **Build and deploy**:
   ```bash
   ./deploy.sh
   ```

2. **Manual deployment**:
   ```bash
   # Build image
   docker build -t gcr.io/$PROJECT_ID/studypath-backend .
   
   # Push to registry
   docker push gcr.io/$PROJECT_ID/studypath-backend
   
   # Deploy to Cloud Run
   gcloud run deploy studypath-backend \
     --image gcr.io/$PROJECT_ID/studypath-backend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### Environment Setup

1. **Create GCS bucket**:
   ```bash
   gsutil mb gs://studypath-uploads
   ```

2. **Set up Firebase**:
   - Create Firebase project
   - Enable Authentication
   - Generate service account key
   - Add environment variables

3. **Configure secrets**:
   ```bash
   # Create secrets in Google Secret Manager
   gcloud secrets create firebase-config --data-file=firebase-config.json
   gcloud secrets create gcp-config --data-file=gcp-config.json
   ```

## Development

### Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile            # Container configuration
├── deploy.sh             # Deployment script
├── cloud-run.yaml        # Cloud Run service configuration
├── config/
│   └── settings.py       # Configuration management
├── auth/
│   └── firebase_auth.py  # Firebase authentication
├── websocket/
│   └── connection_manager.py # WebSocket connection management
└── routes/
    ├── file_upload.py    # File upload endpoints
    └── langgraph_orchestrator.py # LangGraph integration
```

### Testing

```bash
# Run tests
pytest

# Test specific endpoint
curl -X GET http://localhost:8000/health
```

### Monitoring

- Health check: `GET /health`
- WebSocket status: Check connection manager logs
- File upload status: Monitor GCS bucket

## Security

- Firebase ID token validation on all endpoints
- CORS configuration for frontend domains
- Signed URLs for secure file uploads
- Input validation and sanitization
- Rate limiting (implement as needed)

## Troubleshooting

### Common Issues

1. **Firebase auth errors**: Check service account permissions
2. **GCS upload failures**: Verify bucket permissions and CORS
3. **WebSocket disconnections**: Check network and firewall settings
4. **LangGraph timeouts**: Verify orchestrator service availability

### Logs

```bash
# View Cloud Run logs
gcloud logs read --service=studypath-backend --limit=50

# Local development logs
tail -f logs/app.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details
