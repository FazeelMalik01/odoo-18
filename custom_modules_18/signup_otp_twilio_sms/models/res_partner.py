# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software PVT. LTD.
# See LICENSE file for full copyright & licensing details.

from odoo import models, fields
import random
import logging

_logger = logging.getLogger(__name__)


def random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.SystemRandom().choice(chars) for _ in range(20))


class ResPartner(models.Model):
    """Inherited res.partner for new field and functions"""

    _inherit = "res.partner"
    # New field
    custom_signup_url = fields.Char(
        compute="compute_custom_signup_url", string="Custom Signup URL"
    )

    def compute_custom_signup_url(self):
        """proxy for function field towards actual implementation with debug logging"""        
        result = self.sudo()._get_signup_url_for_action()
        
        for partner in self:
            user_ids = partner.user_ids
            if any(u.has_group("base.group_user") for u in user_ids if u != self.env.user):
                self.env["res.users"].check_access_rights("write")    
            partner.custom_signup_url = result.get(partner.id, False)


    def signup_custom_prepare(self, signup_type="reset", expiration=False):
        """
        generate a new token for the partners with the given validity,
        if necessary
        :param expiration: the expiration datetime of the token
        (string, optional)
        """
        for partner in self:
            partner.write(
                {
                    "signup_type": "reset",
                }
            )
        return True
