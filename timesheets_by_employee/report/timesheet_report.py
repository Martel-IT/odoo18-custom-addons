# -*- coding: utf-8 -*-
from odoo import api, models


def _float_to_hhmm(value):
    """Convert float hours to HH:MM string, e.g. 1.5 → '01:30'."""
    hours = int(value)
    minutes = round((value - hours) * 60)
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours:02d}:{minutes:02d}"


class ReportTimesheet(models.AbstractModel):
    _name = 'report.timesheets_by_employee.report_timesheet_employee'
    _description = 'Timesheet Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Prefer docids (standard report flow): the wizard is now printed via
        # report_action(self) without `data`, so the record id arrives as docids.
        # Fall back to active_id for any legacy/context-based invocation.
        if docids:
            docs = self.env['timesheet.report'].browse(docids)
        else:
            docs = self.env['timesheet.report'].browse(
                self.env.context.get('active_id'))

        employee = docs.employee_id

        # ── Fetch timesheet lines ────────────────────────────────────────────
        # Filter by employee, not by user: someone working for two companies
        # has a single user but one hr.employee record per company, so a
        # user_id domain merged both companies' hours into one PDF (and the
        # multi-company rules made the result depend on the company switcher).
        # employee_id is also how hr_timesheet.sheet groups its own lines, so
        # the PDF matches the sheet even when a line's project belongs to the
        # other company.
        domain = [('employee_id', '=', employee.id)]
        if docs.from_date:
            domain.append(('date', '>=', docs.from_date))
        if docs.to_date:
            domain.append(('date', '<=', docs.to_date))
        # Require a project: account.analytic.line rows can come from many
        # places (sale orders, expenses, manual entries) and orphan lines
        # without project would otherwise show up under "No Project" in the
        # PDF even though they aren't part of any timesheet sheet.
        # Also honor the per-project "Exclude from Timesheet Report" flag
        # defined in custom_hr_timesheet_overtime.
        domain += [
            ('project_id', '!=', False),
            ('project_id.excl_from_printed_timesheets', '=', False),
        ]
        records = self.env['account.analytic.line'].search(
            domain, order='project_id, task_id, date')

        # ── Build nested structure: projects → tasks → entries ───────────────
        projects = {}
        total_float = 0.0
        for rec in records:
            proj = rec.project_id.name or 'No Project'
            task = rec.task_id.name or 'No Task'
            projects.setdefault(proj, {'tasks': {}, 'subtotal': 0.0})
            projects[proj]['tasks'].setdefault(task, {'entries': [], 'subtotal': 0.0})
            projects[proj]['tasks'][task]['entries'].append({
                'date': rec.date,
                'description': rec.name or '',
                'duration': _float_to_hhmm(rec.unit_amount),
            })
            projects[proj]['tasks'][task]['subtotal'] += rec.unit_amount
            projects[proj]['subtotal'] += rec.unit_amount
            total_float += rec.unit_amount

        for proj_data in projects.values():
            proj_data['subtotal_display'] = _float_to_hhmm(proj_data['subtotal'])
            for task_data in proj_data['tasks'].values():
                task_data['subtotal_display'] = _float_to_hhmm(task_data['subtotal'])

        timesheet_data = {
            'total_hours_display': _float_to_hhmm(total_float),
            'projects': projects,
        }

        # ── Period string ────────────────────────────────────────────────────
        if docs.from_date and docs.to_date:
            period = (f"From {docs.from_date.strftime('%d/%m/%Y')}"
                      f" To {docs.to_date.strftime('%d/%m/%Y')}")
        elif docs.from_date:
            period = f"From {docs.from_date.strftime('%d/%m/%Y')}"
        elif docs.to_date:
            period = f"To {docs.to_date.strftime('%d/%m/%Y')}"
        else:
            period = ''

        # ── Company data ─────────────────────────────────────────────────────
        # The employee's company, not the active one: printing a Digital4Planet
        # employee while Martel is the current company used to letterhead the
        # PDF with the wrong company.
        company = employee.company_id or self.env.company
        company_data = {
            'name':     company.name,
            'street':   company.street or '',
            'city':     company.city or '',
            'zip':      company.zip or '',
            'state_id': company.state_id.name if company.state_id else '',
            'phone':    company.phone or '',
            'email':    company.email or '',
            'website':  company.website or '',
        }

        # ── Submission / approval info from hr_timesheet.sheet ───────────────
        # OCA hr_timesheet_sheet in v18 does not expose date_submitted or
        # date_approved fields on the sheet. The information is only kept
        # implicitly in mail.tracking.value rows produced by the auto-tracked
        # `state` field. Read it from there: first state transition is the
        # submission, latest transition on a done sheet is the approval.
        reviewer_name = ''
        timesheet_submitted_date = None
        timesheet_approved_date = None
        if employee:
            sheet_domain = [('employee_id', '=', employee.id)]
            if docs.from_date:
                sheet_domain.append(('date_start', '>=', docs.from_date))
            if docs.to_date:
                sheet_domain.append(('date_end', '<=', docs.to_date))
            sheet = self.env['hr_timesheet.sheet'].search(
                sheet_domain, limit=1, order='date_end desc')
            if sheet:
                # Prefer the reviewer's user full name: employee records
                # may carry name variants. Read it with sudo: approvals are
                # cross-company here, so the reviewer's employee record often
                # belongs to another company and the multi-company rule raises
                # AccessError unless that company is active in the switcher.
                reviewer = sheet.reviewer_id.sudo()
                reviewer_name = (reviewer.user_id.name
                                 or reviewer.name) if reviewer else ''
                Tracking = self.env['mail.tracking.value'].sudo()
                tv_first = Tracking.search([
                    ('mail_message_id.model', '=', 'hr_timesheet.sheet'),
                    ('mail_message_id.res_id', '=', sheet.id),
                    ('field_id.name', '=', 'state'),
                ], limit=1, order='create_date asc')
                if tv_first:
                    timesheet_submitted_date = tv_first.mail_message_id.date
                if sheet.state == 'done':
                    tv_last = Tracking.search([
                        ('mail_message_id.model', '=', 'hr_timesheet.sheet'),
                        ('mail_message_id.res_id', '=', sheet.id),
                        ('field_id.name', '=', 'state'),
                    ], limit=1, order='create_date desc')
                    if tv_last:
                        timesheet_approved_date = tv_last.mail_message_id.date

        return {
            'doc_ids':                  self.ids,
            'docs':                     docs,
            'timesheet_data':           timesheet_data,
            'employee':                 employee,
            'period':                   period,
            'company_data':             company_data,
            'reviewer_name':            reviewer_name,
            'timesheet_submitted_date': timesheet_submitted_date,
            'timesheet_approved_date':  timesheet_approved_date,
        }
