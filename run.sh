#!/bin/bash
set -e
cd "$(dirname "$0")"
echo ""
echo "  DealScope — first-pass rental property analysis"
echo "  ==============================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "  Python 3 not found. Install from https://python.org"
    exit 1
fi

if [ ! -d .venv ]; then
    echo "  Creating virtual environment..."
    python3 -m venv .venv
fi
echo "  Installing dependencies from requirements.txt..."
.venv/bin/pip install --quiet -r requirements.txt

echo ""
echo "  Open your browser at: http://localhost:${PORT:-5000}"
echo "  (Set HOST=0.0.0.0 to share on your network; only on a trusted network.)"
echo "  Press Ctrl+C to stop"
echo ""
exec .venv/bin/python app.py
