# GitHub Database Sync Workflow (PythonAnywhere ↔ Local)

Use this guide every time you want to sync `db.sqlite3` between PythonAnywhere and your local machine.

---

## 0) One-time setup (run on BOTH machines)

Run inside your repo folder:

```bash
git config merge.sqlite_union.name "SQLite union merge"
git config merge.sqlite_union.driver "python3 tools/sqlite_union_merge.py git-driver %O %A %B"
```

Confirm:

```bash
git config --get merge.sqlite_union.driver
git check-attr merge -- db.sqlite3
```

Expected merge attr output should include: `db.sqlite3: merge: sqlite_union`

---

## 1) PythonAnywhere: push server DB to GitHub

```bash
cd ~/paratara

# keep server-specific settings local only
git update-index --skip-worktree webSchedule/settings.py

# backup DB first
cp db.sqlite3 "db.sqlite3.bak.$(date +%F_%H%M%S)"

# commit DB update
git add db.sqlite3
git commit -m "Update DB from PythonAnywhere" || true

# integrate remote before pushing
git pull --no-rebase origin main

# push to GitHub
git push origin main
```

---

## 2) Local machine: pull and auto-merge DB

```bash
cd "/Users/nhoj/Desktop/Carpool and Resort Pooling 2025"

# backup local DB
cp db.sqlite3 "db.sqlite3.bak.$(date +%F_%H%M%S)"

# pull from GitHub (this is where DB auto-merge happens)
git pull --no-rebase origin main
```

---

## 3) If pull has conflicts (non-DB files)

If conflicts are in `garden/urls.py`, `requirements.txt`, or migration files, choose one side quickly.

### Keep remote versions (`origin/main`)

```bash
git checkout --theirs garden/urls.py requirements.txt home/migrations/0081_alter_allschedules_daten_alter_allschedules_monthn_and_more.py
git add garden/urls.py requirements.txt home/migrations/0081_alter_allschedules_daten_alter_allschedules_monthn_and_more.py db.sqlite3
git commit -m "Resolve conflicts using remote versions"
```

### Keep local versions

```bash
git checkout --ours garden/urls.py requirements.txt home/migrations/0081_alter_allschedules_daten_alter_allschedules_monthn_and_more.py
git add garden/urls.py requirements.txt home/migrations/0081_alter_allschedules_daten_alter_allschedules_monthn_and_more.py db.sqlite3
git commit -m "Resolve conflicts using local versions"
```

---

## 4) Protect PythonAnywhere settings file (recommended)

Run on PythonAnywhere:

```bash
cd ~/paratara
git update-index --skip-worktree webSchedule/settings.py
git ls-files -v | grep webSchedule/settings.py
```

If the line starts with `S`, it is protected.

If you need to track it again later:

```bash
git update-index --no-skip-worktree webSchedule/settings.py
```

---

## 5) Verify DB merge state

Check unresolved DB conflicts:

```bash
git ls-files -u -- db.sqlite3
```

If no output, DB is in a clean merged state.

Optional quick data checks:

```bash
sqlite3 db.sqlite3 "SELECT 'auth_user', COUNT(*) FROM auth_user;"
sqlite3 db.sqlite3 "SELECT 'django_migrations', COUNT(*) FROM django_migrations;"
```

---

## 6) Important notes

- `git push` does **not** merge anything.
- Merge happens during `git pull` / `git merge`.
- Always create DB backups before pull/push.
- SQLite auto-merge is best-effort; if schemas changed heavily, manual merge may still be needed.

---

## 7) Fast repeat commands

### PythonAnywhere

```bash
cd ~/paratara && git update-index --skip-worktree webSchedule/settings.py && cp db.sqlite3 "db.sqlite3.bak.$(date +%F_%H%M%S)" && git add db.sqlite3 && git commit -m "DB update" || true && git pull --no-rebase origin main && git push origin main
```

### Local

```bash
cd "/Users/nhoj/Desktop/Carpool and Resort Pooling 2025" && cp db.sqlite3 "db.sqlite3.bak.$(date +%F_%H%M%S)" && git pull --no-rebase origin main
```
