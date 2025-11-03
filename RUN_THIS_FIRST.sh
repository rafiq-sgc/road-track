#!/bin/bash

# Road Tracker Pro - Quick Setup Script
# Run this to get started immediately

set -e

echo "🚗 Road Tracker Pro - Quick Setup"
echo "================================="
echo ""

# Check Python version
echo "📌 Checking Python version..."
python3 --version || { echo "❌ Python 3 not found. Please install Python 3.10+"; exit 1; }

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create config if not exists
if [ ! -f "app/config/roi_config.json" ]; then
    echo "⚙️  Creating default configuration..."
    cp app/config/roi_config.example.json app/config/roi_config.json
    echo "✅ Config created at: app/config/roi_config.json"
    echo "   (Edit this file to customize ROIs)"
fi

# Create violations directory
echo "📁 Creating violations directory..."
mkdir -p violations/crops violations/fullframes violations/metadata

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the application:"
echo ""
echo "   uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "   Then open: http://localhost:8000"
echo ""
echo "📚 Documentation:"
echo "   - Quick start: QUICK_START.md"
echo "   - All features: FEATURES_AND_USAGE.md"
echo "   - Deployment: DEPLOYMENT_GUIDE.md"
echo ""
echo "🎯 Your main goal: Detect opposite-direction violators"
echo "   Set 'auto_lane_direction: true' in config for automatic detection!"
echo ""
echo "Happy tracking! 🎉"

