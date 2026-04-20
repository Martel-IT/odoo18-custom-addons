# -*- coding: utf-8 -*-
from odoo import models


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
