# Job Application CRM

A lightweight job application tracking system built with Flask and SQLite.

## Project Structure

```
job-crm/
├── app.py              # Flask application with all routes
├── database.py         # SQLite setup, schema, and query helpers
├── requirements.txt    # Python dependencies (Flask only)
├── CLAUDE.md           # This file
├── templates/
│   ├── base.html               # Shared layout, nav, head
│   ├── index.html              # Dashboard / applications list
│   ├── application_form.html   # Add & edit application form
│   └── application_detail.html # Single application view with notes, contacts, reminders
└── static/
    └── css/
        └── style.css   # Dark/modern stylesheet
```

## Database Schema

- **applications** — core job application record (company, role, status, date_applied, job_url, salary_range, resume_version, notes_general)
- **contacts** — people associated with an application (name, title, email, phone, linkedin)
- **notes** — timestamped notes attached to an application
- **reminders** — follow-up reminders with due date and completion flag
- **resume_versions** — resume version log per application (version label, file path/url, notes)

## Running the App

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

The SQLite database file (`crm.db`) is created automatically on first run.

## Application Statuses

- Wishlist
- Applied
- Phone Screen
- Interview
- Offer
- Rejected
- Withdrawn

## Key Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Dashboard with application list and stats |
| GET | /application/new | New application form |
| POST | /application/new | Save new application |
| GET | /application/<id> | Application detail view |
| GET | /application/<id>/edit | Edit application form |
| POST | /application/<id>/edit | Save edits |
| POST | /application/<id>/delete | Delete application |
| POST | /application/<id>/note | Add note |
| POST | /note/<id>/delete | Delete note |
| POST | /application/<id>/contact | Add contact |
| POST | /contact/<id>/delete | Delete contact |
| POST | /application/<id>/reminder | Add reminder |
| POST | /reminder/<id>/toggle | Toggle reminder done/undone |
| POST | /reminder/<id>/delete | Delete reminder |
| POST | /application/<id>/resume | Add resume version entry |
| POST | /resume/<id>/delete | Delete resume version entry |
