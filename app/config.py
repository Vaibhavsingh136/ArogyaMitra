"""
ArogyaMitra Configuration & Brand Constants
Source of truth: brandguideline.md & systemdesign.md
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
SAMPLE_DOCS_DIR = BASE_DIR / "app" / "static" / "sample_docs"

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SAMPLE_DOCS_DIR, exist_ok=True)

# 3-Tier Database Separation Architecture
# Database A: Patient Identity & Authentication DB
PATIENT_IDENTITY_DB_PATH = DATA_DIR / "patient_identity.db"

# Database B: Staff Identity & Credentials DB (Doctor, Radiologist, Admin)
STAFF_IDENTITY_DB_PATH = DATA_DIR / "staff_identity.db"

# Database C: Medical / Clinical Records DB (Encrypted at rest)
MEDICAL_DB_PATH = DATA_DIR / "medical_records.db"

# Legacy DB Path (kept for reference/migration if needed)
DB_PATH = MEDICAL_DB_PATH

# Encryption Key Management Configuration (Defense in Depth)
# Key is separated from the database storage layer
ENCRYPTION_KEY_SECRET = os.environ.get("AROGYAMITRA_ENCRYPTION_KEY", "ArogyaMitra_ClinicalData_Key_2026_AES256_DefenseInDepth")
AUTH_SECRET_KEY = os.environ.get("AROGYAMITRA_AUTH_SECRET", "arogyamitra_secure_hackathon_token_secret_2026")

# Brand Guidelines Colors (brandguideline.md)
BRAND_PRIMARY = "#7CA68D"      # Arogya Green (Primary CTA, buttons, active states)
BRAND_SECONDARY = "#C0C3B9"    # Soft Sage Gray (Borders, muted panels, secondary UI)
BRAND_BACKGROUND = "#F3EFE3"   # Calm Neutral Background (Patient kiosk screens)
BRAND_TEXT_DARK = "#1E293B"    # Charcoal / Dark Slate for crisp readability
BRAND_CARD_BG = "#FFFFFF"      # Crisp card white

# Supported Languages in ArogyaMitra (Native scripts & locale codes)
SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English", "native": "English", "speech_code": "en-IN", "flag": ""},
    {"code": "hi", "name": "Hindi", "native": "हिन्दी", "speech_code": "hi-IN", "flag": ""},
    {"code": "bn", "name": "Bengali", "native": "বাংলা", "speech_code": "bn-IN", "flag": ""},
    {"code": "te", "name": "Telugu", "native": "తెలుగు", "speech_code": "te-IN", "flag": ""},
    {"code": "ta", "name": "Tamil", "native": "தமிழ்", "speech_code": "ta-IN", "flag": ""},
    {"code": "mr", "name": "Marathi", "native": "मराठी", "speech_code": "mr-IN", "flag": ""},
    {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી", "speech_code": "gu-IN", "flag": ""},
    {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ", "speech_code": "kn-IN", "flag": ""},
    {"code": "or", "name": "Odia", "native": "ଓଡ଼ିଆ", "speech_code": "or-IN", "flag": ""},
    {"code": "ml", "name": "Malayalam", "native": "മലയാളം", "speech_code": "ml-IN", "flag": ""},
    {"code": "pa", "name": "Punjabi", "native": "ਪੰਜਾਬੀ", "speech_code": "pa-IN", "flag": ""},
]

# System Defaults
SESSION_TIMEOUT_MINUTES = 60
MOCK_ABDM_ENABLED = True
AYUSH_MODE_ENABLED_DEFAULT = True
ENVIRONMENT = os.environ.get("AROGYAMITRA_ENV", "development")
# When true, forces DB initialization and demo seed even in production
FORCE_INIT_DB = os.environ.get("FORCE_INIT_DB", "false").lower() in ("1", "true", "yes")
# Comma-separated list of IPs allowed to generate force-init tokens (default localhost)
ADMIN_ALLOWED_IPS = [ip.strip() for ip in os.environ.get("AROGYAMITRA_ADMIN_ALLOWED_IPS", "127.0.0.1,::1").split(",") if ip.strip()]

