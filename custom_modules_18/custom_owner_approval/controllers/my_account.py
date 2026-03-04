import base64

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class OwnerPortalAccount(CustomerPortal):
    """Extend the standard portal account controller to handle owner signatures."""

    def _get_optional_fields(self):
        """Allow the owner signature field to pass through validation."""
        optional_fields = super()._get_optional_fields()
        if 'owner_signature' not in optional_fields:
            optional_fields.append('owner_signature')
        return optional_fields

    def on_account_update(self, values, partner):
        """Persist the uploaded signature on the portal user."""
        # Prevent unknown-field errors during the partner write.
        values.pop('owner_signature', None)

        signature_file = request.httprequest.files.get('owner_signature')
        if signature_file and signature_file.filename:
            user = request.env.user.sudo()
            if hasattr(user, 'sign_signature'):
                signature_content = signature_file.read()
                if signature_content:
                    user.write({
                        'sign_signature': base64.b64encode(signature_content),
                    })

        return super().on_account_update(values, partner)
