from odoo import models, fields

class Employee(models.Model):
    _inherit = "hr.employee"

    remote_plus_code = fields.Char(
        string="Remote Work Plus Code",
        help="Plus Code for precise remote work attendance",
        groups="hr.group_hr_user"  # Restrict to HR users
    )

