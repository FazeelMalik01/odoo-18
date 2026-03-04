from odoo import models, fields

class AccountMove(models.Model):
    _inherit = "account.move"

    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        help="Vendor related to this invoice."
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        help="Link this invoice to a specific project."
    )
