from database import db
from models.reservation import ReservationResponse


async def batch_enrich_reservations(reservations: list) -> list:
    if not reservations:
        return []

    slot_ids = list({r["slot_id"] for r in reservations})
    floor_ids = list({r.get("floor_id") for r in reservations if r.get("floor_id")})
    building_ids = list({r["building_id"] for r in reservations})
    vehicle_ids = list({r["vehicle_id"] for r in reservations})
    user_ids = list({r["user_id"] for r in reservations})

    slots_list = await db.parking_slots.find({"id": {"$in": slot_ids}}, {"_id": 0}).to_list(len(slot_ids))
    floors_list = await db.floors.find({"id": {"$in": floor_ids}}, {"_id": 0}).to_list(len(floor_ids)) if floor_ids else []
    buildings_list = await db.buildings.find({"id": {"$in": building_ids}}, {"_id": 0}).to_list(len(building_ids))
    vehicles_list = await db.vehicles.find({"id": {"$in": vehicle_ids}}, {"_id": 0}).to_list(len(vehicle_ids))
    users_list = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "password": 0}).to_list(len(user_ids))

    slot_map = {s["id"]: s for s in slots_list}
    floor_map = {f["id"]: f for f in floors_list}
    building_map = {b["id"]: b for b in buildings_list}
    vehicle_map = {v["id"]: v for v in vehicles_list}
    user_map = {u["id"]: u for u in users_list}

    result = []
    for res in reservations:
        slot = slot_map.get(res["slot_id"])
        floor = floor_map.get(res.get("floor_id"))
        building = building_map.get(res["building_id"])
        vehicle = vehicle_map.get(res["vehicle_id"])
        user = user_map.get(res["user_id"])

        result.append(ReservationResponse(
            id=res["id"],
            user_id=res["user_id"],
            slot_id=res["slot_id"],
            vehicle_id=res["vehicle_id"],
            building_id=res["building_id"],
            floor_id=res.get("floor_id", ""),
            date=res["date"],
            start_time=res["start_time"],
            end_time=res["end_time"],
            status=res["status"],
            booking_type=res.get("booking_type", "daily"),
            created_at=res["created_at"],
            slot_label=slot["label"] if slot else None,
            floor_label=floor["label"] if floor else None,
            building_name=building["name"] if building else None,
            vehicle_plate=vehicle["plate_number"] if vehicle else None,
            user_name=f"{user['first_name']} {user['last_name']}" if user else None,
            photo_url=res.get("photo_url"),
            qr_token=res.get("qr_token"),
            no_show_reported=res.get("no_show_reported", False),
            reason=res.get("reason"),
        ))
    return result
