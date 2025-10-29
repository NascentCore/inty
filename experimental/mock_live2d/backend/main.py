from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import os
import json
import base64
from pathlib import Path

app = FastAPI(title="Chatbot with Image Selection Demo")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for images
app.mount("/images", StaticFiles(directory="images"), name="images")

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    image_url: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    message: str
    image_url: Optional[str] = None

# Image database with sentiment labels
IMAGE_DATABASE = {
    "happy": [
        {"url": "/images/happy1.jpg", "description": "Smiling character with bright eyes"},
        {"url": "/images/happy2.jpg", "description": "Joyful expression with raised eyebrows"},
    ],
    "sad": [
        {"url": "/images/sad1.jpg", "description": "Droopy eyes and downturned mouth"},
        {"url": "/images/sad2.jpg", "description": "Tears and melancholic expression"},
    ],
    "angry": [
        {"url": "/images/angry1.jpg", "description": "Furrowed brows and clenched jaw"},
        {"url": "/images/angry2.jpg", "description": "Intense glare with tight lips"},
    ],
    "surprised": [
        {"url": "/images/surprised1.jpg", "description": "Wide eyes and open mouth"},
        {"url": "/images/surprised2.jpg", "description": "Raised eyebrows and shocked expression"},
    ],
    "neutral": [
        {"url": "/images/neutral1.jpg", "description": "Calm expression with gentle smile"},
        {"url": "/images/neutral2.jpg", "description": "Peaceful look with soft eyes"},
    ],
    "excited": [
        {"url": "/images/excited1.jpg", "description": "Bright smile with sparkling eyes"},
        {"url": "/images/excited2.jpg", "description": "Energetic expression with wide grin"},
    ],
    "worried": [
        {"url": "/images/worried1.jpg", "description": "Concerned look with furrowed brows"},
        {"url": "/images/worried2.jpg", "description": "Anxious expression with tense mouth"},
    ],
}

def get_gemini_response(message: str, conversation_history: List[ChatMessage]) -> str:
    """Get response from Gemini API"""
    model = genai.GenerativeModel('gemini-pro')
    
    # Build conversation context
    context = "你是一个友好的AI助手，请用中文回复用户的问题。"
    
    # Add conversation history
    for msg in conversation_history[-10:]:  # Keep last 10 messages for context
        if msg.role == "user":
            context += f"\n用户: {msg.content}"
        else:
            context += f"\n助手: {msg.content}"
    
    context += f"\n用户: {message}"
    
    try:
        response = model.generate_content(context)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

def analyze_sentiment_with_gemini(message: str) -> str:
    """Analyze sentiment of the message using Gemini"""
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
请分析以下消息的情感，并从以下选项中选择最匹配的一个：
happy, sad, angry, surprised, neutral, excited, worried

消息: "{message}"

只返回一个情感标签，不要其他内容。
"""
    
    try:
        response = model.generate_content(prompt)
        sentiment = response.text.strip().lower()
        
        # Validate sentiment
        valid_sentiments = ["happy", "sad", "angry", "surprised", "neutral", "excited", "worried"]
        if sentiment in valid_sentiments:
            return sentiment
        else:
            return "neutral"  # Default fallback
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return "neutral"

def select_image(sentiment: str) -> Optional[str]:
    """Select an appropriate image based on sentiment"""
    if sentiment in IMAGE_DATABASE:
        images = IMAGE_DATABASE[sentiment]
        # For simplicity, just return the first image
        # In a real app, you might want to randomize or cycle through images
        return images[0]["url"]
    return None

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        # Get response from Gemini
        bot_response = get_gemini_response(request.message, request.conversation_history)
        
        # Analyze sentiment of the bot's response
        sentiment = analyze_sentiment_with_gemini(bot_response)
        
        # Select appropriate image
        image_url = select_image(sentiment)
        
        return ChatResponse(
            message=bot_response,
            image_url=image_url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Remove the get_image endpoint since we're using StaticFiles now

@app.get("/")
async def root():
    return {"message": "Chatbot with Image Selection Demo API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)