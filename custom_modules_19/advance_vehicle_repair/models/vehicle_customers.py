from odoo import fields, models, api

class VehicleCustomers(models.Model):
    _inherit = 'res.partner'

    count = fields.Integer(string="Bookings", compute='_compute_booking_count')

    def _compute_booking_count(self):
        for record in self:
            record.count=self.env['vehicle.booking'].search_count([('customer_id', '=', record.id)])

    def action_view_bookings(self):
        self.ensure_one()
        return {
            'name': 'Bookings',
            'view_mode': 'list,form',
            'res_model': 'vehicle.booking',
            'domain': [('customer_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'view_id': False,
            'target': 'current',
        }

