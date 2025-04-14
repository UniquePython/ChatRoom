# IMPORTS --------------------------------------------------------------------------------------------------------------------------
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO


import random
import secrets
from datetime import datetime
import os
# -----------------------------------------------------------------------------------------------------------------------------------


# FLASK APP SETUP -------------------------------------------------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(64)
socketio = SocketIO(app)
# -----------------------------------------------------------------------------------------------------------------------------------


# VARIABLES -------------------------------------------------------------------------------------------------------------------------
rooms = {}
# -----------------------------------------------------------------------------------------------------------------------------------


# HELPER METHODS --------------------------------------------------------------------------------------------------------------------
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice('ABC123')
        if code not in rooms:
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
        
        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        
        return redirect(url_for("room"))
    return render_template("home.html")


@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    return render_template("room.html", code=room, messages=rooms[room]["messages"])


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    join_room(room)
    send({"name": name, "message": "has joined the room."}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} has joined room {room}.")


@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    send({"name": name, "message": "has left the room."}, to=room)
    print(f"{name} has left room {room}.")


@socketio.on("message")
def message(data):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        return
    message = data["data"]
    timestamp = datetime.now().strftime(r'%d-%m-%Y %H:%M:%S')
    content = {"name": name, "message": message, "timestamp": timestamp}
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{timestamp} - {name}: {message}")
# -----------------------------------------------------------------------------------------------------------------------------------


# RUN APP ---------------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
# -----------------------------------------------------------------------------------------------------------------------------------