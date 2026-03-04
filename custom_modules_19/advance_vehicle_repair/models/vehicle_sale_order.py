from odoo import models, fields, api, _

class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    jobcard_id = fields.Many2one('vehicle.jobcard', string='Job Card')

