"""
database.py — SQLite setup and query helpers for Job CRM
"""

import sqlite3
from datetime import date

DB_PATH = "crm.db"


def get_db():
    """Open a database connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company         TEXT NOT NULL,
            role            TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'Applied',
            date_applied    TEXT,
            job_url         TEXT,
            salary_range    TEXT,
            resume_version  TEXT,
            notes_general   TEXT,
            created_at      TEXT NOT NULL DEFAULT (date('now')),
            updated_at      TEXT NOT NULL DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id  INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            title           TEXT,
            email           TEXT,
            phone           TEXT,
            linkedin        TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS notes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id  INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            content         TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id  INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            title           TEXT NOT NULL,
            due_date        TEXT,
            done            INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS resume_versions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id  INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            version_label   TEXT NOT NULL,
            file_path       TEXT,
            notes           TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS usage_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            action     TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    conn.commit()

    # Add new columns to applications if they don't exist yet
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(applications)").fetchall()}
    for col, defn in [
        ("fit_score",        "TEXT"),
        ("fit_summary",      "TEXT"),
        ("job_description",  "TEXT"),
    ]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE applications ADD COLUMN {col} {defn}")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

STATUSES = ["Wishlist", "Applied", "Phone Screen", "Interview", "Offer", "Rejected", "Withdrawn"]


def get_all_applications(status_filter=None, search=None):
    conn = get_db()
    query = "SELECT * FROM applications WHERE 1=1"
    params = []
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if search:
        query += " AND (company LIKE ? OR role LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY date_applied DESC, created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_application(app_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    return row


def create_application(data):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications (company, role, status, date_applied, job_url, salary_range, resume_version, notes_general, job_description)
        VALUES (:company, :role, :status, :date_applied, :job_url, :salary_range, :resume_version, :notes_general, :job_description)
    """, {
        "company": data.get("company"),
        "role": data.get("role"),
        "status": data.get("status", "Applied"),
        "date_applied": data.get("date_applied"),
        "job_url": data.get("job_url"),
        "salary_range": data.get("salary_range"),
        "resume_version": data.get("resume_version"),
        "notes_general": data.get("notes_general"),
        "job_description": data.get("job_description"),
    })
    app_id = c.lastrowid
    conn.commit()
    conn.close()
    return app_id


def update_application(app_id, data):
    conn = get_db()
    conn.execute("""
        UPDATE applications
        SET company=:company, role=:role, status=:status, date_applied=:date_applied,
            job_url=:job_url, salary_range=:salary_range, resume_version=:resume_version,
            notes_general=:notes_general, job_description=:job_description, updated_at=date('now')
        WHERE id=:id
    """, {
        "company": data.get("company"),
        "role": data.get("role"),
        "status": data.get("status", "Applied"),
        "date_applied": data.get("date_applied"),
        "job_url": data.get("job_url"),
        "salary_range": data.get("salary_range"),
        "resume_version": data.get("resume_version"),
        "notes_general": data.get("notes_general"),
        "job_description": data.get("job_description"),
        "id": app_id,
    })
    conn.commit()
    conn.close()


def get_applications_with_url_no_jd():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM applications
        WHERE job_url IS NOT NULL AND job_url != ''
        AND (job_description IS NULL OR job_description = '')
    """).fetchall()
    conn.close()
    return rows


def get_applications_without_assessment():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM applications
        WHERE (job_description IS NOT NULL AND job_description != '')
        AND (fit_score IS NULL OR fit_score = '')
    """).fetchall()
    conn.close()
    return rows


def get_applications_without_jd():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM applications
        WHERE job_description IS NULL OR job_description = ''
    """).fetchall()
    conn.close()
    return rows


def update_job_url(app_id, url):
    conn = get_db()
    conn.execute(
        "UPDATE applications SET job_url=?, updated_at=date('now') WHERE id=?",
        (url, app_id)
    )
    conn.commit()
    conn.close()


def update_job_description(app_id, text):
    conn = get_db()
    conn.execute(
        "UPDATE applications SET job_description=?, updated_at=date('now') WHERE id=?",
        (text, app_id)
    )
    conn.commit()
    conn.close()


def delete_application(app_id):
    conn = get_db()
    conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_db()
    rows = conn.execute("""
        SELECT status, COUNT(*) as count FROM applications GROUP BY status
    """).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    conn.close()
    stats = {row["status"]: row["count"] for row in rows}
    stats["Total"] = total
    return stats


def get_monthly_counts():
    conn = get_db()
    rows = conn.execute("""
        SELECT strftime('%Y-%m', date_applied) as month, COUNT(*) as count
        FROM applications
        WHERE date_applied IS NOT NULL AND date_applied >= date('now', '-6 months')
        GROUP BY month ORDER BY month
    """).fetchall()
    conn.close()
    return [{"month": r["month"], "count": r["count"]} for r in rows]


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------

def bulk_delete_applications(ids):
    if not ids:
        return
    conn = get_db()
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM applications WHERE id IN ({placeholders})", list(ids))
    conn.commit()
    conn.close()


def bulk_update_status(ids, status):
    if not ids:
        return
    conn = get_db()
    placeholders = ",".join("?" * len(ids))
    conn.execute(
        f"UPDATE applications SET status=?, updated_at=date('now') WHERE id IN ({placeholders})",
        [status] + list(ids)
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

def get_notes(app_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notes WHERE application_id = ? ORDER BY created_at DESC", (app_id,)
    ).fetchall()
    conn.close()
    return rows


def add_note(app_id, content):
    conn = get_db()
    conn.execute(
        "INSERT INTO notes (application_id, content) VALUES (?, ?)", (app_id, content)
    )
    conn.commit()
    conn.close()


def delete_note(note_id):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

def get_contacts(app_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM contacts WHERE application_id = ? ORDER BY created_at", (app_id,)
    ).fetchall()
    conn.close()
    return rows


def add_contact(app_id, data):
    conn = get_db()
    conn.execute("""
        INSERT INTO contacts (application_id, name, title, email, phone, linkedin)
        VALUES (:application_id, :name, :title, :email, :phone, :linkedin)
    """, {**data, "application_id": app_id})
    conn.commit()
    conn.close()


def delete_contact(contact_id):
    conn = get_db()
    conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

def get_reminders(app_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM reminders WHERE application_id = ? ORDER BY done ASC, due_date ASC", (app_id,)
    ).fetchall()
    conn.close()
    return rows


def get_upcoming_reminders(limit=10):
    today = date.today().isoformat()
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*, a.company, a.role
        FROM reminders r
        JOIN applications a ON r.application_id = a.id
        WHERE r.done = 0 AND (r.due_date IS NULL OR r.due_date >= ?)
        ORDER BY r.due_date ASC
        LIMIT ?
    """, (today, limit)).fetchall()
    conn.close()
    return rows


def get_overdue_reminders():
    today = date.today().isoformat()
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*, a.company, a.role
        FROM reminders r
        JOIN applications a ON r.application_id = a.id
        WHERE r.done = 0 AND r.due_date < ?
        ORDER BY r.due_date ASC
    """, (today,)).fetchall()
    conn.close()
    return rows


def add_reminder(app_id, title, due_date):
    conn = get_db()
    conn.execute(
        "INSERT INTO reminders (application_id, title, due_date) VALUES (?, ?, ?)",
        (app_id, title, due_date or None)
    )
    conn.commit()
    conn.close()


def toggle_reminder(reminder_id):
    conn = get_db()
    conn.execute(
        "UPDATE reminders SET done = CASE WHEN done=1 THEN 0 ELSE 1 END WHERE id = ?",
        (reminder_id,)
    )
    conn.commit()
    conn.close()


def delete_reminder(reminder_id):
    conn = get_db()
    conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Resume Versions
# ---------------------------------------------------------------------------

def get_resume_versions(app_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM resume_versions WHERE application_id = ? ORDER BY created_at DESC", (app_id,)
    ).fetchall()
    conn.close()
    return rows


def add_resume_version(app_id, version_label, file_path, notes):
    conn = get_db()
    conn.execute("""
        INSERT INTO resume_versions (application_id, version_label, file_path, notes)
        VALUES (?, ?, ?, ?)
    """, (app_id, version_label, file_path or None, notes or None))
    conn.commit()
    conn.close()


def delete_resume_version(version_id):
    conn = get_db()
    conn.execute("DELETE FROM resume_versions WHERE id = ?", (version_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Usage Log (AI assessments)
# ---------------------------------------------------------------------------

def get_assessment_count():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) FROM usage_log WHERE action='fit_assessment'").fetchone()
    conn.close()
    return row[0]


def log_assessment():
    conn = get_db()
    conn.execute("INSERT INTO usage_log (action) VALUES ('fit_assessment')")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Fit Assessment
# ---------------------------------------------------------------------------

def update_fit_assessment(app_id, score, summary):
    conn = get_db()
    conn.execute(
        "UPDATE applications SET fit_score=?, fit_summary=?, updated_at=date('now') WHERE id=?",
        (str(score), summary, app_id)
    )
    conn.commit()
    conn.close()
