from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    per_hour_rate = fields.Float(
        string="Per hour Rate",
        help="Rate charged for every extra hour"
    )

    minimum_booking_hrs = fields.Float(
        string="Minimum Booking Hours",
        help="Minimum number of hours required for booking"
    )

    base_hrs = fields.Float(
        string="Base Hours",
        help="Hours included in the standard price. Booking within this time will not incur extra charges; additional time will be charged separately."
    )