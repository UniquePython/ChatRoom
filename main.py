# IMPORTS --------------------------------------------------------------------------------------------------------------------------
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
from flask_sqlalchemy import SQLAlchemy

import random
import secrets
from datetime import datetime
import os
# -----------------------------------------------------------------------------------------------------------------------------------


# FLASK APP SETUP -------------------------------------------------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(64)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")  # Set this in Render
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

socketio = SocketIO(app)
db = SQLAlchemy(app)
port = int(os.environ.get('PORT', 5000))
# -----------------------------------------------------------------------------------------------------------------------------------


# DATABASE MODELS -------------------------------------------------------------------------------------------------------------------
class Room(db.Model):
    code = db.Column(db.String(10), primary_key=True)
    members = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(10), db.ForeignKey("room.code"), nullable=False)
    sender_name = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    room = db.relationship("Room", backref="messages")
# -----------------------------------------------------------------------------------------------------------------------------------


# HELPER METHODS --------------------------------------------------------------------------------------------------------------------
def generate_unique_code(length):
    while True:
        code = ''.join(random.choices('ABC123', k=length))
        if not Room.query.get(code):
            break
    return code
# -----------------------------------------------------------------------------------------------------------------------------------


# ROUTES ----------------------------------------------------------------------------------------------------------------------------
@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        room = Room.query.get(code) if code else None
        if create:
            code = generate_unique_code(4)
            room = Room(code=code)
            db.session.add(room)
            db.session.commit()
        elif not room:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = code
        session["name"] = name

        return redirect(url_for("room"))

    return render_template("home.html")


@app.route("/room")
def room():
    room_code = session.get("room")
    if not room_code or not session.get("name"):
        return redirect(url_for("home"))

    room = Room.query.get(room_code)
    if not room:
        return redirect(url_for("home"))

    messages = Message.query.filter_by(room_code=room_code).all()
    return render_template("room.html", code=room_code, messages=messages)
# -----------------------------------------------------------------------------------------------------------------------------------


# SOCKET EVENTS ---------------------------------------------------------------------------------------------------------------------
@socketio.on("connect")
def connect(auth):
    room_code = session.get("room")
    name = session.get("name")
    if not room_code or not name:
        return

    room = Room.query.get(room_code)
    if not room:
        leave_room(room_code)
        return

    join_room(room_code)
    room.members += 1
    db.session.commit()

    send({"name": name, "message": "has joined the room."}, to=room_code)


@socketio.on("disconnect")
def disconnect():
    room_code = session.get("room")
    name = session.get("name")
    leave_room(room_code)

    room = Room.query.get(room_code)
    if room:
        room.members -= 1
        if room.members <= 0:
            db.session.delete(room)
        db.session.commit()

    send({"name": name, "message": "has left the room."}, to=room_code)


@socketio.on("message")
def message(data):
    room_code = session.get("room")
    name = session.get("name")
    if not room_code or not name:
        return

    message_text = data["data"]
    timestamp = datetime.now()

    msg = Message(room_code=room_code, sender_name=name, message=message_text, timestamp=timestamp)
    db.session.add(msg)
    db.session.commit()

    content = {
        "name": name,
        "message": message_text,
        "timestamp": timestamp.strftime(r"%d-%m-%Y %H:%M:%S")
    }
    send(content, to=room_code)
# -----------------------------------------------------------------------------------------------------------------------------------


# TABLE CREATION --------------------------------------------------------------------------------------------------------------------
@app.route("/create_tables")
def create_tables():
    db.create_all()
    return "Tables created!"
# -----------------------------------------------------------------------------------------------------------------------------------