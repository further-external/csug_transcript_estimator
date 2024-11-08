#!/bin/bash

# Environment Variables
PROJECT="ai-transcript-438020"
REGION="us-central1"


# Authenticate with Google Cloud
echo "Authenticating with Google Cloud..."
gcloud auth login
gcloud auth application-default set-quota-project $PROJECT
gcloud config set project $PROJECT


SERVICE_NAME="transfer-credits-app"
IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Build the container image and submit it to Google Container Registry
echo "Building the container image..."
# Build the container image using docker buildx
IMAGE="us-central1-docker.pkg.dev/$PROJECT/jp/$SERVICE_NAME:latest"
echo "Building the container image..."
docker buildx build --platform linux/amd64,linux/arm64 -t $IMAGE --push .


# Deploy the container to Cloud Run with CPU, memory, and port configuration
CPU="2"          # Number of vCPUs
MEMORY="2Gi"     # Memory size
PORT="8080"      # Default port

# Deploy the container to Cloud Run
echo "Deploying the container to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --cpu $CPU \
  --memory $MEMORY \
  --port $PORT

# Print the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "Service deployed to: $SERVICE_URL"
