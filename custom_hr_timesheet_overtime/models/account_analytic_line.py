from odoo import models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def button_delete_from_sheet(self):
        """Immediately unlink this entry from its sheet and reload the form.

        Unlike the standard one2many delete (which is pending until the parent
        form is saved), this button commits the removal to DB right away so
        that subsequent onchange calls cannot restore the deleted row.
        """
        sheet = self.sheet_id
        self._check_state()
        self.unlink()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr_timesheet.sheet",
            "res_id": sheet.id,
            "view_mode": "form",
            "target": "current",
        }
