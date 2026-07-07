#!/bin/bash
# Hermes Switch Manager — Quick Setup Script
set -e

echo "╔══════════════════════════════════════════╗"
echo "║   Hermes Switch Manager — Setup         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ─── Backend ───
echo "→ Setting up backend..."
cd backend

if [ ! -f .env ]; then
    cp .env.example .env
    echo "  ✓ Created .env from .env.example"
    echo "  ⚠ Edit .env to add your OPENAI_API_KEY and SSH credentials"
fi

echo "  → Installing Python dependencies..."
pip install -r requirements.txt -q
echo "  ✓ Backend dependencies installed"

cd ..

# ─── Frontend ───
echo "→ Setting up frontend..."
cd frontend

if [ ! -d node_modules ]; then
    echo "  → Installing Node.js dependencies..."
    npm install --silent
    echo "  ✓ Frontend dependencies installed"
fi

cd ..

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Setup Complete!                        ║"
echo "║                                          ║"
echo "║   Backend:                               ║"
echo "║     cd backend                           ║"
echo "║     uvicorn main:app --reload            ║"
echo "║                                          ║"
echo "║   Frontend:                              ║"
echo "║     cd frontend                          ║"
echo "║     npm run dev                          ║"
echo "║                                          ║"
echo "║   Docker:                                ║"
echo "║     docker-compose up -d                 ║"
echo "╚══════════════════════════════════════════╝"
