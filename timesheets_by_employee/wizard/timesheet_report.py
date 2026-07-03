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
from datetime import date, datetime
import re
import unicodedata


# Short company labels used in the export filename, keyed by lowercased
# company name. Companies not listed here fall back to their full name.
COMPANY_SHORT_NAMES = {
    'martel innovate': 'Martel CH',
    'digital4planet': 'D4P',
    'martel innovate bv': 'Martel BV',
}


def _split_person_name(name):
    """Split a full name into given-name words and surname parts.

    The surname starts at the first lowercase token, which marks particles
    like "dos"/"de"/"van"; otherwise it is the last token, so multi-word
    given names stay together. Surname parts are further split on
    apostrophes and hyphens, so compound surnames yield several parts.
    """
    normalized = name.replace('’', "'").replace('`', "'")
    normalized = unicodedata.normalize('NFKD', normalized)
    normalized = normalized.encode('ascii', 'ignore').decode()
    tokens = [t for t in normalized.split() if any(c.isalpha() for c in t)]
    if not tokens:
        return [], []
    surname_start = len(tokens) - 1
    for i, token in enumerate(tokens[1:], start=1):
        if token[:1].islower():
            surname_start = i
            break
    given = tokens[:surname_start] or tokens[:1]
    surname = ' '.join(tokens[surname_start:])
    surname_parts = [p for p in re.split(r"['\s-]+", surname) if p]
    return given, surname_parts


def _acronym_from_name(name):
    """Default employee acronym: initial of the first given name plus the
    first two letters of the surname ("John Smith" -> JSM); for compound
    surnames, the initial of each of the first two parts instead
    ("Anna dos Reis" -> ADR, "Marco Dell'Orto" -> MDO)."""
    given, surname_parts = _split_person_name(name or '')
    if not given or not surname_parts:
        return ''
    if len(surname_parts) >= 2:
        return (given[0][0] + surname_parts[0][0] + surname_parts[1][0]).upper()
    return (given[0][0] + surname_parts[0][:2]).upper()


def _alternate_acronym(name):
    """Collision fallback when the default acronym is already taken by a
    more senior employee: initials of the first two given names plus the
    surname initial ("Anna Lisa Rossi" -> ALR instead of ARO)."""
    given, surname_parts = _split_person_name(name or '')
    if len(given) >= 2 and surname_parts:
        return (given[0][0] + given[1][0] + surname_parts[0][0]).upper()
    return _acronym_from_name(name)


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

    def _get_employee_acronym(self, employee, name):
        """Return the acronym for ``name``, falling back to the alternate
        form when the default one belongs to a more senior employee
        (older hr.employee record). Seniority is compared on
        (create_date, id); duplicated employee records of the same person
        (e.g. one per company) are not treated as collisions."""
        acronym = _acronym_from_name(name)
        if not acronym:
            return 'XXX'
        own_key = (employee.create_date or datetime.max,
                   employee.id or float('inf'))
        others = self.env['hr.employee'].sudo().with_context(
            active_test=False).search([('id', 'not in', employee.ids)])
        for other in others:
            if (other.name or '').strip() == name.strip():
                continue
            if _acronym_from_name(other.name) != acronym:
                continue
            if (other.create_date or datetime.max, other.id) < own_key:
                return _alternate_acronym(name)
        return acronym

    def get_export_filename(self):
        """Standardized PDF filename, evaluated by ``print_report_name``:
        <YYYYMM>_<company label>_Timesheet_<employee acronym>_signed
        (e.g. "202605_Martel CH_Timesheet_JSM_signed"). The period comes
        from the wizard start date, the company from the employee record."""
        self.ensure_one()
        period = self.from_date or self.to_date or fields.Date.today()
        employee = self.env['hr.employee'].sudo().with_context(
            active_test=False).search(
            [('user_id', '=', self.user_id.id)], limit=1)
        name = employee.name or self.user_id.name or ''
        acronym = self._get_employee_acronym(employee, name)
        company = employee.company_id or self.env.company
        company_label = COMPANY_SHORT_NAMES.get(
            (company.name or '').strip().lower(), company.name)
        return (f"{period.strftime('%Y%m')}_{company_label}"
                f"_Timesheet_{acronym}_signed")

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
