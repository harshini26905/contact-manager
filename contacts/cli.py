"""Command-line interface: subcommands for scripting + an interactive menu."""
import argparse
import os
import sys

from .storage import ContactStore, DuplicateError, NotFoundError
from .validation import ValidationError, validate_email, validate_name, validate_phone

DEFAULT_DB = os.environ.get("CONTACTS_DB", "data/contacts.db")


def print_table(contacts):
    if not contacts:
        print("(no contacts found)")
        return
    w = max(9, *(len(c.full_name) for c in contacts))
    e = max(5, *(len(c.email) for c in contacts))
    print(f"{'ID':>3}  {'Full name':<{w}}  {'Phone':<16}  {'Email':<{e}}")
    print(f"{'-'*3}  {'-'*w}  {'-'*16}  {'-'*e}")
    for c in contacts:
        print(f"{c.id:>3}  {c.full_name:<{w}}  {c.phone:<16}  {c.email:<{e}}")
    print(f"\n{len(contacts)} contact(s)")


def print_detail(c):
    print(f"ID:        {c.id}\nName:      {c.full_name}\nPhone:     {c.phone}\n"
          f"Email:     {c.email}\nCreated:   {c.created_at}\nUpdated:   {c.updated_at}")


def prompt(label, validator, current=None):
    """Re-prompt until the value is valid. Blank keeps the current value when editing."""
    while True:
        hint = f" [{current}]" if current else ""
        raw = input(f"{label}{hint}: ")
        if current and not raw.strip():
            return current
        try:
            return validator(raw)
        except ValidationError as err:
            print(f"  ! {err}")


def run_command(store, args) -> int:
    try:
        if args.cmd == "add":
            c = store.add(args.name, args.phone, args.email)
            print(f"Added contact #{c.id}."); print_detail(c)
        elif args.cmd == "list":
            print_table(store.list())
        elif args.cmd == "view":
            print_detail(store.get(args.id))
        elif args.cmd == "search":
            print_table(store.list(args.query))
        elif args.cmd == "edit":
            c = store.update(args.id, args.name, args.phone, args.email)
            print(f"Updated contact #{c.id}."); print_detail(c)
        elif args.cmd == "delete":
            c = store.get(args.id)
            if not args.yes and input(f"Delete {c.full_name} ({c.email})? [y/N] ").lower() != "y":
                print("Cancelled."); return 0
            store.delete(args.id); print(f"Deleted contact #{args.id}.")
        elif args.cmd == "import":
            ok, errs = store.import_csv(args.file)
            print(f"Imported {ok} contact(s); skipped {len(errs)}.")
            for line, why in errs:
                print(f"  line {line}: {why}")
        elif args.cmd == "export":
            print(f"Exported {store.export_csv(args.file)} contact(s) to {args.file}.")
        return 0
    except (ValidationError, DuplicateError, NotFoundError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1


def menu(store):
    options = "\n=== Contact Manager ===\n1) Add  2) List  3) View  4) Edit  5) Delete  6) Search  0) Quit\n> "
    while True:
        choice = input(options).strip()
        try:
            if choice == "1":
                name = prompt("Full name", validate_name)
                phone = prompt("Phone", validate_phone)
                email = prompt("Email", validate_email)
                c = store.add(name, phone, email); print(f"Added contact #{c.id}.")
            elif choice == "2":
                print_table(store.list())
            elif choice == "3":
                print_detail(store.get(int(input("ID: "))))
            elif choice == "4":
                c = store.get(int(input("ID to edit: ")))
                print("(press Enter to keep current value)")
                c = store.update(c.id,
                                 prompt("Full name", validate_name, c.full_name),
                                 prompt("Phone", validate_phone, c.phone),
                                 prompt("Email", validate_email, c.email))
                print(f"Updated contact #{c.id}.")
            elif choice == "5":
                c = store.get(int(input("ID to delete: ")))
                if input(f"Delete {c.full_name}? [y/N] ").lower() == "y":
                    store.delete(c.id); print("Deleted.")
            elif choice == "6":
                print_table(store.list(input("Search (name/phone/email): ")))
            elif choice == "0":
                return
            else:
                print("Please choose 0-6.")
        except ValueError:
            print("Error: ID must be a number.")
        except (ValidationError, DuplicateError, NotFoundError) as err:
            print(f"Error: {err}")


def build_parser():
    p = argparse.ArgumentParser(prog="contacts", description="Contact Management System")
    p.add_argument("--db", default=DEFAULT_DB, help="SQLite file (default: data/contacts.db)")
    sub = p.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="add a contact")
    a.add_argument("--name", required=True); a.add_argument("--phone", required=True); a.add_argument("--email", required=True)
    sub.add_parser("list", help="list all contacts")
    v = sub.add_parser("view", help="show one contact"); v.add_argument("id", type=int)
    s = sub.add_parser("search", help="filter by name/phone/email"); s.add_argument("query")
    e = sub.add_parser("edit", help="edit a contact (only given fields change)"); e.add_argument("id", type=int)
    e.add_argument("--name"); e.add_argument("--phone"); e.add_argument("--email")
    d = sub.add_parser("delete", help="delete a contact"); d.add_argument("id", type=int)
    d.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    i = sub.add_parser("import", help="import from CSV"); i.add_argument("file")
    x = sub.add_parser("export", help="export to CSV"); x.add_argument("file")
    sub.add_parser("menu", help="interactive menu (default)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    store = ContactStore(args.db)
    try:
        if args.cmd in (None, "menu"):
            menu(store); return 0
        return run_command(store, args)
    finally:
        store.close()
