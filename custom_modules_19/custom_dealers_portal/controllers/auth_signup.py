from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
import logging

_logger = logging.getLogger(__name__)


class CustomAuthSignupHome(AuthSignupHome):
    """Override auth signup to add dealer signup link"""

    def _prepare_signup_qcontext(self, qcontext):
        """Add dealer signup link to context"""
        result = super()._prepare_signup_qcontext(qcontext)
        qcontext['show_dealer_signup'] = True
        return result
