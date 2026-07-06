#!/usr/bin/env bash
# Set HR acronyms in hr_employee.identification_id from employee_acronyms.csv
# (columns: full_name,acronym). Used by the timesheet PDF export filename
# (timesheets_by_employee/wizard/timesheet_report.py).
#
# Matching:
#   1. via the linked user's full name (res_partner): every employee record
#      of that person gets the acronym, including per-company duplicates
#      with variant names ("<Name> CH", "<Name> NL", ...);
#   2. fallback on the employee record name itself (records without user).
# Names are compared lowercase, apostrophe- and whitespace-normalized.
# Idempotent: only rows whose current value differs are touched.
#
# Usage (on the Odoo VM, as root):
#   ./set_employee_acronyms.sh              # apply on DB "odoo"
#   ./set_employee_acronyms.sh --dry-run    # preview only, rolls back
#   ./set_employee_acronyms.sh -d otherdb -f /path/map.csv
set -euo pipefail

DB_NAME="odoo"
CSV="$(cd "$(dirname "$0")" && pwd)/employee_acronyms.csv"
FINAL="COMMIT"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -d) DB_NAME="$2"; shift 2 ;;
        -f) CSV="$2"; shift 2 ;;
        --dry-run) FINAL="ROLLBACK"; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

[[ -f "$CSV" ]] || { echo "CSV not found: $CSV" >&2; exit 1; }
[[ "$FINAL" == "ROLLBACK" ]] && echo ">>> DRY RUN: nothing will be committed."

{
    cat <<'SQL'
BEGIN;

CREATE TEMP TABLE acr_map(full_name text, acronym text);

COPY acr_map FROM STDIN WITH (FORMAT csv, HEADER true);
SQL
    cat "$CSV"
    echo '\.'
    cat <<'SQL'

-- Normalize for matching: straight apostrophes, single spaces, lowercase.
CREATE FUNCTION pg_temp.norm(t text) RETURNS text LANGUAGE sql IMMUTABLE AS
$fn$ SELECT lower(btrim(regexp_replace(
        replace(replace(t, chr(8217), ''''), '`', ''''),
        '\s+', ' ', 'g'))) $fn$;

-- 1) Match via the linked user's full name: update ALL employee records
--    of that user (per-company duplicates included).
WITH m AS (SELECT pg_temp.norm(full_name) AS k, acronym FROM acr_map)
UPDATE hr_employee e
SET identification_id = m.acronym
FROM m, res_users u, res_partner p
WHERE u.partner_id = p.id
  AND e.user_id = u.id
  AND pg_temp.norm(p.name) = m.k
  AND e.identification_id IS DISTINCT FROM m.acronym
RETURNING e.id AS employee_id, e.name AS employee_record, m.acronym AS set_acronym;

-- 2) Fallback: match the employee record name itself (no linked user).
WITH m AS (SELECT pg_temp.norm(full_name) AS k, acronym FROM acr_map)
UPDATE hr_employee e
SET identification_id = m.acronym
FROM m
WHERE pg_temp.norm(e.name) = m.k
  AND e.identification_id IS DISTINCT FROM m.acronym
RETURNING e.id AS employee_id, e.name AS employee_record, m.acronym AS set_acronym;

-- Map entries that matched no employee at all (check for typos/leavers).
SELECT m.full_name AS unmatched_map_entry, m.acronym
FROM acr_map m
WHERE NOT EXISTS (
    SELECT 1
    FROM hr_employee e
    LEFT JOIN res_users u ON u.id = e.user_id
    LEFT JOIN res_partner p ON p.id = u.partner_id
    WHERE pg_temp.norm(e.name) = pg_temp.norm(m.full_name)
       OR pg_temp.norm(p.name) = pg_temp.norm(m.full_name)
)
ORDER BY 1;

-- Active employees still without an acronym after this run.
SELECT e.id, e.name AS active_employee_missing_acronym
FROM hr_employee e
WHERE e.active
  AND (e.identification_id IS NULL OR btrim(e.identification_id) = '')
ORDER BY e.name;
SQL
    echo "${FINAL};"
} | sudo -u odoo psql -v ON_ERROR_STOP=1 -d "$DB_NAME"
