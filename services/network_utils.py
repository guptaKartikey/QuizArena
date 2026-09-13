import socket
import os
from dotenv import load_dotenv

load_dotenv()

def get_local_ip() -> str:
    """
    Detects the local LAN IP address of the machine running QuizArena,
    allowing mobile phones on the same Wi-Fi network to connect via QR code.
    """
    # 1. Check environment override
    env_url = os.getenv("PLAYER_BASE_URL")
    if env_url and "localhost" not in env_url and "127.0.0.1" not in env_url:
        return env_url.rstrip("/")

    # 2. Auto-detect LAN IP via UDP socket
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
