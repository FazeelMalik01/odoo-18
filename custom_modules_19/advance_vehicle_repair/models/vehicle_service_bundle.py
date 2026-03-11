from odoo import fields, models, api

class AutoServiceBundle(models.Model):
    _name = 'auto.service.bundle'
    _description = "Auto Service Bundle"

    name = fields.Char(string="Bundle Name", required=True)

    line_ids = fields.One2many(
        'auto.service.bundle.line',
        'bundle_id',
        string="Bundle Lines"
    )

class AutoServiceBundleLine(models.Model):
    _name = 'auto.service.bundle.line'
    _description = "Auto Service Bundle Line"

    bundle_id = fields.Many2one(
        'auto.service.bundle',
        string="Bundle",
        ondelete="cascade"
    )

    type = fields.Selection([
        ('service', 'Service'),
        ('spare', 'Spare')
    ], string="Type", required=True, default='service')


    service_id = fields.Many2one(
        'vehicle.services',
        string="Service"
    )

    spare_id = fields.Many2one(
        'product.product',
        string="Spare Part",
        domain=[('spare_part','=',True)]
    )

    quantity = fields.Float(
        string="Quantity",
        default=1
    )

    @api.onchange('type')
    def _onchange_type(self):
        for line in self:
            if line.type == 'service':
                # Clear spare_id
                line.spare_id = False
            elif line.type == 'spare':
                # Clear service_id
                line.service_id = False