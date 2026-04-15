from odoo import http
from odoo.http import request


class PortalCatalogSecurity(http.Controller):
    """Protect public access to product catalog pages on the website.

    All attempts to access the standard /shop or product pages as a public user
    are redirected to the login page. Logged-in users are redirected to the
    dealer portal dashboard instead of the public catalog.
    """

    @http.route(
        [
            "/shop",
            "/shop/<path:subpath>",
            "/product/<model('product.template'):product>",
            "/product/<model('product.template'):product>/<path:subpath>",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def protect_public_catalog(self, **kwargs):
        # If the visitor is not logged in, force them to the login page.
        if request.env.user._is_public():
            # After login, send them to the dealer portal dashboard.
            return request.redirect("/web/login?redirect=/my")

        # Logged-in users: send them to the dealer portal dashboard instead
        # of showing the public catalog.
        return request.redirect("/my")

