from odoo import http
from odoo.http import request
import werkzeug.exceptions


class DownloadAttachmentController(http.Controller):

    @http.route('/download/expense_attachments', type='http', auth='user')
    def download_expense_attachments(self, active_ids=None):
        # --- Authorization: only Expense Managers may use this endpoint ---
        if not request.env.user.has_group('hr_expense.group_hr_expense_manager'):
            raise werkzeug.exceptions.Forbidden()

        if not active_ids:
            raise werkzeug.exceptions.NotFound()

        try:
            parsed_ids = [int(i) for i in active_ids.split(',')]
        except (ValueError, AttributeError):
            raise werkzeug.exceptions.BadRequest()

        # Use search() instead of browse() so that ir.rules are enforced.
        # Records the current user cannot access are silently excluded.
        expense_reports = request.env['hr.expense.sheet'].search(
            [('id', 'in', parsed_ids)]
        )

        if not expense_reports:
            raise werkzeug.exceptions.NotFound()

        # Build filename from the first report (already access-checked)
        report = expense_reports[0]
        employee_name = report.employee_id.name
        report_id = report.id
        filename = f"Expense Report - {employee_name} - {report_id}.pdf"

        # Generate the merged PDF through the wizard
        wizard = request.env['download_exp_attachment'].create({})
        pdf_data = wizard.with_context(active_ids=parsed_ids).generate_pdf_data()

        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ]
        return request.make_response(pdf_data, headers=headers)
