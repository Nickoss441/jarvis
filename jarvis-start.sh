#!/bin/bash
# Jarvis Desktop Launcher
# Start the Jarvis approvals API server for desktop use

JARVIS_HOME="/Users/nickos/Desktop/jarvis"
cd "$JARVIS_HOME"

# Load environment
set -a
source .env.local
set +a

# Create required directories
mkdir -p ~/.jarvis-dev/{notes,artifacts}

# Start approvals API server
echo "🚀 Starting Jarvis Approvals API..."
python3 -m jarvis approvals-api

# Keep the terminal open
exec bash
