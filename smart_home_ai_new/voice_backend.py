import time
import firebase_admin
from firebase_admin import credentials, db

# 🔥 CONNECT FIREBASE
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smarthome1-5428e-default-rtdb.firebaseio.com/ '
})

# ➕ ADD ROOM
def add_room(room):
    db.reference(f"rooms/{room}").set({
        "devices": {
            "light": False,
            "fan": False,
            "ac": False
        }
    })
    print(f"✅ Room '{room}' added")

# ❌ DELETE ROOM
def delete_room(room):
    db.reference(f"rooms/{room}").delete()
    print(f"❌ Room '{room}' deleted")

# 💡 CONTROL DEVICE
def control_device(room, device, state):
    db.reference(f"rooms/{room}/devices/{device}").set(state)
    print(f"💡 {device} in {room} → {state}")

# 🧠 PROCESS COMMAND
def process_command(command):
    command = command.lower().strip()

    try:
        if "add room" in command:
            room = command.replace("add room", "").strip()
            add_room(room)

        elif "delete room" in command:
            room = command.replace("delete room", "").strip()
            delete_room(room)

        elif "turn on" in command:
            words = command.replace("turn on", "").strip().split()
            if len(words) >= 2:
                room = " ".join(words[:-1])   # supports "living room"
                device = words[-1]
                control_device(room, device, True)

        elif "turn off" in command:
            words = command.replace("turn off", "").strip().split()
            if len(words) >= 2:
                room = " ".join(words[:-1])
                device = words[-1]
                control_device(room, device, False)

        else:
            print("⚠️ Command not recognized")

    except Exception as e:
        print("❌ Error:", e)

# 🔁 LISTEN TO FIREBASE
def listen():
    print("🎤 Backend started... Listening for commands...\n")
    last_command = ""

    while True:
        try:
            command = db.reference("commands").get()

            if command and command != last_command:
                print(f"🎤 Received: {command}")
                process_command(command)
                last_command = command

            time.sleep(2)

        except Exception as e:
            print("❌ Firebase Error:", e)
            time.sleep(5)

# ▶️ RUN
if __name__ == "__main__":
    listen()