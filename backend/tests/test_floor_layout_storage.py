"""Backend regression tests for the floor-layout upload pipeline that now
runs through the new storage abstraction (LocalStorage default).

Endpoints under test:
- POST   /api/floors/{floor_id}/layout  (admin)
- DELETE /api/floors/{floor_id}/layout  (admin)
- GET    /api/uploads/{filename}        (auth)
- GET    /api/buildings                 (regression, layout_image_url persists)
"""
import io
import os
import struct
import zlib
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://reserve-park-debug.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin.test@cebuana.com"
USER_EMAIL = "user.test@cebuana.com"
PASSWORD = "Test123!"


# --- Helpers ---------------------------------------------------------------

def _make_png(width: int = 4, height: int = 4) -> bytes:
    """Build a tiny valid PNG entirely in-memory (no Pillow dep)."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # RGB
    raw = b""
    for _ in range(height):
        raw += b"\x00" + b"\xff\x00\x00" * width  # filter byte + red row
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _login(email: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login failed for {email}: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"no access_token in login response: {data}"
    return token


# --- Fixtures --------------------------------------------------------------

@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, PASSWORD)


@pytest.fixture(scope="module")
def user_token() -> str:
    return _login(USER_EMAIL, PASSWORD)


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="module")
def png_bytes() -> bytes:
    return _make_png()


@pytest.fixture(scope="module")
def test_building(admin_headers):
    """Create a throwaway building with 1 floor, yield (building_id, floor_id),
    then delete the building afterwards."""
    payload = {
        "name": f"TEST_storage_{uuid.uuid4().hex[:8]}",
        "address": "Test Addr",
        "total_floors": 1,
        "slots_per_floor": 1,
    }
    r = requests.post(f"{BASE_URL}/api/buildings", json=payload, headers=admin_headers, timeout=30)
    assert r.status_code == 200, f"create building failed: {r.status_code} {r.text}"
    b = r.json()
    bid = b["id"]
    fid = b["floors"][0]["id"]
    yield bid, fid
    # cleanup
    requests.delete(f"{BASE_URL}/api/buildings/{bid}", headers=admin_headers, timeout=20)


# --- Tests: happy path ------------------------------------------------------

class TestFloorLayoutHappyPath:

    def test_upload_png_success_and_url_format(self, admin_headers, test_building, png_bytes):
        _, fid = test_building
        r = requests.post(
            f"{BASE_URL}/api/floors/{fid}/layout",
            files={"file": ("layout.png", png_bytes, "image/png")},
            headers=admin_headers, timeout=30,
        )
        assert r.status_code == 200, f"upload failed: {r.status_code} {r.text}"
        body = r.json()
        assert "layout_image_url" in body
        assert body["layout_image_url"].startswith("/api/uploads/floor_")
        assert body["layout_image_url"].endswith(".png")

    def test_buildings_get_persists_layout_url(self, admin_headers, test_building):
        bid, fid = test_building
        r = requests.get(f"{BASE_URL}/api/buildings", headers=admin_headers, timeout=20)
        assert r.status_code == 200
        target = next((b for b in r.json() if b["id"] == bid), None)
        assert target, "created building missing from list"
        floor = next((f for f in target["floors"] if f["id"] == fid), None)
        assert floor, "floor missing"
        assert floor.get("layout_image_url"), "layout_image_url not persisted"
        assert floor["layout_image_url"].startswith("/api/uploads/floor_")

    def test_get_upload_byte_perfect_roundtrip(self, admin_headers, test_building, png_bytes):
        _, fid = test_building
        # Find URL via buildings GET
        r = requests.get(f"{BASE_URL}/api/buildings", headers=admin_headers, timeout=20)
        floor = next(f for b in r.json() for f in b["floors"] if f["id"] == fid)
        url = f"{BASE_URL}{floor['layout_image_url']}"
        r2 = requests.get(url, headers=admin_headers, timeout=20)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/png")
        assert r2.content == png_bytes, "byte mismatch on round-trip"


# --- Tests: validation / negative -----------------------------------------

class TestFloorLayoutValidation:

    def test_reject_non_image_content_type(self, admin_headers, test_building):
        _, fid = test_building
        r = requests.post(
            f"{BASE_URL}/api/floors/{fid}/layout",
            files={"file": ("evil.png", b"not really an image", "text/plain")},
            headers=admin_headers, timeout=20,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"

    def test_reject_unsupported_extension(self, admin_headers, test_building, png_bytes):
        _, fid = test_building
        # content-type starts with image/ but extension is not allowed
        r = requests.post(
            f"{BASE_URL}/api/floors/{fid}/layout",
            files={"file": ("layout.bmp", png_bytes, "image/bmp")},
            headers=admin_headers, timeout=20,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"

    def test_reject_oversized_payload(self, admin_headers, test_building):
        _, fid = test_building
        big = b"\x00" * (10 * 1024 * 1024 + 1024)  # 10MB + 1KB
        r = requests.post(
            f"{BASE_URL}/api/floors/{fid}/layout",
            files={"file": ("big.png", big, "image/png")},
            headers=admin_headers, timeout=120,
        )
        # FastAPI/uvicorn may also 413 at proxy; either is acceptable rejection
        assert r.status_code in (400, 413), f"expected 400/413, got {r.status_code}"

    def test_invalid_floor_id_returns_404(self, admin_headers, png_bytes):
        bogus = "non-existent-floor-id-xyz-123"
        r = requests.post(
            f"{BASE_URL}/api/floors/{bogus}/layout",
            files={"file": ("layout.png", png_bytes, "image/png")},
            headers=admin_headers, timeout=20,
        )
        assert r.status_code == 404, f"expected 404, got {r.status_code} {r.text}"


# --- Tests: auth / role ----------------------------------------------------

class TestFloorLayoutAuth:

    def test_upload_requires_admin(self, user_headers, test_building, png_bytes):
        _, fid = test_building
        r = requests.post(
            f"{BASE_URL}/api/floors/{fid}/layout",
            files={"file": ("layout.png", png_bytes, "image/png")},
            headers=user_headers, timeout=20,
        )
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_delete_requires_admin(self, user_headers, test_building):
        _, fid = test_building
        r = requests.delete(
            f"{BASE_URL}/api/floors/{fid}/layout",
            headers=user_headers, timeout=20,
        )
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_uploads_get_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/uploads/floor_anything.png", timeout=20)
        assert r.status_code == 401, f"expected 401, got {r.status_code}"


# --- Tests: GET /api/uploads/{filename} ------------------------------------

class TestServeUpload:

    def test_unknown_filename_returns_404(self, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/uploads/floor_doesnotexist_{uuid.uuid4().hex}.png",
            headers=admin_headers, timeout=20,
        )
        assert r.status_code == 404, f"expected 404, got {r.status_code}"

    def test_path_traversal_rejected(self, admin_headers):
        # The ingress/Starlette routing may handle '../etc' before the route,
        # so we accept either 400 (route validation) or 404 (route not matched)
        r = requests.get(
            f"{BASE_URL}/api/uploads/..%2Fetc%2Fpasswd",
            headers=admin_headers, timeout=20,
        )
        assert r.status_code in (400, 404), f"expected 400/404, got {r.status_code} {r.text}"

    def test_disallowed_extension_rejected(self, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/uploads/somefile.txt",
            headers=admin_headers, timeout=20,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"

    def test_jpeg_content_type(self, admin_headers, test_building):
        # Upload a .jpg using PNG bytes (server only checks content_type prefix + ext)
        _, fid = test_building
        png = _make_png()
        r = requests.post(
            f"{BASE_URL}/api/floors/{fid}/layout",
            files={"file": ("layout.jpg", png, "image/jpeg")},
            headers=admin_headers, timeout=20,
        )
        assert r.status_code == 200
        url = r.json()["layout_image_url"]
        assert url.endswith(".jpg")
        r2 = requests.get(f"{BASE_URL}{url}", headers=admin_headers, timeout=20)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/jpeg")


# --- Tests: delete cycle ---------------------------------------------------

class TestFloorLayoutDeleteCycle:

    def test_full_upload_then_delete_clears_db_and_storage(self, admin_headers, png_bytes):
        # Independent building so we don't interfere with module-scoped one
        bpayload = {
            "name": f"TEST_delete_{uuid.uuid4().hex[:8]}",
            "address": "X",
            "total_floors": 1,
            "slots_per_floor": 1,
        }
        b = requests.post(f"{BASE_URL}/api/buildings", json=bpayload, headers=admin_headers, timeout=20).json()
        bid, fid = b["id"], b["floors"][0]["id"]
        try:
            up = requests.post(
                f"{BASE_URL}/api/floors/{fid}/layout",
                files={"file": ("layout.png", png_bytes, "image/png")},
                headers=admin_headers, timeout=20,
            )
            assert up.status_code == 200
            url = up.json()["layout_image_url"]

            # Pre-delete: GET works
            pre = requests.get(f"{BASE_URL}{url}", headers=admin_headers, timeout=20)
            assert pre.status_code == 200

            # Delete
            d = requests.delete(f"{BASE_URL}/api/floors/{fid}/layout", headers=admin_headers, timeout=20)
            assert d.status_code == 200

            # DB field cleared
            blist = requests.get(f"{BASE_URL}/api/buildings", headers=admin_headers, timeout=20).json()
            floor = next(f for bb in blist if bb["id"] == bid for f in bb["floors"] if f["id"] == fid)
            assert floor.get("layout_image_url") in (None, ""), \
                f"layout_image_url still set after delete: {floor.get('layout_image_url')}"

            # Object removed
            post = requests.get(f"{BASE_URL}{url}", headers=admin_headers, timeout=20)
            assert post.status_code == 404, f"object still served after delete: {post.status_code}"
        finally:
            requests.delete(f"{BASE_URL}/api/buildings/{bid}", headers=admin_headers, timeout=20)
