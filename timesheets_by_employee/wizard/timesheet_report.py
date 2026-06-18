# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Jumana Jabin MP (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models
from odoo.exceptions import UserError
from datetime import date


class TimesheetReport(models.TransientModel):
    """Create a Transient model for Wizard"""
    _name = 'timesheet.report'
    _description = 'Timesheet Report Wizard'

    user_id = fields.Many2one(
        'res.users',
        string="Employee",
        required=True, help="You can select the employee")
    from_date = fields.Date(
        string="Starting Date",
        help="You can select the starting dates for the PDF report")
    to_date = fields.Date(
        string="Ending Date",
        help="You can select the ending dates for the PDF report")

    def print_timesheet(self):
        """Redirect to the timesheet PDF report for this wizard record."""
        today = fields.Date.today()
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise UserError("Start date cannot be after end date.")
            if self.from_date > today or self.to_date > today:
                raise UserError("Start date and end date cannot be in the future.")
        # NB: do NOT pass `data` here. The report reads the wizard via
        # `active_id` from the context, not via `data`. Passing a non-empty
        # `data` makes the web client build a report URL without docids, which
        # prevents `print_report_name` from being evaluated — the PDF would then
        # download as "Timesheets - <timestamp>.pdf" instead of the custom name.
        return self.env.ref(
            'timesheets_by_employee.action_report_print_timesheets'). \
            report_action(self)
