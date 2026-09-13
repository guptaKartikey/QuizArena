import subprocess
import sys
import time
import os

def main():
    print("=" * 60)
    print("🏆 Starting QuizArena — Real-Time QR Multiplayer Platform")
    print("=" * 60)

    # Environment variables
    host = os.getenv("HOST", "0.0.0.0")
    backend_port = os.getenv("PORT", "8000")
    streamlit_port = os.getenv("STREAMLIT_PORT", "8501")

    # Command 1: Uvicorn FastAPI server
    fastapi_cmd = [
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", host,
        "--port", backend_port,
        "--reload"
    ]

    # Command 2: Streamlit Admin UI
    streamlit_cmd = [
        sys.executable, "-m", "streamlit", "run", "admin/app.py",
        "--server.port", streamlit_port,
        "--server.headless", "true"
    ]

    print(f"🚀 Launching Backend Server on http://localhost:{backend_port}...")
    backend_process = subprocess.Popen(fastapi_cmd)

    time.sleep(2)

    print(f"🚀 Launching Admin Dashboard on http://localhost:{streamlit_port}...")
    admin_process = subprocess.Popen(streamlit_cmd)

    print("\n✅ QuizArena is running!")
    print(f"   • Admin Dashboard: http://localhost:{streamlit_port}")
    print(f"   • Mobile Player App: http://localhost:{backend_port}")
    print("   • Default Admin Credentials: admin / change_me")
    print("\nPress Ctrl+C to stop both servers.")

    try:
        backend_process.wait()
        admin_process.wait()
    except KeyboardInterrupt:
        print("\nStopping QuizArena servers...")
        backend_process.terminate()
        admin_process.terminate()
        backend_process.wait()
        admin_process.wait()
        print("Servers stopped cleanly.")

if __name__ == "__main__":
    main()
