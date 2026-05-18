from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import os

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
    "happy": ["/images/happy1.jpg", "/images/happy2.jpg"],
    "sad": ["/images/sad1.jpg", "/images/sad2.jpg"],
    "angry": ["/images/angry1.jpg", "/images/angry2.jpg"],
    "surprised": ["/images/surprised1.jpg", "/images/surprised2.jpg"],
    "neutral": ["/images/neutral1.jpg", "/images/neutral2.jpg"],
    "excited": ["/images/excited1.jpg", "/images/excited2.jpg"],
    "worried": ["/images/worried1.jpg", "/images/worried2.jpg"],
}


def get_gemini_response(
    message: str, conversation_history: List[ChatMessage]
) -> str:
    """Get response from Gemini API"""
    model = genai.GenerativeModel("gemini-pro")

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
        raise HTTPException(
            status_code=500, detail=f"Gemini API error: {str(e)}"
        )


def analyze_sentiment_with_gemini(message: str) -> str:
    """Analyze sentiment of the message using Gemini"""
    model = genai.GenerativeModel("gemini-pro")

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
        valid_sentiments = [
            "happy",
            "sad",
            "angry",
            "surprised",
            "neutral",
            "excited",
            "worried",
        ]
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
        return images[0]
    return None


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        # Get response from Gemini
        bot_response = get_gemini_response(
            request.message, request.conversation_history
        )

        # Analyze sentiment of the bot's response
        sentiment = analyze_sentiment_with_gemini(bot_response)

        # Select appropriate image
        image_url = select_image(sentiment)

        return ChatResponse(message=bot_response, image_url=image_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Chatbot with Image Selection Demo API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
