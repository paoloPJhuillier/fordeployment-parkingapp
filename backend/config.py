import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# JWT Config
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = float(os.environ.get('JWT_EXPIRATION_HOURS', 24))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Security constants
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_TAGS = {'vip', 'group_head'}

# Cookie config
COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = int(JWT_EXPIRATION_HOURS * 3600)
# Controls the `Secure` flag on auth cookies. Must be True behind TLS (production),
# should be False for plain-HTTP local Docker testing.
IS_SECURE = os.environ.get("COOKIE_SECURE", "true").strip().lower() in ("1", "true", "yes")

# Static files directory for uploads. Override with UPLOAD_DIR env var for
# containerized deployments where uploads must live on a mounted volume.
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(ROOT_DIR / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("parking_app")
