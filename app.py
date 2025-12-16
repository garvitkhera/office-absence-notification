from flask import Flask, render_template, request, jsonify
import sqlite3
import json
from datetime import datetime, date
from email_service import send_alert_email
from pathlib import Path

app = Flask(__name__)

DB_PATH = "absences.db"
CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS absences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_bearer TEXT NOT NULL,
            absence_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(key_bearer, absence_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_date DATE NOT NULL UNIQUE,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def check_and_send_alert(target_date):
    """Check if all key bearers are absent and send alert if needed."""
    config = load_config()
    key_bearers = config["key_bearers"]
    
    conn = get_db()
    
    # Check if alert already sent for this date
    existing = conn.execute(
        "SELECT id FROM email_log WHERE alert_date = ?", 
        (target_date,)
    ).fetchone()
    
    if existing:
        conn.close()
        return {"sent": False, "reason": "already_sent"}
    
    # Get absences for this date
    absences = conn.execute(
        "SELECT DISTINCT key_bearer FROM absences WHERE absence_date = ?",
        (target_date,)
    ).fetchall()
    
    absent_names = {row["key_bearer"] for row in absences}
    all_bearer_names = {kb["name"] for kb in key_bearers}
    
    if absent_names >= all_bearer_names:  # All key bearers are absent
        # Send email
        success = send_alert_email(config, target_date, key_bearers)
        
        if success:
            conn.execute("INSERT INTO email_log (alert_date) VALUES (?)", (target_date,))
            conn.commit()
            conn.close()
            return {"sent": True, "reason": "all_absent"}
        else:
            conn.close()
            return {"sent": False, "reason": "email_failed"}
    
    conn.close()
    return {"sent": False, "reason": "not_all_absent", "absent": len(absent_names), "total": len(all_bearer_names)}

@app.route("/")
def index():
    config = load_config()
    return render_template("index.html", key_bearers=config["key_bearers"])

@app.route("/api/mark-absent", methods=["POST"])
def mark_absent():
    data = request.json
    key_bearer = data.get("key_bearer")
    dates = data.get("dates", [])  # List of date strings YYYY-MM-DD
    
    if not key_bearer or not dates:
        return jsonify({"error": "Missing key_bearer or dates"}), 400
    
    conn = get_db()
    alerts_sent = []
    
    for d in dates:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO absences (key_bearer, absence_date) VALUES (?, ?)",
                (key_bearer, d)
            )
            conn.commit()
            
            # Check if alert needs to be sent
            alert_result = check_and_send_alert(d)
            if alert_result["sent"]:
                alerts_sent.append(d)
        except Exception as e:
            print(f"Error marking absence: {e}")
    
    conn.close()
    
    return jsonify({
        "success": True,
        "dates_marked": dates,
        "alerts_sent": alerts_sent
    })

@app.route("/api/absences")
def get_absences():
    """Get all absences for calendar display."""
    conn = get_db()
    rows = conn.execute(
        "SELECT key_bearer, absence_date FROM absences WHERE absence_date >= date('now')"
    ).fetchall()
    conn.close()
    
    absences = {}
    for row in rows:
        d = row["absence_date"]
        if d not in absences:
            absences[d] = []
        absences[d].append(row["key_bearer"])
    
    return jsonify(absences)

@app.route("/api/my-absences/<key_bearer>")
def get_my_absences(key_bearer):
    """Get absences for a specific key bearer."""
    conn = get_db()
    rows = conn.execute(
        "SELECT absence_date FROM absences WHERE key_bearer = ? AND absence_date >= date('now')",
        (key_bearer,)
    ).fetchall()
    conn.close()
    
    return jsonify([row["absence_date"] for row in rows])

@app.route("/api/cancel-absence", methods=["POST"])
def cancel_absence():
    data = request.json
    key_bearer = data.get("key_bearer")
    dates = data.get("dates", [])
    
    conn = get_db()
    for d in dates:
        conn.execute(
            "DELETE FROM absences WHERE key_bearer = ? AND absence_date = ?",
            (key_bearer, d)
        )
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "dates_cancelled": dates})

@app.route("/api/status/<date_str>")
def get_status(date_str):
    """Get status for a specific date."""
    config = load_config()
    key_bearers = config["key_bearers"]
    
    conn = get_db()
    absences = conn.execute(
        "SELECT key_bearer FROM absences WHERE absence_date = ?",
        (date_str,)
    ).fetchall()
    conn.close()
    
    absent_names = {row["key_bearer"] for row in absences}
    
    status = []
    for kb in key_bearers:
        status.append({
            "name": kb["name"],
            "absent": kb["name"] in absent_names
        })
    
    all_absent = len(absent_names) >= len(key_bearers)
    
    return jsonify({
        "date": date_str,
        "key_bearers": status,
        "all_absent": all_absent,
        "absent_count": len(absent_names),
        "total_count": len(key_bearers)
    })

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
