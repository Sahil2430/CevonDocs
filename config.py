import os
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER          = os.environ.get("AI_PROVIDER", "openai").lower()
OPENAI_API_KEY       = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY       = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY         = os.environ.get("GROQ_API_KEY", "")
OPENAI_MODEL         = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_MODEL         = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
GROQ_MODEL           = os.environ.get("GROQ_MODEL", "llama-3.2-11b-vision-preview")
MODERATION_PROVIDER  = os.environ.get("MODERATION_PROVIDER", "auto").lower()
MODERATION_MODEL     = os.environ.get("MODERATION_MODEL", "omni-moderation-latest")

REVIEW_THRESHOLD     = float(os.environ.get("REVIEW_THRESHOLD", "0.75"))
MODERATION_THRESHOLD = float(os.environ.get("MODERATION_THRESHOLD", "0.7"))
ENABLE_PROVIDER_FALLBACK = os.environ.get("ENABLE_PROVIDER_FALLBACK", "true").lower() == "true"
MAX_IMAGE_DIMENSION  = int(os.environ.get("MAX_IMAGE_DIMENSION", "2048"))
UPLOAD_DIR           = os.environ.get("UPLOAD_DIR", "uploads")
DATABASE_PATH        = os.environ.get("DATABASE_PATH", "cevondocs.db")
COST_PER_TOKEN       = float(os.environ.get("COST_PER_TOKEN", "0.0000025"))
APP_VERSION          = "1.0.0"

