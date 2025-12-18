from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime, date, timedelta
from supabase import create_client, Client
from email_service import send_alert_email, send_change_of_plans_email

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

def get_weekday_name(d):
    """Get lowercase weekday name from date."""
    return d.strftime("%A").lower()

def get_week_dates(start_date):
    """Get Monday-Friday dates for the week containing start_date."""
    monday = start_date - timedelta(days=start_date.weekday())
    return [monday + timedelta(days=i) for i in range(5)]

def get_two_week_dates():
    """Get dates for current week and next week (Mon-Fri each)."""
    today = date.today()
    current_week = get_week_dates(today)
    next_week = get_week_dates(today + timedelta(days=7))
    return current_week + next_week

def run_monthly_sync():
    """Run monthly sync operations - populate next month on 25th, cleanup last month on 5th."""
    today = date.today()
    current_month = today.month
    current_year = today.year
    
    # On 25th or later: populate next month's absences
    if today.day >= 25:
        next_month = current_month + 1 if current_month < 12 else 1
        next_year = current_year if current_month < 12 else current_year + 1
        sync_key = f"populate_{next_year}_{next_month}"
        
        existing = supabase.table("sync_log").select("id").eq("sync_key", sync_key).execute()
        if not existing.data:
            populate_month_absences(next_year, next_month)
            supabase.table("sync_log").insert({"sync_key": sync_key}).execute()
    
    # On 5th or later: cleanup last month's absences
    if today.day >= 5:
        last_month = current_month - 1 if current_month > 1 else 12
        last_year = current_year if current_month > 1 else current_year - 1
        sync_key = f"cleanup_{last_year}_{last_month}"
        
        existing = supabase.table("sync_log").select("id").eq("sync_key", sync_key).execute()
        if not existing.data:
            cleanup_month_absences(last_year, last_month)
            supabase.table("sync_log").insert({"sync_key": sync_key}).execute()

def populate_month_absences(year, month):
    """Populate absences for a month based on usual absence patterns."""
    usual = supabase.table("usual_absences").select("*").execute()
    
    if not usual.data:
        return
    
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    entries = []
    current = first_day
    while current <= last_day:
        weekday = get_weekday_name(current)
        if weekday in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
            for pattern in usual.data:
                if pattern.get(weekday, False):
                    entries.append({
                        "key_bearer": pattern["key_bearer"],
                        "absence_date": current.isoformat()
                    })
        current += timedelta(days=1)
    
    for entry in entries:
        try:
            supabase.table("absences").upsert(entry, on_conflict="key_bearer,absence_date").execute()
        except:
            pass

def cleanup_month_absences(year, month):
    """Remove all absences from a past month."""
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    supabase.table("absences").delete().gte("absence_date", first_day.isoformat()).lte("absence_date", last_day.isoformat()).execute()

def check_and_send_alert(target_date):
    """Check if all key bearers are absent and send alert if needed."""
    config = load_config()
    key_bearers = config["key_bearers"]
    
    existing = supabase.table("email_log").select("id").eq("alert_date", target_date).execute()
    
    if existing.data:
        return {"sent": False, "reason": "already_sent"}
    
    absences = supabase.table("absences").select("key_bearer").eq("absence_date", target_date).execute()
    
    absent_names = {row["key_bearer"] for row in absences.data}
    all_bearer_names = {kb["name"] for kb in key_bearers}
    
    if absent_names >= all_bearer_names:
        success = send_alert_email(config, target_date, key_bearers)
        
        if success:
            supabase.table("email_log").insert({"alert_date": target_date, "followup_sent": False}).execute()
            return {"sent": True, "reason": "all_absent"}
        else:
            return {"sent": False, "reason": "email_failed"}
    
    return {"sent": False, "reason": "not_all_absent", "absent": len(absent_names), "total": len(all_bearer_names)}

@app.route("/")
def index():
    run_monthly_sync()
    config = load_config()
    return render_template("index.html", key_bearers=config["key_bearers"])

@app.route("/api/mark-absent", methods=["POST"])
def mark_absent():
    data = request.json
    key_bearer = data.get("key_bearer")
    dates = data.get("dates", [])
    confirmed = data.get("confirmed", False)
    
    if not key_bearer or not dates:
        return jsonify({"error": "Missing key_bearer or dates"}), 400
    
    alerts_sent = []
    
    for d in dates:
        try:
            supabase.table("absences").upsert({
                "key_bearer": key_bearer,
                "absence_date": d
            }, on_conflict="key_bearer,absence_date").execute()
            
            if confirmed:
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

@app.route("/api/check-absence-impact", methods=["POST"])
def check_absence_impact():
    """Check if marking these absences would trigger an email alert."""
    data = request.json
    key_bearer = data.get("key_bearer")
    dates = data.get("dates", [])
    
    config = load_config()
    key_bearers = config["key_bearers"]
    all_bearer_names = {kb["name"] for kb in key_bearers}
    
    will_trigger = []
    
    for d in dates:
        existing = supabase.table("email_log").select("id").eq("alert_date", d).execute()
        if existing.data:
            continue
        
        absences = supabase.table("absences").select("key_bearer").eq("absence_date", d).execute()
        absent_names = {row["key_bearer"] for row in absences.data}
        absent_names.add(key_bearer)
        
        if absent_names >= all_bearer_names:
            will_trigger.append(d)
    
    return jsonify({
        "will_trigger_email": len(will_trigger) > 0,
        "trigger_dates": will_trigger
    })

@app.route("/api/check-removal-impact", methods=["POST"])
def check_removal_impact():
    """Check if removing absences would trigger a 'change of plans' email."""
    data = request.json
    key_bearer = data.get("key_bearer")
    dates = data.get("dates", [])
    
    will_trigger = []
    
    for d in dates:
        log_entry = supabase.table("email_log").select("*").eq("alert_date", d).execute()
        
        if log_entry.data and not log_entry.data[0].get("followup_sent", False):
            will_trigger.append(d)
    
    return jsonify({
        "will_trigger_email": len(will_trigger) > 0,
        "trigger_dates": will_trigger
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
    confirmed = data.get("confirmed", False)
    
    config = load_config()
    followup_sent_for = []
    
    for d in dates:
        supabase.table("absences").delete().eq("key_bearer", key_bearer).eq("absence_date", d).execute()
        
        if confirmed:
            log_entry = supabase.table("email_log").select("*").eq("alert_date", d).execute()
            
            if log_entry.data and not log_entry.data[0].get("followup_sent", False):
                success = send_change_of_plans_email(config, d, key_bearer)
                
                if success:
                    supabase.table("email_log").update({"followup_sent": True}).eq("alert_date", d).execute()
                    followup_sent_for.append(d)
    
    return jsonify({"success": True, "dates_cancelled": dates, "followup_emails_sent": followup_sent_for})

@app.route("/api/usual-absences/<key_bearer>")
def get_usual_absences(key_bearer):
    """Get usual absence pattern for a key bearer."""
    result = supabase.table("usual_absences").select("*").eq("key_bearer", key_bearer).execute()
    
    if result.data:
        pattern = result.data[0]
        return jsonify({
            "monday": pattern.get("monday", False),
            "tuesday": pattern.get("tuesday", False),
            "wednesday": pattern.get("wednesday", False),
            "thursday": pattern.get("thursday", False),
            "friday": pattern.get("friday", False)
        })
    else:
        return jsonify({
            "monday": False,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": False
        })

@app.route("/api/usual-absences", methods=["POST"])
def update_usual_absences():
    """Update usual absence pattern for a key bearer."""
    data = request.json
    key_bearer = data.get("key_bearer")
    pattern = {
        "key_bearer": key_bearer,
        "monday": data.get("monday", False),
        "tuesday": data.get("tuesday", False),
        "wednesday": data.get("wednesday", False),
        "thursday": data.get("thursday", False),
        "friday": data.get("friday", False)
    }
    
    supabase.table("usual_absences").upsert(pattern, on_conflict="key_bearer").execute()
    
    # Update remaining days of current month
    today = date.today()
    if today.month == 12:
        last_day = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    current = today
    while current <= last_day:
        weekday = get_weekday_name(current)
        if weekday in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
            if pattern.get(weekday, False):
                try:
                    supabase.table("absences").upsert({
                        "key_bearer": key_bearer,
                        "absence_date": current.isoformat()
                    }, on_conflict="key_bearer,absence_date").execute()
                except:
                    pass
        current += timedelta(days=1)
    
    return jsonify({"success": True, "message": "Usual absence pattern updated"})

@app.route("/api/weekly-status")
def get_weekly_status():
    """Get 2-week status for all key bearers."""
    config = load_config()
    key_bearers = config["key_bearers"]
    all_bearer_names = [kb["name"] for kb in key_bearers]
    
    dates = get_two_week_dates()
    date_strs = [d.isoformat() for d in dates]
    
    result = supabase.table("absences").select("key_bearer, absence_date").in_("absence_date", date_strs).execute()
    
    absence_map = {}
    for row in result.data:
        d = row["absence_date"]
        if d not in absence_map:
            absence_map[d] = set()
        absence_map[d].add(row["key_bearer"])
    
    weeks = []
    
    # Current week
    current_week_dates = dates[:5]
    current_week = {"label": "This Week", "days": []}
    for d in current_week_dates:
        d_str = d.isoformat()
        absent = absence_map.get(d_str, set())
        day_data = {
            "date": d_str,
            "day_name": d.strftime("%a"),
            "day_num": d.day,
            "month": d.strftime("%b"),
            "bearers": [],
            "all_absent": len(absent) >= len(all_bearer_names)
        }
        for name in all_bearer_names:
            day_data["bearers"].append({"name": name, "absent": name in absent})
        current_week["days"].append(day_data)
    weeks.append(current_week)
    
    # Next week
    next_week_dates = dates[5:]
    next_week = {"label": "Next Week", "days": []}
    for d in next_week_dates:
        d_str = d.isoformat()
        absent = absence_map.get(d_str, set())
        day_data = {
            "date": d_str,
            "day_name": d.strftime("%a"),
            "day_num": d.day,
            "month": d.strftime("%b"),
            "bearers": [],
            "all_absent": len(absent) >= len(all_bearer_names)
        }
        for name in all_bearer_names:
            day_data["bearers"].append({"name": name, "absent": name in absent})
        next_week["days"].append(day_data)
    weeks.append(next_week)
    
    return jsonify({"weeks": weeks, "key_bearers": all_bearer_names})

@app.route("/api/status/<date_str>")
def get_status(date_str):
    """Get status for a specific date."""
    config = load_config()
    key_bearers = config["key_bearers"]
    
    result = supabase.table("absences").select("key_bearer").eq("absence_date", date_str).execute()
    absent_names = {row["key_bearer"] for row in result.data}
    
    status = []
    for kb in key_bearers:
        status.append({"name": kb["name"], "absent": kb["name"] in absent_names})
    
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
    run_monthly_sync()
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
