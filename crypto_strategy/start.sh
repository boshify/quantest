#!/bin/bash
set -e

# Use the PORT environment variable if provided, otherwise default to 8000
PORT=${PORT:-8000}

# Run the application
exec python -m uvicorn app:app --host 0.0.0.0 --port $PORT 