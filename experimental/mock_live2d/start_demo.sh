#!/bin/bash
echo "🚀 Starting Chatbot Demo (Demo Mode - No API Key Required)"
echo "=================================================="

# Start backend in demo mode
echo "📡 Starting backend server..."
cd backend
python3 demo_main.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend
echo "🎨 Starting frontend..."
cd ../frontend
npm install --silent
npm start &
FRONTEND_PID=$!

echo "✅ Demo started successfully!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for user to stop
wait