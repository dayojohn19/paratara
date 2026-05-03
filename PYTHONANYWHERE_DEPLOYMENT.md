# PythonAnywhere Deployment Guide

This project is a Django app with settings in `webSchedule.settings`. The steps below match the current repo layout and the deployment changes already prepared in the codebase.

## 1) Create the PythonAnywhere app

In PythonAnywhere:

1. Open the **Web** tab.
2. Click **Add a new web app**.
3. Choose **Manual configuration**.
4. Pick the same Python version you plan to use for the virtualenv.

## 2) Clone the project on PythonAnywhere

Open a **Bash console** and run:

```bash
cd ~
git clone <your-repo-url> Carpool-and-Resort-Pooling-2025
cd ~/Carpool-and-Resort-Pooling-2025
```

If the repo is already there:

```bash
cd ~/Carpool-and-Resort-Pooling-2025
git pull origin main
```

(Your PythonAnywhere home: `/home/digitallife11/`)

## 3) Create a virtualenv and install dependencies

Example using Python 3.10:

```bash
mkvirtualenv --python=/usr/bin/python3.10 carpool-env
workon carpool-env
cd ~/Carpool-and-Resort-Pooling-2025
pip install --upgrade pip
pip install -r requirements.txt
```

If `mysqlclient` fails to build on PythonAnywhere, install the system-recommended wheel/build deps from PythonAnywhere docs first, then rerun `pip install -r requirements.txt`.

## 4) Create the environment file

Create `~/Carpool-and-Resort-Pooling-2025/.env` using `.env.example` as the base.

Minimum values:

```env
DEBUG=False
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_HOSTS=localhost,127.0.0.1,digitallife11.pythonanywhere.com
PYTHONANYWHERE_DOMAIN=digitallife11.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://digitallife11.pythonanywhere.com
OPENAI_API_KEY=
```

If you want to keep using SQLite on PythonAnywhere, you do not need `DATABASE_URL`. The app now defaults to `db.sqlite3` in the project root.

If you want an external database instead, set `DATABASE_URL`.

Examples:

```env
DATABASE_URL=sqlite:////home/yourusername/Carpool-and-Resort-Pooling-2025/db.sqlite3
```

```env
DATABASE_URL=postgres://user:password@host:5432/dbname
```

## 5) Point the web app to the virtualenv

In the **Web** tab:

1. Set **Source code** to `/home/yourusername/Carpool-and-Resort-Pooling-2025`
2. Set **Working directory** to `/home/yourusername/Carpool-and-Resort-Pooling-2025`
3. Set **Virtualenv** to:

```
/home/digitallife11/.virtualenvs/carpool-env
```

(Or verify with: `workon carpool-env && python -c "import sys; print(sys.prefix)"`)

## 6) Configure the WSGI file

This repo now includes a template file named `pythonanywhere_wsgi.py`.

In PythonAnywhere:

1. Open the web app's **WSGI configuration file**.
2. Replace its contents with the contents of `pythonanywhere_wsgi.py` (it already has your path).

The line is already set to:

```python
PROJECT_HOME = Path("/home/digitallife11/Carpool-and-Resort-Pooling-2025")
```

The WSGI template loads `.env`, adds the repo to `sys.path`, and points Django at `webSchedule.settings`.

## 7) Static and media mappings

In the **Web** tab, add these mappings:

Static files:

- URL: `/static/`
- Directory: `/home/digitallife11/Carpool-and-Resort-Pooling-2025/staticfiles`

Media files:

- URL: `/media/`
- Directory: `/home/digitallife11/Carpool-and-Resort-Pooling-2025/media`

## 8) Run migrations and collect static

In Bash:

```bash
workon carpool-env
cd /home/digitallife11/Carpool-and-Resort-Pooling-2025
python manage.py migrate
python manage.py collectstatic --noinput
```

## 9) Load or replace the SQLite database

If you want PythonAnywhere to use your local `db.sqlite3`, upload it to:

```bash
/home/digitallife11/Carpool-and-Resort-Pooling-2025/db.sqlite3
```

Recommended sequence:

```bash
cd /home/digitallife11/Carpool-and-Resort-Pooling-2025
cp db.sqlite3 db.sqlite3.backup.$(date +%F_%H%M%S)
```

Then upload the local file via the **Files** tab or `scp` (from your local machine):

```bash
scp /path/to/local/db.sqlite3 digitallife11@ssh.pythonanywhere.com:/home/digitallife11/Carpool-and-Resort-Pooling-2025/db.sqlite3
```

If both local and server databases contain different new data, do not overwrite blindly. Use the merge workflow in `tools/sqlite_union_merge.py` instead.

## 10) Reload and verify

In PythonAnywhere:

1. Click **Reload** on the web app.
2. Open `https://digitallife11.pythonanywhere.com/`
3. Test login, admin, media uploads, and the PayPal webhook route if applicable.

## 11) Update workflow after first deploy

For later updates:

```bash
workon carpool-env
cd /home/digitallife11/Carpool-and-Resort-Pooling-2025
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then click **Reload** in the **Web** tab.

## 12) Notes specific to this repo

- The app now reads `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `PYTHONANYWHERE_DOMAIN`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, and `SQLITE_DB_NAME` from environment variables.
- If `OPENAI_API_KEY` is missing, Django will still boot; the value is now optional at import time.
- Static files are already configured through WhiteNoise, but PythonAnywhere static mappings are still the cleaner setup.
