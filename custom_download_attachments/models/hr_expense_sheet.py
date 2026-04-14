import base64
import io
import logging

from odoo import fields, models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

_logger = logging.getLogger(__name__)


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    date_approve = fields.Date(
        string='Approval Date',
        readonly=True,
    )

    def write(self, vals):
        """Set date_approve automatically when state changes to 'approve'."""
        if vals.get('state') == 'approve':
            vals.setdefault('date_approve', fields.Date.today())
        return super().write(vals)

    def action_print_expense_report(self):
        """
        Print a single merged PDF:
          1. Custom expense sheet report (with ID + Approval Date)
          2. All expense line attachments (PDFs / images) appended after
        """
        self.ensure_one()

        # ── 1. Render the custom expense report PDF ───────────────────────────
        report = self.env.ref(
            'custom_download_attachments.action_report_expense_sheet_martel'
        )
        pdf_report, _ = self.env['ir.actions.report']._render_qweb_pdf(
            report.report_name, self.ids
        )

        writer = OdooPdfFileWriter()

        report_reader = OdooPdfFileReader(io.BytesIO(pdf_report), strict=False)
        for page in report_reader.pages:
            writer.add_page(page)

        # ── 2. Append attachment pages (graceful: skip if none) ───────────────
        try:
            wizard = self.env['download_exp_attachment'].create({})
            pdf_atts = wizard.with_context(active_ids=[self.id]).generate_pdf_data()
            att_reader = OdooPdfFileReader(io.BytesIO(pdf_atts), strict=False)
            for page in att_reader.pages:
                writer.add_page(page)
        except Exception as exc:
            _logger.info(
                'No attachments to merge for expense sheet %s: %s', self.id, exc
            )

        # ── 3. Write merged PDF ───────────────────────────────────────────────
        merged_buf = io.BytesIO()
        writer.write(merged_buf)
        merged_buf.seek(0)

        employee = (self.employee_id.name or 'employee').replace('/', '-')
        filename = f"Expense_Report_{employee}_{self.id}.pdf"

        # Temporary attachment (no res_model → cleaned up by vacuum)
        temp_att = self.env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(merged_buf.getvalue()),
            'res_model': False,
            'res_id': False,
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{temp_att.id}/{filename}?download=true',
            'target': 'new',
        }

    def action_download_attachments_pdf(self):
        """Download all expense attachments merged into a single PDF."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/download/expense_attachments?active_ids={self.id}',
            'target': 'new',
        }
