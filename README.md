# Park Agility Office Presence Tracker

A web app to track employee office presence and alert when no key bearers are available.

## Features

- **Employee Management** - All employees tracked in database with "Has Key" status
- **Usual Weekly Pattern** - Set regular days in/out of office (auto-populates absences)
- **Quick Absence Marking** - Today, Tomorrow, or calendar picker
- **2-Week Overview** - See all employees' availability with key holder indicators
- **Smart Email Alerts**:
  - "No key bearers available" when all key holders mark absent
  - "Change of plans" when someone becomes available after alert was sent
- **Confirmation Popups** - Before any email-triggering action
- **Sydney Timezone** - Auto-handles daylight savings
- **Auto-sync** - Populates next month on 25th, cleans up old data on 5th

## Tech Stack

- **Backend:** Python / Flask
- **Database:** Supabase (PostgreSQL)
- **Hosting:** Render.com
- **Email:** Outlook / Office 365
- **Timezone:** pytz (Australia/Sydney)

## Deployment

1. **Supabase:** Create project → run `supabase_setup.sql` in SQL Editor
2. **GitHub:** Push code to repository
3. **Render:** Deploy from GitHub → add environment variables
4. **UptimeRobot:** Ping `/health` every 5 min (keeps free tier active)

## Configuration

- **Employees:** Managed in Supabase `employees` table
- **Recipients:** Edit `config.json` for email alert recipients

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

## Database Tables

- **employees** - name, email, has_key
- **absences** - employee_name, absence_date
- **usual_absences** - employee_name, monday-friday booleans
- **email_log** - alert_date, followup_sent
- **sync_log** - tracks monthly sync operations

## License

MIT
