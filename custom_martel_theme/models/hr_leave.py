# -*- coding: utf-8 -*-
from odoo import api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.depends_context('timeoff_clean_employee_names')
    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('timeoff_clean_employee_names'):
            for employee in self:
                # The user full name (res.users) is the clean, canonical one:
                # per-company employee records carry hand-typed variant names
                # (e.g. "Jane Doe D4P") and multi-record users also get a
                # " - Company" suffix appended by standard Odoo.
                user = employee.sudo().user_id
                employee.display_name = user.name or employee.name


class CleanEmployeeNames:
    """Show the clean employee name in time off lists and exports.

    The flag is injected in the read entry points of the web list views
    (web_search_read for the rows, web_read_group for the group headers)
    and of the XLSX/CSV export controller (export_data for the rows,
    read_group for the group headers — see web/controllers/export.py).
    Employee dropdowns and forms are left untouched on purpose: there the
    " - Company" suffix still disambiguates multi-company records. The
    company info dropped from the name is shown as its own column instead
    (see views/hr_leave_overrides.xml).
    """

    def web_search_read(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().web_search_read(*args, **kwargs)

    def web_read_group(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().web_read_group(*args, **kwargs)

    def read_group(self, domain, fields, groupby, offset=0, limit=None,
                   orderby=False, lazy=True):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().read_group(domain, fields, groupby, offset=offset,
                                  limit=limit, orderby=orderby, lazy=lazy)

    def export_data(self, fields_to_export):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().export_data(fields_to_export)


class HrLeave(CleanEmployeeNames, models.Model):
    _inherit = 'hr.leave'


class HrLeaveReport(CleanEmployeeNames, models.Model):
    _inherit = 'hr.leave.report'


class HrLeaveAllocation(CleanEmployeeNames, models.Model):
    _inherit = 'hr.leave.allocation'
