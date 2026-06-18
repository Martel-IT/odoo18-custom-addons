from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def attach_document(self, **kwargs):
        """Validate receipt format before Odoo sets it as the main attachment.

        Receipts are uploaded as 'pending' attachments (res_model
        'mail.compose.message', mimetype possibly False for formats Odoo can't
        recognise like HEIC). The core attach_document then calls
        _message_set_main_attachment_id, which does r.mimetype.endswith(...) and
        crashes on a False mimetype. We reject anything that is not clearly a
        supported PDF/image here, before that happens — including attachments
        with an empty mimetype (exactly the HEIC case), which must be blocked
        rather than skipped.
        """
        attachments = self.env['ir.attachment'].browse(
            kwargs.get('attachment_ids') or [])
        bad = attachments.filtered(
            lambda a: not self.env['ir.attachment']._is_allowed_expense_format(
                a.name, a.mimetype))
        if bad:
            raise UserError(_(
                "Unsupported file format for '%s'. You can only attach PDF or "
                "standard image files (PDF, JPG, JPEG, PNG)."
            ) % ', '.join(b.name or b.mimetype or _('unknown') for b in bad))
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
