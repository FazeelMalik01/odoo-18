from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    phone_secondary = fields.Char(string='Secondary Phone')
    last_name = fields.Char(string='Last Name')
    partner_latitude  = fields.Float(
        string="Geo Latitude",
        digits=(10, 7),
        help="Latitude of the partner's address (populated by Mapbox autocomplete).",
    )
    partner_longitude = fields.Float(
        string="Geo Longitude",
        digits=(10, 7),
        help="Longitude of the partner's address (populated by Mapbox autocomplete).",
    )

    rental_order_count = fields.Integer(
        string='Event Bookings',
        compute='_compute_rental_order_count',
    )

    @api.depends_context('company')
    def _compute_rental_order_count(self):
        domain = [('is_rental_order', '=', True), ('partner_id', 'child_of', self.ids)]
        grouped = self.env['sale.order'].read_group(
            domain, ['partner_id'], ['partner_id']
        )
        counts = {g['partner_id'][0]: g['partner_id_count'] for g in grouped}
        for partner in self:
            partner.rental_order_count = counts.get(partner.id, 0)

    def action_open_rental_bookings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'rental_pos_page',
            'name': 'Event Booking',
            'context': {
                'rental_pos_partner_id': self.id,
            },
        }
