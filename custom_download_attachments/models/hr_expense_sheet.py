import base64
import io
import logging

from odoo import api, fields, models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

_logger = logging.getLogger(__name__)


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    date_approve = fields.Date(
        string='Approval Date',
        compute='_compute_date_approve',
        # store=False → no DB column, works immediately without module upgrade
    )

    @api.depends('state', 'message_ids.tracking_value_ids')
    def _compute_date_approve(self):
        """
        Read the approval date from the chatter: find the first tracking message
        where the 'state' field was set to 'approve' (label contains 'approv').
        Falls back to False if no such message exists.
        """
        for sheet in self:
            approval_date = False
            if sheet.state in ('approve', 'post', 'done'):
                for msg in sheet.message_ids.sorted('date'):
                    for tv in msg.tracking_value_ids:
                        field_name = tv.field_id.name if tv.field_id else ''
                        new_val = (tv.new_value_char or '').lower()
                        if field_name == 'state' and 'approv' in new_val:
                            approval_date = msg.date.date()
                            break
                    if approval_date:
                        break
            sheet.date_approve = approval_date

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
