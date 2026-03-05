"""
app.py — Flask application for Job Application CRM
Run: python app.py
"""

from flask import Flask, render_template, request, redirect, url_for, flash, abort
from datetime import date
import database as db
import csv
import io
import os

app = Flask(__name__)
app.secret_key = "job-crm-secret-key-change-in-production"

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
RESUME_PATH = os.path.join(UPLOAD_DIR, "resume.pdf")
ASSESSMENT_CAP = 1000


# ---------------------------------------------------------------------------
# Context processors
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    return {
        "statuses": db.STATUSES,
        "overdue_count": len(db.get_overdue_reminders()),
        "today": date.today().isoformat(),
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    status_filter = request.args.get("status", "")
    search = request.args.get("search", "")
    applications = db.get_all_applications(
        status_filter=status_filter or None,
        search=search or None
    )
    stats = db.get_stats()
    upcoming = db.get_upcoming_reminders(limit=5)
    overdue = db.get_overdue_reminders()
    monthly_counts = db.get_monthly_counts()
    return render_template(
        "index.html",
        applications=applications,
        stats=stats,
        upcoming=upcoming,
        overdue=overdue,
        status_filter=status_filter,
        search=search,
        monthly_counts=monthly_counts,
    )


# ---------------------------------------------------------------------------
# Application CRUD
# ---------------------------------------------------------------------------

@app.route("/application/new", methods=["GET", "POST"])
def new_application():
    if request.method == "POST":
        data = {
            "company": request.form["company"].strip(),
            "role": request.form["role"].strip(),
            "status": request.form.get("status", "Applied"),
            "date_applied": request.form.get("date_applied") or None,
            "job_url": request.form.get("job_url", "").strip() or None,
            "salary_range": request.form.get("salary_range", "").strip() or None,
            "resume_version": request.form.get("resume_version", "").strip() or None,
            "notes_general": request.form.get("notes_general", "").strip() or None,
            "job_description": request.form.get("job_description", "").strip() or None,
        }
        if not data["company"] or not data["role"]:
            flash("Company and Role are required.", "error")
            return render_template("application_form.html", form=data, action="new")
        app_id = db.create_application(data)
        flash(f"Application to {data['company']} added!", "success")
        return redirect(url_for("application_detail", app_id=app_id))
    return render_template("application_form.html", form={}, action="new")


@app.route("/application/<int:app_id>")
def application_detail(app_id):
    application = db.get_application(app_id)
    if not application:
        abort(404)
    notes = db.get_notes(app_id)
    contacts = db.get_contacts(app_id)
    reminders = db.get_reminders(app_id)
    resume_versions = db.get_resume_versions(app_id)
    assessment_count = db.get_assessment_count()
    resume_exists = os.path.exists(RESUME_PATH)
    return render_template(
        "application_detail.html",
        app=application,
        notes=notes,
        contacts=contacts,
        reminders=reminders,
        resume_versions=resume_versions,
        assessment_count=assessment_count,
        assessment_cap=ASSESSMENT_CAP,
        resume_exists=resume_exists,
    )


@app.route("/application/<int:app_id>/edit", methods=["GET", "POST"])
def edit_application(app_id):
    application = db.get_application(app_id)
    if not application:
        abort(404)
    if request.method == "POST":
        data = {
            "company": request.form["company"].strip(),
            "role": request.form["role"].strip(),
            "status": request.form.get("status", "Applied"),
            "date_applied": request.form.get("date_applied") or None,
            "job_url": request.form.get("job_url", "").strip() or None,
            "salary_range": request.form.get("salary_range", "").strip() or None,
            "resume_version": request.form.get("resume_version", "").strip() or None,
            "notes_general": request.form.get("notes_general", "").strip() or None,
            "job_description": request.form.get("job_description", "").strip() or None,
        }
        if not data["company"] or not data["role"]:
            flash("Company and Role are required.", "error")
            return render_template("application_form.html", form=data, action="edit", app_id=app_id)
        db.update_application(app_id, data)
        flash("Application updated.", "success")
        return redirect(url_for("application_detail", app_id=app_id))
    return render_template("application_form.html", form=dict(application), action="edit", app_id=app_id)


@app.route("/application/<int:app_id>/delete", methods=["POST"])
def delete_application(app_id):
    application = db.get_application(app_id)
    if not application:
        abort(404)
    db.delete_application(app_id)
    flash(f"Application to {application['company']} deleted.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Bulk Operations
# ---------------------------------------------------------------------------

@app.route("/bulk-delete", methods=["POST"])
def bulk_delete():
    ids = request.form.getlist("ids")
    if not ids:
        flash("No applications selected.", "error")
        return redirect(url_for("index"))
    db.bulk_delete_applications([int(i) for i in ids])
    flash(f"Deleted {len(ids)} application(s).", "info")
    return redirect(url_for("index"))


@app.route("/bulk-status", methods=["POST"])
def bulk_status():
    ids = request.form.getlist("ids")
    status = request.form.get("status")
    if not ids:
        flash("No applications selected.", "error")
        return redirect(url_for("index"))
    if not status or status not in db.STATUSES:
        flash("Invalid status selected.", "error")
        return redirect(url_for("index"))
    db.bulk_update_status([int(i) for i in ids], status)
    flash(f"Updated status to '{status}' for {len(ids)} application(s).", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

@app.route("/application/<int:app_id>/note", methods=["POST"])
def add_note(app_id):
    content = request.form.get("content", "").strip()
    if content:
        db.add_note(app_id, content)
        flash("Note added.", "success")
    else:
        flash("Note cannot be empty.", "error")
    return redirect(url_for("application_detail", app_id=app_id) + "#notes")


@app.route("/note/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id):
    app_id = request.form.get("app_id")
    db.delete_note(note_id)
    flash("Note deleted.", "info")
    return redirect(url_for("application_detail", app_id=app_id) + "#notes")


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

@app.route("/application/<int:app_id>/contact", methods=["POST"])
def add_contact(app_id):
    name = request.form.get("name", "").strip()
    if not name:
        flash("Contact name is required.", "error")
        return redirect(url_for("application_detail", app_id=app_id) + "#contacts")
    data = {
        "name": name,
        "title": request.form.get("title", "").strip() or None,
        "email": request.form.get("email", "").strip() or None,
        "phone": request.form.get("phone", "").strip() or None,
        "linkedin": request.form.get("linkedin", "").strip() or None,
    }
    db.add_contact(app_id, data)
    flash(f"Contact {name} added.", "success")
    return redirect(url_for("application_detail", app_id=app_id) + "#contacts")


@app.route("/contact/<int:contact_id>/delete", methods=["POST"])
def delete_contact(contact_id):
    app_id = request.form.get("app_id")
    db.delete_contact(contact_id)
    flash("Contact deleted.", "info")
    return redirect(url_for("application_detail", app_id=app_id) + "#contacts")


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

@app.route("/application/<int:app_id>/reminder", methods=["POST"])
def add_reminder(app_id):
    title = request.form.get("title", "").strip()
    due_date = request.form.get("due_date", "").strip() or None
    if not title:
        flash("Reminder title is required.", "error")
        return redirect(url_for("application_detail", app_id=app_id) + "#reminders")
    db.add_reminder(app_id, title, due_date)
    flash("Reminder added.", "success")
    return redirect(url_for("application_detail", app_id=app_id) + "#reminders")


@app.route("/reminder/<int:reminder_id>/toggle", methods=["POST"])
def toggle_reminder(reminder_id):
    app_id = request.form.get("app_id")
    db.toggle_reminder(reminder_id)
    return redirect(url_for("application_detail", app_id=app_id) + "#reminders")


@app.route("/reminder/<int:reminder_id>/delete", methods=["POST"])
def delete_reminder(reminder_id):
    app_id = request.form.get("app_id")
    db.delete_reminder(reminder_id)
    flash("Reminder deleted.", "info")
    return redirect(url_for("application_detail", app_id=app_id) + "#reminders")


# ---------------------------------------------------------------------------
# Resume Versions
# ---------------------------------------------------------------------------

@app.route("/application/<int:app_id>/resume", methods=["POST"])
def add_resume_version(app_id):
    version_label = request.form.get("version_label", "").strip()
    if not version_label:
        flash("Version label is required.", "error")
        return redirect(url_for("application_detail", app_id=app_id) + "#resume")
    file_path = request.form.get("file_path", "").strip() or None
    notes = request.form.get("notes", "").strip() or None
    db.add_resume_version(app_id, version_label, file_path, notes)
    flash("Resume version added.", "success")
    return redirect(url_for("application_detail", app_id=app_id) + "#resume")


@app.route("/resume/<int:version_id>/delete", methods=["POST"])
def delete_resume_version(version_id):
    app_id = request.form.get("app_id")
    db.delete_resume_version(version_id)
    flash("Resume version deleted.", "info")
    return redirect(url_for("application_detail", app_id=app_id) + "#resume")


# ---------------------------------------------------------------------------
# Settings (resume upload + usage)
# ---------------------------------------------------------------------------

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        f = request.files.get("resume_pdf")
        if not f or not f.filename.endswith(".pdf"):
            flash("Please upload a valid PDF file.", "error")
            return redirect(url_for("settings"))
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        f.save(RESUME_PATH)
        flash("Resume uploaded successfully.", "success")
        return redirect(url_for("settings"))

    assessment_count = db.get_assessment_count()
    resume_exists = os.path.exists(RESUME_PATH)
    return render_template(
        "settings.html",
        assessment_count=assessment_count,
        assessment_cap=ASSESSMENT_CAP,
        resume_exists=resume_exists,
    )


# ---------------------------------------------------------------------------
# Fetch Job Description
# ---------------------------------------------------------------------------

def search_job_url(company, role):
    """Use Serper.dev to search Google for a job posting URL."""
    import requests

    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return None

    query = f'{company} {role} job posting site:greenhouse.io OR site:lever.co OR site:ashbyhq.com OR site:indeed.com'
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": 5},
            timeout=10,
        )
        data = resp.json()
        for result in data.get("organic", []):
            url = result.get("link", "")
            if url:
                return url
    except Exception:
        pass
    return None


def scrape_job_description(url):
    """Use Playwright to scrape a job description from a URL."""
    from playwright.sync_api import sync_playwright

    # Site-specific selectors (tried in order)
    SELECTORS = [
        # Ashby
        ".ashby-job-posting-brief-description",
        "[data-testid='job-description']",
        # Greenhouse
        "#content .job-post",
        "#app_body",
        # Lever
        ".posting-description",
        ".posting-page",
        # Indeed
        "#jobDescriptionText",
        ".jobsearch-JobComponent-description",
        # Generic
        "main article",
        "article",
        "[class*='job-description']",
        "[class*='jobDescription']",
        "[class*='description']",
        "main",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)  # let JS render

            text = None
            for selector in SELECTORS:
                try:
                    el = page.query_selector(selector)
                    if el:
                        t = el.inner_text().strip()
                        if len(t) > 200:  # ignore tiny matches
                            text = t
                            break
                except Exception:
                    continue

            # Fallback: grab body text, truncated
            if not text:
                text = page.inner_text("body").strip()
                text = "\n".join(
                    line for line in text.splitlines()
                    if len(line.strip()) > 30
                )[:8000]

        finally:
            browser.close()

    return text[:8000] if text else None


@app.route("/fetch-all-jd", methods=["POST"])
def fetch_all_job_descriptions():
    import time
    apps = db.get_applications_without_jd()
    success, failed = 0, 0
    for a in apps:
        try:
            url = a["job_url"]
            # If no URL, search for one
            if not url:
                url = search_job_url(a["company"], a["role"])
                if url:
                    db.update_job_url(a["id"], url)
            if url:
                text = scrape_job_description(url)
                if text:
                    db.update_job_description(a["id"], text)
                    success += 1
                else:
                    failed += 1
            else:
                failed += 1
            time.sleep(1)  # be polite to DuckDuckGo
        except Exception:
            failed += 1
    flash(f"Fetched {success} job description(s). {failed} could not be found.", "success" if success else "error")
    return redirect(url_for("index"))


@app.route("/application/<int:app_id>/fetch-jd", methods=["POST"])
def fetch_job_description(app_id):
    application = db.get_application(app_id)
    if not application:
        abort(404)
    url = application["job_url"]
    try:
        if not url:
            url = search_job_url(application["company"], application["role"])
            if url:
                db.update_job_url(app_id, url)
            else:
                flash("Could not find a job posting URL for this application.", "error")
                return redirect(url_for("application_detail", app_id=app_id))
        text = scrape_job_description(url)
        if text:
            db.update_job_description(app_id, text)
            flash("Job description fetched successfully!", "success")
        else:
            flash("Could not extract job description from that page (site may block scraping).", "error")
    except Exception as e:
        flash(f"Fetch failed: {e}", "error")
    return redirect(url_for("application_detail", app_id=app_id))


# ---------------------------------------------------------------------------
# AI Fit Assessment
# ---------------------------------------------------------------------------

def run_assessment(resume_text, job_description):
    """Call Claude API and return (score, summary) or raise on failure."""
    import anthropic, json

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    prompt = f"""You are a career coach analyzing how well a candidate's resume matches a job description.

Resume:
{resume_text[:6000]}

Job Description:
{job_description[:4000]}

Return ONLY a valid JSON object (no extra text, no markdown) with these exact keys:
{{
  "score": <integer 1-10>,
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "gaps": ["<gap 1>", "<gap 2>", ...],
  "tips": ["<tip 1>", "<tip 2>", ...]
}}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw)
    score = int(result.get("score", 0))
    parts = []
    if result.get("strengths"):
        parts.append("Strengths:\n" + "\n".join(f"- {s}" for s in result["strengths"]))
    if result.get("gaps"):
        parts.append("Gaps:\n" + "\n".join(f"- {g}" for g in result["gaps"]))
    if result.get("tips"):
        parts.append("Tips:\n" + "\n".join(f"- {t}" for t in result["tips"]))
    return score, "\n\n".join(parts)


@app.route("/bulk-assess", methods=["POST"])
def bulk_assess():
    if not os.path.exists(RESUME_PATH):
        flash("No resume uploaded. Please upload your resume in Settings first.", "error")
        return redirect(url_for("index"))
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        flash("ANTHROPIC_API_KEY not set.", "error")
        return redirect(url_for("index"))

    import fitz
    doc = fitz.open(RESUME_PATH)
    resume_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    apps = db.get_applications_without_assessment()
    remaining = ASSESSMENT_CAP - db.get_assessment_count()
    apps = apps[:remaining]  # respect cap

    success, failed = 0, 0
    for a in apps:
        try:
            score, summary = run_assessment(resume_text, a["job_description"])
            db.update_fit_assessment(a["id"], score, summary)
            db.log_assessment()
            success += 1
        except Exception:
            failed += 1

    flash(f"Assessed {success} application(s). {failed} failed. {remaining - success} cap remaining.", "success" if success else "error")
    return redirect(url_for("index"))


@app.route("/application/<int:app_id>/assess", methods=["POST"])
def assess_fit(app_id):
    application = db.get_application(app_id)
    if not application:
        abort(404)

    # Check cap
    if db.get_assessment_count() >= ASSESSMENT_CAP:
        flash("Assessment cap of 1000 reached. Cannot run more assessments.", "error")
        return redirect(url_for("application_detail", app_id=app_id))

    # Check resume
    if not os.path.exists(RESUME_PATH):
        flash("No resume uploaded. Please upload your resume in Settings first.", "error")
        return redirect(url_for("application_detail", app_id=app_id))

    # Check job description
    job_description = application["job_description"]
    if not job_description or not job_description.strip():
        flash("No job description found. Please add a job description to this application first.", "error")
        return redirect(url_for("application_detail", app_id=app_id))

    # Extract resume text
    try:
        import fitz
        doc = fitz.open(RESUME_PATH)
        resume_text = "\n".join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        flash(f"Could not read resume PDF: {e}", "error")
        return redirect(url_for("application_detail", app_id=app_id))

    # Call Claude API
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        flash("ANTHROPIC_API_KEY environment variable not set.", "error")
        return redirect(url_for("application_detail", app_id=app_id))

    try:
        score, summary = run_assessment(resume_text, job_description)
    except Exception as e:
        flash(f"AI assessment failed: {e}", "error")
        return redirect(url_for("application_detail", app_id=app_id))

    db.update_fit_assessment(app_id, score, summary)
    db.log_assessment()
    flash(f"Fit assessment complete! Score: {score}/10", "success")
    return redirect(url_for("application_detail", app_id=app_id))


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------

# Map common values in the Outcome column to CRM statuses
OUTCOME_STATUS_MAP = {
    "offer":        "Offer",
    "rejected":     "Rejected",
    "reject":       "Rejected",
    "interview":    "Interview",
    "phone screen": "Phone Screen",
    "phone":        "Phone Screen",
    "applied":      "Applied",
    "wishlist":     "Wishlist",
    "withdrawn":    "Withdrawn",
    "withdraw":     "Withdrawn",
}

def map_status(outcome):
    if not outcome:
        return "Applied"
    return OUTCOME_STATUS_MAP.get(outcome.strip().lower(), "Applied")


@app.route("/import", methods=["GET", "POST"])
def import_csv():
    if request.method == "POST":
        f = request.files.get("csv_file")
        if not f or not f.filename.endswith(".csv"):
            flash("Please upload a valid .csv file.", "error")
            return redirect(url_for("import_csv"))

        stream = io.StringIO(f.stream.read().decode("utf-8-sig"))
        reader = csv.DictReader(stream)

        imported = 0
        skipped = 0
        for row in reader:
            company = row.get("Company", "").strip()
            role = row.get("Title", "").strip()
            if not company or not role:
                skipped += 1
                continue
            data = {
                "company":        company,
                "role":           role,
                "status":         map_status(row.get("Outcome", "")),
                "date_applied":   row.get("Date", "").strip() or None,
                "salary_range":   row.get("Salary", "").strip() or None,
                "notes_general":  row.get("Fit", "").strip() or None,
                "job_url":        None,
                "resume_version": None,
                "job_description": None,
            }
            db.create_application(data)
            imported += 1

        flash(f"Imported {imported} application(s). {skipped} row(s) skipped (missing Company or Title).", "success")
        return redirect(url_for("index"))

    return render_template("import_csv.html")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    db.init_db()
    print("Job CRM running at http://127.0.0.1:5000")
    app.run(debug=True)
