from odoo import models, fields

class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'

    discount_type = fields.Selection(
        selection=[
            ('sol_discount', "On All Order Lines"),
        ],
        default='sol_discount',
    )
