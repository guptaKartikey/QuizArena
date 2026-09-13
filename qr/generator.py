import qrcode
import io
import base64
from PIL import Image

def generate_qr_code_image(url: str) -> Image.Image:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF").convert("RGB")
    return img

def generate_qr_code_bytes(url: str) -> bytes:
    img = generate_qr_code_image(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def generate_qr_code_base64(url: str) -> str:
    img_bytes = generate_qr_code_bytes(url)
    encoded = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
