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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('res_model') in _EXPENSE_MODELS:
                self._check_expense_attachment_format(vals)
        return super().create(vals_list)

    @api.model
    def _check_expense_attachment_format(self, vals):
        """Reject expense attachments that are not a common, supported format.

        Validation uses both the declared mimetype and the file extension so
        that exotic formats (e.g. HEIC) are blocked even when the browser
        reports a generic mimetype.
        """
        name = vals.get('name') or ''
        mimetype = (vals.get('mimetype') or '').lower()

        # A binary file with no name/mimetype yet can't be validated here;
        # skip it (URL attachments, inline records, etc. are not receipts).
        if not name and not mimetype:
            return

        ext_ok = name.lower().endswith(_ALLOWED_EXTENSIONS)
        mime_ok = mimetype in _ALLOWED_MIMETYPES

        # Accept when either signal is a known-good format; reject only when a
        # signal is present and clearly unsupported.
        if ext_ok or mime_ok:
            return

        raise UserError(_(
            "Unsupported file format for '%s'. You can only attach PDF or "
            "standard image files (PDF, JPG, JPEG, PNG)."
        ) % (name or mimetype))
