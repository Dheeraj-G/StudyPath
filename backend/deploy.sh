#!/bin/bash

# Deployment script for StudyPath Backend to Google Cloud Run

set -e

# Configuration
PROJECT_ID="your-gcp-project-id"
SERVICE_NAME="studypath-backend"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Deploying StudyPath Backend to Google Cloud Run..."

# Build and push Docker image
echo "📦 Building Docker image..."
docker build -t $IMAGE_NAME .

echo "📤 Pushing image to Google Container Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 300 \
  --concurrency 100 \
  --set-env-vars "PORT=8000" \
  --set-env-vars "GCS_BUCKET_NAME=studypath-uploads"

echo "✅ Deployment complete!"
echo "🌐 Service URL: https://$SERVICE_NAME-$REGION.a.run.app"
