import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app/data/app.db")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
VERIFICATION_CODE_EXPIRE_MINUTES = int(os.getenv("VERIFICATION_CODE_EXPIRE_MINUTES", "5"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_IMAGE_SIZE_MB = 5
MAX_POST_CONTENT_LENGTH = 280
PAGE_SIZE = 20
