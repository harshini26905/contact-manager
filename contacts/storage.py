"""SQLite persistence layer. Data survives restarts because it lives in a .db file."""
import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .validation import ValidationError, validate_email, validate_name, validate_phone


class DuplicateError(Exception):
    def __init__(self, field: str, existing: "Contact"):
        self.field, self.existing = field, existing
        super().__init__(f"Duplicate {field}: already used by contact #{existing.id} ({existing.full_name}).")


class NotFoundError(Exception):
    pass


@dataclass
class Contact:
    id: int
    full_name: str
    phone: str
    email: str
    created_at: str = ""
    updated_at: str = ""


SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name  TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    phone      TEXT NOT NULL UNIQUE,
    email      TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(full_name COLLATE NOCASE);
"""


class ContactStore:
    def __init__(self, path: str = "data/contacts.db"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self):
        self.conn.close()

    # ---------- helpers ----------
    @staticmethod
    def _row(r) -> Contact:
        return Contact(**{k: r[k] for k in r.keys()})

    def _find_dup(self, phone: str, email: str, exclude_id: Optional[int] = None):
        for field, val in (("phone", phone), ("email", email)):
            r = self.conn.execute(
                f"SELECT * FROM contacts WHERE {field} = ? AND id != ?", (val, exclude_id or -1)
            ).fetchone()
            if r:
                raise DuplicateError(field, self._row(r))

    # ---------- CRUD ----------
    def add(self, full_name: str, phone: str, email: str) -> Contact:
        name, phone, email = validate_name(full_name), validate_phone(phone), validate_email(email)
        self._find_dup(phone, email)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO contacts (full_name, phone, email) VALUES (?,?,?)", (name, phone, email)
            )
        return self.get(cur.lastrowid)

    def get(self, contact_id: int) -> Contact:
        r = self.conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
        if not r:
            raise NotFoundError(f"No contact with id {contact_id}.")
        return self._row(r)

    def list(self, query: Optional[str] = None) -> List[Contact]:
        """List all contacts, or filter by case-insensitive substring of name, phone or email."""
        if not query or not query.strip():
            rows = self.conn.execute("SELECT * FROM contacts ORDER BY full_name COLLATE NOCASE").fetchall()
        else:
            q = query.strip()
            esc = lambda s: s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            like = f"%{esc(q.lower())}%"
            digits = "".join(c for c in q if c.isdigit() or c == "+")
            phone_like = f"%{esc(digits)}%" if digits else like
            rows = self.conn.execute(
                """SELECT * FROM contacts
                   WHERE lower(full_name) LIKE ? ESCAPE '\\'
                      OR lower(email)     LIKE ? ESCAPE '\\'
                      OR phone            LIKE ? ESCAPE '\\'
                   ORDER BY full_name COLLATE NOCASE""",
                (like, like, phone_like),
            ).fetchall()
        return [self._row(r) for r in rows]

    def update(self, contact_id: int, full_name: Optional[str] = None,
               phone: Optional[str] = None, email: Optional[str] = None) -> Contact:
        cur = self.get(contact_id)
        name = validate_name(full_name) if full_name is not None else cur.full_name
        ph = validate_phone(phone) if phone is not None else cur.phone
        em = validate_email(email) if email is not None else cur.email
        self._find_dup(ph, em, exclude_id=contact_id)
        with self.conn:
            self.conn.execute(
                "UPDATE contacts SET full_name=?, phone=?, email=?, updated_at=datetime('now') WHERE id=?",
                (name, ph, em, contact_id),
            )
        return self.get(contact_id)

    def delete(self, contact_id: int) -> Contact:
        c = self.get(contact_id)
        with self.conn:
            self.conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        return c

    # ---------- CSV import/export ----------
    def import_csv(self, path: str):
        """Returns (imported_count, [(line_no, reason), ...]) - bad rows are skipped, not fatal."""
        ok, errors = 0, []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                try:
                    self.add(row.get("full_name", ""), row.get("phone", ""), row.get("email", ""))
                    ok += 1
                except (ValidationError, DuplicateError) as e:
                    errors.append((i, str(e)))
        return ok, errors

    def export_csv(self, path: str) -> int:
        contacts = self.list()
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["full_name", "phone", "email"])
            for c in contacts:
                w.writerow([c.full_name, c.phone, c.email])
        return len(contacts)
