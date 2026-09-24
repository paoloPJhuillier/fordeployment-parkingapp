#!/usr/bin/env python3
"""
Seed script for Pacific Star Building dedicated slot policy demo.
Creates: Pacific Star building, floors (B1-B4), 23 slots, policy, zone,
         test users with slot registrations.
"""
import asyncio
import uuid
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import bcrypt

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

def hash_pw(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def uid():
    return str(uuid.uuid4())

NOW = datetime.now(timezone.utc).isoformat()
DEFAULT_PASSWORD = hash_pw("Test123!")

async def main():
    # Check if already seeded
    existing = await db.buildings.find_one({"name": "Pacific Star Building"})
    if existing:
        print("Pacific Star Building already exists. Skipping seed.")
        print(f"Building ID: {existing['id']}")
        return

    print("Seeding Pacific Star Building data...")

    # 1. Create Building
    building_id = uid()
    building = {
        "id": building_id,
        "name": "Pacific Star Building",
        "address": "Makati Avenue corner Gil Puyat, Makati City",
        "total_floors": 4,
        "created_at": NOW,
    }
    await db.buildings.insert_one(building)
    print(f"  Building: Pacific Star ({building_id})")

    # 2. Create Floors: B1, B2 (dedicated), B3, B4 (open)
    floors = {}
    for label in ["Basement 1", "Basement 2", "Basement 3", "Basement 4"]:
        fid = uid()
        floors[label] = fid
        await db.floors.insert_one({
            "id": fid,
            "label": label,
            "building_id": building_id,
            "layout_image_url": None,
        })
    print(f"  Floors: {list(floors.keys())}")

    # 3. Create Slots
    # B1: 10 company-owned slots
    # B2: 8 company-owned + 5 CLRB rented = 13 slots
    # B3: 8 open parking slots
    # B4: 8 open parking slots
    slot_ids = {}
    slot_counter = 0

    async def add_slot(floor_label, label, ownership):
        nonlocal slot_counter
        sid = uid()
        slot_ids[label] = sid
        await db.parking_slots.insert_one({
            "id": sid,
            "label": label,
            "floor_id": floors[floor_label],
            "building_id": building_id,
            "status": "available",
            "row": slot_counter // 5,
            "column": slot_counter % 5,
            "ownership_type": ownership,
        })
        slot_counter += 1
        return sid

    # B1: 10 company-owned
    b1_slots = []
    for i in range(1, 11):
        sid = await add_slot("Basement 1", f"B1-{i:02d}", "company_owned")
        b1_slots.append(sid)

    # B2: 8 company-owned + 5 CLRB rented
    slot_counter = 0
    b2_co_slots = []
    for i in range(1, 9):
        sid = await add_slot("Basement 2", f"B2-{i:02d}", "company_owned")
        b2_co_slots.append(sid)
    b2_clrb_slots = []
    for i in range(9, 14):
        sid = await add_slot("Basement 2", f"B2-{i:02d}", "rented_clrb")
        b2_clrb_slots.append(sid)

    # B3: 8 open parking
    slot_counter = 0
    for i in range(1, 9):
        await add_slot("Basement 3", f"B3-{i:02d}", "open_parking")

    # B4: 8 open parking
    slot_counter = 0
    for i in range(1, 9):
        await add_slot("Basement 4", f"B4-{i:02d}", "open_parking")

    total_slots = len(slot_ids)
    print(f"  Slots: {total_slots} total (18 company + 5 CLRB + 16 open)")

    # 4. Create Building Policy
    policy_id = uid()
    await db.building_policies.insert_one({
        "id": policy_id,
        "building_id": building_id,
        "policy_type": "dedicated_slot",
        "enabled": True,
        "max_users_per_slot": 5,
        "open_floor_ids": [floors["Basement 3"], floors["Basement 4"]],
        "requires_sticker": True,
        "created_at": NOW,
        "updated_at": NOW,
    })
    print(f"  Policy: dedicated_slot (open floors: B3, B4)")

    # 5. Create Zone
    zone_id = uid()

    # 6. Create Test Users
    test_users = [
        ("psb.user1@cebuana.com", "Maria", "Santos", "CLRB", "PSB-001", "ABC-1234"),
        ("psb.user2@cebuana.com", "Juan", "Dela Cruz", "CLRB", "PSB-002", "XYZ-5678"),
        ("psb.user3@cebuana.com", "Ana", "Reyes", "CLRB", "PSB-003", "DEF-9012"),
        ("psb.user4@cebuana.com", "Carlos", "Garcia", "CLRB", "PSB-004", "GHI-3456"),
        ("psb.user5@cebuana.com", "Elena", "Cruz", "CLRB", "PSB-005", "JKL-7890"),
        ("psb.noassign@cebuana.com", "Pedro", "Lim", "CLRB", "PSB-006", "MNO-1111"),
        ("psb.nosticker@cebuana.com", "Rosa", "Tan", "CLRB", None, "PQR-2222"),
    ]

    user_ids = []
    for email, first, last, company, sticker, plate in test_users:
        existing_user = await db.users.find_one({"email": email})
        if existing_user:
            user_ids.append(existing_user["id"])
            continue
        user_id = uid()
        user_ids.append(user_id)
        await db.users.insert_one({
            "id": user_id,
            "email": email,
            "password": DEFAULT_PASSWORD,
            "first_name": first,
            "last_name": last,
            "company": company,
            "role": "user",
            "assigned_buildings": [],
            "main_building": building_id,
            "tags": [],
            "is_blocked": False,
            "must_change_password": False,
            "default_start_time": "08:00",
            "default_end_time": "18:00",
            "parking_sticker_number": sticker,
            "no_show_count": 0,
            "created_at": NOW,
        })

        # Register vehicle
        await db.vehicles.insert_one({
            "id": uid(),
            "user_id": user_id,
            "plate_number": plate,
            "make": "Toyota",
            "model": "Vios",
            "color": "White",
            "building_id": building_id,
            "created_at": NOW,
        })

    print(f"  Users: {len(test_users)} created")

    # Create zone with building and users
    await db.zones.insert_one({
        "id": zone_id,
        "name": "Pacific Star Zone",
        "building_ids": [building_id],
        "user_ids": user_ids,
        "created_at": NOW,
    })
    print(f"  Zone: Pacific Star Zone")

    # 7. Create Slot Registrations
    # User 1-3: assigned to B1-01 (3 users sharing 1 slot)
    # User 4: assigned to B1-02
    # User 5: assigned to B2-09 (CLRB rented slot)
    # User 6 (Pedro): has sticker but NO slot assignment - can only use open floors
    # User 7 (Rosa): NO sticker, NO slot - cannot book at all

    registrations = [
        (0, b1_slots[0], "B1-01"),  # Maria -> B1-01
        (1, b1_slots[0], "B1-01"),  # Juan -> B1-01
        (2, b1_slots[0], "B1-01"),  # Ana -> B1-01
        (3, b1_slots[1], "B1-02"),  # Carlos -> B1-02
        (4, b2_clrb_slots[0], "B2-09"),  # Elena -> B2-09
    ]

    for user_idx, slot_id, slot_label in registrations:
        email, first, last, company, sticker, plate = test_users[user_idx]
        await db.slot_registrations.insert_one({
            "id": uid(),
            "slot_id": slot_id,
            "building_id": building_id,
            "floor_id": floors["Basement 1"] if slot_label.startswith("B1") else floors["Basement 2"],
            "user_id": user_ids[user_idx],
            "vehicle_plate": plate,
            "sticker_number": sticker,
            "status": "active",
            "registered_at": NOW,
        })

    print(f"  Registrations: {len(registrations)} created")

    print("\n" + "=" * 60)
    print("SEED COMPLETE - Pacific Star Building")
    print("=" * 60)
    print()
    print("TEST ACCOUNTS (all password: Test123!):")
    print("-" * 60)
    print(f"{'Email':<35} {'Name':<20} {'Scenario'}")
    print("-" * 60)
    print(f"{'psb.user1@cebuana.com':<35} {'Maria Santos':<20} Assigned B1-01 (shared slot)")
    print(f"{'psb.user2@cebuana.com':<35} {'Juan Dela Cruz':<20} Assigned B1-01 (shared slot)")
    print(f"{'psb.user3@cebuana.com':<35} {'Ana Reyes':<20} Assigned B1-01 (shared slot)")
    print(f"{'psb.user4@cebuana.com':<35} {'Carlos Garcia':<20} Assigned B1-02")
    print(f"{'psb.user5@cebuana.com':<35} {'Elena Cruz':<20} Assigned B2-09 (CLRB rented)")
    print(f"{'psb.noassign@cebuana.com':<35} {'Pedro Lim':<20} Has sticker, NO slot (open floors only)")
    print(f"{'psb.nosticker@cebuana.com':<35} {'Rosa Tan':<20} NO sticker (cannot book)")
    print()
    print("BUILDING LAYOUT:")
    print(f"  B1 (Dedicated): 10 slots (company-owned)")
    print(f"  B2 (Dedicated): 8 company + 5 CLRB = 13 slots")
    print(f"  B3 (Open):      8 slots (any sticker holder)")
    print(f"  B4 (Open):      8 slots (any sticker holder)")
    print()
    print(f"  Admin: admin.test@cebuana.com / Test123!")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
