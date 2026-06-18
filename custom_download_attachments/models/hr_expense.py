from odoo import api, fields, models, _


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def attach_document(self, **kwargs):
        """Reject unsupported receipt uploads (Attach Receipt button).

        Validates every uploaded id (the core only forwards the last one to
        _message_set_main_attachment_id, so a non-last HEIC would slip through).
        """
        attachments = self.env['ir.attachment'].browse(
            kwargs.get('attachment_ids') or [])
        self.env['ir.attachment']._assert_expense_attachments_allowed(attachments)
        return super().attach_document(**kwargs)

    def _message_set_main_attachment_id(self, attachments, force=False, filter_xml=True):
        """Reject unsupported attachments at the exact point Odoo crashes.

        This is the single chokepoint reached by every path that sets a main
        attachment (Attach Receipt, chatter message_post, ...). The core does
        r.mimetype.endswith(...) which raises on a False mimetype (HEIC); we
        block such attachments here with a clear message instead.
        """
        self.env['ir.attachment']._assert_expense_attachments_allowed(attachments)
        return super()._message_set_main_attachment_id(
            attachments, force=force, filter_xml=filter_xml)

    @api.model
    def run_vacuum_cleaner(self):
        self.env['ir.attachment'].search([
            ('name', 'ilike', 'expense_report_%'),
            ('res_model', '=', False),
            ('mimetype', '=', 'application/pdf'),
            ('res_id', '=', False),
            ('type', '=', 'binary')
        ]).unlink()
