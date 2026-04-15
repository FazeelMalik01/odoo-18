from odoo import fields, models, api

class VehicleServices(models.Model):
    _name = 'vehicle.services'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Vehicle Services"

    name = fields.Char(string="Name", required=True, tracking=True)
    product_id = fields.Many2one('product.product',string='Product')
    service_team_id=fields.Many2one('vehicle.teams', string="Service Team")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True, tracking=True)
    service_amount = fields.Float(string="Service Charge", required=True, tracking=True)
    colr_picker = fields.Integer(string="color", tracking=True)
    is_recurring = fields.Boolean(string="Recurring", tracking=True)
    recurring_days = fields.Integer(string="Days After", help="Number of days after which service repeats")
    estimated_time = fields.Float( string="Estimated Time", help="Estimated service duration")


    @api.model
    def create(self, vals):
        # Create the service record first
        record = super(VehicleServices, self).create(vals)

        # Automatically create product if not already linked
        if not record.product_id:
            product = self.env['product.product'].create({
                'name': record.name,
                'type': 'service',
                'lst_price': record.service_amount,
                'created_from_service': True,
            })
            record.product_id = product.id

        return record

    def write(self, vals):
        res = super(VehicleServices, self).write(vals)

        # Update linked product if name or service_amount changed
        for record in self:
            if record.product_id:
                update_vals = {}
                if 'name' in vals:
                    update_vals['name'] = record.name
                if 'service_amount' in vals:
                    update_vals['lst_price'] = record.service_amount
                if update_vals:
                    record.product_id.write(update_vals)

        return res