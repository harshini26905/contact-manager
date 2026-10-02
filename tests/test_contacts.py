import pytest

from contacts.storage import ContactStore, DuplicateError, NotFoundError
from contacts.validation import ValidationError


@pytest.fixture
def store():
    s = ContactStore(":memory:")
    yield s
    s.close()


def add(store, n="Asha Rao", p="+91 98765 43210", e="asha@example.com"):
    return store.add(n, p, e)


def test_add_and_get_normalises(store):
    c = add(store, "  asha   rao ", "+91 (987) 654-3210", " ASHA@Example.com ")
    assert (c.full_name, c.phone, c.email) == ("asha rao", "+919876543210", "asha@example.com")
    assert store.get(c.id).email == "asha@example.com"


@pytest.mark.parametrize("n,p,e", [
    ("", "9876543210", "a@b.co"), ("A", "9876543210", "a@b.co"), ("1234", "9876543210", "a@b.co"),
    ("Asha", "", "a@b.co"), ("Asha", "abc", "a@b.co"), ("Asha", "123", "a@b.co"),
    ("Asha", "9876543210", ""), ("Asha", "9876543210", "nope"), ("Asha", "9876543210", "a@b"),
])
def test_validation_rejects(store, n, p, e):
    with pytest.raises(ValidationError):
        store.add(n, p, e)
    assert store.list() == []


def test_duplicate_phone_format_insensitive(store):
    add(store)
    with pytest.raises(DuplicateError) as ei:
        store.add("Other", "+919876543210", "other@example.com")
    assert ei.value.field == "phone"


def test_duplicate_email_case_insensitive(store):
    add(store)
    with pytest.raises(DuplicateError) as ei:
        store.add("Other", "5551234567", "ASHA@example.com")
    assert ei.value.field == "email"


def test_list_sorted_and_search(store):
    add(store, "Zed Zee", "1111111111", "z@example.com")
    add(store, "Amy Adams", "2222222222", "amy@work.org")
    assert [c.full_name for c in store.list()] == ["Amy Adams", "Zed Zee"]
    assert [c.full_name for c in store.list("adams")] == ["Amy Adams"]
    assert [c.full_name for c in store.list("WORK.ORG")] == ["Amy Adams"]
    assert [c.full_name for c in store.list("222-222")] == ["Amy Adams"]
    assert store.list("zzzz-nomatch") == []


def test_search_treats_wildcards_literally(store):
    add(store)
    assert store.list("%") == []
    assert store.list("_") == []


def test_update_partial_and_dup_checks(store):
    a = add(store)
    b = store.add("Bob", "5551234567", "bob@example.com")
    assert store.update(a.id, full_name="Asha R").full_name == "Asha R"
    assert store.update(a.id, phone=a.phone).id == a.id  # keeping own phone is not a duplicate
    with pytest.raises(DuplicateError):
        store.update(b.id, email="asha@example.com")
    with pytest.raises(ValidationError):
        store.update(b.id, phone="x")
    with pytest.raises(NotFoundError):
        store.update(999, full_name="Nobody")


def test_delete(store):
    c = add(store)
    store.delete(c.id)
    with pytest.raises(NotFoundError):
        store.get(c.id)
    with pytest.raises(NotFoundError):
        store.delete(c.id)


def test_persistence_across_restart(tmp_path):
    db = str(tmp_path / "c.db")
    s1 = ContactStore(db); add(s1); s1.close()
    s2 = ContactStore(db)
    assert [c.email for c in s2.list()] == ["asha@example.com"]
    s2.close()


def test_csv_import_skips_bad_rows(tmp_path):
    s = ContactStore(":memory:")
    ok, errs = s.import_csv("sample_data/contacts.csv")
    assert ok == 5 and len(errs) == 3
    out = tmp_path / "out.csv"
    assert s.export_csv(str(out)) == 5
