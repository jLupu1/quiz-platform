# Quiz Platform

A Django-based quiz platform designed to create, deliver, and manage quizzes with support for **automated marking**.

This project was developed as part of a dissertation project (COM3610) and includes a grading workflow that can automatically mark objective questions (e.g. MCQ) and optionally auto-mark free-text responses using an AI grading engine.

## Tech Stack

- **Backend:** Python / **Django**
- **Database:** **PostgreSQL** (configured via environment variables)
- **Frontend:** Django templates (HTML) + static assets
- **AJAX/UX:** `django-htmx`

## Project Structure (high level)

- `com3610/` – Django project (settings/urls/wsgi)
- `users/` – authentication, user profiles, admin user management
- `courses/` – course management and enrollments
- `questions/` – question types and question bank
- `quizzes/` – quizzes, attempts, submissions
- `templates/`, `static/` – UI templates and static assets
- `services.py` – submission processing & automated grading orchestration

## Prerequisites

- **Python 3.x**
- **PostgreSQL**
- (Recommended) `virtualenv` / `venv`

> Note: The repository does not currently include a `requirements.txt` / `pyproject.toml`. You will need to install dependencies manually (see below) or add a requirements file.

## Environment Variables

The Django settings (`com3610/settings.py`) load environment variables (via `python-dotenv`) and expect the following values:

- `SECRET_KEY` – Django secret key
- `DB_NAME` – PostgreSQL database name
- `DB_USER` – PostgreSQL user
- `DB_PASSWORD` – PostgreSQL password
- `DB_HOST` – PostgreSQL host (e.g. `localhost`)
- `DB_PORT` – PostgreSQL port (e.g. `5432`)

Create a `.env` file in the repository root:

```dotenv
SECRET_KEY=replace-me
DB_NAME=quiz_platform
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/jLupu1/quiz-platform.git
cd quiz-platform
```

2. **Create and activate a virtual environment**

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\\Scripts\\Activate.ps1
```

3. **Install dependencies**

Because there is no pinned dependency file in the repo, install the minimum set required to run the application:

```bash
pip install \
  Django \
  psycopg2-binary \
  python-dotenv \
  django-htmx
```

If your project uses additional packages, install them as needed.

4. **Run database migrations**

```bash
python manage.py migrate
```

5. **Create an admin user (optional, recommended)**

```bash
python manage.py createsuperuser
```

## Running the App

Start the Django development server:

```bash
python manage.py runserver
```

Then open:

- http://127.0.0.1:8000/

## Automated Marking

Automated marking is orchestrated from `services.py` via `process_quiz_submission(...)`:

- MCQ / Either-Or questions are auto-graded directly.
- Short answer and essay questions can be auto-marked when configured (see question options) and will use the grading engine.

Depending on your grading engine implementation, you may need to provide additional API keys/environment variables for any external AI provider.

## Development Notes

- The project uses a custom user model: `AUTH_USER_MODEL = 'users.User'`.
- Settings default `DEBUG = False`; for local development you may want to enable debug mode in `com3610/settings.py`.

## License

No license file is currently included in this repository. Add a `LICENSE` file if you plan to distribute this project.
