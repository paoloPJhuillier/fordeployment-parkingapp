import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from database import db
from auth.security import require_admin
from models import UserRole, ReservationStatus
import features as feature_flags

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/reports/stats")
async def get_stats(
    building_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    query = {}
    if building_id:
        query["building_id"] = building_id
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}

    reservations = await db.reservations.find(query, {"_id": 0}).to_list(10000)

    total_reservations = len(reservations)
    confirmed = len([r for r in reservations if r["status"] == ReservationStatus.CONFIRMED])
    cancelled = len([r for r in reservations if r["status"] == ReservationStatus.CANCELLED])
    pending = len([r for r in reservations if r["status"] == ReservationStatus.PENDING])
    no_shows = len([r for r in reservations if r.get("no_show_reported", False)])

    buildings_count = await db.buildings.count_documents({})
    total_slots = await db.parking_slots.count_documents({})
    total_users = await db.users.count_documents({"role": UserRole.USER})

    daily_stats = {}
    for res in reservations:
        date = res["date"]
        if date not in daily_stats:
            daily_stats[date] = {"date": date, "total": 0, "confirmed": 0, "cancelled": 0, "no_shows": 0}
        daily_stats[date]["total"] += 1
        if res["status"] == ReservationStatus.CONFIRMED:
            daily_stats[date]["confirmed"] += 1
        elif res["status"] == ReservationStatus.CANCELLED:
            daily_stats[date]["cancelled"] += 1
        if res.get("no_show_reported"):
            daily_stats[date]["no_shows"] += 1

    # Batch fetch all buildings to avoid N+1 queries
    unique_building_ids = list({res["building_id"] for res in reservations})
    all_buildings = await db.buildings.find(
        {"id": {"$in": unique_building_ids}}, {"_id": 0, "id": 1, "name": 1}
    ).to_list(len(unique_building_ids))
    building_name_map = {b["id"]: b["name"] for b in all_buildings}

    building_stats = {}
    for res in reservations:
        bid = res["building_id"]
        building_name = building_name_map.get(bid)
        if not building_name:
            continue  # Skip reservations for deleted/unknown buildings
        if bid not in building_stats:
            building_stats[bid] = {
                "building_id": bid,
                "building_name": building_name,
                "total": 0,
                "confirmed": 0,
            }
        building_stats[bid]["total"] += 1
        if res["status"] == ReservationStatus.CONFIRMED:
            building_stats[bid]["confirmed"] += 1

    return {
        "summary": {
            "total_reservations": total_reservations,
            "confirmed": confirmed,
            "cancelled": cancelled,
            "pending": pending,
            "no_shows": no_shows,
            "buildings_count": buildings_count,
            "total_slots": total_slots,
            "total_users": total_users,
            "occupancy_rate": round((confirmed / total_slots * 100) if total_slots > 0 else 0, 2),
        },
        "daily_breakdown": sorted(daily_stats.values(), key=lambda d: d.get("date") or ""),
        "building_breakdown": list(building_stats.values()),
    }


@router.post("/reports/ai-insights")
async def generate_ai_insights(
    building_id: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    # Hard gate: if Ops disabled the feature (or it auto-resolved to off
    # because EMERGENT_LLM_KEY is empty), don't even import the SDK — just
    # tell the caller cleanly. The frontend uses the same flag via
    # /api/system/features to hide the UI surface.
    if not feature_flags.ai_insights_enabled():
        raise HTTPException(
            status_code=503,
            detail="AI Insights are disabled in this deployment.",
        )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        query = {}
        building_name = "All Buildings"
        if building_id:
            query["building_id"] = building_id
            b = await db.buildings.find_one({"id": building_id}, {"_id": 0})
            if b:
                building_name = b["name"]

        reservations = await db.reservations.find(query, {"_id": 0}).to_list(1000)
        buildings = await db.buildings.find({}, {"_id": 0}).to_list(100)
        total_slots = await db.parking_slots.count_documents(query if building_id else {})
        total_users = await db.users.count_documents({"role": UserRole.USER})

        confirmed_count = len([r for r in reservations if r["status"] == ReservationStatus.CONFIRMED])
        cancelled_count = len([r for r in reservations if r["status"] == ReservationStatus.CANCELLED])
        pending_count = len([r for r in reservations if r["status"] == ReservationStatus.PENDING])
        no_show_count = len([r for r in reservations if r.get("no_show_reported", False)])
        occupancy_rate = round((confirmed_count / total_slots * 100) if total_slots > 0 else 0, 2)

        data_snapshot = {
            "buildings": len(buildings),
            "total_slots": total_slots,
            "total_users": total_users,
            "total_reservations": len(reservations),
            "confirmed": confirmed_count,
            "cancelled": cancelled_count,
            "pending": pending_count,
            "no_shows": no_show_count,
            "occupancy_rate": occupancy_rate,
        }

        data_summary = f"""
Parking System Data ({building_name}):
- Total Buildings: {len(buildings)}
- Total Parking Slots: {total_slots}
- Total Users: {total_users}
- Total Reservations: {len(reservations)}
- Confirmed: {confirmed_count}
- Cancelled: {cancelled_count}
- Pending: {pending_count}
- No-Shows: {no_show_count}
- Occupancy Rate: {occupancy_rate}%
"""

        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            return {"insights": "AI insights not available. Please configure EMERGENT_LLM_KEY."}

        chat = LlmChat(
            api_key=api_key,
            session_id=f"parking-insights-{str(uuid.uuid4())[:8]}",
            system_message="You are a parking analytics expert. Analyze the data and provide 3-5 actionable insights. Use markdown formatting with bold headers for each insight. Be concise and business-focused. Format each insight as: **Insight Title**: explanation and recommendation.",
        ).with_model("openai", "gpt-4o")

        user_message = UserMessage(text=f"Analyze this parking data and provide insights:\n{data_summary}")
        response = await chat.send_message(user_message)

        # Persist the insight
        insight_doc = {
            "id": str(uuid.uuid4()),
            "building_id": building_id,
            "building_name": building_name,
            "content": response,
            "data_snapshot": data_snapshot,
            "generated_by": current_user["id"],
            "generated_by_name": f"{current_user['first_name']} {current_user['last_name']}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.ai_insights.insert_one(insight_doc)

        return {
            "id": insight_doc["id"],
            "insights": response,
            "data_snapshot": data_snapshot,
            "building_name": building_name,
            "generated_at": insight_doc["generated_at"],
        }
    except Exception as e:
        logger.error(f"AI insights error: {e}")
        return {"insights": f"Unable to generate AI insights: {str(e)}"}


@router.get("/reports/ai-insights/history")
async def get_insights_history(
    limit: int = 10,
    current_user: dict = Depends(require_admin),
):
    if not feature_flags.ai_insights_enabled():
        return []
    insights = await db.ai_insights.find(
        {}, {"_id": 0}
    ).sort("generated_at", -1).to_list(limit)
    return insights


@router.delete("/reports/ai-insights/{insight_id}")
async def delete_insight(insight_id: str, current_user: dict = Depends(require_admin)):
    result = await db.ai_insights.delete_one({"id": insight_id})
    if result.deleted_count == 0:
        return {"message": "Insight not found"}
    return {"message": "Insight deleted"}
