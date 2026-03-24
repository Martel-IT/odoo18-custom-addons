from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def action_print_expense_report(self):
        """Print the standard Odoo expense sheet report."""
        self.ensure_one()
        return self.env.ref('hr_expense.action_report_hr_expense_sheet').report_action(self)

    def action_download_attachments_pdf(self):
        """Download all expense attachments merged into a single PDF."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/download/expense_attachments?active_ids={self.id}',
            'target': 'new',
        }
