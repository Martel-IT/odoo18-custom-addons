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

    def get_timesheets(self, docs):
        domain = [('user_id', '=', docs.user_id[0].id)]
        if docs.from_date:
            domain.append(('date', '>=', docs.from_date))
        if docs.to_date:
            domain.append(('date', '<=', docs.to_date))

        records = self.env['account.analytic.line'].search(
            domain, order='project_id, task_id, date')

        # Group by project → task → entries
        projects = {}
        total_float = 0.0
        for rec in records:
            project_name = rec.project_id.name or '—'
            task_name = rec.task_id.name or '—'
            projects.setdefault(project_name, {})
            projects[project_name].setdefault(task_name, [])
            projects[project_name][task_name].append({
                'date': rec.date.strftime('%d/%m/%Y') if rec.date else '',
                'description': rec.name or '',
                'duration': _float_to_hhmm(rec.unit_amount),
                'duration_float': rec.unit_amount,
            })
            total_float += rec.unit_amount

        # Build structured list for the template
        project_list = []
        for project_name, tasks in projects.items():
            task_list = []
            project_total = 0.0
            for task_name, entries in tasks.items():
                task_total = sum(e['duration_float'] for e in entries)
                project_total += task_total
                task_list.append({
                    'name': task_name,
                    'entries': entries,
                    'total': _float_to_hhmm(task_total),
                })
            project_list.append({
                'name': project_name,
                'tasks': task_list,
                'total': _float_to_hhmm(project_total),
            })

        return project_list, _float_to_hhmm(total_float)

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['timesheet.report'].browse(
            self.env.context.get('active_id'))

        identification = []
        for rec in self.env['hr.employee'].search(
                [('user_id', '=', docs.user_id[0].id)]):
            identification.append({'id': rec.id, 'name': rec.name})

        projects, total = self.get_timesheets(docs)

        company_id = self.env['res.company'].search(
            [('name', '=', docs.user_id[0].company_id.name)])

        period = None
        if docs.from_date and docs.to_date:
            period = f"From {docs.from_date.strftime('%d/%m/%Y')} To {docs.to_date.strftime('%d/%m/%Y')}"
        elif docs.from_date:
            period = f"From {docs.from_date.strftime('%d/%m/%Y')}"
        elif docs.to_date:
            period = f"To {docs.to_date.strftime('%d/%m/%Y')}"

        return {
            'doc_ids': self.ids,
            'docs': docs,
            'projects': projects,
            'total': total,
            'identification': identification,
            'company': company_id,
            'period': period,
        }
