"""CSV encoding shared by directory and analytics exports; no domain/API imports."""
import csv
import io


def safe_text(value):
    # Excel may ignore leading whitespace/control characters before a formula.
    return "'" + value if value.lstrip(" \t\r\n\ufeff\x00\x0b\x0c").startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value


def csv_bytes(columns, rows):
    target = io.StringIO(newline="")
    writer = csv.writer(target, lineterminator="\r\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([safe_text(value) if isinstance(value, str) else value for value in (row.get(c) for c in columns)])
    return target.getvalue().encode("utf-8-sig")
