from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime, date
from supabase import create_client, Client
from email_service import send_alert_email

# Load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

CONFIG_PATH = "config.json"

# Supabase client
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", "")
)

def load_config():
    """Load config from JSON file, override email settings with env vars if present."""
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    
    if os.environ.get("SMTP_HOST"):
        config["email"]["smtp_host"] = os.environ.get("SMTP_HOST")
    if os.environ.get("SMTP_PORT"):
        config["email"]["smtp_port"] = int(os.environ.get("SMTP_PORT"))
    if os.environ.get("SMTP_USER"):
        config["email"]["smtp_user"] = os.environ.get("SMTP_USER")
    if os.environ.get("SMTP_PASSWORD"):
        config["email"]["smtp_password"] = os.environ.get("SMTP_PASSWORD")
    if os.environ.get("FROM_EMAIL"):
        config["email"]["from_email"] = os.environ.get("FROM_EMAIL")
    if os.environ.get("FROM_NAME"):
        config["email"]["from_name"] = os.environ.get("FROM_NAME")
    
    return config

def check_and_send_alert(target_date):
    """Check if all key bearers are absent and send alert if needed."""
    config = load_config()
    key_bearers = config["key_bearers"]
    
    # Check if alert already sent for this date
    existing = supabase.table("email_log").select("id").eq("alert_date", target_date).execute()
    
    if existing.data:
        return {"sent": False, "reason": "already_sent"}
    
    # Get absences for this date
    absences = supabase.table("absences").select("key_bearer").eq("absence_date", target_date).execute()
    
    absent_names = {row["key_bearer"] for row in absences.data}
    all_bearer_names = {kb["name"] for kb in key_bearers}
    
    if absent_names >= all_bearer_names:  # All key bearers are absent
        success = send_alert_email(config, target_date, key_bearers)
        
        if success:
            supabase.table("email_log").insert({"alert_date": target_date}).execute()
            return {"sent": True, "reason": "all_absent"}
        else:
            return {"sent": False, "reason": "email_failed"}
    
    return {"sent": False, "reason": "not_all_absent", "absent": len(absent_names), "total": len(all_bearer_names)}

@app.route("/")
def index():
    config = load_config()
    return render_template("index.html", key_bearers=config["key_bearers"])

@app.route("/api/mark-absent", methods=["POST"])
def mark_absent():
    data = request.json
    key_bearer = data.get("key_bearer")
    dates = data.get("dates", [])
    
    if not key_bearer or not dates:
        return jsonify({"error": "Missing key_bearer or dates"}), 400
    
    alerts_sent = []
    
    for d in dates:
        try:
            # Upsert to handle duplicates
            supabase.table("absences").upsert({
                "key_bearer": key_bearer,
                "absence_date": d
            }, on_conflict="key_bearer,absence_date").execute()
            
            alert_result = check_and_send_alert(d)
            if alert_result["sent"]:
                alerts_sent.append(d)
        except Exception as e:
            print(f"Error marking absence: {e}")
    
    return jsonify({
        "success": True,
        "dates_marked": dates,
        "alerts_sent": alerts_sent
    })

@app.route("/api/absences")
def get_absences():
    """Get all absences for calendar display."""
    today = date.today().isoformat()
    result = supabase.table("absences").select("key_bearer, absence_date").gte("absence_date", today).execute()
    
    absences = {}
    for row in result.data:
        d = row["absence_date"]
        if d not in absences:
            absences[d] = []
        absences[d].append(row["key_bearer"])
    
    return jsonify(absences)

@app.route("/api/my-absences/<key_bearer>")
def get_my_absences(key_bearer):
    """Get absences for a specific key bearer."""
    today = date.today().isoformat()
    result = supabase.table("absences").select("absence_date").eq("key_bearer", key_bearer).gte("absence_date", today).order("absence_date").execute()
    
    return jsonify([row["absence_date"] for row in result.data])

@app.route("/api/cancel-absence", methods=["POST"])
def cancel_absence():
    data = request.json
    key_bearer = data.get("key_bearer")
    dates = data.get("dates", [])
    
    for d in dates:
        supabase.table("absences").delete().eq("key_bearer", key_bearer).eq("absence_date", d).execute()
    
    return jsonify({"success": True, "dates_cancelled": dates})

@app.route("/api/status/<date_str>")
def get_status(date_str):
    """Get status for a specific date."""
    config = load_config()
    key_bearers = config["key_bearers"]
    
    result = supabase.table("absences").select("key_bearer").eq("absence_date", date_str).execute()
    
    absent_names = {row["key_bearer"] for row in result.data}
    
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
    
@app.route("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
