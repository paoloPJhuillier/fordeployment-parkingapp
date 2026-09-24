import uuid
import logging
from datetime import datetime, timezone

from database import db

logger = logging.getLogger(__name__)


async def create_notification(user_id: str, title: str, message: str, notification_type: str = "info"):
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.notifications.insert_one(notification)
    logger.info(f"Created notification for user {user_id}: {title} (inserted_id: {result.inserted_id})")
