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


# Show the clean employee name in time off lists and exports. The flag is
# injected in the read entry points of the web list views (web_search_read
# for the rows, web_read_group for the group headers) and of the XLSX/CSV
# export controller (export_data for the rows, read_group for the group
# headers — see web/controllers/export.py). Employee dropdowns and forms are
# left untouched on purpose: there the " - Company" suffix still
# disambiguates multi-company records. The company info dropped from the
# name is shown as its own column instead (see views/hr_leave_overrides.xml).
# The four methods are repeated per model because the registry rejects
# plain-Python mixin bases on models ("object layout differs" when it
# reassigns __bases__ during setup_models).
#
# web_search_read, web_read_group and read_group are model-level methods in
# core Odoo (@api.model): the overrides MUST keep that decorator, otherwise
# call_kw treats them as record methods and tries to pop a recordset off the
# (empty) positional args -> "IndexError: list index out of range". export_data
# is a regular recordset method, so it stays undecorated.

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def web_search_read(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().web_search_read(*args, **kwargs)

    @api.model
    def web_read_group(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().web_read_group(*args, **kwargs)

    @api.model
    def read_group(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().read_group(*args, **kwargs)

    def export_data(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().export_data(*args, **kwargs)


class HrLeaveReport(models.Model):
    _inherit = 'hr.leave.report'

    @api.model
    def web_search_read(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().web_search_read(*args, **kwargs)

    @api.model
    def web_read_group(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().web_read_group(*args, **kwargs)

    @api.model
    def read_group(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().read_group(*args, **kwargs)

    def export_data(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().export_data(*args, **kwargs)


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.model
    def web_search_read(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().web_search_read(*args, **kwargs)

    @api.model
    def web_read_group(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().web_read_group(*args, **kwargs)

    @api.model
    def read_group(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().read_group(*args, **kwargs)

    def export_data(self, *args, **kwargs):
        self = self.with_context(timeoff_clean_employee_names=True)
        return super().export_data(*args, **kwargs)
