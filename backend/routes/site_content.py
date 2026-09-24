from fastapi import APIRouter, HTTPException, Depends

from database import db
from auth.security import require_admin
from models import SiteContentUpdate

router = APIRouter()


@router.get("/site-content")
async def get_site_content():
    content = await db.site_content.find_one({"key": "login_page"}, {"_id": 0})
    if not content:
        return {
            "heading_line1": "Reserve Your",
            "heading_highlight": "Parking Spot",
            "heading_line3": "with Ease",
            "description": "Seamlessly book, manage, and track your parking reservations across all Cebuana Lhuillier buildings.",
            "badge1_text": "Multiple Buildings",
            "badge2_text": "Secure Access",
            "announcement": "",
        }
    return {k: v for k, v in content.items() if k != "key"}


@router.put("/admin/site-content")
async def update_site_content(data: SiteContentUpdate, current_user: dict = Depends(require_admin)):
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_data["key"] = "login_page"
    await db.site_content.update_one(
        {"key": "login_page"},
        {"$set": update_data},
        upsert=True,
    )
    return {"message": "Site content updated"}
