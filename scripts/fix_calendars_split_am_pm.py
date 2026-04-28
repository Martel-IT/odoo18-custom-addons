"""
fix_calendars_split_am_pm.py
----------------------------
Splits all resource.calendar attendances into morning/afternoon halves to
enable Odoo's half-day leave button.

Logic per attendance slot:
  - if entirely AM (hour_to <= 12.5): keep/relabel as 'morning'
  - if entirely PM (hour_from >= 12.5): keep/relabel as 'afternoon'
  - if spans lunch: split at 13:00 into morning + afternoon (no lunch break)

The total weekly hours are preserved EXACTLY. Only labels and split points
change. Two-week calendars are processed transparently because each
attendance has its own week_type.

USAGE:
  1) Run with DRY_RUN=True (default) and review the proposed changes:
     cat scripts/fix_calendars_split_am_pm.py | sudo -u odoo \\
         /nix/store/.../bin/odoo shell --database=odoo --db_user=odoo \\
         --no-http --shell-interface=python

  2) If output looks good, change DRY_RUN to False, re-run.
"""

DRY_RUN = True  # ← set to False to apply changes

DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def classify(hour_from, hour_to, period):
    """Returns one of:
       ('keep',)
       ('relabel', new_period)
       ('split', split_at)
    """
    # entirely AM (slot ends at 13:00 or earlier)
    if hour_to <= 13.0:
        return ('keep',) if period == 'morning' else ('relabel', 'morning')
    # entirely PM (slot starts at 13:00 or later)
    if hour_from >= 13.0:
        return ('keep',) if period == 'afternoon' else ('relabel', 'afternoon')
    # spans lunch — split at 13:00
    return ('split', 13.0)


print("\n" + "=" * 80)
print(f"CALENDAR SPLIT AM/PM — DRY_RUN={DRY_RUN}")
print("=" * 80)

calendars = env['resource.calendar'].search([])
total_changes = 0
total_calendars_changed = 0

for cal in calendars:
    attendances = cal.attendance_ids.filtered(
        lambda a: not a.date_from and not a.date_to
        and not a.resource_id and not a.display_type
    )

    plans = []
    for att in attendances:
        action = classify(att.hour_from, att.hour_to, att.day_period)
        if action[0] != 'keep':
            plans.append((att, action))

    if not plans:
        continue

    total_calendars_changed += 1
    print(f"\n— {cal.name}  (id={cal.id}, hpd={cal.hours_per_day})")
    for att, action in plans:
        dow = DAYS[int(att.dayofweek)]
        if action[0] == 'relabel':
            print(f"    {dow} {att.hour_from:5.2f}-{att.hour_to:5.2f}: "
                  f"relabel {att.day_period} → {action[1]}")
        elif action[0] == 'split':
            split_at = action[1]
            print(f"    {dow} {att.hour_from:5.2f}-{att.hour_to:5.2f}: "
                  f"split at {split_at:.2f}")
            print(f"        → morning   {att.hour_from:5.2f}-{split_at:5.2f}  "
                  f"({split_at - att.hour_from:.2f}h)")
            print(f"        → afternoon {split_at:5.2f}-{att.hour_to:5.2f}  "
                  f"({att.hour_to - split_at:.2f}h)")
        total_changes += 1

    if not DRY_RUN:
        for att, action in plans:
            if action[0] == 'relabel':
                att.day_period = action[1]
            elif action[0] == 'split':
                split_at = action[1]
                env['resource.calendar.attendance'].create({
                    'name': att.name or f'Attendance {DAYS[int(att.dayofweek)]} PM',
                    'dayofweek': att.dayofweek,
                    'hour_from': split_at,
                    'hour_to': att.hour_to,
                    'day_period': 'afternoon',
                    'calendar_id': cal.id,
                    'sequence': (att.sequence or 10) + 1,
                    'week_type': att.week_type if att.week_type else False,
                })
                att.write({
                    'hour_to': split_at,
                    'day_period': 'morning',
                })

print("\n" + "=" * 80)
print(f"SUMMARY: {total_changes} attendance changes "
      f"across {total_calendars_changed} calendars")
print("=" * 80)

if DRY_RUN:
    print("⚠ DRY RUN — no changes applied. "
          "Edit DRY_RUN=False and re-run to commit.\n")
else:
    env.cr.commit()
    print("✓ Committed to database.\n")
