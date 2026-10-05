import sqlite3
from datetime import datetime

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-in-production"
socketio = SocketIO(app, cors_allowed_origins="*")

DB = "chat.db"


def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                username TEXT NOT NULL,
                text TEXT NOT NULL,
                time TEXT NOT NULL
            )"""
        )


def save_message(room, username, text):
    now = datetime.now().strftime("%H:%M")
    with sqlite3.connect(DB) as conn:
        conn.execute(
            "INSERT INTO messages (room, username, text, time) VALUES (?, ?, ?, ?)",
            (room, username, text, now),
        )
    return now


def get_history(room, limit=50):
    with sqlite3.connect(DB) as conn:
        rows = conn.execute(
            "SELECT username, text, time FROM messages WHERE room = ? "
            "ORDER BY id DESC LIMIT ?",
            (room, limit),
        ).fetchall()
    return [{"username": u, "text": t, "time": tm} for u, t, tm in reversed(rows)]


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("join")
def on_join(data):
    room, username = data["room"], data["username"]
    join_room(room)
    emit("history", get_history(room))  # sent only to the user who joined
    emit("status", {"msg": f"{username} joined #{room}"}, to=room)


@socketio.on("leave")
def on_leave(data):
    room, username = data["room"], data["username"]
    leave_room(room)
    emit("status", {"msg": f"{username} left #{room}"}, to=room)


@socketio.on("message")
def on_message(data):
    room, username, text = data["room"], data["username"], data["text"].strip()
    if not text:
        return
    time = save_message(room, username, text)
    emit("message", {"username": username, "text": text, "time": time}, to=room)


if __name__ == "__main__":
    init_db()
    socketio.run(app, debug=True, port=5000)
