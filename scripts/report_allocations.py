"""
report_allocations.py
---------------------
Read-only report of all hr.leave.allocation records (state=validate),
grouped by (employee, leave type), with date ranges and target hours
computed from the employee's resource_calendar.

Highlights:
  - Duplicates: same (employee, type) appearing more than once
  - Wrong hours: actual hours_display != target (only for "Vacation - Employee")

Target rule: 200h × (hours_week / 40h)  — i.e. proportional to contract %.

USAGE:
  cat scripts/report_allocations.py | sudo -u odoo \\
      /nix/store/.../bin/odoo shell --database=odoo --db_user=odoo \\
      --no-http --shell-interface=python
"""

from collections import defaultdict


def vacation_target_hours(emp):
    cal = emp.resource_calendar_id
    if not cal:
        return None
    hours_week = sum(
        a.hour_to - a.hour_from
        for a in cal.attendance_ids
        if not a.date_from and not a.date_to
        and not a.resource_id and not a.display_type
    )
    return (hours_week / 40.0) * 200.0


print("\n" + "=" * 130)
print("ALLOCATION REPORT  (state=validate)")
print("=" * 130)

allocations = env['hr.leave.allocation'].search([('state', '=', 'validate')])
groups = defaultdict(list)
for a in allocations:
    groups[(a.employee_id.id, a.holiday_status_id.id)].append(a)

duplicates_count = 0
wrong_hours_count = 0

for (emp_id, lt_id), allocs in sorted(
    groups.items(),
    key=lambda kv: (env['hr.employee'].browse(kv[0][0]).name or '',
                    env['hr.leave.type'].browse(kv[0][1]).name or '')
):
    emp = env['hr.employee'].browse(emp_id)
    lt = env['hr.leave.type'].browse(lt_id)

    is_dup = len(allocs) > 1
    target = vacation_target_hours(emp) if lt.name == 'Vacation - Employee' else None

    flags = []
    if is_dup:
        flags.append('DUP')
        duplicates_count += 1

    total_hours = sum(a.number_of_hours_display for a in allocs)
    if target is not None and abs(total_hours - target) > 0.5:
        flags.append(f'WRONG (sum={total_hours:.1f}h, target={target:.1f}h)')
        wrong_hours_count += 1

    flag_str = ' | '.join(flags) if flags else '—'
    target_str = f"{target:.1f}h" if target is not None else "—"

    print(f"\n[{flag_str}]  {emp.name}  →  {lt.name}  (target: {target_str})")
    for a in sorted(allocs, key=lambda x: x.date_from or False):
        df = a.date_from.isoformat() if a.date_from else 'N/A'
        dt = a.date_to.isoformat() if a.date_to else 'no end'
        print(f"    id={a.id:5} | {df} → {dt:10} | "
              f"days: {a.number_of_days:7.2f} | "
              f"hours: {a.number_of_hours_display:8.2f} | "
              f"taken: {a.leaves_taken:6.2f}")

print("\n" + "=" * 130)
print(f"Summary: {duplicates_count} pairs with multiple allocations | "
      f"{wrong_hours_count} pairs with wrong target hours")
print("=" * 130 + "\n")
