# StudyPath Setup Guide

## 🚀 How to Run StudyPath

### Prerequisites
- Python 3.11+ (you have 3.13.2 ✅)
- Node.js 18+ and npm
- Firebase project
- Google Cloud project (for GCS)

### 1. Backend Setup

#### Option A: Local Development

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env with your actual values (see configuration section below)

# Run the backend
python3 main.py
```

#### Option B: Docker

```bash
cd backend

# Build Docker image
docker build -t studypath-backend .

# Run container
docker run -p 8000:8000 --env-file .env studypath-backend
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local
# Edit .env.local with your actual values

# Run development server
npm run dev
```

### 3. Configuration

#### Backend Environment (.env)
```bash
# Server Configuration
PORT=8000
DEBUG=true

# Firebase Configuration
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour private key here\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GCS_BUCKET_NAME=studypath-uploads

# LangGraph Orchestrator
LANGGRAPH_API_URL=http://localhost:8001

# Redis (optional for local dev)
REDIS_URL=redis://localhost:6379
```

#### Frontend Environment (.env.local)
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Firebase Configuration
NEXT_PUBLIC_FIREBASE_API_KEY=your-firebase-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-firebase-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your-messaging-sender-id
NEXT_PUBLIC_FIREBASE_APP_ID=your-firebase-app-id
```

### 4. Firebase Setup

1. **Create Firebase Project**:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create new project
   - Enable Authentication → Sign-in method → Google

2. **Generate Service Account**:
   - Go to Project Settings → Service Accounts
   - Generate new private key
   - Download JSON file
   - Extract values for backend .env

3. **Get Frontend Config**:
   - Go to Project Settings → General
   - Copy config values to frontend .env.local

### 5. Google Cloud Setup

1. **Create GCS Bucket**:
   ```bash
   gsutil mb gs://studypath-uploads
   ```

2. **Set up Service Account**:
   - Go to IAM & Admin → Service Accounts
   - Create service account with Storage Admin role
   - Download key file

### 6. Running the Application

#### Start Backend
```bash
cd backend
source venv/bin/activate
python3 main.py
```
Backend will be available at: http://localhost:8000

#### Start Frontend
```bash
cd frontend
npm run dev
```
Frontend will be available at: http://localhost:3000

### 7. Testing the Setup

1. **Backend Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Frontend**:
   - Open http://localhost:3000
   - Sign in with Google
   - Upload a file
   - Start a learning session

### 8. Deployment (Optional)

#### Deploy Backend to Cloud Run
```bash
cd backend
./deploy.sh
```

#### Deploy Frontend to Vercel
```bash
cd frontend
npm run build
# Follow Vercel deployment instructions
```

### Troubleshooting

#### Common Issues:

1. **Firebase Auth Errors**:
   - Check service account permissions
   - Verify project ID and keys

2. **GCS Upload Failures**:
   - Verify bucket exists and has correct permissions
   - Check CORS configuration

3. **WebSocket Connection Issues**:
   - Ensure backend is running on port 8000
   - Check firewall settings

4. **Python Import Errors**:
   - Make sure virtual environment is activated
   - Install missing dependencies: `pip install -r requirements.txt`

#### Logs:
```bash
# Backend logs
tail -f logs/app.log

# Frontend logs
# Check browser console
```

### Development Workflow

1. **Start Backend**: `cd backend && python3 main.py`
2. **Start Frontend**: `cd frontend && npm run dev`
3. **Make Changes**: Edit code in your IDE
4. **Test**: Refresh browser to see changes
5. **Debug**: Check console logs and network tab

### Next Steps

Once running locally:
1. Upload study materials (PDFs, images, audio)
2. Sign in with Google
3. Start a learning session
4. Chat with the AI about your materials
5. Generate personalized study plans

The application will route your files and messages through the LangGraph orchestrator to specialized AI agents for processing!
