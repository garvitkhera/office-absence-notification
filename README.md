# 🔑 Park Agility Office Key Tracker

A web app that alerts employees when no key bearers will be in the office.

## The Problem

If everyone who has office keys is absent on the same day, other employees get locked out.

## The Solution

Key bearers mark their absence dates in the app. When **all** key bearers mark the same date as absent, an automatic email alert is sent to all employees.

## Features

- **Usual Weekly Pattern** - Set your regular days in/out of office (auto-populates absences)
- **Quick date selection** - Today, Tomorrow, or calendar picker
- **2-Week Overview** - See all key bearers' availability for current and next week
- **Smart Email Alerts**:
  - "No key bearers available" when all mark absent
  - "Change of plans" when someone becomes available after an alert was sent
- **Confirmation Popups** - Before any email is triggered
- **Auto-sync** - Populates next month's absences on the 25th, cleans up old data on the 5th

## Tech Stack

- **Backend:** Python / Flask
- **Database:** Supabase (PostgreSQL)
- **Hosting:** Render.com
- **Email:** Outlook / Office 365

## Deployment

1. **Supabase:** Create project → run `supabase_setup.sql` in SQL Editor
2. **GitHub:** Push code to repository
3. **Render:** Deploy from GitHub → add environment variables
4. **UptimeRobot:** Ping `/health` every 5 min (keeps free tier active)

## Configuration

Edit `config.json` to update:
- **key_bearers** - People who have office keys
- **recipients** - People who receive alert emails

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/public key |
| `SMTP_HOST` | `smtp.office365.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | Outlook email address |
| `SMTP_PASSWORD` | Outlook app password |
| `FROM_EMAIL` | Sender email address |
| `FROM_NAME` | Sender display name |

## License

MIT
