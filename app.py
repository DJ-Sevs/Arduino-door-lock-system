from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import mysql.connector
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "ultraelectromagneticpop" #session key
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

#db connectionnnn lololololol
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="doorlock_user",
        password="12345",
        database="doorlock"
    )

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.route('/')
def index():
    return redirect(url_for('login')) if 'user' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user'] = user['username']
            return redirect(url_for('history'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    #fetch display logs
    cursor.execute("SELECT * FROM access_log ORDER BY timestamp DESC LIMIT 10")
    logs = cursor.fetchall()
    #fetchdispaly count
    cursor.execute("SELECT username, (SELECT COUNT(*) FROM access_log WHERE event = CONCAT('SUCCESS: ', users.username)) as success_count FROM users")
    user_stats = cursor.fetchall()
    #fetch display failed attemps
    cursor.execute("SELECT COUNT(*) as unknown_count FROM access_log WHERE event = 'PIN_FAILURE'")
    unknown_count = cursor.fetchone()['unknown_count']
    conn.close()
    return render_template('history.html', logs=logs, user_stats=user_stats, unknown_count=unknown_count)

@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    error = None

    if request.method == 'POST':
        name = request.form['username']
        pin = request.form['pin_code']
        
        # Unique PIN Check when adding new user
        cursor.execute("SELECT username FROM users WHERE pin_code = %s", (pin,))
        existing = cursor.fetchone()
        
        if existing:
            error = f"Error: PIN {pin} is already assigned to {existing['username']}."
        else:
            cursor.execute("INSERT INTO users (username, pin_code) VALUES (%s, %s)", (name, pin))
            conn.commit()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('users.html', users=users, error=error)

@app.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    error = None

    if request.method == 'POST':
        new_name = request.form['username']
        new_pin = request.form['pin_code']

        #pin check if may ara na when editing
        cursor.execute("SELECT username FROM users WHERE pin_code = %s AND id != %s", (new_pin, user_id))
        existing = cursor.fetchone()

        if existing:
            error = f"Cannot update: PIN {new_pin} is already used by {existing['username']}."
        else:
            cursor.execute("UPDATE users SET username=%s, pin_code=%s WHERE id=%s", (new_name, new_pin, user_id))
            conn.commit()
            conn.close()
            return redirect(url_for('manage_users'))

    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    target_user = cursor.fetchone()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('users.html', users=users, edit_user=target_user, error=error)

#users delete
@app.route('/delete-user/<int:user_id>')
def delete_user(user_id):
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_users'))

#API for door trigger
@app.route('/open-door', methods=['POST'])
def open_door():
    # Allow if web session exists OR if mobile API KEY is provided
    api_key = request.headers.get("X-API-KEY")
    if 'user' in session or api_key == "ultraelectromagneticpop":  # Simple API key check for mobile access
        try:
            requests.post("http://localhost:5051/open-door")
            return jsonify({"status": "success"})
        except: 
            return jsonify({"status": "error"}), 55555555555555555555555555555555555555
    return jsonify({"status": "unauthorized"}), 403

#API for fetching logs in JSON format (for mobile app)
@app.route('/history-json')
def history_json():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch logs (limit 20)
    cursor.execute("SELECT * FROM access_log ORDER BY timestamp DESC LIMIT 20")
    logs = cursor.fetchall()
    
    # Format dates for JSON
    for log in logs:
        if log['timestamp']:
            log['timestamp'] = log['timestamp'].strftime("%Y-%m-%d %H:%M:%S")

    # Fetch User Stats
    cursor.execute("""
        SELECT username, 
        (SELECT COUNT(*) FROM access_log WHERE event = CONCAT('SUCCESS: ', users.username)) as success_count 
        FROM users
    """)
    user_stats = cursor.fetchall()

    # Fetch Unknown PIN count
    cursor.execute("SELECT COUNT(*) as unknown_count FROM access_log WHERE event = 'PIN_FAILURE'")
    unknown_count = cursor.fetchone()['unknown_count']

    conn.close()
    return jsonify({
        "logs": logs,
        "user_stats": user_stats,
        "unknown_count": unknown_count
    })

#WebSocket endpoint for real-time log updates
@app.route('/emit_log', methods=['POST'])
def emit_log():
    data = request.json
    socketio.emit('new_log', data)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    socketio.run(app, port=5000, host='0.0.0.0', debug=True)
