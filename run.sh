#!/bin/bash
echo ""
echo "  🏠 DealScope — Real Estate Investment Analyzer"
echo "  ==============================================="
echo "  Zero API keys required"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python 3 not found. Install from https://python.org"
    exit 1
fi

# Install dependencies
echo "  Installing dependencies..."
pip3 install flask flask-cors requests --quiet --break-system-packages 2>/dev/null || \
pip3 install flask flask-cors requests --quiet 2>/dev/null

echo "  Starting server..."
echo ""
echo "  ✅ Open your browser at: http://localhost:5000"
echo "  ✅ Share with others on your network: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "  Press Ctrl+C to stop"
echo ""
python3 app.py
