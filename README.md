# 🔑 Park Agility Office Key Tracker

A simple web app that alerts employees when no key bearers will be in the office.

## The Problem

If everyone who has office keys is absent on the same day, other employees get locked out.

## The Solution

Key bearers mark their absence dates in the app. When **all** key bearers mark the same date as absent, an automatic email alert is sent to all employees.

## How It Works

1. Key bearer selects their name
2. Picks dates they won't be in office (Today, Tomorrow, or calendar selection)
3. Clicks "Not Going to Office"
4. If all key bearers are now absent for that date → email alert sent immediately
5. Employees receive notification to make alternative arrangements

## Features

- Quick date selection (Today / Tomorrow / Calendar)
- View and cancel your scheduled absences
- Real-time status of today's key bearer availability
- Automatic email alerts (sent only once per date)
- Clean, mobile-friendly interface

## Tech Stack

- **Backend:** Python / Flask
- **Database:** Supabase (PostgreSQL)
- **Hosting:** Render.com
- **Email:** Outlook / Office 365

**Quick summary:**
1. Create Supabase project → run `supabase_setup.sql`
2. Push code to GitHub
3. Deploy on Render → add environment variables
4. Set up UptimeRobot to ping `/health` every 5 min (keeps free tier active)

## Configuration

Edit `config.json` to update:
- **key_bearers** - people who have office keys
- **recipients** - people who receive alert emails

Email credentials are stored securely as environment variables, not in code.

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