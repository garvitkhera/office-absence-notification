from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime, date, timedelta
from supabase import create_client, Client
from email_service import send_alert_email, send_change_of_plans_email
import pytz

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

def get_sydney_timezone():
    """Get current Sydney timezone (handles DST automatically)."""
    return pytz.timezone('Australia/Sydney')

def get_sydney_now():
    """Get current datetime in Sydney timezone."""
    sydney_tz = get_sydney_timezone()
    return datetime.now(sydney_tz)

def get_sydney_today():
    """Get today's date in Sydney timezone."""
    return get_sydney_now().date()

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

def get_key_bearers():
    """Get all employees who have office keys."""
    result = supabase.table("employees").select("*").eq("has_key", True).execute()
    return result.data if result.data else []

def get_all_employees():
    """Get all employees."""
    result = supabase.table("employees").select("*").order("name").execute()
    return result.data if result.data else []

def get_weekday_name(d):
    """Get lowercase weekday name from date."""
    return d.strftime("%A").lower()

def get_week_dates(start_date):
    """Get Monday-Friday dates for the week containing start_date."""
    monday = start_date - timedelta(days=start_date.weekday())
    return [monday + timedelta(days=i) for i in range(5)]

def get_two_week_dates():
    """Get dates for current week and next week (Mon-Fri each)."""
    today = get_sydney_today()
    current_week = get_week_dates(today)
    next_week = get_week_dates(today + timedelta(days=7))
    return current_week + next_week

def run_monthly_sync():
    """Run monthly sync operations - populate next month on 25th, cleanup last month on 5th."""
    today = get_sydney_today()
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
                        "employee_name": pattern["employee_name"],
                        "absence_date": current.isoformat()
                    })
        current += timedelta(days=1)
    
    for entry in entries:
        try:
            supabase.table("absences").upsert(entry, on_conflict="employee_name,absence_date").execute()
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

def can_send_new_alert(target_date):
    """Check if we can send a new alert for this date.
    Returns True if:
    - No email_log entry exists, OR
    - Email_log entry exists AND followup_sent=True (someone became available, so cycle reset)
    """
    existing = supabase.table("email_log").select("*").eq("alert_date", target_date).execute()
    
    if not existing.data:
        return True
    
    # If followup was sent, we can send a new alert
    return existing.data[0].get("followup_sent", False)

def check_and_send_alert(target_date):
    """Check if all key bearers are absent and send alert if needed."""
    config = load_config()
    key_bearers = get_key_bearers()
    
    if not key_bearers:
        return {"sent": False, "reason": "no_key_bearers"}
    
    # Check if we can send a new alert
    if not can_send_new_alert(target_date):
        return {"sent": False, "reason": "already_sent"}
    
    absences = supabase.table("absences").select("employee_name").eq("absence_date", target_date).execute()
    
    absent_names = {row["employee_name"] for row in absences.data}
    all_bearer_names = {kb["name"] for kb in key_bearers}
    
    if absent_names >= all_bearer_names:
        success = send_alert_email(config, target_date, key_bearers)
        
        if success:
            # Delete old entry if exists, then insert fresh one
            supabase.table("email_log").delete().eq("alert_date", target_date).execute()
            supabase.table("email_log").insert({"alert_date": target_date, "followup_sent": False}).execute()
            return {"sent": True, "reason": "all_absent"}
        else:
            return {"sent": False, "reason": "email_failed"}
    
    return {"sent": False, "reason": "not_all_absent", "absent": len(absent_names & all_bearer_names), "total": len(all_bearer_names)}

@app.route("/")
def index():
    run_monthly_sync()
    employees = get_all_employees()
    sydney_today = get_sydney_today().isoformat()
    return render_template("index.html", employees=employees, sydney_today=sydney_today)

@app.route("/api/employees")
def api_get_employees():
    """Get all employees."""
    employees = get_all_employees()
    return jsonify(employees)

@app.route("/api/employees/<employee_name>/toggle-key", methods=["POST"])
def toggle_key_status(employee_name):
    """Toggle has_key status for an employee."""
    data = request.json
    new_status = data.get("has_key", False)
    
    supabase.table("employees").update({"has_key": new_status}).eq("name", employee_name).execute()
    
    return jsonify({"success": True, "has_key": new_status})

@app.route("/api/mark-absent", methods=["POST"])
def mark_absent():
    data = request.json
    employee_name = data.get("employee_name")
    dates = data.get("dates", [])
    confirmed = data.get("confirmed", False)
    
    if not employee_name or not dates:
        return jsonify({"error": "Missing employee_name or dates"}), 400
    
    alerts_sent = []
    
    for d in dates:
        try:
            supabase.table("absences").upsert({
                "employee_name": employee_name,
                "absence_date": d
            }, on_conflict="employee_name,absence_date").execute()
            
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
    employee_name = data.get("employee_name")
    dates = data.get("dates", [])
    
    # Check if this employee has a key
    employee = supabase.table("employees").select("has_key").eq("name", employee_name).execute()
    if not employee.data or not employee.data[0].get("has_key"):
        return jsonify({"will_trigger_email": False, "trigger_dates": []})
    
    key_bearers = get_key_bearers()
    all_bearer_names = {kb["name"] for kb in key_bearers}
    
    will_trigger = []
    
    for d in dates:
        # Check if we can send a new alert for this date
        if not can_send_new_alert(d):
            continue
        
        absences = supabase.table("absences").select("employee_name").eq("absence_date", d).execute()
        absent_names = {row["employee_name"] for row in absences.data}
        absent_names.add(employee_name)
        
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
    employee_name = data.get("employee_name")
    dates = data.get("dates", [])
    
    # Check if this employee has a key
    employee = supabase.table("employees").select("has_key").eq("name", employee_name).execute()
    if not employee.data or not employee.data[0].get("has_key"):
        return jsonify({"will_trigger_email": False, "trigger_dates": []})
    
    will_trigger = []
    
    for d in dates:
        # Check if an alert was sent AND followup not yet sent
        log_entry = supabase.table("email_log").select("*").eq("alert_date", d).execute()
        
        if log_entry.data and not log_entry.data[0].get("followup_sent", False):
            will_trigger.append(d)
    
    return jsonify({
        "will_trigger_email": len(will_trigger) > 0,
        "trigger_dates": will_trigger
    })

@app.route("/api/check-usual-absence-impact", methods=["POST"])
def check_usual_absence_impact():
    """Check if updating usual absence pattern would trigger email alerts."""
    data = request.json
    employee_name = data.get("employee_name")
    day = data.get("day")  # e.g., 'monday'
    
    # Check if this employee has a key
    employee = supabase.table("employees").select("has_key").eq("name", employee_name).execute()
    if not employee.data or not employee.data[0].get("has_key"):
        return jsonify({"will_trigger_email": False, "trigger_dates": []})
    
    key_bearers = get_key_bearers()
    all_bearer_names = {kb["name"] for kb in key_bearers}
    
    # Get all dates for this weekday from today to end of month
    today = get_sydney_today()
    if today.month == 12:
        last_day = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    will_trigger = []
    current = today
    while current <= last_day:
        if get_weekday_name(current) == day:
            d_str = current.isoformat()
            
            # Check if we can send a new alert
            if not can_send_new_alert(d_str):
                current += timedelta(days=1)
                continue
            
            # Get current absences
            absences = supabase.table("absences").select("employee_name").eq("absence_date", d_str).execute()
            absent_names = {row["employee_name"] for row in absences.data}
            absent_names.add(employee_name)
            
            if absent_names >= all_bearer_names:
                will_trigger.append(d_str)
        
        current += timedelta(days=1)
    
    return jsonify({
        "will_trigger_email": len(will_trigger) > 0,
        "trigger_dates": will_trigger
    })
    
@app.route("/api/check-usual-presence-impact", methods=["POST"])
def check_usual_presence_impact():
    """Check if marking a day as 'present' would trigger change of plans emails."""
    data = request.json
    employee_name = data.get("employee_name")
    day = data.get("day")  # e.g., 'monday'
    
    # Check if this employee has a key
    employee = supabase.table("employees").select("has_key").eq("name", employee_name).execute()
    if not employee.data or not employee.data[0].get("has_key"):
        return jsonify({"will_trigger_email": False, "trigger_dates": []})
    
    # Get all dates for this weekday from tomorrow to end of month
    today = get_sydney_today()
    tomorrow = today + timedelta(days=1)
    if today.month == 12:
        last_day = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    will_trigger = []
    current = tomorrow
    while current <= last_day:
        if get_weekday_name(current) == day:
            d_str = current.isoformat()
            
            # Check if an alert was sent AND followup not yet sent
            log_entry = supabase.table("email_log").select("*").eq("alert_date", d_str).execute()
            if log_entry.data and not log_entry.data[0].get("followup_sent", False):
                will_trigger.append(d_str)
        
        current += timedelta(days=1)
    
    return jsonify({
        "will_trigger_email": len(will_trigger) > 0,
        "trigger_dates": will_trigger
    })

@app.route("/api/absences")
def get_absences():
    """Get all absences for calendar display."""
    today = get_sydney_today().isoformat()
    result = supabase.table("absences").select("employee_name, absence_date").gte("absence_date", today).execute()
    
    absences = {}
    for row in result.data:
        d = row["absence_date"]
        if d not in absences:
            absences[d] = []
        absences[d].append(row["employee_name"])
    
    return jsonify(absences)

@app.route("/api/my-absences/<employee_name>")
def get_my_absences(employee_name):
    """Get absences for a specific employee."""
    today = get_sydney_today().isoformat()
    result = supabase.table("absences").select("absence_date").eq("employee_name", employee_name).gte("absence_date", today).order("absence_date").execute()
    
    return jsonify([row["absence_date"] for row in result.data])

@app.route("/api/cancel-absence", methods=["POST"])
def cancel_absence():
    data = request.json
    employee_name = data.get("employee_name")
    dates = data.get("dates", [])
    confirmed = data.get("confirmed", False)
    
    config = load_config()
    followup_sent_for = []
    
    for d in dates:
        # Delete the absence first
        supabase.table("absences").delete().eq("employee_name", employee_name).eq("absence_date", d).execute()
        
        if confirmed:
            # Check if we need to send "change of plans" email
            log_entry = supabase.table("email_log").select("*").eq("alert_date", d).execute()
            
            if log_entry.data and not log_entry.data[0].get("followup_sent", False):
                success = send_change_of_plans_email(config, d, employee_name)
                
                if success:
                    # Mark followup as sent - this allows a new alert to be sent if all become absent again
                    supabase.table("email_log").update({"followup_sent": True}).eq("alert_date", d).execute()
                    followup_sent_for.append(d)
    
    return jsonify({"success": True, "dates_cancelled": dates, "followup_emails_sent": followup_sent_for})

@app.route("/api/usual-absences/<employee_name>")
def get_usual_absences(employee_name):
    """Get usual absence pattern for an employee."""
    result = supabase.table("usual_absences").select("*").eq("employee_name", employee_name).execute()
    
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
    """Update usual absence pattern for an employee."""
    data = request.json
    employee_name = data.get("employee_name")
    confirmed = data.get("confirmed", False)
    pattern = {
        "employee_name": employee_name,
        "monday": data.get("monday", False),
        "tuesday": data.get("tuesday", False),
        "wednesday": data.get("wednesday", False),
        "thursday": data.get("thursday", False),
        "friday": data.get("friday", False)
    }
    
    supabase.table("usual_absences").upsert(pattern, on_conflict="employee_name").execute()
    
    # Update from TOMORROW to end of current month
    today = get_sydney_today()
    tomorrow = today + timedelta(days=1)
    if today.month == 12:
        last_day = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    config = load_config()
    alerts_sent = []
    followup_sent = []
    
    current = tomorrow
    while current <= last_day:
        weekday = get_weekday_name(current)
        if weekday in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
            d_str = current.isoformat()
            
            if pattern.get(weekday, False):
                # Day marked as ABSENT - add absence
                try:
                    supabase.table("absences").upsert({
                        "employee_name": employee_name,
                        "absence_date": d_str
                    }, on_conflict="employee_name,absence_date").execute()
                    
                    # Check if this triggers an email alert
                    if confirmed:
                        alert_result = check_and_send_alert(d_str)
                        if alert_result["sent"]:
                            alerts_sent.append(d_str)
                except:
                    pass
            else:
                # Day marked as PRESENT - remove absence if exists
                try:
                    supabase.table("absences").delete().eq("employee_name", employee_name).eq("absence_date", d_str).execute()
                    
                    # Check if this triggers a "change of plans" email
                    if confirmed:
                        log_entry = supabase.table("email_log").select("*").eq("alert_date", d_str).execute()
                        if log_entry.data and not log_entry.data[0].get("followup_sent", False):
                            success = send_change_of_plans_email(config, d_str, employee_name)
                            if success:
                                supabase.table("email_log").update({"followup_sent": True}).eq("alert_date", d_str).execute()
                                followup_sent.append(d_str)
                except:
                    pass
        
        current += timedelta(days=1)
    
    return jsonify({
        "success": True, 
        "message": "Usual absence pattern updated", 
        "alerts_sent": alerts_sent,
        "followup_sent": followup_sent
    })

@app.route("/api/weekly-status")
def get_weekly_status():
    """Get 2-week status for all employees."""
    employees = get_all_employees()
    key_bearers = get_key_bearers()
    key_bearer_names = {kb["name"] for kb in key_bearers}
    
    dates = get_two_week_dates()
    date_strs = [d.isoformat() for d in dates]
    
    result = supabase.table("absences").select("employee_name, absence_date").in_("absence_date", date_strs).execute()
    
    absence_map = {}
    for row in result.data:
        d = row["absence_date"]
        if d not in absence_map:
            absence_map[d] = set()
        absence_map[d].add(row["employee_name"])
    
    weeks = []
    
    # Current week
    current_week_dates = dates[:5]
    current_week = {"label": "This Week", "days": []}
    for d in current_week_dates:
        d_str = d.isoformat()
        absent = absence_map.get(d_str, set())
        
        # Check if all KEY BEARERS are absent
        absent_key_bearers = absent & key_bearer_names
        all_key_bearers_absent = len(key_bearer_names) > 0 and absent_key_bearers >= key_bearer_names
        
        day_data = {
            "date": d_str,
            "day_name": d.strftime("%a"),
            "day_num": d.day,
            "month": d.strftime("%b"),
            "employees": [],
            "all_key_bearers_absent": all_key_bearers_absent
        }
        for emp in employees:
            day_data["employees"].append({
                "name": emp["name"],
                "has_key": emp.get("has_key", False),
                "absent": emp["name"] in absent
            })
        current_week["days"].append(day_data)
    weeks.append(current_week)
    
    # Next week
    next_week_dates = dates[5:]
    next_week = {"label": "Next Week", "days": []}
    for d in next_week_dates:
        d_str = d.isoformat()
        absent = absence_map.get(d_str, set())
        
        absent_key_bearers = absent & key_bearer_names
        all_key_bearers_absent = len(key_bearer_names) > 0 and absent_key_bearers >= key_bearer_names
        
        day_data = {
            "date": d_str,
            "day_name": d.strftime("%a"),
            "day_num": d.day,
            "month": d.strftime("%b"),
            "employees": [],
            "all_key_bearers_absent": all_key_bearers_absent
        }
        for emp in employees:
            day_data["employees"].append({
                "name": emp["name"],
                "has_key": emp.get("has_key", False),
                "absent": emp["name"] in absent
            })
        next_week["days"].append(day_data)
    weeks.append(next_week)
    
    return jsonify({"weeks": weeks, "employees": [{"name": e["name"], "has_key": e.get("has_key", False)} for e in employees]})

@app.route("/api/status/<date_str>")
def get_status(date_str):
    """Get status for a specific date."""
    employees = get_all_employees()
    key_bearers = get_key_bearers()
    key_bearer_names = {kb["name"] for kb in key_bearers}
    
    result = supabase.table("absences").select("employee_name").eq("absence_date", date_str).execute()
    absent_names = {row["employee_name"] for row in result.data}
    
    status = []
    for emp in employees:
        status.append({
            "name": emp["name"],
            "has_key": emp.get("has_key", False),
            "absent": emp["name"] in absent_names
        })
    
    absent_key_bearers = absent_names & key_bearer_names
    all_key_bearers_absent = len(key_bearer_names) > 0 and absent_key_bearers >= key_bearer_names
    
    return jsonify({
        "date": date_str,
        "employees": status,
        "all_key_bearers_absent": all_key_bearers_absent,
        "absent_key_bearer_count": len(absent_key_bearers),
        "total_key_bearer_count": len(key_bearer_names)
    })

@app.route("/api/sydney-time")
def get_sydney_time():
    """Get current Sydney time."""
    sydney_now = get_sydney_now()
    return jsonify({
        "datetime": sydney_now.isoformat(),
        "date": sydney_now.date().isoformat(),
        "time": sydney_now.strftime("%H:%M:%S"),
        "timezone": str(sydney_now.tzname()),
        "utc_offset": str(sydney_now.strftime("%z"))
    })

@app.route("/health")
def health():
    run_monthly_sync()
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
