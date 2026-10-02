"""Input validation and normalisation. Raises ValidationError with a clear message."""
import re


class ValidationError(ValueError):
    pass


_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")


def validate_name(value: str) -> str:
    value = " ".join((value or "").split())
    if not value:
        raise ValidationError("Full name is required.")
    if len(value) < 2 or len(value) > 100:
        raise ValidationError("Full name must be 2-100 characters.")
    if not any(c.isalpha() for c in value):
        raise ValidationError("Full name must contain at least one letter.")
    return value


def validate_phone(value: str) -> str:
    """Strip spaces, dashes, dots and brackets; accept optional leading '+', 7-15 digits."""
    raw = (value or "").strip()
    if not raw:
        raise ValidationError("Phone number is required.")
    cleaned = re.sub(r"[\s\-\.\(\)]", "", raw)
    if not re.fullmatch(r"\+?\d{7,15}", cleaned):
        raise ValidationError("Phone must have 7-15 digits (optional leading +). Example: +91 98765 43210")
    return cleaned


def validate_email(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        raise ValidationError("Email address is required.")
    if len(value) > 254 or not _EMAIL_RE.match(value):
        raise ValidationError("Email address is not valid. Example: name@example.com")
    return value
