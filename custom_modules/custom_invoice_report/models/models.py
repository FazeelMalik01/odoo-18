from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_invoice_qr_string(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for move in self:

            # direct report PDF URL (no token)
            qr_url = f"{base_url}/public/invoice/pdf/{move.id}"

            move.qr_text = qr_url

    qr_text = fields.Text(
        "QR Code Text",
        compute="_get_invoice_qr_string",
        store=False
    )