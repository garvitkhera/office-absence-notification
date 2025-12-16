# 🔑 Park Agility Office Key Tracker

Simple webapp to track key bearer availability and auto-alert employees when no one with keys will be in the office.

## Quick Start (Local)

```bash
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`

## Configuration

Edit `config.json`:

```json
{
  "email": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "support@mycompany.com",
    "smtp_password": "your-app-password",
    "from_email": "support@mycompany.com",
    "from_name": "Office Key Tracker",
    "use_tls": true
  },
  "key_bearers": [
    {"name": "Alice Johnson", "email": "alice@mycompany.com"},
    {"name": "Bob Smith", "email": "bob@mycompany.com"}
  ],
  "recipients": [
    {"name": "All Staff", "email": "all-staff@mycompany.com"}
  ]
}
```

### Gmail Setup
1. Enable 2FA on your Google account
2. Generate an App Password: Google Account → Security → App Passwords
3. Use that password in `smtp_password`

### Other Email Providers
- **Outlook**: smtp.office365.com:587
- **SendGrid**: smtp.sendgrid.net:587
- **Mailgun**: smtp.mailgun.org:587

## Free Hosting Options

### Option 1: Railway (Recommended)
1. Push code to GitHub
2. Go to [railway.app](https://railway.app)
3. New Project → Deploy from GitHub
4. Add environment variable for sensitive data (optional)
5. Done! Free tier includes 500 hours/month

### Option 2: Render
1. Push code to GitHub
2. Go to [render.com](https://render.com)
3. New → Web Service → Connect GitHub
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn app:app`

### Option 3: PythonAnywhere (Always Free)
1. Go to [pythonanywhere.com](https://pythonanywhere.com)
2. Create free account
3. Upload files via Files tab
4. Create Web App → Flask → Python 3.10
5. Set source code path

### Option 4: Fly.io
```bash
flyctl launch
flyctl deploy
```

## How It Works

1. Key bearer selects their name
2. Picks date(s): Today, Tomorrow, or calendar selection
3. Clicks "Not Going to Office"
4. System checks if ALL key bearers are now absent for that date
5. If yes → auto-sends alert email to all recipients
6. Email is only sent once per date (tracked in DB)

## Database

Uses SQLite (`absences.db`) - no setup needed. File is created automatically.

For production with multiple instances, switch to PostgreSQL:
```python
# Replace get_db() with your PostgreSQL connection
```

## API Endpoints

- `GET /` - Main UI
- `POST /api/mark-absent` - Mark dates as absent
- `POST /api/cancel-absence` - Cancel an absence
- `GET /api/status/<date>` - Get status for a date
- `GET /api/my-absences/<name>` - Get user's absences
- `GET /api/absences` - Get all future absences

## License

MIT - do whatever you want with it.
