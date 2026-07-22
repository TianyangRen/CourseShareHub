# CourseShare Hub

A distributed course-resource sharing platform built with Django for
**COMP-8347 – Internet Applications and Distributed Systems** (Summer 2026).

Guests browse and search public resources; registered students upload, manage,
comment on, and favourite materials; admins manage everything.

- 📋 Full design & grading blueprint: [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md)
- 👥 Team: Honghao Zhang · Tianyang Ren · Lei Jiang · Kun Lan · Zhihan Zhang

## Tech stack
Python 3.14 · Django 6.0 · SQLite (JSON fixtures) · Bootstrap 5

## Local setup

```bash
# 1. Clone, then create & activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows (PowerShell/CMD)
# source venv/bin/activate       # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. (later) load sample data from JSON fixtures
# python manage.py loaddata categories courses resources

# 5. Create an admin account
python manage.py createsuperuser

# 6. Run
python manage.py runserver
```

Then open http://127.0.0.1:8000/ (admin at `/admin/`).

> **Forgot-password** uses the console email backend — the reset link is printed
> in the terminal running `runserver` (no external email service needed).

## Project layout
```
coursesharehub/   project settings + root URLs
hub/              main app: models.py · views.py · forms.py · urls.py + templates
templates/        base.html shell + registration/ (auth templates)
static/           css/js/img (theme.css)
media/            user uploads (gitignored)
docs/             PROJECT_PLAN.md
```

## Team workflow
- Work on a personal branch: `feat/<name>-<module>`; open a PR into `main`.
- Commit little and often with **descriptive** messages
  (e.g. `Add UserHistory session tracking`), spread across weeks.
- **Add `comp8347proj` as a repository collaborator** (course requirement).

## Academic integrity
Per the course outline, using AI tools or external source code results in a
grade of **0**. `PROJECT_PLAN.md` is a design blueprint only — every member must
write and understand their own code. The individual viva/Q&A is the highest-
weighted grading component.
