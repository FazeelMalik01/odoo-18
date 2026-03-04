from odoo import fields, models, api

class VehicleBrand(models.Model):
    _name = 'vehicle.brand'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Vehicle Brands"

    name = fields.Char(string="Name", tracking=True, required=True)
    image = fields.Image(
        string="Image", max_width=128, max_height=128,
        help="This field holds the image used for this brand, limited to 128x128 px")
