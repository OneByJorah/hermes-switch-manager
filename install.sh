#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Installing hermes-switch-manager ==="

if ! command -v docker &> /dev/null; then
    echo "Docker is required but not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Docker Compose is required but not installed."
    exit 1
fi

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env from .env.example. Please review and set real values before production use."
    elif [ -f backend/.env.example ]; then
        cp backend/.env.example .env
        echo "Created .env from backend/.env.example. Please review and set real values before production use."
    else
        echo "No .env.example found; creating empty .env"
        touch .env
    fi
fi

echo "Building and starting hermes-switch-manager on port 3000..."
if docker compose version &> /dev/null; then
    docker compose up --build -d
else
    docker-compose up --build -d
fi

echo "hermes-switch-manager installed. Access: http://localhost:3000"
