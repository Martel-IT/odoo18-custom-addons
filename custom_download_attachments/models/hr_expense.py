from odoo import api, fields, models, _

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def attach_document(self, **kwargs):
        """Validate receipt format before Odoo sets it as the main attachment.

        Receipts are uploaded as 'pending' attachments (res_model
        'mail.compose.message', mimetype possibly False for formats Odoo can't
        recognise like HEIC). The core attach_document then calls
        _message_set_main_attachment_id, which does r.mimetype.endswith(...) and
        crashes on a False mimetype. We reject unsupported formats here, before
        that happens, so the user gets a clear message instead of a server error.
        """
        attachments = self.env['ir.attachment'].browse(
            kwargs.get('attachment_ids') or [])
        for att in attachments:
            self.env['ir.attachment']._assert_allowed_expense_format(
                att.name, att.mimetype)
        return super().attach_document(**kwargs)

    @api.model
    def run_vacuum_cleaner(self):
        self.env['ir.attachment'].search([
            ('name', 'ilike', 'expense_report_%'),
            ('res_model', '=', False),
            ('mimetype', '=', 'application/pdf'),
            ('res_id', '=', False),
            ('type', '=', 'binary')
        ]).unlink()
