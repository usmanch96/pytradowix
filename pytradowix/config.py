import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, cast

session_lock = threading.Lock()

def resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is not None:
        base_dir = Path(base_path)
    else:
        base_dir = Path(__file__).resolve().parent
    return base_dir / relative_path

def session_path() -> Path:
    """Get path to the user's local session storage (~/.pytradowix/session.json)."""
    return Path.home() / ".pytradowix" / "session.json"

def load_session(email: str, default_user_agent: str) -> Dict[str, Any]:
    """Load session data for a specific email from session.json."""
    output_file = session_path()
    with session_lock:
        all_sessions: dict[str, Any] = {}
        if output_file.exists():
            try:
                all_sessions = json.loads(output_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        else:
            output_file.parent.mkdir(exist_ok=True, parents=True)

        if email not in all_sessions:
            all_sessions[email] = {
                "token": None,
                "user_agent": default_user_agent
            }
            try:
                output_file.write_text(json.dumps(all_sessions, indent=4), encoding="utf-8")
            except OSError:
                pass

        return cast(Dict[str, Any], all_sessions[email])

def update_session(email: str, token: str, user_agent: str) -> None:
    """Update and persist session data for a specific email in session.json."""
    output_file = session_path()
    with session_lock:
        all_sessions = {}
        if output_file.exists():
            try:
                all_sessions = json.loads(output_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        
        all_sessions[email] = {
            "token": token,
            "user_agent": user_agent
        }
        
        try:
            output_file.parent.mkdir(exist_ok=True, parents=True)
            output_file.write_text(json.dumps(all_sessions, indent=4), encoding="utf-8")
        except OSError:
            pass
