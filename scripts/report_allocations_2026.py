"""
report_allocations_2026.py
--------------------------
Focused report on 2026 vacation allocations.

For each (employee, "Vacation - Employee"):
  - Current year (2026) allocation hours vs target
  - Carryover from previous years (sum of remaining hours)
  - Total effective available

Target rule: 200h × (hours_week / 40h)

USAGE:
  cat scripts/report_allocations_2026.py | sudo -u odoo \\
      /nix/store/.../bin/odoo shell --database=odoo --db_user=odoo \\
      --no-http --shell-interface=python
"""

from collections import defaultdict
from datetime import date


CURRENT_YEAR = 2026


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


print("\n" + "=" * 140)
print(f"VACATION ALLOCATIONS REPORT — focus on year {CURRENT_YEAR}")
print("=" * 140)

vacation_lt = env['hr.leave.type'].search([('name', '=', 'Vacation - Employee')], limit=1)
if not vacation_lt:
    print("⚠ Leave type 'Vacation - Employee' not found")
else:
    allocations = env['hr.leave.allocation'].search([
        ('state', '=', 'validate'),
        ('holiday_status_id', '=', vacation_lt.id),
    ])
    by_emp = defaultdict(list)
    for a in allocations:
        by_emp[a.employee_id.id].append(a)

    print(f"\n{'EMPLOYEE':<35}  {'TARGET':>8}  {'CURRENT (2026)':>15}  {'CARRYOVER':>11}  {'TOTAL AVAIL':>12}  STATUS")
    print("-" * 140)

    issues = []
    for emp_id, allocs in sorted(by_emp.items(),
                                  key=lambda kv: env['hr.employee'].browse(kv[0]).name or ''):
        emp = env['hr.employee'].browse(emp_id)
        target = vacation_target_hours(emp)

        current_year_allocs = [a for a in allocs if a.date_from and a.date_from.year >= CURRENT_YEAR]
        old_allocs = [a for a in allocs if a.date_from and a.date_from.year < CURRENT_YEAR]

        current_hours = sum(a.number_of_hours_display for a in current_year_allocs)
        carryover = sum(
            (a.number_of_hours_display - a.leaves_taken) for a in old_allocs
        )
        total_avail = current_hours + carryover

        status_flags = []
        if target is not None:
            if not current_year_allocs:
                status_flags.append("❌ NO 2026 ALLOC")
            elif abs(current_hours - target) > 0.5:
                status_flags.append(f"⚠ 2026 MISMATCH (got {current_hours:.1f}h, target {target:.1f}h)")

        if len(current_year_allocs) > 1:
            status_flags.append(f"⚠ {len(current_year_allocs)} alloc 2026 (multiple)")

        status = ' | '.join(status_flags) if status_flags else 'ok'

        target_str = f"{target:.1f}h" if target is not None else "—"

        print(f"{emp.name:<35}  {target_str:>8}  "
              f"{current_hours:>13.1f}h  "
              f"{carryover:>9.1f}h  "
              f"{total_avail:>10.1f}h  "
              f"{status}")

        if status_flags:
            issues.append((emp.name, status))
            for a in current_year_allocs:
                print(f"     2026 alloc id={a.id}: hours={a.number_of_hours_display:.1f}, days={a.number_of_days:.2f}")

    print("\n" + "=" * 140)
    print(f"Total employees with issues: {len(issues)}")
    for name, status in issues:
        print(f"   - {name}: {status}")
    print("=" * 140 + "\n")
