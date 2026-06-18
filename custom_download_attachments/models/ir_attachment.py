from odoo import api, models, _
from odoo.exceptions import UserError

# Models whose attachments are merged into the printed expense PDF.
_EXPENSE_MODELS = ('hr.expense', 'hr.expense.sheet')

# Only common formats we can actually render into the merged PDF are allowed.
# Keep this in sync with the converter in download_attachments.py.
_ALLOWED_MIMETYPES = {
    'application/pdf',
    'image/jpeg',
    'image/jpg',
    'image/png',
}
_ALLOWED_EXTENSIONS = ('.pdf', '.jpg', '.jpeg', '.png')


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _is_allowed_expense_format(self, name, mimetype):
        """Return True if an expense attachment is a supported PDF/image format.

        Checks both the file extension and the mimetype, because Odoo cannot
        guess the mimetype of exotic formats (e.g. HEIC) and stores it as
        ``False`` — which later crashes the core main-attachment logic on
        ``r.mimetype.endswith(...)``.
        """
        name = (name or '').lower()
        mimetype = (mimetype or '').lower()
        return name.endswith(_ALLOWED_EXTENSIONS) or mimetype in _ALLOWED_MIMETYPES

    @api.model
    def _assert_allowed_expense_format(self, name, mimetype):
        """Raise a clear error if an expense attachment is an unsupported format."""
        # Nothing to validate yet (URL attachments, inline records, ...).
        if not name and not mimetype:
            return
        if self._is_allowed_expense_format(name, mimetype):
            return
        raise UserError(_(
            "Unsupported file format for '%s'. You can only attach PDF or "
            "standard image files (PDF, JPG, JPEG, PNG)."
        ) % (name or mimetype))

    @api.model
    def _assert_expense_attachments_allowed(self, attachments):
        """Raise if any record in `attachments` is not a supported expense format.

        Strict (no early-return on empty mimetype): an attachment Odoo cannot
        identify — e.g. HEIC, stored with mimetype=False — is exactly what must
        be rejected, since it later crashes _message_set_main_attachment_id.
        """
        bad = attachments.filtered(
            lambda a: not self._is_allowed_expense_format(a.name, a.mimetype))
        if bad:
            raise UserError(_(
                "Unsupported file format for '%s'. You can only attach PDF or "
                "standard image files (PDF, JPG, JPEG, PNG)."
            ) % ', '.join(b.name or b.mimetype or _('unknown') for b in bad))

    @api.model_create_multi
    def create(self, vals_list):
        # Covers attachments created directly against an expense (non-pending
        # uploads). Pending uploads land here as 'mail.compose.message' and are
        # validated later, when linked to the expense via attach_document.
        for vals in vals_list:
            if vals.get('res_model') in _EXPENSE_MODELS:
                self._assert_allowed_expense_format(
                    vals.get('name'), vals.get('mimetype'))
        return super().create(vals_list)
