# Todo List Backend (Django)

Simple Django REST backend for a Todo app with:
- Authentication (token-based)
- Task CRUD (with `due_date` + `due_time`)
- Premium upgrade flow
- In-app notifications
- Scheduled reminders (cron) with email + SMS
- Request logging (JSON) + rotating file logs
- API rate limiting middleware

## Tech Stack
- Django
- Django REST Framework
- MySQL
- django-crontab
- Twilio (SMS)

## Project Structure
- `api/` -> app code (models, views, serializers, cron, middleware)
- `backend/` -> Django settings and project config
- `logs/backend.log` -> JSON logs (rotating file handler)

## Quick Start
1. Create/activate virtual environment.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Configure `.env` (see example below).
4. Run migrations:
```bash
python manage.py migrate
```
5. Start server:
```bash
python manage.py runserver
```

## Environment Variables (`.env`)
```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=todo_db
DB_USER=root
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=3306

EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
```

## Authentication
Uses DRF token auth.

- Register: `POST /api/register/`
- Login: `POST /api/login/`

Send token in headers for protected APIs:
```http
Authorization: Token <your_token>
```

## Main APIs

### Tasks
- `GET /api/tasks/`
- `POST /api/tasks/`
- `GET /api/tasks/<id>/`
- `PUT /api/tasks/<id>/`
- `PATCH /api/tasks/<id>/`
- `DELETE /api/tasks/<id>/`
- `GET /api/tasks/due-tomorrow/`

Task fields:
- `title`
- `due_date` (`YYYY-MM-DD`)
- `due_time` (`HH:MM` recommended)
- `is_completed`
- `updated_at` (read-only)

### Profile
- `GET /api/profile/me/` -> current user details
- `PATCH /api/profile/update/` -> update `username`, `email`, `phone_number`
- `POST /api/profile/change-password/` -> change password with validation
- `POST /api/profile/upgrade_premium/` -> set account to premium

### Notifications
- `GET /api/notifications/`
- `POST /api/notifications/<notification_id>/read/`

### Admin
- `GET /api/admin/users/`
- `GET /api/admin/stats/`

## Reminder System (Cron)
Cron job function: `api.cron.remind_due_tasks`

Current schedule:
- Every minute (`* * * * *`)

It sends reminder through:
- Notification table (in-app)
- Email (if user email exists)
- SMS (if phone + Twilio config exist)

### Enable cron jobs
```bash
python manage.py crontab add
python manage.py crontab show
```

After cron changes:
```bash
python manage.py crontab remove
python manage.py crontab add
```

## Logging
- JSON log format
- Console + rotating file handler
- File path: `logs/backend.log`
- Rotation:
  - max file size: 10 MB
  - backups kept: 5

## Rate Limiting
Middleware-based rate limiting for `/api/` routes.

Config in `backend/settings.py`:
- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_WINDOW_SECONDS`
- `RATE_LIMIT_MAX_REQUESTS`
- `RATE_LIMIT_PATH_PREFIXES`
- `RATE_LIMIT_EXEMPT_PATHS`

## Notes
- If you added new model fields (example: `due_time`, `updated_at`), always run:
```bash
python manage.py migrate
```
- If task creation fails with "unknown column", migration is missing.
