from odoo import models, fields

class VehicleKilometerLog(models.Model):
    _name = 'vehicle.kilometer.log'
    _description = "Vehicle Kilometer Log"
    _order = "date desc, id desc"

    vehicle_id = fields.Many2one(
        'vehicle.register',
        string="Vehicle",
        required=True,
        ondelete='cascade'
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        readonly=True
    )

    kilometer = fields.Float(
        string="Kilometer",
        required=True,
        readonly=True
    )