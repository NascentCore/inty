from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import random

app = FastAPI(title="Chatbot with Image Selection Demo (Demo Mode)")

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

# Simple demo responses
DEMO_RESPONSES = {
    "greeting": [
        "你好！很高兴见到你！",
        "嗨！今天过得怎么样？",
        "你好呀！有什么我可以帮助你的吗？",
    ],
    "weather": [
        "今天天气很不错呢！阳光明媚，适合出去走走。",
        "天气有点阴，不过很凉爽舒适。",
        "今天下雨了，记得带伞哦！",
    ],
    "help": [
        "当然可以！我很乐意帮助你。",
        "没问题，我会尽力协助你的。",
        "好的，请告诉我你需要什么帮助。",
    ],
    "default": [
        "这是一个很有趣的问题！",
        "让我想想怎么回答你...",
        "这让我想到了很多有趣的事情。",
        "你的问题很有深度呢！",
    ],
}


def get_demo_response(message: str) -> str:
    """Get a demo response based on keywords"""
    message_lower = message.lower()

    if any(word in message_lower for word in ["你好", "hi", "hello", "嗨"]):
        return random.choice(DEMO_RESPONSES["greeting"])
    elif any(
        word in message_lower for word in ["天气", "weather", "下雨", "晴天"]
    ):
        return random.choice(DEMO_RESPONSES["weather"])
    elif any(
        word in message_lower for word in ["帮助", "help", "帮忙", "协助"]
    ):
        return random.choice(DEMO_RESPONSES["help"])
    else:
        return random.choice(DEMO_RESPONSES["default"])


def analyze_sentiment_demo(message: str) -> str:
    """Demo sentiment analysis based on keywords"""
    message_lower = message.lower()

    if any(
        word in message_lower
        for word in [
            "开心",
            "高兴",
            "快乐",
            "兴奋",
            "太棒了",
            "awesome",
            "great",
        ]
    ):
        return "happy"
    elif any(
        word in message_lower
        for word in ["难过", "伤心", "沮丧", "失望", "sad", "upset"]
    ):
        return "sad"
    elif any(
        word in message_lower
        for word in ["生气", "愤怒", "恼火", "angry", "mad"]
    ):
        return "angry"
    elif any(
        word in message_lower
        for word in ["惊讶", "震惊", "意外", "surprised", "wow"]
    ):
        return "surprised"
    elif any(
        word in message_lower
        for word in ["担心", "焦虑", "紧张", "worried", "anxious"]
    ):
        return "worried"
    elif any(
        word in message_lower
        for word in ["兴奋", "激动", "excited", "thrilled"]
    ):
        return "excited"
    else:
        return "neutral"


def select_image(sentiment: str) -> Optional[str]:
    """Select an appropriate image based on sentiment"""
    if sentiment in IMAGE_DATABASE:
        images = IMAGE_DATABASE[sentiment]
        return random.choice(images)
    return None


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint (demo mode)"""
    try:
        # Get demo response
        bot_response = get_demo_response(request.message)

        # Analyze sentiment of the bot's response
        sentiment = analyze_sentiment_demo(bot_response)

        # Select appropriate image
        image_url = select_image(sentiment)

        return ChatResponse(message=bot_response, image_url=image_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {
        "message": "Chatbot with Image Selection Demo API (Demo Mode - No Gemini API required)"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
