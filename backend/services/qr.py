import os
import secrets
import base64
import qrcode
from io import BytesIO


def generate_qr_token() -> str:
    return secrets.token_urlsafe(16)


def generate_qr_code_image(qr_token: str) -> str:
    frontend_url = os.environ.get('CORS_ORIGINS', '').split(',')[0].strip()
    qr_content = f"{frontend_url}/scan/{qr_token}"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_content)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#08263e", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
