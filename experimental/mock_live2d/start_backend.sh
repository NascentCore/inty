#!/bin/bash
cd backend
pip install -r requirements.txt
export GEMINI_API_KEY="your_gemini_api_key_here"
python main.py