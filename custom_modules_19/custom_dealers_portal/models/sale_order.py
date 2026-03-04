from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dealer = fields.Many2one(
        'res.partner',
        string='Dealer',
        help='Dealer who created this order from portal'
    )
    
    shipping_option_dropship = fields.Selection(
        [
            ('rate_quote', 'Provide a rate quote before shipping'),
            ('cheapest_rate', 'Please ship at cheapest rate'),
            ('own_carrier', 'Client will use their own carrier'),
            ('client_pickup', 'Client will pickup'),
            ('yannick_pickup', 'Yannick will pickup this order'),
            ('dhc_courier', 'Ship with DHC\'s courier and add cost to invoice'),
        ],
        string='Shipping Option for Dropship',
        help='Shipping option preference for dropship orders'
    )