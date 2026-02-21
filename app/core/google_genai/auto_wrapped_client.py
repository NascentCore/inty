from google import genai
from langsmith import wrappers

def main():
    # genai.Client() reads GOOGLE_API_KEY / GEMINI_API_KEY from the environment
    