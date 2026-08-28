#!/usr/bin/env bash
# ManakMitra — Render build script
#
# Render calls this during the build phase. It runs on a Linux container with
# Python already available (Render's Python runtime). We install Node ourselves
# for the frontend build, then rebuild the ChromaDB vector index from the
# committed seed corpus.
#
# Build command (set in render.yaml or dashboard):
#   chmod +x build.sh && ./build.sh

set -o errexit  # exit on first error

echo "=== [1/4] Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [2/4] Installing Node.js for frontend build ==="
# Render's Python runtime doesn't include Node by default.
# Use the Node version specified in env, or default to 20.
NODE_VERSION="${NODE_VERSION:-20}"
curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
apt-get install -y nodejs || true
# If apt fails (non-root), try nvm fallback — but on Render's build env
# apt should work. If Node is already available, skip.
node --version || { echo "Node.js installation failed"; exit 1; }

echo "=== [3/4] Building the frontend ==="
cd frontend
npm install
npm run build
cd ..

echo "=== [4/4] Building the vector index ==="
# The ChromaDB index is gitignored (rebuilt from the seed corpus on every deploy).
# This also downloads the sentence-transformers model (~90 MB) on first run.
python -m ingestion.build_index --rebuild

echo ""
echo "=== Build complete ==="
echo "  Frontend bundle: frontend/dist/"
echo "  Vector index:    data/chroma/"
