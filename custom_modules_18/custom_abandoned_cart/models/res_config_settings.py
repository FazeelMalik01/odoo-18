import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    send_whatsapp_abandoned_cart = fields.Boolean(
        string="Automatically send abandoned checkout WhatsApp"
    )

    whatsapp_abandoned_cart_delay = fields.Integer(
        string="Send after",
        default=1
    )

    whatsapp_abandoned_cart_template_id = fields.Many2one(
        'whatsapp.template',
        string="Abandoned Cart Template",
        domain="[('model', '=', 'sale.order')]"
    )

    def set_values(self):
        super().set_values()
        config = self.env['ir.config_parameter'].sudo()

        # Save settings
        config.set_param(
            'website.send_whatsapp_abandoned_cart',
            self.send_whatsapp_abandoned_cart
        )

        config.set_param(
            'website.whatsapp_abandoned_cart_delay',
            self.whatsapp_abandoned_cart_delay
        )

        config.set_param(
            'website.whatsapp_abandoned_cart_template_id',
            self.whatsapp_abandoned_cart_template_id.id or False
        )

        # Sync cron interval with minutes delay
        cron = self.env.ref(
            'custom_abandoned_cart.ir_cron_whatsapp_abandoned_cart',
            raise_if_not_found=False
        )

        if cron:
            delay = max(1, self.whatsapp_abandoned_cart_delay)
            cron.write({
                'interval_number': delay,
                'interval_type': 'minutes',
            })
            _logger.info(
                "Updated cron interval to %s minutes.",
                delay
            )

    def get_values(self):
        res = super().get_values()
        config = self.env['ir.config_parameter'].sudo()

        template_id = config.get_param(
            'website.whatsapp_abandoned_cart_template_id'
        )

        res.update(
            send_whatsapp_abandoned_cart=
                config.get_param('website.send_whatsapp_abandoned_cart') == 'True',

            whatsapp_abandoned_cart_delay=int(
                config.get_param(
                    'website.whatsapp_abandoned_cart_delay',
                    default=1
                )
            ),

            whatsapp_abandoned_cart_template_id=
                int(template_id) if template_id else False,
        )
        return res