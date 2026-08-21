#!/bin/bash

# Kill any process on port 8286
echo "Cleaning up port 8286..."
lsof -ti:8286 | xargs kill -9 2>/dev/null || true
sleep 1

# Start the server
echo "Starting Ephemera API..."
npm run dev:node
