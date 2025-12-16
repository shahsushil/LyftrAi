#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

# --- 1. Python Virtual Environment Setup ---
ENV_NAME=".venv"
echo "--- Setting up Python environment ---"
if [ ! -d "$ENV_NAME" ]; then
    echo "Creating virtual environment..."
    python -m venv "$ENV_NAME"
fi
source "$ENV_NAME/bin/activate"
pip install --upgrade pip

# --- 2. Install Python Dependencies ---
echo "Installing Python dependencies..."
pip install -r requirements.txt

# --- 3. Install Playwright Browsers ---
echo "Installing Playwright browsers..."
playwright install

# --- 4. Build React Frontend ---
echo "--- Building React Frontend ---"
# NOTE: Requires Node.js and npm/yarn/pnpm to be installed globally on the system
pushd frontend
npm install
npm run build
popd

# --- 5. Start the Web Server ---
echo "--- Starting FastAPI server on http://localhost:8000 ---"
# Serve from the root directory to access the backend folder
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --app-dir .