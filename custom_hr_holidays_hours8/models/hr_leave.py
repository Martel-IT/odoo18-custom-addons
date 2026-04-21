# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.tools import float_round


class HolidaysRequest(models.Model):
    _inherit = 'hr.leave'

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        # Hours/8 fixed mapping — ignores resource_calendar working-hours.
        # Overriding at this hook propagates to _compute_duration AND
        # _compute_leave_type_increases_duration, which both call it.
        result = super()._get_durations(
            check_leave_type=check_leave_type,
            resource_calendar=resource_calendar,
        )
        return {
            leave_id: ((hours or 0.0) / 8.0, hours)
            for leave_id, (_days, hours) in result.items()
        }

    @api.depends('number_of_hours', 'number_of_days', 'leave_type_request_unit')
    def _compute_duration_display(self):
        # Show both days and hours for hour-based leave types, restoring
        # the Odoo 16 style "X days (HH:MM hours)" in the New Time Off dialog.
        super()._compute_duration_display()
        for leave in self:
            if leave.leave_type_request_unit != "hour":
                continue
            total_hours = leave.number_of_hours or 0.0
            days = total_hours / 8.0
            hours, minutes = divmod(abs(total_hours) * 60, 60)
            minutes = round(minutes)
            if minutes == 60:
                minutes = 0
                hours += 1
            leave.duration_display = "%g %s (%d:%02d %s)" % (
                float_round(days, precision_digits=2),
                _("days"),
                hours,
                minutes,
                _("hours"),
            )
