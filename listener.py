import serial, mysql.connector, requests, json, threading
from datetime import datetime
from flask import Flask, jsonify


ser = serial.Serial('COM5', 9600) 
db_config = {"host": "localhost", 
            "user": "doorlock_user", 
            "password": "12345", 
            "database": "doorlock"
            }

# API for dor trigger
listener_app = Flask(__name__)

#door trigger to arduino
@listener_app.route('/open-door', methods=['POST'])
def trigger_open():
    print("[Listener] Manual unlock request received...")
    ser.write(b'OPEN\n')
    return jsonify({"status": "door_triggered"})

def start_api():
    listener_app.run(port=5051)


threading.Thread(target=start_api, daemon=True).start()

#Serial monitor loop siya ni ang responsible sa arduino connection
print("Listener active. Monitoring COM port and API...")
while True:
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()
        try:
            data = json.loads(line)
            if data.get("event") == "PIN_SUBMITTED":
                pin = data.get("pin")
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                cursor.execute("SELECT username FROM users WHERE pin_code = %s", (pin,))
                user = cursor.fetchone()
                
                if user:
                    username = user[0]
                    log_msg = f"SUCCESS: {username}"
                    ser.write(f"OPEN:{username}\n".encode())
                else:
                    log_msg = "PIN_FAILURE"
                    ser.write(b"DENY\n")
                
                #kada enteter pin ga insert sa db
                ts = datetime.now()
                cursor.execute("INSERT INTO access_log (event, pin, timestamp) VALUES (%s, %s, %s)", (log_msg, pin, ts))
                conn.commit()
                conn.close()

                #web update real time
                requests.post("http://localhost:5000/emit_log", json={
                    "event": log_msg, "pin": pin, "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S")
                })
        except:
            pass