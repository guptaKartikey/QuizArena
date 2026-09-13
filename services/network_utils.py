import socket
import os
from dotenv import load_dotenv

load_dotenv()

from urllib.parse import urlparse

def normalize_cloud_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip().rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    
    # If on Render and missing .onrender.com (e.g. https://quizarena-backend-knwp)
    if "onrender.com" not in url and "localhost" not in url and "127.0.0.1" not in url:
        try:
            parsed = urlparse(url)
            if parsed.hostname and "." not in parsed.hostname:
                clean_host = f"https://{parsed.hostname}.onrender.com"
                if parsed.path:
                    clean_host += parsed.path
                return clean_host
        except Exception:
            pass
    return url

def get_local_ip() -> str:
    """
    Detects the public URL or local LAN IP address of the machine running QuizArena,
    allowing mobile phones / players to connect via QR code or join link.
    """
    # 1. Check explicit player base URL override
    player_url = os.getenv("PLAYER_BASE_URL", "").strip().rstrip("/")
    if player_url:
        return normalize_cloud_url(player_url)

    # 2. Check API_BASE_URL (set on Render for admin to point to backend)
    api_url = os.getenv("API_BASE_URL", "").strip().rstrip("/")
    if api_url and "localhost" not in api_url and "127.0.0.1" not in api_url:
        return normalize_cloud_url(api_url)

    # 3. Check Render External URL
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if render_url:
        return normalize_cloud_url(render_url)

    # 4. If running locally on LAN, auto-detect LAN IP via UDP socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        port = os.getenv("PORT", "8000")
        return f"http://{ip}:{port}"
    except Exception:
        port = os.getenv("PORT", "8000")
        return f"http://localhost:{port}"
