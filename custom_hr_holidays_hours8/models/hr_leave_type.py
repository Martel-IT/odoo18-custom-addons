# -*- coding: utf-8 -*-
from odoo import models


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    # Dashboard payload fields whose values are expressed in the leave type's
    # native unit. For request_unit='hour' we convert them to days via the
    # 8h = 1d rule enforced by this module, so the Time Off dashboard shows
    # "days" everywhere regardless of how each leave type was configured.
    _HOURS_TO_DAYS_FIELDS = (
        "remaining_leaves",
        "virtual_remaining_leaves",
        "max_leaves",
        "accrual_bonus",
        "leaves_taken",
        "virtual_leaves_taken",
        "leaves_requested",
        "leaves_approved",
        "closest_allocation_remaining",
        "closest_allocation_duration",
        "exceeding_duration",
        "total_virtual_excess",
        "max_allowed_negative",
    )

    def get_allocation_data_request(self, target_date=None, hidden_allocations=True):
        # Only the dashboard RPC is rewritten; the underlying
        # get_allocation_data (and virtual_remaining_leaves field) keeps
        # values in hours so internal computations stay consistent.
        result = super().get_allocation_data_request(
            target_date=target_date,
            hidden_allocations=hidden_allocations,
        )
        for entry in result:
            # entry = (name, data_dict, requires_allocation, leave_type_id)
            data = entry[1]
            if data.get("request_unit") != "hour":
                continue
            for key in self._HOURS_TO_DAYS_FIELDS:
                val = data.get(key)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    data[key] = round(val / 8.0, 2)
            data["request_unit"] = "day"
        return result
