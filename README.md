# Contact Management System

A command-line contact manager in Python 3.8+ with **no runtime dependencies** (standard library only).
Contacts are stored in a **SQLite** file, so data persists across program restarts.

## Features

| Requirement | Implementation |
|---|---|
| CRUD | `add`, `list` / `view`, `edit`, `delete` (plus an interactive menu) |
| Fields | Full name, phone, email (all mandatory) |
| Persistence | SQLite file (default `data/contacts.db`) |
| Search / filter | Case-insensitive substring match on name, phone **or** email |
| Validation | Clear error messages; interactive mode re-prompts until input is valid |
| Duplicates | Rejected on **phone** or **email** (format-insensitive), on add *and* edit |
| Extras | CSV import/export, delete confirmation, 18 automated tests |

## Quick start

```bash
git clone <your-repo-url> && cd contact-manager

python -m contacts                       # interactive menu
python -m contacts add --name "Aarav Sharma" --phone "+91 98765 43210" --email aarav@example.com
python -m contacts list
python -m contacts view 1
python -m contacts search aarav          # or part of a phone number / email
python -m contacts edit 1 --email aarav.new@example.com   # only given fields change
python -m contacts delete 1              # asks for confirmation (-y to skip)
python -m contacts import sample_data/contacts.csv
python -m contacts export backup.csv
```

Use a different database file with `--db path/to/file.db` or the `CONTACTS_DB` environment variable.

## Storage format

SQLite database, one table (`contacts/storage.py`):

```sql
CREATE TABLE contacts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name  TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    phone      TEXT NOT NULL UNIQUE,      -- normalised: optional '+', then digits only
    email      TEXT NOT NULL UNIQUE,      -- normalised: lower-case
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Why SQLite: atomic writes (no half-written file after a crash), `UNIQUE` constraints as a second line
of defence against duplicates, and no extra install. You can inspect the file with `sqlite3 data/contacts.db`.

**Normalisation** happens before saving, so equivalent input is treated as the same value:

- Name: trimmed, repeated spaces collapsed.
- Phone: spaces, dashes, dots and brackets removed → `+91 (98765) 43210` is stored as `+919876543210`.
- Email: trimmed and lower-cased → `ASHA@Example.com` is stored as `asha@example.com`.

## Validation rules

| Field | Rule |
|---|---|
| Full name | Required, 2–100 chars, must contain a letter |
| Phone | Required, 7–15 digits, optional leading `+` |
| Email | Required, must look like `name@domain.tld`, max 254 chars |
| Duplicates | Same phone or same email as another contact → rejected, naming the existing contact |

## Sample data

`sample_data/contacts.csv` (CSV format: header `full_name,phone,email`). It deliberately includes
bad rows to show error handling:

```csv
full_name,phone,email
Aarav Sharma,+91 98765 43210,aarav.sharma@example.com
Priya Natarajan,+91 90030-11223,priya.n@example.com
Meera Iyer,044 2345 6789,meera.iyer@example.com
John Carter,+1 (415) 555-0134,john.carter@example.com
Sofia Rossi,+39 06 1234 5678,sofia.rossi@example.com
Priya Natarajan,+91 90030 11223,another@example.com     <- duplicate phone (different format)
Bad Email,9876543210,not-an-email                       <- invalid email
,9876543210,noname@example.com                          <- missing name
```

Importing into an empty database adds 5 contacts and reports the 3 skipped rows with line numbers.

## Demo

`demo/demo_session.txt` is a recorded terminal session showing create, read, update, delete, search,
validation errors, duplicate handling, and persistence across separate runs.
Regenerate it with `bash demo/run_demo.sh`. For screenshots or a screencast, run that script (or the
interactive menu) in a terminal and capture it.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q          # 18 tests: CRUD, validation, duplicates, search, persistence, CSV
```

## Project layout

```
contacts/
  validation.py   input rules + normalisation
  storage.py      SQLite CRUD, search, CSV import/export
  cli.py          argparse subcommands + interactive menu
  __main__.py     enables `python -m contacts`
tests/            pytest suite
sample_data/      sample CSV
demo/             demo script + recorded session
```

## Design notes / limitations

- Duplicate policy is phone **or** email. Two people sharing a landline would need a policy change (drop the `UNIQUE` on `phone`).
- Phone numbers are not validated per country; the 7–15 digit rule follows the E.164 maximum length.
- Search is substring-based; `%` and `_` are escaped so they match literally.
