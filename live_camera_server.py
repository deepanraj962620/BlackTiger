import base64
import binascii
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
import secrets

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(16)

# Flask-SocketIO otherwise selects eventlet whenever it is installed.  Eventlet
# is deprecated and is especially unreliable on Windows, where it can cause
# Socket.IO connections to repeatedly reconnect.  Threading is supported by
# the standard Flask development server and keeps this local consent-based
# sharing server stable on Windows, Linux, and macOS.
socketio = SocketIO(
    app,
    async_mode="threading",
    cors_allowed_origins="*",
    ping_interval=25,
    ping_timeout=60,
)

SESSIONS = {}
SHARE_CONNECTIONS = {}
VIEWER_CONNECTIONS = {}
RECORDINGS = {}
RECORDING_DIR = Path(__file__).resolve().parent / "recordings"
_SESSION_LOCK = threading.RLock()


def _recording_event(session_id, state, **details):
    payload = {"state": state, **details}
    socketio.emit("recording_status", payload, room=f"viewer:{session_id}")
    socketio.emit("phone_recording_status", payload, room=f"share:{session_id}")


def _finish_recording(session_id, state="stopped", message=None):
    with _SESSION_LOCK:
        recording = RECORDINGS.pop(session_id, None)
        if recording is None:
            return
        writer = recording["writer"]
        if writer is not None:
            writer.release()
        path = recording["path"]
        frames = recording["frames"]
        if frames == 0:
            path.unlink(missing_ok=True)

    details = {
        "frames": frames,
        "path": str(path.relative_to(Path(__file__).resolve().parent)) if frames else None,
    }
    if message:
        details["message"] = message
    _recording_event(session_id, state, **details)


def _record_frame(session_id, image_data):
    try:
        encoded = base64.b64decode(image_data.partition(",")[2], validate=True)
        frame = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
    except (binascii.Error, ValueError, cv2.error):
        return
    if frame is None:
        return
    height, width = frame.shape[:2]

    try:
        with _SESSION_LOCK:
            recording = RECORDINGS.get(session_id)
            if recording is None:
                return
            if recording["writer"] is None:
                writer = cv2.VideoWriter(
                    str(recording["path"]),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    2.5,
                    (width, height),
                )
                if not writer.isOpened():
                    writer.release()
                    raise RuntimeError(
                        "This computer could not open an MP4 video writer."
                    )
                recording["writer"] = writer
                recording["size"] = (width, height)
            if recording["size"] != (width, height):
                frame = cv2.resize(frame, recording["size"])
            recording["writer"].write(frame)
            recording["frames"] += 1
    except (OSError, RuntimeError, cv2.error) as error:
        _finish_recording(
            session_id,
            state="error",
            message=f"Recording stopped: {error}",
        )

@app.get("/")
def home():
    return render_template("live_home.html")

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.route("/share/<session_id>")
def share(session_id):
    if session_id not in SESSIONS:
        return "Invalid or expired BlackTiger share link.", 404
    meta = SESSIONS[session_id]
    return render_template(
        "live_share.html",
        session_id=session_id,
        theme=meta.get("theme", "festival"),
        title=meta.get("title", "BlackTiger Live Camera Share"),
    )

@app.route("/viewer/<session_id>")
def viewer(session_id):
    if session_id not in SESSIONS:
        return "Invalid or expired BlackTiger viewer link.", 404
    meta = SESSIONS[session_id]
    return render_template(
        "live_viewer.html",
        session_id=session_id,
        title=meta.get("title", "BlackTiger Live Viewer"),
    )

@app.post("/api/session")
def create_session():
    data = request.get_json(force=True)
    sid = secrets.token_urlsafe(8)
    SESSIONS[sid] = {
        "theme": data.get("theme", "festival"),
        "title": data.get("title", "BlackTiger Live Camera Share"),
        "created": time.time(),
        "sharing": False,
        "recording_consent": False,
    }
    return jsonify({"session_id": sid})

@socketio.on("join_share")
def join_share(data):
    if not isinstance(data, dict):
        return
    sid = data.get("session_id")
    if sid in SESSIONS:
        SHARE_CONNECTIONS[request.sid] = sid
        join_room(f"share:{sid}")
        SESSIONS[sid]["recording_consent"] = data.get("recording_consent") is True
        emit("share_status", {"ok": True})
        socketio.emit("viewer_status", {"status": "phone_connected"}, room=f"viewer:{sid}")
        socketio.emit(
            "recording_consent",
            {"allowed": SESSIONS[sid]["recording_consent"]},
            room=f"viewer:{sid}",
        )


@socketio.on("set_recording_consent")
def set_recording_consent(data):
    if not isinstance(data, dict):
        return
    sid = data.get("session_id")
    if sid not in SESSIONS or SHARE_CONNECTIONS.get(request.sid) != sid:
        return
    allowed = data.get("allowed") is True
    SESSIONS[sid]["recording_consent"] = allowed
    socketio.emit("recording_consent", {"allowed": allowed}, room=f"viewer:{sid}")
    if not allowed:
        _finish_recording(
            sid,
            message="Phone user withdrew recording consent.",
        )

@socketio.on("join_viewer")
def join_viewer(data):
    if not isinstance(data, dict):
        return
    sid = data.get("session_id")
    if sid in SESSIONS:
        join_room(f"viewer:{sid}")
        VIEWER_CONNECTIONS[request.sid] = sid
        emit("viewer_status", {"status": "viewer_connected"})
        emit(
            "recording_consent",
            {"allowed": SESSIONS[sid].get("recording_consent", False)},
        )
        if SESSIONS[sid].get("sharing"):
            emit("viewer_status", {"status": "sharing_started"})
        if sid in RECORDINGS:
            emit(
                "recording_status",
                {
                    "state": "started",
                    "path": str(
                        RECORDINGS[sid]["path"].relative_to(
                            Path(__file__).resolve().parent
                        )
                    ),
                },
            )

@socketio.on("start_sharing")
def start_sharing(data):
    if not isinstance(data, dict):
        return
    sid = data.get("session_id")
    if sid in SESSIONS and SHARE_CONNECTIONS.get(request.sid) == sid:
        SESSIONS[sid]["sharing"] = True
        socketio.emit("viewer_status", {"status": "sharing_started"}, room=f"viewer:{sid}")

@socketio.on("stop_sharing")
def stop_sharing(data):
    if not isinstance(data, dict):
        return
    sid = data.get("session_id")
    if sid in SESSIONS and SHARE_CONNECTIONS.get(request.sid) == sid:
        SESSIONS[sid]["sharing"] = False
        _finish_recording(sid)
        socketio.emit("viewer_status", {"status": "sharing_stopped"}, room=f"viewer:{sid}")


@socketio.on("start_recording")
def start_recording(data):
    if not isinstance(data, dict):
        return
    sid = data.get("session_id")
    if sid not in SESSIONS or VIEWER_CONNECTIONS.get(request.sid) != sid:
        return
    session = SESSIONS[sid]
    if not session.get("sharing"):
        emit("recording_status", {"state": "error", "message": "Start camera sharing before recording."})
        return
    if not session.get("recording_consent"):
        emit("recording_status", {"state": "error", "message": "The phone user has not consented to recording."})
        return
    with _SESSION_LOCK:
        if sid in RECORDINGS:
            emit("recording_status", {"state": "error", "message": "Recording is already active."})
            return
        try:
            RECORDING_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"blacktiger_live_{datetime.now():%Y%m%d_%H%M%S}_{sid}.mp4"
            path = RECORDING_DIR / filename
            RECORDINGS[sid] = {
                "path": path,
                "writer": None,
                "size": None,
                "frames": 0,
            }
        except OSError as error:
            emit("recording_status", {"state": "error", "message": f"Could not create recordings folder: {error}"})
            return
    _recording_event(sid, "started", path=f"recordings/{filename}")


@socketio.on("stop_recording")
def stop_recording(data):
    if not isinstance(data, dict):
        return
    sid = data.get("session_id")
    if sid in SESSIONS and VIEWER_CONNECTIONS.get(request.sid) == sid:
        _finish_recording(sid)

@socketio.on("frame")
def frame(data):
    if not isinstance(data, dict):
        return
    sid = data.get("session_id")
    image = data.get("image")
    if (
        sid in SESSIONS
        and SHARE_CONNECTIONS.get(request.sid) == sid
        and SESSIONS[sid].get("sharing")
        and isinstance(image, str)
        and image.startswith("data:image/jpeg;base64,")
        and len(image) <= 2_000_000
    ):
        if sid in RECORDINGS:
            _record_frame(sid, image)
        socketio.emit("frame", {"image": image}, room=f"viewer:{sid}")

@socketio.on("disconnect")
def disconnect():
    sid = SHARE_CONNECTIONS.pop(request.sid, None)
    if sid in SESSIONS and SESSIONS[sid].get("sharing"):
        SESSIONS[sid]["sharing"] = False
        _finish_recording(sid)
        socketio.emit("viewer_status", {"status": "sharing_stopped"}, room=f"viewer:{sid}")
    viewer_sid = VIEWER_CONNECTIONS.pop(request.sid, None)
    if viewer_sid is not None:
        _finish_recording(viewer_sid)


if __name__ == "__main__":
    # This makes `python live_camera_server.py` useful during local debugging.
    # The interactive BlackTiger menu uses the same app through camera_portal.
    socketio.run(
        app,
        host="0.0.0.0",
        port=8090,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
