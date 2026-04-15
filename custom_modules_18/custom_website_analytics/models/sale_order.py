# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Inject website analytic account into order lines on confirmation."""
        result = super().action_confirm()
        for order in self:
            website = order.website_id
            _logger.info("ANALYTIC DEBUG: order=%s website=%s analytic=%s",
                         order.name, website, website.analytic_account_id if website else None)
            if website and website.analytic_account_id:
                analytic_distribution = {str(website.analytic_account_id.id): 100.0}
                for line in order.order_line:
                    _logger.info("ANALYTIC DEBUG: Setting analytic_distribution=%s on line %s",
                                 analytic_distribution, line)
                    line.sudo().write({'analytic_distribution': analytic_distribution})
        return result