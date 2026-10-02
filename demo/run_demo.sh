#!/usr/bin/env bash
# Reproduces demo/demo_session.txt  (run from repo root: bash demo/run_demo.sh)
export CONTACTS_DB=$(mktemp -d)/demo.db
run() { echo; echo "\$ python -m contacts $*"; python -m contacts "$@"; }

echo "### 1. CREATE"
run add --name "Aarav Sharma" --phone "+91 98765 43210" --email "aarav.sharma@example.com"
run add --name "Meera Iyer" --phone "044 2345 6789" --email "meera.iyer@example.com"
echo; echo "### 2. VALIDATION & DUPLICATES"
run add --name "" --phone "123" --email "x@y.com"
run add --name "Test" --phone "abc" --email "x@y.com"
run add --name "Test" --phone "9876543210" --email "bad-email"
run add --name "Imposter" --phone "+919876543210" --email "new@example.com"
run add --name "Imposter" --phone "5551234567" --email "AARAV.SHARMA@example.com"
echo; echo "### 3. BULK IMPORT (bad/duplicate rows reported, not fatal)"
run import sample_data/contacts.csv
echo; echo "### 4. READ (list / view)"
run list
run view 1
echo; echo "### 5. SEARCH (name, phone digits, email)"
run search priya
run search 555-0134
run search example.com
run search nomatch
echo; echo "### 6. UPDATE"
run edit 2 --email "meera.i@newmail.com"
run edit 2 --phone "+91 98765 43210"
echo; echo "### 7. DELETE"
run delete 3 -y
run view 3
echo; echo "### 8. PERSISTENCE (each command above is a fresh process; DB file on disk:)"
ls -l "$CONTACTS_DB" | awk '{print $5" bytes  "$NF}' | sed "s#/.*/#.../#"
run list
echo; echo "### 9. INTERACTIVE MENU (re-prompts on invalid input)"
printf '1\nA\nJo Doe\nabc\n+44 20 7946 0958\nbad\njo@example.com\n6\njo\n0\n' | python -m contacts menu
