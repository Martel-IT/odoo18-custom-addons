from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        result["web_base_url"] = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )
        return result
