import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_alert_email(config, alert_date, absent_bearers):
    """Send alert email when all key bearers are absent."""
    
    email_config = config["email"]
    recipients = config["recipients"]
    
    date_obj = datetime.strptime(alert_date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%A, %B %d, %Y")
    
    to_emails = [r["email"] for r in recipients]
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔑 Park Agility Office Alert - No Key Bearers Available - {formatted_date}"
    msg["From"] = f"{email_config['from_name']} <{email_config['from_email']}>"
    msg["To"] = ", ".join(to_emails)
    
    text_content = f"""
PARK AGILITY - OFFICE ACCESS ALERT

Date: {formatted_date}

All key bearers have indicated they will NOT be in the office on this date.

Key Bearers Status:
{chr(10).join([f"  - {kb['name']}: Not Available" for kb in absent_bearers])}

Please make alternative arrangements if you need office access on this day.

---
This is an automated message from the Park Agility Office Key Tracker.
"""
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1e2a5e; color: white; padding: 30px; border-radius: 12px 12px 0 0; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .tagline {{ color: #3dbb91; font-size: 12px; letter-spacing: 1px; margin-top: 8px; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; }}
        .date-box {{ background: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; border-left: 4px solid #dc2626; }}
        .date-box h2 {{ margin: 0; color: #dc2626; font-size: 20px; }}
        .status-list {{ background: white; padding: 20px; border-radius: 8px; }}
        .status-item {{ padding: 10px 0; border-bottom: 1px solid #eee; display: flex; align-items: center; }}
        .status-item:last-child {{ border-bottom: none; }}
        .status-icon {{ width: 24px; height: 24px; background: #dc2626; border-radius: 50%; margin-right: 12px; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
        .warning-box {{ margin-top: 20px; padding: 15px; background: #fef3e6; border-radius: 8px; color: #b45309; border: 1px solid #fcd9b6; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Park Agility Office Key Tracker</h1>
            <div class="tagline">FASTER.SMARTER.GREENER.</div>
        </div>
        <div class="content">
            <div class="date-box">
                <h2>⚠️ {formatted_date}</h2>
                <p style="margin: 10px 0 0 0; color: #666;">No key bearers available</p>
            </div>
            <p><strong>All key bearers</strong> have indicated they will NOT be in the office on this date.</p>
            <div class="status-list">
                <h3 style="margin-top: 0; color: #1e2a5e;">Key Bearers Status:</h3>
                {''.join([f'<div class="status-item"><span class="status-icon">✕</span><span>{kb["name"]} - Not Available</span></div>' for kb in absent_bearers])}
            </div>
            <div class="warning-box">
                ⚠️ Please make alternative arrangements if you need office access on this day.
            </div>
        </div>
        <div class="footer">
            This is an automated message from the Park Agility Office Key Tracker.
        </div>
    </div>
</body>
</html>
"""
    
    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        if email_config.get("use_tls", True):
            server = smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"])
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(email_config["smtp_host"], email_config["smtp_port"])
        
        server.login(email_config["smtp_user"], email_config["smtp_password"])
        server.sendmail(email_config["from_email"], to_emails, msg.as_string())
        server.quit()
        
        print(f"Alert email sent for {alert_date} to {len(to_emails)} recipients")
        return True
        
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def send_change_of_plans_email(config, alert_date, key_bearer_name):
    """Send email when someone becomes available after all-absent alert was sent."""
    
    email_config = config["email"]
    recipients = config["recipients"]
    
    date_obj = datetime.strptime(alert_date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%A, %B %d, %Y")
    
    to_emails = [r["email"] for r in recipients]
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔑 Park Agility Office Update - Change of Plans - {formatted_date}"
    msg["From"] = f"{email_config['from_name']} <{email_config['from_email']}>"
    msg["To"] = ", ".join(to_emails)
    
    text_content = f"""
PARK AGILITY - CHANGE OF PLANS

Date: {formatted_date}

Good news! {key_bearer_name} is now going to be in the office on this date.

The office will be accessible.

---
This is an automated message from the Park Agility Office Key Tracker.
"""
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1e2a5e; color: white; padding: 30px; border-radius: 12px 12px 0 0; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .tagline {{ color: #3dbb91; font-size: 12px; letter-spacing: 1px; margin-top: 8px; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; }}
        .date-box {{ background: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; border-left: 4px solid #3dbb91; }}
        .date-box h2 {{ margin: 0; color: #3dbb91; font-size: 20px; }}
        .good-news {{ background: #d4f5e9; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0; }}
        .good-news h3 {{ margin: 0 0 10px 0; color: #1a7a5a; }}
        .good-news p {{ margin: 0; color: #166534; font-size: 16px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Park Agility Office Key Tracker</h1>
            <div class="tagline">FASTER.SMARTER.GREENER.</div>
        </div>
        <div class="content">
            <div class="date-box">
                <h2>✓ {formatted_date}</h2>
                <p style="margin: 10px 0 0 0; color: #666;">Change of Plans</p>
            </div>
            <div class="good-news">
                <h3>Good News!</h3>
                <p><strong>{key_bearer_name}</strong> is now going to be in the office on this date.</p>
            </div>
            <p style="text-align: center; color: #666;">The office will be accessible. 🎉</p>
        </div>
        <div class="footer">
            This is an automated message from the Park Agility Office Key Tracker.
        </div>
    </div>
</body>
</html>
"""
    
    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        if email_config.get("use_tls", True):
            server = smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"])
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(email_config["smtp_host"], email_config["smtp_port"])
        
        server.login(email_config["smtp_user"], email_config["smtp_password"])
        server.sendmail(email_config["from_email"], to_emails, msg.as_string())
        server.quit()
        
        print(f"Change of plans email sent for {alert_date} - {key_bearer_name} now available")
        return True
        
    except Exception as e:
        print(f"Failed to send change of plans email: {e}")
        return False
