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
        docs = self.env['timesheet.report'].browse(
            self.env.context.get('active_id'))

        user = docs.user_id[0]
        employee = self.env['hr.employee'].search(
            [('user_id', '=', user.id)], limit=1)

        # ── Fetch timesheet lines ────────────────────────────────────────────
        domain = [('user_id', '=', user.id)]
        if docs.from_date:
            domain.append(('date', '>=', docs.from_date))
        if docs.to_date:
            domain.append(('date', '<=', docs.to_date))
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
        company = self.env.company
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
                reviewer_name = sheet.reviewer_id.name if sheet.reviewer_id else ''
                timesheet_submitted_date = (
                    getattr(sheet, 'date_submitted', None)
                    or getattr(sheet, 'write_date', None))
                timesheet_approved_date = getattr(sheet, 'date_approved', None)

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
