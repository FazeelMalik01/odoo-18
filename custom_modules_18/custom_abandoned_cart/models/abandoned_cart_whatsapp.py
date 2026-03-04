import logging
from datetime import timedelta
from odoo import models, fields

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    whatsapp_abandoned_sent = fields.Boolean(default=False)

    def _cron_send_abandoned_cart_whatsapp(self):
        _logger.info("=== WhatsApp Abandoned Cart Cron Started ===")

        config = self.env['ir.config_parameter'].sudo()

        # Boolean stored as string
        enabled = config.get_param(
            'website.send_whatsapp_abandoned_cart'
        ) == 'True'

        if not enabled:
            _logger.info("WhatsApp abandoned cart is disabled.")
            return

        # Delay stored in HOURS (as per your settings UI)
        delay_hours = int(config.get_param(
            'website.whatsapp_abandoned_cart_delay',
            default=1
        ))

        threshold_time = fields.Datetime.now() - timedelta(hours=delay_hours)

        # Get configured template
        template_id = config.get_param(
            'website.whatsapp_abandoned_cart_template_id'
        )

        if not template_id:
            _logger.error("No WhatsApp template configured in settings.")
            return

        template = self.env['whatsapp.template'].browse(int(template_id))

        if not template.exists():
            _logger.error("Configured WhatsApp template not found.")
            return

        _logger.info("Using WhatsApp template: %s", template.name)

        # Use write_date for inactivity logic (more accurate than date_order)
        abandoned_orders = self.search([
            ('website_id', '!=', False),
            ('state', '=', 'draft'),
            ('write_date', '<=', threshold_time),
            ('whatsapp_abandoned_sent', '=', False),
            ('partner_id', '!=', False),
        ])

        _logger.info("Found %s abandoned carts.", len(abandoned_orders))

        for order in abandoned_orders:
            partner = order.partner_id

            phone = partner.mobile or partner.phone
            if not phone:
                _logger.warning(
                    "Order %s skipped: No phone number.",
                    order.name
                )
                continue

            try:
                template.send_message(order.id)

                order.whatsapp_abandoned_sent = True

                _logger.info(
                    "WhatsApp sent for order %s to %s",
                    order.name,
                    phone
                )

            except Exception as e:
                _logger.exception(
                    "Failed sending WhatsApp for order %s: %s",
                    order.name,
                    str(e)
                )

        _logger.info("=== WhatsApp Abandoned Cart Cron Finished ===")