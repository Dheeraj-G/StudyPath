# StudyPath

StudyPath is an AI-powered learning platform that transforms your learning materials (PDFs, images, audio) into interactive knowledge trees and quizzes. The system automatically analyzes uploaded content, generates hierarchical knowledge structures, creates unique assessment questions, and provides personalized study recommendations based on quiz performance.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Backend Components](#backend-components)
- [Frontend Components](#frontend-components)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Data Flow](#data-flow)
- [Deployment](#deployment)

## Overview

StudyPath enables users to:
- **Upload learning materials**: PDF documents, images (JPEG, PNG), and audio files (MP3, WAV, M4A, AAC)
- **Automatic content processing**: Extract text, analyze images with OCR, transcribe audio
- **Knowledge tree generation**: Create hierarchical knowledge structures (up to 5 levels) from parsed content
- **Interactive quizzes**: Generate unique multiple-choice questions for each concept
- **Visual progress tracking**: View quiz results and recommended study order with interactive graph visualizations
- **Real-time updates**: WebSocket-based communication for processing progress and notifications

## Features

### Core Features
- **Multi-format file support**: PDF, images (with OCR), and audio files
- **Intelligent content parsing**: LLM-powered extraction of key concepts and information
- **Hierarchical knowledge trees**: Auto-generated concept hierarchies (1-5 levels)
- **Adaptive quiz generation**: Unique, context-aware multiple-choice questions
- **Performance visualization**: Color-coded knowledge trees showing quiz performance
- **Personalized study recommendations**: Ordered list of topics to review based on incorrect answers
- **Real-time processing**: Live updates via WebSocket for file processing and tree generation

### Advanced Features
- **Question uniqueness validation**: Ensures no duplicate questions across all trees
- **Consolidated tree generation**: Combines related concepts into unified trees
- **Sequential level enforcement**: Validates and fixes tree structure to prevent level skipping
- **Quiz result persistence**: Stores and retrieves quiz history
- **Responsive graph visualization**: Interactive D3.js-based tree visualization

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104.1
- **Web Server**: Uvicorn
- **Language**: Python 3.13
- **Orchestration**: LangGraph 0.2.23
- **LLM Integration**: LangChain 0.2.10 + LangChain-Groq 0.1.4
- **AI Models**: Groq API (Llama models)
  - PDF Processing: `llama-3.1-70b-versatile`
  - Image Analysis: `llama-3.2-11b-vision-preview`
  - Audio Processing: `llama-3.1-8b-instant`
  - Knowledge Trees: `llama-3.1-8b-instant`
- **Database**: Google Cloud Firestore
- **Storage**: Google Cloud Storage (Firebase Storage)
- **Authentication**: Firebase Authentication
- **WebSocket**: FastAPI WebSocket support
- **Image Processing**: PIL/Pillow 10.4.0
- **OCR**: pytesseract 0.3.10
- **PDF Processing**: PyPDF 3.17.0

### Frontend
- **Framework**: Next.js 16.0.0 (App Router)
- **Language**: TypeScript 5
- **UI Library**: React 19.2.0
- **Styling**: Tailwind CSS 4.1.9
- **UI Components**: Radix UI primitives
- **Graph Visualization**: react-d3-tree 3.6.6
- **Authentication**: Firebase SDK 10.7.1
- **HTTP Client**: Native Fetch API
- **State Management**: React Hooks (useState, useEffect)

## Project Structure

```
StudyPath/
├── backend/                    # FastAPI backend application
│   ├── auth/                  # Authentication modules
│   │   └── firebase_auth.py   # Firebase token verification
│   ├── config/                # Configuration management
│   │   └── settings.py        # Application settings and environment variables
│   ├── models/                # Data models
│   │   └── study_models.py   # Pydantic models for API requests/responses
│   ├── routes/                # API route handlers
│   │   ├── file_upload.py     # File upload endpoints
│   │   ├── knowledge_tree.py  # Knowledge tree generation endpoints
│   │   └── langgraph_orchestrator.py  # LangGraph pipeline orchestration
│   ├── services/            # Business logic services
│   │   ├── firestore_service.py      # Firestore database operations
│   │   ├── gcs_service.py           # Google Cloud Storage operations
│   │   ├── knowledge_tree_agent.py   # Knowledge tree generation logic
│   │   ├── knowledge_tree_pipeline.py # Knowledge tree LangGraph pipeline
│   │   ├── langgraph_pipeline.py     # Main file processing pipeline
│   │   └── parsers/                  # Content parsers
│   │       ├── pdf_parser.py         # PDF text and image extraction
│   │       ├── image_parser.py       # Image analysis with OCR
│   │       └── audio_parser.py       # Audio transcription and analysis
│   ├── websocket/             # WebSocket management
│   │   └── connection_manager.py    # WebSocket connection handling
│   ├── main.py                # FastAPI application entry point
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile             # Docker configuration
│   ├── cloud-run.yaml         # Google Cloud Run deployment config
│   └── env.example            # Environment variables template
│
├── frontend/                  # Next.js frontend application
│   ├── app/                   # Next.js App Router pages
│   │   ├── layout.tsx         # Root layout component
│   │   ├── page.tsx           # Main application page
│   │   ├── signin/            # Authentication pages
│   │   │   └── page.tsx       # Sign-in page
│   │   └── globals.css        # Global styles
│   ├── components/            # React components
│   │   ├── auth-guard.tsx     # Authentication wrapper
│   │   ├── chat-panel.tsx     # Main chat interface with quiz functionality
│   │   ├── file-upload-sidebar.tsx  # File upload interface
│   │   ├── notification.tsx   # Toast notification system
│   │   ├── progress-bar.tsx   # File processing progress indicator
│   │   ├── quiz-ready-modal.tsx      # Quiz preparation modal
│   │   ├── quiz-results-modal.tsx    # Quiz results and visualization
│   │   ├── roadmap-modal.tsx  # Study roadmap display
│   │   └── ui/                # Reusable UI components (shadcn/ui)
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── dialog.tsx
│   │       └── input.tsx
│   ├── lib/                   # Utility libraries
│   │   ├── auth-service.ts    # Firebase authentication service
│   │   ├── file-upload-service.ts    # File upload API client
│   │   ├── knowledge-tree-service.ts # Knowledge tree API client
│   │   ├── utils.ts           # Utility functions
│   │   └── websocket-service.ts      # WebSocket client service
│   ├── package.json           # Node.js dependencies
│   ├── tsconfig.json          # TypeScript configuration
│   └── next.config.ts         # Next.js configuration
│
└── README.md                   # This file
```

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  File Upload │  │  Chat Panel  │  │ Quiz System  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                  │
│                    ┌───────▼────────┐                        │
│                    │ WebSocket      │                        │
│                    │ Service        │                        │
│                    └───────┬────────┘                        │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             │ HTTP/WebSocket
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                    Backend (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            WebSocket Connection Manager             │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                         │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │            LangGraph Orchestration Pipeline          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │ PDF Parser │  │Image Parser│  │Audio Parser│    │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘    │   │
│  │        │               │                │           │   │
│  │        └───────────────┼────────────────┘           │   │
│  │                        │                            │   │
│  │                  ┌─────▼──────┐                    │   │
│  │                  │ Consolidate │                    │   │
│  │                  └─────┬──────┘                    │   │
│  │                        │                            │   │
│  │                  ┌─────▼──────┐                    │   │
│  │                  │   Store    │                    │   │
│  │                  │  (Firestore)│                    │   │
│  │                  └────────────┘                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Knowledge Tree Generation Pipeline           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │   │
│  │  │   Retrieve   │─▶│   Generate   │─▶│  Store   │  │   │
│  │  │   Content    │  │    Trees     │  │  Trees   │  │   │
│  │  └──────────────┘  └──────┬───────┘  └──────────┘  │   │
│  │                           │                        │   │
│  │                    ┌──────▼────────┐              │   │
│  │                    │Knowledge Tree  │              │   │
│  │                    │Agent (LLM)     │              │   │
│  │                    └─────────────────┘              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Firestore  │  │     GCS      │  │  Firebase    │     │
│  │   Service    │  │   Service    │  │    Auth      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **File Upload Flow**:
   ```
   User → Frontend → GCS (Signed URL Upload) → Firestore Metadata → WebSocket Notification
   ```

2. **Content Processing Flow**:
   ```
   Upload Complete → LangGraph Pipeline → PDF/Image/Audio Parsers → 
   Groq LLM → Parsed Content → Firestore Storage → WebSocket Progress Updates
   ```

3. **Knowledge Tree Generation Flow**:
   ```
   User Request → Retrieve Parsed Content → Knowledge Tree Agent → 
   LLM Tree Generation → Question Generation → Store Trees → 
   WebSocket Completion → Frontend Display
   ```

4. **Quiz Flow**:
   ```
   Knowledge Trees Ready → Quiz Ready Modal → User Takes Quiz → 
   Answer Submission → Results Calculation → Quiz Results Modal → 
   Store Results → Visualization
   ```

## Backend Components

### Core Services

#### 1. **File Upload Service** (`routes/file_upload.py`)
- **Purpose**: Handles secure file uploads to Google Cloud Storage
- **Endpoints**:
  - `POST /api/files/upload-url`: Generate signed upload URL
  - `POST /api/files/complete`: Mark upload as complete and trigger processing
  - `GET /api/files/files`: List user's uploaded files
  - `POST /api/files/download-url`: Generate signed download URL
  - `DELETE /api/files/files/{file_id}`: Delete file and associated data
- **Features**:
  - User-namespaced file storage
  - Duplicate file detection
  - Automatic processing trigger
  - Derived asset tracking (extracted images, processed content)

#### 2. **LangGraph Orchestrator** (`routes/langgraph_orchestrator.py`)
- **Purpose**: Coordinate the LangGraph pipeline for processing uploaded files
- **Endpoints**:
  - `POST /api/orchestrator/learning-session`: Start learning session processing
- **Pipeline Flow**:
  1. Parse user files (PDF, Image, Audio)
  2. Embed parsed documents (future feature)
  3. Generate learning summary (future feature)
  4. Automatically trigger knowledge tree generation

#### 3. **Knowledge Tree API** (`routes/knowledge_tree.py`)
- **Purpose**: Manage knowledge tree generation and quiz results
- **Endpoints**:
  - `POST /api/knowledge-trees/generate`: Generate knowledge trees from parsed content
  - `GET /api/knowledge-trees`: Retrieve knowledge trees for user
  - `POST /api/knowledge-trees/quiz-results`: Store quiz results
  - `GET /api/knowledge-trees/quiz-results/last`: Get last quiz results

### Parsers

#### 1. **PDF Parser** (`services/parsers/pdf_parser.py`)
- **Model**: `llama-3.1-70b-versatile`
- **Features**:
  - Text extraction and chunking
  - Image extraction from PDFs
  - LLM-powered content analysis (topics, key points, summaries)
  - Concurrent processing with rate limiting
- **Output Structure**:
  ```python
  {
    "type": "pdf",
    "results": [
      {
        "file_path": "...",
        "chunks_processed": 5,
        "llm_outputs": [...],
        "extracted_images": [...]
      }
    ],
    "derived_image_urls": [...]  # For downstream image processing
  }
  ```

#### 2. **Image Parser** (`services/parsers/image_parser.py`)
- **Model**: `llama-3.2-11b-vision-preview`
- **Features**:
  - OCR text extraction using pytesseract
  - Vision model analysis (objects, text, diagrams, concepts)
  - Image preprocessing (grayscale, sharpen, resize)
  - Multimodal input (image URLs + OCR text)
- **Output Structure**:
  ```python
  {
    "type": "image",
    "urls": [...],
    "ocr_texts": [...],
    "raw": "{JSON with objects, text_snippets, diagrams, concepts, description}"
  }
  ```

#### 3. **Audio Parser** (`services/parsers/audio_parser.py`)
- **Model**: `llama-3.1-8b-instant`
- **Features**:
  - Audio URL processing
  - LLM-powered analysis and transcription
- **Output Structure**:
  ```python
  {
    "type": "audio",
    "urls": [...],
    "raw": "{JSON with transcript_outline, key_takeaways, action_items, speakers}"
  }
  ```

### Knowledge Tree Services

#### 1. **Knowledge Tree Agent** (`services/knowledge_tree_agent.py`)
- **Purpose**: Core logic for generating knowledge trees and questions
- **Key Components**:
  - `KnowledgeTreeNode`: Tree node data structure
  - `KnowledgeTreeAgent`: Main agent class
  - `create_knowledge_trees()`: Generate tree structure from content
  - `generate_question_for_node()`: Create unique questions for each node
  - `build_tree_with_questions()`: Recursively build tree with questions
  - `process_parsed_data()`: Main entry point for tree generation
- **Features**:
  - Tree consolidation (prefers 1 tree unless concepts are fundamentally different)
  - Maximum 5 levels (configurable, but trees can be shallower)
  - Sequential level validation (no level skipping)
  - Question uniqueness enforcement
  - Single-attempt question generation (skip on failure)
  - Concise tree and question generation
- **Validation**:
  - `_validate_and_fix_tree_levels()`: Ensures sequential levels without gaps
  - Question uniqueness checking across all trees

#### 2. **Knowledge Tree Pipeline** (`services/knowledge_tree_pipeline.py`)
- **Purpose**: LangGraph pipeline for knowledge tree generation
- **Pipeline Nodes**:
  1. `retrieve_parsed_content_node`: Fetch parsed content from Firestore
  2. `generate_trees_node`: Generate knowledge trees using agent
  3. `store_trees_node`: Store generated trees in Firestore
- **State Management**: Uses `KnowledgeTreeState` TypedDict

### Infrastructure Services

#### 1. **Firestore Service** (`services/firestore_service.py`)
- **Purpose**: All Firestore database operations
- **Collections Structure**:
  ```
  users/{user_id}/
    ├── uploads/{file_id}              # File metadata
    ├── parsed_content/{doc_id}        # Parsed content from files
    ├── knowledge_trees/{tree_id}      # Generated knowledge trees
    ├── quiz_results/{result_id}       # Quiz results history
    ├── derived_assets/{asset_id}     # Processed files (images, etc.)
    └── learning_sessions/{session_id} # Learning session data (future)
  ```
- **Key Methods**:
  - File metadata CRUD operations
  - Parsed content storage and retrieval
  - Knowledge tree storage
  - Quiz results storage and retrieval
  - Derived asset tracking

#### 2. **GCS Service** (`services/gcs_service.py`)
- **Purpose**: Google Cloud Storage operations
- **Features**:
  - Signed URL generation (upload/download)
  - User-namespaced file storage
  - File upload verification
  - File deletion with prefix matching
  - Direct file upload support

#### 3. **WebSocket Connection Manager** (`websocket/connection_manager.py`)
- **Purpose**: Manage WebSocket connections for real-time communication
- **Features**:
  - Per-user connection management
  - Broadcast and personal message sending
  - Connection state tracking
  - Automatic cleanup on disconnect

### LangGraph Pipelines

#### 1. **Main Processing Pipeline** (`services/langgraph_pipeline.py`)
- **Graph Structure**:
  ```
  START → [PDF Node] ┐
         [Image Node]├─→ Wait Node → Consolidate Node → Store Node → END
         [Audio Node]┘
  ```
- **Features**:
  - Parallel processing of PDF, Image, and Audio
  - Progress tracking via WebSocket
  - Result consolidation
  - Image node runs after PDF to process derived images
  - Result merging for multiple runs

#### 2. **Knowledge Tree Pipeline** (`services/knowledge_tree_pipeline.py`)
- **Graph Structure**:
  ```
  START → Retrieve Content → Generate Trees → Store Trees → END
  ```
- **Features**:
  - Automatic tree generation after file processing
  - Progress updates via WebSocket
  - Error handling and reporting

## Frontend Components

### Pages

#### 1. **Main Application Page** (`app/page.tsx`)
- **Purpose**: Main application interface
- **Features**:
  - Authentication state management
  - File upload orchestration
  - Chat interface integration
  - Quiz management
  - Modal state management (Quiz Ready, Quiz Results, Roadmap)
  - WebSocket integration
  - Knowledge tree fetching
  - Quiz results persistence

#### 2. **Sign-In Page** (`app/signin/page.tsx`)
- **Purpose**: User authentication
- **Features**:
  - Google Sign-In via Firebase
  - Auto-redirect if already authenticated
  - Clean, minimal UI

### Components

#### 1. **Chat Panel** (`components/chat-panel.tsx`)
- **Purpose**: Main interaction interface
- **Features**:
  - Message display and input
  - Quiz question rendering
  - Answer button interface (A, B, C, D with full text)
  - Answer submission and feedback
  - One-answer-per-question enforcement
  - Connection status indicator
  - "Last Quiz Results" button
  - User info and logout

#### 2. **File Upload Sidebar** (`components/file-upload-sidebar.tsx`)
- **Purpose**: File upload management
- **Features**:
  - Drag-and-drop file upload
  - File validation (type and size)
  - Upload progress tracking
  - File list display
  - Delete functionality
  - Processing trigger button

#### 3. **Quiz Ready Modal** (`components/quiz-ready-modal.tsx`)
- **Purpose**: Notify user when quiz is ready
- **Features**:
  - Question count display
  - Start quiz button
  - Dismiss option

#### 4. **Quiz Results Modal** (`components/quiz-results-modal.tsx`)
- **Purpose**: Display quiz results and recommended study order
- **Features**:
  - Two-view navigation (Results / Recommended Study Order)
  - Interactive D3.js tree visualization
  - Color-coded nodes:
    - Green: Correct answers
    - Red: Incorrect answers / Recommended study topics
    - Gray: No question generated
  - Recommended study order list with descriptions
  - Tree width: 80% of modal width
  - Zoom and drag functionality

#### 5. **Progress Bar** (`components/progress-bar.tsx`)
- **Purpose**: Visual progress indicator
- **Features**:
  - Parsing progress by file type
  - Percentage display

#### 6. **Notification System** (`components/notification.tsx`)
- **Purpose**: Toast notifications for user feedback
- **Types**: info, success, warning, error
- **Features**: Auto-dismiss, manual dismiss, stacking

#### 7. **Roadmap Modal** (`components/roadmap-modal.tsx`)
- **Purpose**: Display study roadmap (future feature)

### Services (Frontend Libraries)

#### 1. **WebSocket Service** (`lib/websocket-service.ts`)
- **Purpose**: Real-time communication with backend
- **Features**:
  - Connection management
  - Auto-reconnect logic
  - Message type routing
  - Callback system for different message types
  - Progress tracking
  - Error handling

#### 2. **File Upload Service** (`lib/file-upload-service.ts`)
- **Purpose**: File upload API client
- **Features**:
  - Signed URL generation
  - Direct GCS upload
  - File validation (type and size)
  - User file listing
  - File deletion

#### 3. **Knowledge Tree Service** (`lib/knowledge-tree-service.ts`)
- **Purpose**: Knowledge tree API client
- **Features**:
  - Knowledge tree fetching
  - Quiz results storage and retrieval
  - Question flattening utility
  - Authentication token management

#### 4. **Auth Service** (`lib/auth-service.ts`)
- **Purpose**: Firebase authentication management
- **Features**:
  - Google Sign-In
  - Token management
  - Auth state listeners
  - Current user retrieval

## Setup & Installation

### Prerequisites

- **Python**: 3.13+
- **Node.js**: 18+ (for Next.js)
- **Google Cloud Account**: For Firebase/GCS
- **Groq API Key**: For LLM access
- **Tesseract OCR**: For image text extraction (optional but recommended)

### Backend Setup

1. **Clone the repository**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Tesseract OCR** (for image parsing):
   ```bash
   # macOS
   brew install tesseract
   
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

5. **Configure environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

6. **Set up Firebase Service Account**:
   - Download service account JSON from Firebase Console
   - Place as `service-account.json` in backend directory

7. **Run the server**:
   ```bash
   python main.py
   # Or
   uvicorn main:app --reload
   ```

### Frontend Setup

1. **Navigate to frontend**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment variables**:
   Create `.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_WS_URL=ws://localhost:8000
   NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
   ```

4. **Run development server**:
   ```bash
   npm run dev
   ```

5. **Build for production**:
   ```bash
   npm run build
   npm start
   ```

## Configuration

### Environment Variables

#### Backend (.env)
```env
# Google Cloud / Firebase
GOOGLE_CLOUD_PROJECT=studypath-29e9b
GCS_BUCKET_NAME=studypath-29e9b.firebasestorage.app
GOOGLE_APPLICATION_CREDENTIALS=service-account.json

# Groq / LLM (Required)
GROQ_API_KEY=your_groq_api_key_here

# Optional: Override default models
GROQ_PDF_MODEL=llama-3.1-70b-versatile
GROQ_IMAGE_MODEL=llama-3.2-11b-vision-preview
GROQ_AUDIO_MODEL=llama-3.1-8b-instant
GROQ_KNOWLEDGE_TREE_MODEL=llama-3.1-8b-instant

# Server (Optional)
PORT=8000
DEBUG=true
HOST=0.0.0.0
```

#### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
```

### File Type Support

#### PDF
- **Extensions**: `.pdf`
- **MIME Types**: `application/pdf`
- **Max Size**: 100MB

#### Images
- **Extensions**: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`
- **MIME Types**: `image/jpeg`, `image/png`, `image/gif`
- **Max Size**: 100MB
- **Features**: OCR text extraction, vision model analysis

#### Audio
- **Extensions**: `.mp3`, `.wav`, `.m4a`, `.aac`
- **MIME Types**: `audio/mpeg`, `audio/wav`, `audio/mp3`
- **Max Size**: 100MB

## API Documentation

### File Upload Endpoints

#### Generate Upload URL
```http
POST /api/files/upload-url
Authorization: Bearer <firebase_token>
Content-Type: application/json

{
  "file_name": "document.pdf",
  "file_type": "pdf",
  "file_size": 1024000,
  "content_type": "application/pdf"
}
```

#### Complete Upload
```http
POST /api/files/complete
Authorization: Bearer <firebase_token>
Content-Type: application/json

{
  "file_id": "file_id_here",
  "file_size": 1024000
}
```

#### List User Files
```http
GET /api/files/files
Authorization: Bearer <firebase_token>
```

### Knowledge Tree Endpoints

#### Generate Knowledge Trees
```http
POST /api/knowledge-trees/generate
Authorization: Bearer <firebase_token>
Content-Type: application/json

{
  "session_id": "optional_session_id"
}
```

#### Get Knowledge Trees
```http
GET /api/knowledge-trees
Authorization: Bearer <firebase_token>
```

#### Store Quiz Results
```http
POST /api/knowledge-trees/quiz-results
Authorization: Bearer <firebase_token>
Content-Type: application/json

{
  "quiz_results": [...],
  "knowledge_trees": [...]
}
```

#### Get Last Quiz Results
```http
GET /api/knowledge-trees/quiz-results/last
Authorization: Bearer <firebase_token>
```

### WebSocket Messages

#### Message Types

1. **`parsing_progress`**: File parsing progress updates
   ```json
   {
     "type": "parsing_progress",
     "data": {
       "file_type": "pdf",
       "parsed": 2,
       "total": 5,
       "percentage": 40
     }
   }
   ```

2. **`processing_complete`**: Processing completion notification
   ```json
   {
     "type": "processing_complete",
     "content": "Document processing completed successfully!"
   }
   ```

3. **`knowledge_tree_progress`**: Knowledge tree generation progress
   ```json
   {
     "type": "knowledge_tree_progress",
     "content": "Generating questions...",
     "data": {
       "step": "generating_questions",
       "percentage": 60
     }
   }
   ```

4. **`knowledge_tree_complete`**: Knowledge tree generation completion
   ```json
   {
     "type": "knowledge_tree_complete",
     "content": "✅ Knowledge trees generated successfully!",
     "data": {
       "tree_id": "...",
       "status": "completed",
       "total_nodes": 15
     }
   }
   ```

## Data Flow

### Complete User Journey

1. **User Uploads Files**:
   - Frontend validates file (type, size)
   - Generates signed upload URL from backend
   - Uploads directly to GCS
   - Marks upload as complete
   - Backend stores metadata in Firestore

2. **File Processing**:
   - LangGraph orchestrator triggers processing pipeline
   - PDF/Image/Audio parsers process files in parallel
   - LLM analyzes content and extracts information
   - Results stored in Firestore
   - WebSocket sends progress updates

3. **Knowledge Tree Generation**:
   - Automatically triggered after file processing
   - Agent retrieves parsed content
   - LLM generates hierarchical tree structure
   - Questions generated for each node (with uniqueness checks)
   - Trees validated and stored

4. **Quiz Interaction**:
   - User sees "Quiz Ready" modal
   - Takes quiz, answers questions
   - Results calculated and visualized
   - Results stored for future reference

5. **Results Visualization**:
   - Interactive tree graph with color-coded nodes
   - Recommended study order based on incorrect answers
   - Previous quiz results can be retrieved

## Deployment

### Backend Deployment

The backend can be deployed to:
- **Google Cloud Run** (recommended): See `cloud-run.yaml`
- **Docker**: Use provided `Dockerfile`
- **Any Python hosting**: Configure environment variables

### Frontend Deployment

The frontend can be deployed to:
- **Vercel** (recommended for Next.js)
- **Netlify**
- **Any static hosting** with Next.js support

### Environment Setup for Production

1. Set up Firebase project
2. Configure GCS bucket
3. Set environment variables in hosting platform
4. Deploy backend first, then frontend
5. Update frontend `.env.local` with production API URLs

## Key Design Decisions

1. **Tree Consolidation**: Prefers single unified trees unless concepts are fundamentally different, reducing complexity
2. **Question Uniqueness**: Enforces uniqueness across all trees to prevent duplicate questions
3. **Level Validation**: Automatically fixes level gaps to ensure sequential tree structure
4. **Single Attempt Generation**: Questions have one attempt; failures result in skipped nodes
5. **Concise Generation**: Encourages shallow trees and brief questions while maintaining quality
6. **WebSocket Communication**: Real-time updates for better user experience during processing
7. **Direct GCS Upload**: Signed URLs for secure, efficient file uploads

## Future Enhancements

- [ ] Embedding service for semantic search
- [ ] Learning summary generation
- [ ] Progress tracking across sessions
- [ ] Study plan recommendations
- [ ] Multi-language support
- [ ] Collaborative features
- [ ] Mobile app support

---

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
