# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Customer display fields (readonly, with labels like Event information)
    partner_company_display = fields.Char(related='partner_id.commercial_company_name', string='Company', readonly=True)
    partner_email_display = fields.Char(related='partner_id.email', string='Email', readonly=True)
    partner_phone_display = fields.Char(related='partner_id.phone', string='Phone', readonly=True)
    partner_phone_secondary_display = fields.Char(related='partner_id.phone_secondary', string='Secondary Phone', readonly=True)
    partner_street_display = fields.Char(related='partner_id.street', string='Address', readonly=True)
    partner_street2_display = fields.Char(related='partner_id.street2', string='Address (cont.)', readonly=True)
    partner_city_display = fields.Char(related='partner_id.city', string='City', readonly=True)
    partner_state_id_display = fields.Many2one(related='partner_id.state_id', string='State', readonly=True)
    partner_zip_display = fields.Char(related='partner_id.zip', string='Zip/Postal code', readonly=True)
    partner_country_id_display = fields.Many2one(related='partner_id.country_id', string='Country', readonly=True)

    referrer_id = fields.Many2one('res.partner', string='Referrer', ondelete='set null')

    how_did_you_hear = fields.Selection(
        selection=[
            ('google_search', 'Google Search'),
            ('repeat_customer', 'Repeat Customer'),
            ('yardbash', 'Yardbash'),
            ('referral', 'Referral'),
            ('chat', 'Chat'),
            ('google_ad', 'Google Ad'),
            ('radio', 'Radio'),
            ('gig_salad', 'Gig Salad'),
            ('yelp', 'Yelp'),
            ('facebook', 'Facebook'),
            ('vehicle_graphic', 'Vehicle Graphic'),
            ('kazzam', 'Kazzam'),
            ('kidzaustin', 'Kidzaustin'),
            ('bing', 'Bing'),
            ('instagram', 'Instagram'),
            ('livemom', 'Livemom'),
            ('web_search_not_google', 'Web Search (not Google)'),
            ('sign', 'Sign'),
            ('printed_ad', 'Printed Ad'),
            ('groupon', 'Groupon'),
            ('yellow_pages', 'Yellow pages'),
        ],
        string='How did you hear about us',
    )

    event_location_name = fields.Char(string='Location name')
    event_same_as_billing = fields.Boolean(string='Same as billing', default=False)
    event_street = fields.Char(string='Address')
    event_street2 = fields.Char(string='Address (cont.)')
    event_city = fields.Char(string='City')
    event_state_id = fields.Many2one(
        'res.country.state',
        string='State',
        ondelete='restrict',
        domain="[('country_id', '=?', event_country_id)]",
    )
    event_zip = fields.Char(string='Zip/Postal code')
    event_zip_verification_id = fields.Many2one(
        'rental.zipcode',
        string='Zip verification',
        ondelete='set null',
        help='Select a zip code from the configuration list. Must match the EVENT zip code, not the billing zip code.',
    )
    event_type = fields.Char(string='Type of event')
    damage_waiver = fields.Selection(
        selection=[
            ('yes', 'Yes - I want to be protected against accidental damage (10%)'),
            ('no', 'No - I will take full responsibility for accidental, intentional, & theft during my rental period'),
        ],
        string='Damage waiver',
        default='yes',
    )
    event_location = fields.Selection(
        selection=[
            ('no', 'No'),
            ('yes_20', 'Yes ($20)'),
        ],
        string='Event location',
    )
    event_country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')

    # Additional information – required acknowledgments
    additional_weather_policy_agreed = fields.Boolean(
        string='I agree to the weather and payment policy above',
        required=True,
    )
    additional_setup_terms_agreed = fields.Boolean(
        string='I agree to the setup and electrical terms above',
        required=True,
    )

    setup_surface = fields.Selection(
        selection=[
            ('grass', 'Grass'),
            ('dirt', 'Dirt'),
            ('indoor', 'Indoor'),
            ('concrete_no_charge', 'Concrete (No Charge) ($0.00)'),
            ('asphalt_35', 'Asphalt ($35.00)'),
            ('concrete_35', 'Concrete ($35.00)'),
            ('turf_35', 'Turf ($35.00)'),
            ('drive_in_movie_asphalt_100', 'Drive In Movie Asphalt ($100.00)'),
        ],
        string='Setup surface',
    )
    general_discount = fields.Float(string='General Discount')
    internal_notes = fields.Text(string='Internal Notes')
    override_travel_fee = fields.Monetary(string='Override Travel Fee', currency_field='currency_id')
    override_deposit_amount = fields.Monetary(string='Override Deposit Amount', currency_field='currency_id')
    override_tax_amount = fields.Monetary(string='Override Tax Amount', currency_field='currency_id')
    miscellaneous_fees = fields.Monetary(string='Miscellaneous Fees', currency_field='currency_id')

    def _sync_event_address_from_partner(self):
        """Copy partner address to event address when Same as billing is checked (used in onchange and write)."""
        if self.event_same_as_billing and self.partner_id:
            self.event_street = self.partner_id.street
            self.event_street2 = self.partner_id.street2
            self.event_city = self.partner_id.city
            self.event_state_id = self.partner_id.state_id
            self.event_zip = self.partner_id.zip
            self.event_country_id = self.partner_id.country_id
        elif not self.event_same_as_billing:
            self.event_street = False
            self.event_street2 = False
            self.event_city = False
            self.event_state_id = False
            self.event_zip = False
            self.event_country_id = False

    @api.onchange('event_same_as_billing', 'partner_id')
    def _onchange_event_same_as_billing(self):
        self._sync_event_address_from_partner()

    @api.model_create_multi
    def create(self, vals_list):
        """When creating with Same as billing checked, fill event address from partner if not provided."""
        for vals in vals_list:
            if vals.get('event_same_as_billing') and vals.get('partner_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                if partner and 'event_street' not in vals:
                    vals.update({
                        'event_street': partner.street,
                        'event_street2': partner.street2,
                        'event_city': partner.city,
                        'event_state_id': partner.state_id.id if partner.state_id else False,
                        'event_zip': partner.zip,
                        'event_country_id': partner.country_id.id if partner.country_id else False,
                    })
        return super().create(vals_list)

    def write(self, vals):
        """When saving with Same as billing checked, ensure event address is synced from partner (readonly fields may not be sent)."""
        if len(self) == 1 and self.event_same_as_billing and self.partner_id:
            # Readonly event address fields may not be in the save payload; inject from partner so they persist
            if 'event_street' not in vals:
                vals = dict(vals)
                vals.update({
                    'event_street': self.partner_id.street,
                    'event_street2': self.partner_id.street2,
                    'event_city': self.partner_id.city,
                    'event_state_id': self.partner_id.state_id.id if self.partner_id.state_id else False,
                    'event_zip': self.partner_id.zip,
                    'event_country_id': self.partner_id.country_id.id if self.partner_id.country_id else False,
                })
        return super().write(vals)

    def action_confirm(self):
        """Require Additional information checkboxes to be agreed before confirming."""
        for order in self:
            if not order.additional_weather_policy_agreed:
                raise UserError(
                    'You must agree to the weather and payment policy (rain check / refunds) before confirming the order.'
                )
            if not order.additional_setup_terms_agreed:
                raise UserError(
                    "You must agree to the setup and electrical terms (rock/gravel, circuits, 50' ft electricity) before confirming the order."
                )
        return super().action_confirm()
