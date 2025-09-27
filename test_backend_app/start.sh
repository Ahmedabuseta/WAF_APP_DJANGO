#!/bin/bash
# Simple startup script for test backend app

echo "🎯 Starting Test Backend App..."
echo "📍 Will run on http://127.0.0.1:3000"
echo "⏹️  Press Ctrl+C to stop"
echo ""

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run the app
python app.py runserver 127.0.0.1:3000