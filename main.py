# IMPORTS --------------------------------------------------------------------------------------------------------------------------
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO

import random
import secrets
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
    return render_template("room.html")
# -----------------------------------------------------------------------------------------------------------------------------------


# RUN APP ---------------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    socketio.run(app)
# -----------------------------------------------------------------------------------------------------------------------------------