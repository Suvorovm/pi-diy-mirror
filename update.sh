#!/bin/bash

git fetch

git pull

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Pulling latest changes..."
git pull

echo "==> Activating virtual environment..."
source .venv/bin/activate

echo "==> Installing dependencies..."
pip install -q -r requirements.txt

echo "==> Restarting service..."
sudo systemctl restart smart_mirror

echo ""
echo "Done! Status:"
sudo systemctl status smart_mirror --no-pager -l
