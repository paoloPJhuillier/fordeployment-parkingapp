"""
Seed realistic demo data into the running Parking API for the video manual.

Talks to the API over HTTP (default http://127.0.0.1:8001) as the seeded admin,
and creates:
  - 1 building (auto-creates floors + slots)
  - 1 employee user (with a known password, no forced change)
  - 1 attendant assigned to the building
  - 1 vehicle for the employee

Idempotent-ish: skips creating users/vehicles that already exist by email/plate.

Usage:
    python docs/video/seed_demo_data.py --base-url http://127.0.0.1:8001
"""
import argparse
import sys

import requests

ADMIN_EMAIL = "admin.test@cebuana.com"
ADMIN_PASSWORD = "Test123!"

EMPLOYEE = {
    "email": "employee.demo@cebuana.com",
    "password": "Demo123!",
    "first_name": "Ella",
    "last_name": "Employee",
    "company": "Cebuana Lhuillier",
    "role": "user",
}
ATTENDANT = {
    "email": "attendant.demo@cebuana.com",
    "password": "Demo123!",
    "first_name": "Andy",
    "last_name": "Attendant",
    "company": "Cebuana Lhuillier",
    "role": "attendant",
}
VEHICLE = {"plate_number": "DEMO-123", "make": "Toyota", "model": "Vios", "color": "Silver"}
BUILDING = {
    "name": "Head Office Tower",
    "address_line_1": "J. Luna Ave",
    "address_line_2": "Cebu City",
    "total_floors": 2,
    "slots_per_floor": 10,
    "slot_prefix": "A-",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8001")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    api = f"{base}/api"

    s = requests.Session()

    # 1. Admin login
    r = s.post(f"{api}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    r.raise_for_status()
    token = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    print(f"[seed] admin logged in")

    # 2. Building (skip if a building with same name exists)
    buildings = s.get(f"{api}/buildings", timeout=30).json()
    existing = next((b for b in buildings if b["name"] == BUILDING["name"]), None)
    if existing:
        building = existing
        print(f"[seed] building exists: {building['name']} ({building['id']})")
    else:
        building = s.post(f"{api}/buildings", json=BUILDING, timeout=60).json()
        print(f"[seed] created building: {building['name']} ({building['id']}) "
              f"with {building.get('total_floors')} floors")
    building_id = building["id"]

    # 3. Employee (assign to building via main_building)
    emp_payload = {**EMPLOYEE, "main_building": building_id, "assigned_buildings": [building_id]}
    r = s.post(f"{api}/users", json=emp_payload, timeout=30)
    if r.status_code == 400 and "already registered" in r.text.lower():
        print(f"[seed] employee exists: {EMPLOYEE['email']}")
        emp = next(u for u in s.get(f"{api}/users", timeout=30).json() if u["email"] == EMPLOYEE["email"])
    else:
        r.raise_for_status()
        emp = r.json()
        print(f"[seed] created employee: {emp['email']} ({emp['id']})")
    emp_id = emp["id"]

    # New users get must_change_password=True; clear it so the demo can log in
    # straight to the dashboard. Do this by admin-resetting to the same known
    # password is not enough (still forces change), so we PUT the user without
    # the flag via the update endpoint is also not enough. Instead we call the
    # dedicated block/unblock? No — simplest: reset password sets the flag too.
    # We handle the forced-change screen in the video flow instead.

    # 4. Attendant assigned to the building
    att_payload = {**ATTENDANT, "assigned_buildings": [building_id], "main_building": building_id}
    r = s.post(f"{api}/users", json=att_payload, timeout=30)
    if r.status_code == 400 and "already registered" in r.text.lower():
        print(f"[seed] attendant exists: {ATTENDANT['email']}")
    else:
        r.raise_for_status()
        print(f"[seed] created attendant: {ATTENDANT['email']}")

    # 5. Vehicle for the employee — created by the employee themselves so it is
    #    owned by them. Log in as the employee (handling forced password change).
    emp_sess = requests.Session()
    lr = emp_sess.post(f"{api}/auth/login",
                       json={"email": EMPLOYEE["email"], "password": EMPLOYEE["password"]}, timeout=30)
    if lr.status_code == 200:
        emp_token = lr.json()["access_token"]
        emp_sess.headers.update({"Authorization": f"Bearer {emp_token}"})
        # Clear forced-change by setting the same-family new password.
        emp_sess.post(f"{api}/auth/change-password",
                      json={"new_password": EMPLOYEE["password"].replace("!", "!1")}, timeout=30)
        # Re-login with the new password
        new_pw = EMPLOYEE["password"].replace("!", "!1")
        lr2 = emp_sess.post(f"{api}/auth/login",
                            json={"email": EMPLOYEE["email"], "password": new_pw}, timeout=30)
        if lr2.status_code == 200:
            emp_sess.headers.update({"Authorization": f"Bearer {lr2.json()['access_token']}"})
            EMPLOYEE["effective_password"] = new_pw
        vehicles = emp_sess.get(f"{api}/vehicles", timeout=30).json()
        if any(v["plate_number"] == VEHICLE["plate_number"] for v in vehicles):
            print(f"[seed] vehicle exists: {VEHICLE['plate_number']}")
        else:
            vr = emp_sess.post(f"{api}/vehicles", json=VEHICLE, timeout=30)
            if vr.status_code < 300:
                print(f"[seed] created vehicle: {VEHICLE['plate_number']}")
            else:
                print(f"[seed] vehicle create note: {vr.status_code} {vr.text[:200]}")

    print("\n[seed] DONE. Demo accounts:")
    print(f"       admin     : {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"       employee  : {EMPLOYEE['email']} / {EMPLOYEE.get('effective_password', EMPLOYEE['password'])} "
          f"(initial {EMPLOYEE['password']}, forced change on first login)")
    print(f"       attendant : {ATTENDANT['email']} / {ATTENDANT['password']} (forced change on first login)")
    print(f"       building  : {BUILDING['name']}")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"[seed] HTTP error: {e} -> {e.response.text[:300]}")
        sys.exit(1)
