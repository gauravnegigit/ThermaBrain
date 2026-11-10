"""
Guardrail for LLM-written SQL. The agent's DB login is already read-only, but the previous
`startswith("SELECT")` check let through stacked statements ("SELECT 1; DROP ...") and
comment tricks. Voice input widens the prompt-injection surface (anyone can speak to the
console), so the SQL is validated *before* it reaches the database as well.
"""
from __future__ import annotations

import re

ALLOWED_RELATION = "FDE_VIEWS.VW_ACTIVE_FLEET"
MAX_ROWS = 10

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|MERGE|EXEC|EXECUTE|GRANT|REVOKE|DENY|"
    r"OPENROWSET|OPENQUERY|OPENDATASOURCE|BULK|SHUTDOWN|WAITFOR|INTO|XP_\w+|SP_\w+)\b",
    re.IGNORECASE,
)
_RELATIONS = re.compile(r"\b(?:FROM|JOIN)\s+([\[\]\w.]+)", re.IGNORECASE)
_SYS_SCHEMAS = re.compile(r"\b(sys|INFORMATION_SCHEMA|master|msdb|tempdb)\b\s*\.", re.IGNORECASE)


class UnsafeSQL(ValueError):
    pass


def validate_select(sql: str) -> str:
    """Return a cleaned single SELECT statement or raise UnsafeSQL with a user-safe reason."""
    if not sql or not sql.strip():
        raise UnsafeSQL("Empty query.")
    cleaned = re.sub(r"--[^\n]*", " ", sql)                      # line comments
    cleaned = re.sub(r"/\*.*?\*/", " ", cleaned, flags=re.DOTALL)  # block comments
    cleaned = cleaned.strip().rstrip(";").strip()

    if ";" in cleaned:
        raise UnsafeSQL("Only a single statement is allowed.")
    if not re.match(r"(?is)^(SELECT|WITH)\b", cleaned):
        raise UnsafeSQL("Only SELECT operations are authorized.")
    m = _FORBIDDEN.search(cleaned)
    if m:
        raise UnsafeSQL(f"Keyword '{m.group(1).upper()}' is not permitted.")
    if _SYS_SCHEMAS.search(cleaned):
        raise UnsafeSQL("System schemas are off limits.")

    rels = [r.replace("[", "").replace("]", "").upper() for r in _RELATIONS.findall(cleaned)]
    if not rels:
        raise UnsafeSQL(f"Query must read from {ALLOWED_RELATION}.")
    bad = [r for r in rels if r != ALLOWED_RELATION]
    if bad:
        raise UnsafeSQL(f"Only {ALLOWED_RELATION} may be queried (got {bad[0]}).")
    return cleaned
