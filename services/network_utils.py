import socket
import os
from dotenv import load_dotenv

load_dotenv()

def get_local_ip() -> str:
    """
    Detects the public URL or local LAN IP address of the machine running QuizArena,
    allowing mobile phones / players to connect via QR code or join link.
    """
    # 1. Check explicit player base URL override
    player_url = os.getenv("PLAYER_BASE_URL", "").strip().rstrip("/")
    if player_url:
        if not player_url.startswith("http://") and not player_url.startswith("https://"):
            player_url = "https://" + player_url
        return player_url

    # 2. Check API_BASE_URL (set on Render for admin to point to backend)
    api_url = os.getenv("API_BASE_URL", "").strip().rstrip("/")
    if api_url and "localhost" not in api_url and "127.0.0.1" not in api_url:
        if not api_url.startswith("http://") and not api_url.startswith("https://"):
            api_url = "https://" + api_url
        return api_url

    # 3. Check Render External URL
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if render_url:
        if not render_url.startswith("http://") and not render_url.startswith("https://"):
            render_url = "https://" + render_url
        return render_url

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
