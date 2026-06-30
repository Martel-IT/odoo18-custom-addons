"""
Refresh stored running-balance snapshots on every Approved timesheet sheet.

Why this exists
---------------
``total_diff_hours`` and ``total_duty_hours_done`` are snapshot fields that
the custom module ``custom_hr_timesheet_overtime`` writes when a sheet
transitions to state ``done``. They cache the cumulative balance and the
duty hours of the period so list views and downstream computations stay
cheap.

After the public-holiday fix (commit ``aa3ba9b``), the calculation of duty
hours changes — days covered by ``resource.calendar.leaves`` now count as
zero duty. Snapshots taken before that commit hold the old (wrong) values
and are not refreshed automatically: the snapshot only gets rewritten if
the sheet leaves and re-enters the ``done`` state.

This script walks every ``done`` sheet in chronological order per employee
and forces a fresh snapshot, so each sheet's running balance is rebuilt
using its predecessor's already-corrected value.

How to run
----------
On the staging/prod machine, with Odoo stopped (or at least no human user
mid-approve), run::

    ./odoo-bin shell -c /etc/odoo/odoo.conf -d <dbname> --no-http \\
        < scripts/backfill_timesheet_snapshots.py

The script commits at the end. Output goes to stdout. If anything fails on
a single sheet the loop continues and the failure is summarised at the
end — no rollback of the rest.
"""

from collections import defaultdict
from datetime import date

# OD18 went live on this date. Sheets with `date_end < MIGRATION_CUTOFF`
# are pre-migration: their authoritative snapshot lives in OD16 and is
# imported via the `restore_clean_odoo18v2.sh` step that copies OD16's
# `total_duty_hours_done` and `total_diff_hours` into OD18.
#
# We MUST NOT recompute those: OCA 16→18 does not carry over a clean
# enough copy of resource.calendar.leaves / hr.leave to reproduce the
# duty hours OD16 computed. Empirically, recomputing here drifts by
# ~8h per missing leave day — adding up to ~30h over 9 years for some
# employees (e.g. Gabriele Cerfoglio).
MIGRATION_CUTOFF = date(2025, 12, 1)

Sheet = env['hr_timesheet.sheet'].sudo()

done_sheets = Sheet.search(
    [('state', '=', 'done')],
    order='employee_id, date_start asc',
)
print("Found %d approved sheets to refresh." % len(done_sheets))

by_employee = defaultdict(list)
for s in done_sheets:
    by_employee[s.employee_id.id].append(s)

total_ok = 0
total_skipped = 0
errors = []

for emp_id, sheets in by_employee.items():
    emp_name = sheets[0].employee_id.name or "(no name)"
    print("  %s [id=%s]: %d sheets" % (emp_name, emp_id, len(sheets)))
    for sheet in sheets:
        try:
            if sheet.date_end and sheet.date_end < MIGRATION_CUTOFF:
                # Trust OD16 imported snapshot, do not recompute.
                total_skipped += 1
                continue

            # Zero the snapshot fields so the compute methods fall through
            # to the live branch on the next read. The custom write()
            # override only mutates these fields when 'state' is in vals,
            # so a direct write here is safe.
            sheet.write({
                'total_duty_hours_done': 0.0,
                'total_diff_hours': 0.0,
            })
            sheet.invalidate_recordset([
                'total_duty_hours',
                'calculate_diff_hours',
                'prev_timesheet_diff',
            ])

            new_duty = sheet.total_duty_hours
            new_diff = sheet.calculate_diff_hours

            sheet.write({
                'total_duty_hours_done': new_duty,
                'total_diff_hours': new_diff,
            })
            total_ok += 1
        except Exception as exc:
            errors.append((sheet.id, sheet.display_name, str(exc)))
            print("    ERROR on sheet %s (%s): %s"
                  % (sheet.id, sheet.display_name, exc))

env.cr.commit()
print("---")
print("Done. Refreshed %d sheets. Skipped (pre-cutoff): %d. Errors: %d"
      % (total_ok, total_skipped, len(errors)))
for sid, name, err in errors:
    print("  - %s | %s | %s" % (sid, name, err))
