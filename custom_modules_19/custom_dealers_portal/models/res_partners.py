from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    dealer = fields.Many2one(
        'res.partner',          # model to select from
        string='Dealer',
        help='Select a dealer from existing contacts'
    )
    customer_ids = fields.One2many(
        'res.partner',        # target model
        'dealer',             # field on the target model
        string='Customers'
    )
    
    mobile_number = fields.Char(
        string='Mobile Number',
        help='Mobile phone number'
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

    def _dealer_portal_address_label(self):
        """Re-use the portal address formatting for invoice/delivery contacts.

        This is used by ``name_get`` override below so that fields like
        ``partner_invoice_id`` / ``partner_shipping_id`` on sale orders show
        the actual address (street / city / zip / country) instead of
        ``Parent, Invoice`` or ``Parent, Delivery`` when the child contact
        has no explicit name.
        """
        self.ensure_one()

        parts = []
        if self.street:
            parts.append(self.street)
        if getattr(self, "street2", False):
            parts.append(self.street2)
        if self.city:
            parts.append(self.city)
        if getattr(self, "state_id", False) and self.state_id:
            parts.append(self.state_id.name)
        if getattr(self, "zip", False) and self.zip:
            parts.append(self.zip)
        if getattr(self, "country_id", False) and self.country_id:
            parts.append(self.country_id.name)

        addr = ", ".join([p for p in parts if p])
        return addr or False

    def name_get(self):
        """Tweak display of invoice/delivery children without a name.

        For such records, we show the formatted address so that backend
        fields like partner_invoice_id / partner_shipping_id match what
        the dealer sees in the portal dropdowns.
        """
        # Build the standard name_get result manually to avoid super() issues
        res = []
        for partner in self:
            # Standard Odoo partner name_get logic
            name = partner.name or ''
            if not name:
                # For contacts without name, Odoo typically shows "Parent, Type"
                if partner.parent_id and partner.type:
                    name = "%s, %s" % (partner.parent_id.name or '', partner.type.title())
                elif partner.parent_id:
                    name = partner.parent_id.name or ''
                else:
                    name = partner.display_name or str(partner.id)
            res.append((partner.id, name))
        
        # Map id -> current name
        name_map = {pid: name for pid, name in res}

        override = {}
        for partner in self:
            # Check if it's an invoice/delivery contact without a meaningful name
            if partner.type in ("invoice", "delivery") and (not partner.name or not partner.name.strip()):
                label = partner._dealer_portal_address_label()
                if label:
                    override[partner.id] = label

        if not override:
            return res

        return [(pid, override.get(pid, name_map[pid])) for pid, _name in res]