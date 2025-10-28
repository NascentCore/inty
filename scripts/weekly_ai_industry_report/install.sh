#!/bin/bash
# Installation script for AI Industry Weekly Report Generator

echo "🚀 Installing AI Industry Weekly Report Generator..."
echo "=================================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Make scripts executable
chmod +x weekly_ai_industry_report.py
chmod +x test_weekly_ai_report.py
chmod +x example_usage.py

echo "✅ Scripts made executable"

# Run tests
echo "🧪 Running tests..."
python3 test_weekly_ai_report.py

if [ $? -eq 0 ]; then
    echo "✅ All tests passed"
else
    echo "⚠️  Some tests failed, but installation completed"
fi

echo ""
echo "🎉 Installation completed!"
echo ""
echo "📋 Next steps:"
echo "1. Set your environment variables:"
echo "   export GOOGLE_CSE_API_KEY='your_api_key'"
echo "   export GOOGLE_CSE_ID='your_cse_id'"
echo "   export GEMINI_API_KEY='your_gemini_key'"
echo ""
echo "2. Run the report generator:"
echo "   python3 weekly_ai_industry_report.py"
echo ""
echo "3. See examples:"
echo "   python3 example_usage.py"
echo ""
echo "4. Or use the launcher from the main scripts directory:"
echo "   python3 ../ai_weekly_report.py"
echo ""
echo "📚 For more information, see README.md"