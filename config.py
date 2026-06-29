import os
from dotenv import load_dotenv

load_dotenv(".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_DAYS", "7"))

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./chatgpt.db")

AI_PROVIDER = os.environ.get("AI_PROVIDER", "groq").lower()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_UPLOAD_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "text/plain", "text/csv", "application/json",
    "application/pdf",
}
