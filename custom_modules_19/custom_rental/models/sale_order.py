# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import copy
import json
import logging
import secrets
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ui_booking_status = fields.Selection(
        selection=[
            ("quote", "Quote"),
            ("booked", "Booked"),
        ],
        string="Status",
        compute="_compute_ui_booking_status",
        store=False,
    )

    ui_sales_health = fields.Selection(
        selection=[
            ("green", "Green"),
            ("yellow", "Yellow"),
            ("red", "Red"),
        ],
        string="Sales Health",
        compute="_compute_ui_sales_health",
        store=True,
        readonly=True,
        help="Rental list health: green when deposit, final invoice, and pre-event call are complete.",
    )

    pre_event_call_confirmed = fields.Boolean(
        string="Pre-event call confirmed",
        default=True,
        help="If unchecked, rental list shows a follow-up in Action Needed (when payments are otherwise complete).",
    )

    ui_action_needed = fields.Char(
        string="Action Needed",
        compute="_compute_ui_action_needed",
        store=True,
        readonly=True,
    )
    ui_action_needed_level = fields.Selection(
        selection=[
            ("green", "Green"),
            ("yellow", "Yellow"),
            ("red", "Red"),
        ],
        string="Action Needed Level",
        compute="_compute_ui_action_needed",
        store=True,
        readonly=True,
    )

    rental_calendar_title = fields.Char(
        string="Calendar label",
        compute="_compute_rental_calendar_display",
    )
    rental_calendar_color_hex = fields.Char(
        string="Calendar color",
        compute="_compute_rental_calendar_display",
    )

    # Customer display fields (readonly, with labels like Event information)
    partner_company_display = fields.Char(
        related="partner_id.commercial_company_name", string="Company", readonly=False
    )
    partner_email_display = fields.Char(
        related="partner_id.email", string="Email", readonly=False
    )
    partner_phone_display = fields.Char(
        related="partner_id.phone", string="Phone", readonly=False
    )
    partner_phone_secondary_display = fields.Char(
        related="partner_id.phone_secondary", string="Secondary Phone", readonly=False
    )
    partner_street_display = fields.Char(
        related="partner_id.street", string="Address", readonly=False
    )
    partner_street2_display = fields.Char(
        related="partner_id.street2", string="Address (cont.)", readonly=False
    )
    partner_city_display = fields.Char(
        related="partner_id.city", string="City", readonly=False
    )
    partner_state_id_display = fields.Many2one(
        related="partner_id.state_id", string="State", readonly=False
    )
    partner_zip_display = fields.Char(
        related="partner_id.zip", string="Zip/Postal code", readonly=False
    )
    partner_country_id_display = fields.Many2one(
        related="partner_id.country_id", string="Country", readonly=False
    )

    referrer_id = fields.Many2one("res.partner", string="Referrer", ondelete="set null")

    how_did_you_hear = fields.Selection(
        selection=[
            ("google_search", "Google Search"),
            ("repeat_customer", "Repeat Customer"),
            ("yardbash", "Yardbash"),
            ("referral", "Referral"),
            ("chat", "Chat"),
            ("google_ad", "Google Ad"),
            ("radio", "Radio"),
            ("gig_salad", "Gig Salad"),
            ("yelp", "Yelp"),
            ("facebook", "Facebook"),
            ("vehicle_graphic", "Vehicle Graphic"),
            ("kazzam", "Kazzam"),
            ("kidzaustin", "Kidzaustin"),
            ("bing", "Bing"),
            ("instagram", "Instagram"),
            ("livemom", "Livemom"),
            ("web_search_not_google", "Web Search (not Google)"),
            ("sign", "Sign"),
            ("printed_ad", "Printed Ad"),
            ("groupon", "Groupon"),
            ("yellow_pages", "Yellow pages"),
        ],
        string="How did you hear about us",
    )

    event_location_name = fields.Char(string="Location name")
    event_same_as_billing = fields.Boolean(string="Same as billing", default=False)
    event_street = fields.Char(string="Address")
    event_street2 = fields.Char(string="Address (cont.)")
    event_city = fields.Char(string="City")
    event_state_id = fields.Many2one(
        "res.country.state",
        string="State",
        ondelete="restrict",
        domain="[('country_id', '=?', event_country_id)]",
    )
    event_zip = fields.Char(string="Zip/Postal code")
    event_zip_verification_id = fields.Many2one(
        "rental.zipcode",
        string="Zip verification",
        compute="_compute_event_zip_verification_id",
        store=True,
        readonly=True,
        ondelete="set null",
        help="Matching zip code record from configuration (checked automatically from EVENT zip).",
    )
    event_zip_verification_status = fields.Selection(
        selection=[
            ("available", "Available"),
            ("not_available", "Not available"),
        ],
        string="Zip verification",
        compute="_compute_event_zip_verification_status",
        store=False,
    )
    event_type = fields.Selection(
        selection=[
            ("birthdays", "Birthdays"),
            ("hoa_community", "HOA & Community"),
            ("school_church_youth", "School, Church & Youth"),
            ("company_team", "Company & Team"),
            ("other", "Other"),
        ],
        string="Type of event",
        help="Type of Event? Birthday Party - Age of guests? Wedding, Bachelor Party, Corporate, School, etc.",
    )
    damage_waiver = fields.Selection(
        selection=[
            ("yes", "Yes - I want to be protected against accidental damage (10%)"),
            (
                "no",
                "No - I will take full responsibility for accidental, intentional, & theft during my rental period",
            ),
        ],
        string="Damage waiver",
        default="yes",
    )
    event_location = fields.Selection(
        selection=[
            ("no", "No"),
            ("yes_20", "Yes ($20)"),
        ],
        string="Event location",
    )
    event_country_id = fields.Many2one(
        "res.country", string="Country", ondelete="restrict"
    )

    # Additional information – required acknowledgments
    additional_weather_policy_agreed = fields.Boolean(
        string="I agree to the weather and payment policy above",
        required=True,
    )
    additional_setup_terms_agreed = fields.Boolean(
        string="I agree to the setup and electrical terms above",
        required=True,
    )

    setup_surface = fields.Selection(
        selection=[
            ("grass", "Grass"),
            ("dirt", "Dirt"),
            ("indoor", "Indoor"),
            ("concrete_no_charge", "Concrete (No Charge) ($0.00)"),
            ("asphalt_35", "Asphalt ($35.00)"),
            ("concrete_35", "Concrete ($35.00)"),
            ("turf_35", "Turf ($35.00)"),
            ("drive_in_movie_asphalt_100", "Drive In Movie Asphalt ($100.00)"),
        ],
        string="Setup surface",
    )
    general_discount = fields.Float(string="General Discount")
    internal_notes = fields.Text(string="Internal Notes")
    customer_notes = fields.Text(string="Customer Notes")
    override_travel_fee = fields.Monetary(
        string="Override Travel Fee", currency_field="currency_id"
    )
    override_deposit_amount = fields.Monetary(
        string="Override Deposit Amount", currency_field="currency_id"
    )
    override_tax_amount = fields.Monetary(
        string="Override Tax Amount", currency_field="currency_id"
    )
    miscellaneous_fees = fields.Monetary(
        string="Miscellaneous Fees", currency_field="currency_id"
    )
    tip = fields.Monetary(
        string="tip", currency_field="currency_id"
    )
    event_latitude  = fields.Float(
        string="Event Latitude",
        digits=(10, 7),
        help="Latitude of the event address (populated by Mapbox autocomplete in Rental POS).",
    )
    event_longitude = fields.Float(
        string="Event Longitude",
        digits=(10, 7),
        help="Longitude of the event address (populated by Mapbox autocomplete in Rental POS).",
    )
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

    extra_fees_total = fields.Monetary(
        compute='_compute_extra_fees_total',
        store=True,
        currency_field='currency_id',
    )
    is_freedom_fun_admin = fields.Boolean(
        string="Is Freedom Fun Admin",
        compute="_compute_is_freedom_fun_admin",
        store=False,
    )

    @api.depends_context('uid')
    def _compute_is_freedom_fun_admin(self):
        is_admin = self.env.user.has_group('custom_rental.group_freedom_fun_admin')
        for record in self:
            record.is_freedom_fun_admin = is_admin

    @api.depends("state")
    def _compute_ui_booking_status(self):
        for order in self:
            if order.state in ("sale", "done"):
                order.ui_booking_status = "booked"
            elif order.state in ("draft", "sent"):
                order.ui_booking_status = "quote"
            else:
                order.ui_booking_status = False

    def _rental_deposit_invoiced(self):
        self.ensure_one()
        return (self.amount_invoiced or 0.0) > 0.0

    def _rental_event_within_48h_or_past(self, now):
        """True when rental start is in the past or within the next 48 hours."""
        self.ensure_one()
        if not self.rental_start_date:
            return False
        hours = (self.rental_start_date - now).total_seconds() / 3600.0
        return hours <= 48

    @api.depends(
        "state",
        "invoice_status",
        "rental_start_date",
        "amount_invoiced",
        "pre_event_call_confirmed",
    )
    def _compute_ui_sales_health(self):
        now = fields.Datetime.now()
        for order in self:
            if order.state == "cancel":
                order.ui_sales_health = False
                continue
            dep = order._rental_deposit_invoiced()
            fin = order.invoice_status == "invoiced"
            pre = order.pre_event_call_confirmed
            if dep and fin and pre:
                order.ui_sales_health = "green"
                continue
            if order.state in ("draft", "sent"):
                order.ui_sales_health = "yellow"
                continue
            urgent = order._rental_event_within_48h_or_past(now)
            order.ui_sales_health = "red" if urgent else "yellow"

    @api.depends(
        "state",
        "invoice_status",
        "rental_start_date",
        "amount_invoiced",
        "amount_total",
        "pre_event_call_confirmed",
    )
    def _compute_ui_action_needed(self):
        now = fields.Datetime.now()
        for order in self:
            if order.state == "cancel":
                order.ui_action_needed = False
                order.ui_action_needed_level = False
                continue
            dep = order._rental_deposit_invoiced()
            fin = order.invoice_status == "invoiced"
            pre = order.pre_event_call_confirmed
            urgent = order._rental_event_within_48h_or_past(now)

            if order.state in ("draft", "sent"):
                order.ui_action_needed = _("Deposit needed")
                order.ui_action_needed_level = "yellow"
                continue

            if dep and fin and pre:
                order.ui_action_needed = _("All clear")
                order.ui_action_needed_level = "green"
                continue

            if not dep:
                order.ui_action_needed = _("Deposit needed")
                order.ui_action_needed_level = "red" if urgent else "yellow"
                continue

            if not fin:
                days_late = 0
                if order.rental_start_date and order.rental_start_date < now:
                    days_late = (now.date() - order.rental_start_date.date()).days
                if days_late > 0:
                    order.ui_action_needed = _("Final pymt needed - %s days late") % days_late
                else:
                    order.ui_action_needed = _("Final pymt needed")
                order.ui_action_needed_level = "red" if urgent else "yellow"
                continue

            if not pre:
                order.ui_action_needed = _("Pre-event call not confirmed")
                order.ui_action_needed_level = "red" if urgent else "yellow"
                continue

            order.ui_action_needed = False
            order.ui_action_needed_level = False

    def _rental_calendar_partner_last_name(self):
        self.ensure_one()
        p = self.partner_id
        if not p:
            return ""
        ln = (p.last_name or "").strip()
        if ln:
            return ln
        name = (p.name or "").strip()
        if "," in name:
            return name.split(",", 1)[0].strip()
        parts = name.split()
        return parts[-1] if parts else ""

    def _rental_calendar_experience_label(self):
        self.ensure_one()
        lines = self.order_line.filtered(lambda l: not l.display_type and l.product_id)
        rent_lines = lines.filtered(lambda l: l.product_id.rent_ok)
        if rent_lines:
            return rent_lines[0].product_id.name or ""
        if lines:
            return lines[0].product_id.name or ""
        return ""

    @api.depends(
        "name",
        "state",
        "partner_id",
        "partner_id.last_name",
        "partner_id.name",
        "order_line.display_type",
        "order_line.product_id",
        "order_line.product_id.name",
        "order_line.product_id.rent_ok",
    )
    def _compute_rental_calendar_display(self):
        for order in self:
            if order.state in ("draft", "sent"):
                order.rental_calendar_color_hex = "#fffbea"
            elif order.state in ("sale", "done"):
                order.rental_calendar_color_hex = "#0c668d"
            elif order.state == "cancel":
                order.rental_calendar_color_hex = "#9e9e9e"
            else:
                order.rental_calendar_color_hex = "#6c757d"
            name = (order.name or "").strip()
            last = order._rental_calendar_partner_last_name()
            exp = order._rental_calendar_experience_label()
            parts = []
            if name:
                parts.append(name)
            if last:
                parts.append(last)
            if exp:
                parts.append(exp)
            if len(parts) >= 2:
                order.rental_calendar_title = " — ".join(parts)
            elif len(parts) == 1:
                order.rental_calendar_title = parts[0]
            else:
                order.rental_calendar_title = ""

    @api.depends(
        'override_travel_fee',
        'override_deposit_amount',
        'miscellaneous_fees',
        'tip',
    )
    def _compute_extra_fees_total(self):
        for order in self:
            order.extra_fees_total = sum([
                order.override_travel_fee or 0.0,
                order.override_deposit_amount or 0.0,
                order.miscellaneous_fees or 0.0,
                order.tip or 0.0,
            ])

    def _get_extra_fees_monetary_sum(self):
        """Sum of order-level fees (same logic as extra_fees_total, without dependency issues)."""
        self.ensure_one()
        return sum([
            self.override_travel_fee or 0.0,
            self.override_deposit_amount or 0.0,
            self.miscellaneous_fees or 0.0,
            self.tip or 0.0,
        ])

    def _get_damage_waiver_amount(self, subtotal=None):
        """Damage waiver is 10% of subtotal when selected."""
        self.ensure_one()
        if self.damage_waiver != 'yes':
            return 0.0
        base = subtotal if subtotal is not None else (self.amount_untaxed or 0.0)
        return (self.currency_id.round(base * 0.10) if self.currency_id else (base * 0.10))

    def _get_event_location_fixed_amount(self):
        """Event location fee is fixed $20 when selected."""
        self.ensure_one()
        if self.event_location != 'yes_20':
            return 0.0
        return 20.0

    _SETUP_SURFACE_FEES = {
        'asphalt_35': 35.0,
        'concrete_35': 35.0,
        'turf_35': 35.0,
        'drive_in_movie_asphalt_100': 100.0,
    }
    _SETUP_SURFACE_LABELS = {
        'asphalt_35': 'Asphalt',
        'concrete_35': 'Concrete',
        'turf_35': 'Turf',
        'drive_in_movie_asphalt_100': 'Drive In Movie Asphalt',
    }

    def _get_setup_surface_fixed_amount(self):
        """Setup surface fee based on selection value."""
        self.ensure_one()
        return self._SETUP_SURFACE_FEES.get(self.setup_surface or '', 0.0)

    def _get_setup_surface_fee_label(self):
        """Human-readable label for the setup surface fee line."""
        self.ensure_one()
        name = self._SETUP_SURFACE_LABELS.get(self.setup_surface or '', 'Surface')
        return f'&#x1F6E0; Setup Surface Fee ({name})'

    def _get_percent_fees_monetary_sum(self, subtotal=None):
        """Percent-based fees derived from subtotal (damage waiver, event location, setup surface)."""
        self.ensure_one()
        base = subtotal if subtotal is not None else (self.amount_untaxed or 0.0)
        return (
            self._get_damage_waiver_amount(base)
            + self._get_event_location_fixed_amount()
            + self._get_setup_surface_fixed_amount()
        )

    def _get_effective_sales_tax_percent(self):
        """Effective sales-tax %; prefer explicit override when provided."""
        self.ensure_one()
        if (self.override_tax_amount or 0.0) > 0:
            return self.override_tax_amount
        if not self.amount_untaxed:
            return 0.0
        return (self.amount_tax or 0.0) / self.amount_untaxed * 100.0

    def _get_tax_on_summary_components(self, subtotal=None):
        """Tax applied on summary taxable components: subtotal + waiver + event location + setup surface."""
        self.ensure_one()
        base = subtotal if subtotal is not None else (self.amount_untaxed or 0.0)
        waiver = self._get_damage_waiver_amount(base)
        event_fee = self._get_event_location_fixed_amount()
        surface_fee = self._get_setup_surface_fixed_amount()
        pct = self._get_effective_sales_tax_percent()
        taxable_extra = waiver + event_fee + surface_fee
        if not pct or not taxable_extra:
            return 0.0
        return self.currency_id.round(taxable_extra * (pct / 100.0)) if self.currency_id else taxable_extra * (pct / 100.0)

    @api.depends(
        'order_line.price_subtotal',
        'currency_id',
        'company_id',
        'payment_term_id',
        'override_travel_fee',
        'override_deposit_amount',
        'override_tax_amount',
        'miscellaneous_fees',
        'tip',
        'setup_surface',
    )
    def _compute_amounts(self):
        """Line totals from core; add rental extra fees so amount_total matches the form tax widget."""
        super()._compute_amounts()
        for order in self:
            extra = order._get_extra_fees_monetary_sum() + order._get_percent_fees_monetary_sum(order.amount_untaxed)
            extra_tax = order._get_tax_on_summary_components(order.amount_untaxed)
            total = order.amount_untaxed + order.amount_tax + extra + extra_tax
            if order.currency_id:
                total = order.currency_id.round(total)
            order.amount_total = total

    def _tax_totals_dict_from_value(self, raw):
        """Normalize tax_totals cache (dict / JSON bytes / str) for safe mutation."""
        if not raw:
            return {}
        if isinstance(raw, dict):
            return copy.deepcopy(raw)
        if isinstance(raw, (bytes, bytearray, memoryview)):
            raw = bytes(raw).decode("utf-8", errors="replace")
        if isinstance(raw, str):
            return json.loads(raw) if raw else {}
        return {}

    @api.depends_context('lang')
    @api.depends(
        'order_line.price_subtotal',
        'currency_id',
        'company_id',
        'payment_term_id',
        'override_travel_fee',
        'override_deposit_amount',
        'override_tax_amount',
        'miscellaneous_fees',
        'tip',
        'setup_surface',
        # Must run after _compute_amounts so amount_total (and monetary fields) match fee lines.
        'amount_total',
    )
    def _compute_tax_totals(self):
        super()._compute_tax_totals()

        for order in self:
            extra_total = (
                order._get_extra_fees_monetary_sum()
                + order._get_percent_fees_monetary_sum(order.amount_untaxed)
                + order._get_tax_on_summary_components(order.amount_untaxed)
            )
            currency = order.currency_id
            totals = self._tax_totals_dict_from_value(order.tax_totals)
            extra_tax = order._get_tax_on_summary_components(order.amount_untaxed)

            fees = [
                ('Travel Fee', order.override_travel_fee or 0.0),
                ('Deposit', order.override_deposit_amount or 0.0),
                ('Misc Fees', order.miscellaneous_fees or 0.0),
                ('Tip', order.tip or 0.0),
                ('Damage Waiver (10%)', order._get_damage_waiver_amount(order.amount_untaxed)),
                ('Event Location ($20)', order._get_event_location_fixed_amount()),
                (order._get_setup_surface_fee_label(), order._get_setup_surface_fixed_amount()),
            ]
            fee_names = {f[0] for f in fees}

            if totals:
                # Clean out old custom lines
                original_subtotals = [
                    line for line in totals.get('subtotals', [])
                    if line.get('name') not in fee_names
                ]
                # Align tax line with order summary basis (subtotal + waiver + event location).
                if extra_tax:
                    for line in original_subtotals:
                        if isinstance(line.get('name'), str) and line.get('name').startswith('Tax'):
                            line['base_amount_currency'] = (line.get('base_amount_currency') or 0.0) + extra_tax
                            line['base_amount'] = (line.get('base_amount') or 0.0) + extra_tax
                            break

                new_lines = [
                    {
                        'name': label,
                        'base_amount_currency': amount,
                        'base_amount': amount,
                        'tax_amount_currency': 0.0,
                        'tax_amount': 0.0,
                        'tax_groups': [],
                    }
                    for label, amount in fees if amount
                ]

                totals['subtotals'] = original_subtotals + new_lines

            if totals:
                # Footer total: same as stored amount_total (includes all extra fees).
                lines_comp_total = totals.get('total_amount')
                doc_total = order.amount_total
                if currency:
                    doc_total = currency.round(doc_total)
                totals['total_amount_currency'] = doc_total
                if order.currency_id == order.company_id.currency_id:
                    totals['total_amount'] = doc_total
                elif order.currency_id and lines_comp_total is not None:
                    extra_comp = order.currency_id._convert(
                        extra_total,
                        order.company_id.currency_id,
                        order.company_id,
                        order.date_order or fields.Date.context_today(order),
                    )
                    totals['total_amount'] = order.company_id.currency_id.round(
                        lines_comp_total + extra_comp
                    )
                else:
                    totals['total_amount'] = doc_total
                order.tax_totals = totals

    @api.onchange(
        'override_travel_fee',
        'override_deposit_amount',
        'override_tax_amount',
        'miscellaneous_fees',
        'tip',
    )
    def _onchange_extra_fees(self):
        self._compute_amounts()
        self._compute_tax_totals()

    def _get_pos_fee_line_values(self, include_tip=True):
        """Return order-level fee labels/amounts to mirror SO totals on invoices."""
        self.ensure_one()
        fees = [
            {'name': 'Travel Fee', 'amount': self.override_travel_fee or 0.0, 'taxable': False},
            {'name': 'Deposit', 'amount': self.override_deposit_amount or 0.0, 'taxable': False},
            {'name': 'Misc Fees', 'amount': self.miscellaneous_fees or 0.0, 'taxable': False},
            {'name': 'Damage Waiver (10%)', 'amount': self._get_damage_waiver_amount(self.amount_untaxed or 0.0), 'taxable': True},
            {'name': 'Event Location ($20)', 'amount': self._get_event_location_fixed_amount(), 'taxable': True},
            {'name': self._get_setup_surface_fee_label(), 'amount': self._get_setup_surface_fixed_amount(), 'taxable': True},
        ]
        if include_tip:
            fees.append({'name': 'Tip', 'amount': self.tip or 0.0, 'taxable': False})
        return [fee for fee in fees if fee['amount']]

    def _apply_pos_fee_lines_to_invoice(self, invoice, ratio=1.0, include_tip=True):
        """Append fee lines to draft invoice so invoice amounts match sale order totals."""
        self.ensure_one()
        if not invoice or invoice.state != 'draft':
            return

        ratio = min(1.0, max(0.0, float(ratio or 0.0)))
        currency = invoice.currency_id or self.currency_id
        sale_tax_ids = (
            self.order_line.mapped('tax_ids').ids
            if 'tax_ids' in self.order_line._fields
            else self.order_line.mapped('tax_id').ids
        )
        fee_lines = self._get_pos_fee_line_values(include_tip=include_tip)
        if not fee_lines:
            return

        fee_names = {fee['name'] for fee in fee_lines}
        existing_fee_lines = invoice.invoice_line_ids.filtered(lambda l: (l.name or '') in fee_names)
        if existing_fee_lines:
            existing_fee_lines.unlink()

        commands = []
        for fee in fee_lines:
            label = fee['name']
            amount = fee['amount']
            fee_amount = currency.round(amount * ratio) if currency else (amount * ratio)
            if not fee_amount:
                continue
            commands.append((0, 0, {
                'name': label,
                'quantity': 1.0,
                'price_unit': fee_amount,
                'tax_ids': [(6, 0, sale_tax_ids if fee.get('taxable') else [])],
            }))
        if commands:
            invoice.write({'invoice_line_ids': commands})


    @api.depends("event_zip", "company_id")
    def _compute_event_zip_verification_id(self):
        """Set matching rental.zipcode from EVENT zip so status persists after save."""
        RentalZip = self.env["rental.zipcode"]
        for order in self:
            if not order.event_zip:
                order.event_zip_verification_id = False
                continue
            domain = [
                ("name", "=", order.event_zip),
                ("company_id", "=", order.company_id.id if order.company_id else False),
            ]
            zipcode = RentalZip.search(domain, limit=1)
            order.event_zip_verification_id = zipcode

    @api.depends("event_zip_verification_id", "event_zip")
    def _compute_event_zip_verification_status(self):
        for order in self:
            if not order.event_zip:
                order.event_zip_verification_status = False
            elif order.event_zip_verification_id:
                order.event_zip_verification_status = "available"
            else:
                order.event_zip_verification_status = "not_available"

    @api.onchange("event_same_as_billing", "partner_id")
    def _onchange_event_same_as_billing(self):
        self._sync_event_address_from_partner()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # If no partner, create one from the display fields
            if not vals.get("partner_id"):
                partner_vals = self._build_partner_vals(vals)
                if partner_vals.get("name"):
                    partner = self.env["res.partner"].create(partner_vals)
                    vals["partner_id"] = partner.id
            else:
                # Partner exists — push display field edits back to it
                self._push_to_partner(vals.get("partner_id"), vals)

            # existing same-as-billing logic
            if vals.get("event_same_as_billing") and vals.get("partner_id"):
                partner = self.env["res.partner"].browse(vals["partner_id"])
                if partner and "event_street" not in vals:
                    vals.update({
                        "event_street": partner.street,
                        "event_street2": partner.street2,
                        "event_city": partner.city,
                        "event_state_id": partner.state_id.id if partner.state_id else False,
                        "event_zip": partner.zip,
                        "event_country_id": partner.country_id.id if partner.country_id else False,
                    })
        return super().create(vals_list)

    def write(self, vals):
        for order in self:
            if order.partner_id:
                order._push_to_partner(order.partner_id.id, vals)
            elif not order.partner_id:
                partner_vals = order._build_partner_vals(vals)
                if partner_vals.get("name"):
                    partner = self.env["res.partner"].create(partner_vals)
                    vals["partner_id"] = partner.id

            # existing same-as-billing logic
            if len(self) == 1 and self.event_same_as_billing and self.partner_id:
                vals = dict(vals)
                def _set_if_missing_or_empty(key, value):
                    if key not in vals or vals.get(key) in (None, False, ""):
                        vals[key] = value
                _set_if_missing_or_empty("event_street", self.partner_id.street)
                _set_if_missing_or_empty("event_street2", self.partner_id.street2)
                _set_if_missing_or_empty("event_city", self.partner_id.city)
                _set_if_missing_or_empty("event_state_id", self.partner_id.state_id.id if self.partner_id.state_id else False)
                _set_if_missing_or_empty("event_zip", self.partner_id.zip)
                _set_if_missing_or_empty("event_country_id", self.partner_id.country_id.id if self.partner_id.country_id else False)

        return super().write(vals)

    def _build_partner_vals(self, vals):
        """Build a res.partner vals dict from the display fields in sale order vals."""
        partner_vals = {}
        
        # Name: try to get from partner_name or compose from first/last if you have those
        name = vals.get("partner_name") or (self.partner_id.name if self.partner_id else False)
        if name:
            partner_vals["name"] = name

        field_map = {
            "partner_email_display": "email",
            "partner_phone_display": "phone",
            "partner_phone_secondary_display": "phone_secondary",
            "partner_street_display": "street",
            "partner_street2_display": "street2",
            "partner_city_display": "city",
            "partner_zip_display": "zip",
            "partner_state_id_display": "state_id",
            "partner_country_id_display": "country_id",
            "partner_company_display": "commercial_company_name",
        }
        for order_field, partner_field in field_map.items():
            if order_field in vals:
                partner_vals[partner_field] = vals[order_field]

        return partner_vals

    def _push_to_partner(self, partner_id, vals):
        """Write any changed display fields back to the linked res.partner."""
        if not partner_id:
            return
        partner_vals = {}
        field_map = {
            "partner_email_display": "email",
            "partner_phone_display": "phone",
            "partner_phone_secondary_display": "phone_secondary",
            "partner_street_display": "street",
            "partner_street2_display": "street2",
            "partner_city_display": "city",
            "partner_zip_display": "zip",
            "partner_state_id_display": "state_id",
            "partner_country_id_display": "country_id",
            "partner_company_display": "commercial_company_name",
        }
        for order_field, partner_field in field_map.items():
            if order_field in vals:
                partner_vals[partner_field] = vals[order_field]

        if partner_vals:
            self.env["res.partner"].browse(partner_id).write(partner_vals)

    def action_confirm(self):
        """Require Additional information checkboxes to be agreed before confirming."""
        for order in self:
            if not order.additional_weather_policy_agreed:
                raise UserError(
                    "You must agree to the weather and payment policy (rain check / refunds) before confirming the order."
                )
            if not order.additional_setup_terms_agreed:
                raise UserError(
                    "You must agree to the setup and electrical terms (rock/gravel, circuits, 50' ft electricity) before confirming the order."
                )
        return super().action_confirm()

    def action_create_and_send_invoice_pos(self, deposit_percent=0, flow_type='quote_full', remaining_percent=0):
        """Create invoice and send Freedom Fun quote email with payment link.

        flow_type values:
            'quote_full'    – Send Quote, no deposit  → "pay full amount"
            'quote_deposit' – Send Quote, X% deposit  → "pay X% to confirm"
            'remaining'     – Partial already paid    → "complete remaining Y%"
        """
        self.ensure_one()

        # ── 0. Confirm the sale order if still draft ──────────
        if self.state in ('draft', 'sent'):
            self.action_confirm()

        # ── 1. Create wizard & invoice ────────────────────────
        if deposit_percent > 0:
            wizard = self.env['sale.advance.payment.inv'].create({
                'advance_payment_method': 'percentage',
                'amount': deposit_percent,
                'sale_order_ids': [(6, 0, [self.id])],
            })
        else:
            wizard = self.env['sale.advance.payment.inv'].create({
                'advance_payment_method': 'percentage',
                'amount': 100,
                'sale_order_ids': [(6, 0, [self.id])],
            })

        wizard.with_context(
            active_ids=[self.id],
            active_model='sale.order'
        ).create_invoices()

        # ── 2. Find the created draft invoice ─────────────────
        invoice = self.invoice_ids.filtered(lambda m: m.state == 'draft')[:1]

        if not invoice:
            raise UserError("Invoice could not be created.")

        # ── 3. Mirror order-level fees on invoice then confirm ───────────────
        if flow_type == 'remaining' and remaining_percent:
            ratio = (remaining_percent or 0.0) / 100.0
        elif deposit_percent > 0:
            ratio = deposit_percent / 100.0
        else:
            ratio = 1.0
        self._apply_pos_fee_lines_to_invoice(invoice, ratio=ratio, include_tip=True)
        invoice.action_post()

        # ── 4. Ensure access token exists ─────────────────────
        if not invoice.access_token:
            invoice.sudo().write({'access_token': secrets.token_urlsafe(32)})

        access_token = invoice.access_token
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
        # For remaining-balance invoices add flow=remaining so the payment page hides
        # the 30% deposit option and shows only the outstanding amount.
        flow_param = 'remaining' if flow_type == 'remaining' else 'quote'
        payment_url = f"{base_url}/rental/pay/{invoice.id}?access_token={access_token}&flow={flow_param}"

        _logger.info("Invoice %s payment URL: %s", invoice.name, payment_url)

        # ── 5. Partner / currency / symbol ────────────────────
        partner  = invoice.partner_id
        currency = invoice.currency_id
        sym      = currency.symbol
        amount_str = f"{sym}{invoice.amount_residual:,.2f}"

        # ── 6. Duration helpers ───────────────────────────────
        def _duration_hours(start_dt, end_dt):
            if not start_dt or not end_dt:
                return 1
            try:
                hours = (end_dt - start_dt).total_seconds() / 3600
                return max(1.0, hours)
            except Exception:
                return 1

        def _fmt_duration(hours):
            return f"{int(hours)} hrs" if hours == int(hours) else f"{hours:.1f} hrs"

        # ── 7. Build order lines HTML ─────────────────────────
        lines_html = ""
        for line in self.order_line:

            # Skip ghost lines (no product, zero qty, or $0)
            if not line.product_id or line.product_uom_qty == 0 or line.price_unit == 0:
                continue

            date_str     = ""
            duration_str = ""
            start_dt     = None
            end_dt       = None

            if hasattr(line, 'start_date') and line.start_date:
                start_dt = line.start_date
                end_dt   = line.return_date if hasattr(line, 'return_date') and line.return_date else None
                try:
                    date_str = start_dt.strftime('%a, %b %-d  %-I:%M %p')
                    if end_dt:
                        date_str += ' \u2192 ' + end_dt.strftime('%-I:%M %p')
                        duration_str = _fmt_duration(_duration_hours(start_dt, end_dt))
                except Exception:
                    date_str = str(start_dt)

            unit_price = line.price_unit or 0
            line_total = unit_price * line.product_uom_qty

            duration_badge = (
                f'<span style="font-size:11px; background:#056690; color:white; '
                f'border-radius:3px; padding:1px 6px; margin-left:6px;">'
                f'{duration_str}</span>'
            ) if duration_str else ""

            code_row = (
                f'<br/><span style="font-size: 12px; color: #999;">'
                f'{line.product_id.default_code}</span>'
            ) if line.product_id.default_code else ""

            lines_html += f"""
            <tr>
                <td style="padding: 10px 14px; border-bottom: 1px solid #e8e8e8; vertical-align: top;">
                    <strong style="font-size: 14px; color: #222;">{line.product_id.name or ''}</strong>
                    {duration_badge}
                    {f'<br/><span style="font-size: 12px; color: #888;">{date_str}</span>' if date_str else ''}
                    {code_row}
                </td>
                <td style="padding: 10px 14px; border-bottom: 1px solid #e8e8e8;
                           text-align: center; color: #555; font-size: 14px;">
                    x {int(line.product_uom_qty)}
                </td>
                <td style="padding: 10px 14px; border-bottom: 1px solid #e8e8e8;
                           text-align: right; font-weight: bold; font-size: 14px;">
                    {sym}{line_total:,.2f}
                </td>
            </tr>
            """

        # ── 8. Compute totals ─────────────────────────────────
        subtotal   = self.amount_untaxed
        travel_fee = getattr(self, 'override_travel_fee', 0.0) or 0.0
        misc_fees  = getattr(self, 'miscellaneous_fees', 0.0) or 0.0

        # Discount
        gen_discount    = getattr(self, 'general_discount', 0.0) or 0.0
        discount_amount = subtotal * (gen_discount / 100) if gen_discount > 0 else 0.0

        # Damage waiver (10% of cart subtotal if customer opted in)
        damage_waiver_opted = getattr(self, 'damage_waiver', 'no') == 'yes'
        damage_waiver_amount = round(subtotal * 0.10, 2) if damage_waiver_opted else 0.0

        # Non-residential event location fee ($20)
        event_location_fee = 20.0 if getattr(self, 'event_location', '') == 'yes_20' else 0.0

        # Setup surface fee — use the same helper methods as _get_pos_fee_line_values()
        # so the email always matches what is applied to the invoice, including the
        # drive_in_movie_asphalt_100 ($100) case.
        setup_surface_fee = self._get_setup_surface_fixed_amount()
        setup_surface_fee_label = self._get_setup_surface_fee_label()  # already includes emoji + name

        # Tax
        # override_tax_amount stores the tax RATE as a percentage (e.g. 10 = 10%)
        override_tax_pct = getattr(self, 'override_tax_amount', 0.0) or 0.0
        taxable_base = max(0, subtotal - discount_amount + damage_waiver_amount + event_location_fee + setup_surface_fee)
        if override_tax_pct > 0:
            tax_amount = round(taxable_base * (override_tax_pct / 100), 2)
            tax_label  = f"Tax ({override_tax_pct:g}%)"
        elif self.amount_tax and self.amount_tax > 0:
            # Derive rate from the sale order, then apply it to the full taxable_base
            # (which includes damage waiver + setup surface + location fee) so the
            # email tax matches the order summary exactly.
            eff_rate   = (self.amount_tax / subtotal) if subtotal else 0.07
            tax_amount = round(taxable_base * eff_rate, 2)
            rate_pct   = round(eff_rate * 100, 1)
            tax_label  = f"Tax ({rate_pct:g}%)"
        else:
            tax_amount = round(taxable_base * 0.07, 2)
            tax_label  = "Tax (7%)"

        # Grand total
        grand_total = (
            subtotal
            - discount_amount
            + damage_waiver_amount
            + event_location_fee
            + setup_surface_fee
            + travel_fee
            + misc_fees
            + tax_amount
        )
        deposit_amt = invoice.amount_residual
        remaining   = grand_total - deposit_amt

        # ── 9. Company + customer info ────────────────────────
        company      = self.company_id
        company_name = company.name or 'Freedom Fun USA'
        quote_num    = self.name or ''

        cust_name   = partner.name or ''
        cust_street = partner.street or ''
        cust_city   = ''
        if partner.city:
            state_name = partner.state_id.name if partner.state_id else ''
            cust_city  = f"{partner.city}, {state_name} {partner.zip or ''}".strip(', ')
        cust_email  = partner.email or ''
        cust_phone  = partner.phone or ''
        created_by  = self.user_id.name if self.user_id else ''
        note        = self.note or ''

        # ── 10. Totals row helper ─────────────────────────────
        def total_row(label, value, color="#555", bold=False, bg="white"):
            fw = "bold" if bold else "normal"
            return f"""
            <tr style="background:{bg};">
                <td style="padding:8px 14px; border-bottom:1px solid #eee;
                           text-align:right; color:{color};
                           font-size:13px; font-weight:{fw};">{label}</td>
                <td style="padding:8px 14px; border-bottom:1px solid #eee;
                           text-align:right; width:110px;
                           font-weight:bold; font-size:13px; color:{color};">
                    {sym}{value:,.2f}
                </td>
            </tr>"""

        totals_rows = total_row("SubTotal", subtotal)

        if discount_amount > 0:
            totals_rows += total_row(
                f'Discount ({gen_discount}%)', -discount_amount, color="#e74c3c"
            )

        # Damage waiver — only shown if customer opted in
        if damage_waiver_amount > 0:
            totals_rows += total_row(
                "&#x1F6E1; Damage Waiver (10%)", damage_waiver_amount, color="#056690"
            )

        # Non-residential fee — only shown if selected
        if event_location_fee > 0:
            totals_rows += total_row(
                "&#x1F4CD; Non-Residential Location Fee", event_location_fee, color="#056690"
            )

        # Setup surface fee — only shown when surface has a charge
        if setup_surface_fee > 0:
            totals_rows += total_row(setup_surface_fee_label, setup_surface_fee, color="#056690")

        if travel_fee > 0:
            totals_rows += total_row("&#x1F697; Travel Fee", travel_fee)

        if misc_fees > 0:
            totals_rows += total_row("Miscellaneous Fees", misc_fees)

        # Tax always shown
        totals_rows += total_row(tax_label, tax_amount)

        # Grand total row
        totals_rows += f"""
            <tr style="background:#f0f0f0;">
                <td style="padding:10px 14px; text-align:right;
                           font-weight:bold; font-size:15px; color:#1b1b1b;">
                    Grand Total
                </td>
                <td style="padding:10px 14px; text-align:right;
                           font-weight:bold; font-size:16px; color:#1b1b1b;">
                    {sym}{grand_total:,.2f}
                </td>
            </tr>"""

        # Deposit row — only if deposit_percent > 0
        if deposit_percent > 0:
            totals_rows += f"""
            <tr style="background:#ffef7a;">
                <td style="padding:10px 14px; text-align:right;
                           font-weight:bold; color:#056690; font-size:14px;">
                    Due Today ({deposit_percent}% Deposit)
                </td>
                <td style="padding:10px 14px; text-align:right;
                           font-weight:bold; color:#056690; font-size:15px;">
                    {sym}{deposit_amt:,.2f}
                </td>
            </tr>
            <tr style="background:#fafafa;">
                <td style="padding:8px 14px; text-align:right;
                           color:#888; font-size:12px;">
                    Remaining after deposit
                </td>
                <td style="padding:8px 14px; text-align:right;
                           color:#888; font-size:12px;">
                    {sym}{remaining:,.2f}
                </td>
            </tr>"""

        # ── 11. Flow-specific content ─────────────────────────
        def cta_btn(label, bg='#056690'):
            return f"""
            <div style="text-align: center; margin: 20px 0;">
                <a href="{payment_url}"
                   style="background-color: {bg}; color: #ffffff;
                          padding: 14px 36px; text-decoration: none;
                          border-radius: 4px; font-size: 16px; font-weight: bold;
                          display: inline-block; letter-spacing: 0.3px;">
                    {label}
                </a>
            </div>"""

        if flow_type == 'remaining':
            header_badge  = f'ORDER #{quote_num} — REMAINING BALANCE'
            email_subject = f'{company_name} - Order #{quote_num} - Remaining Balance Due ({remaining_percent}%)'
            hero_html = f"""
            <div style="background: #e8f4fb; border: 2px solid #056690;
                        padding: 24px 28px; text-align: center;">
                <h2 style="color: #056690; margin: 0 0 10px; font-size: 18px;">
                    Remaining Balance Due: {sym}{invoice.amount_residual:,.2f}
                </h2>
                <p style="color: #555; margin: 0 0 16px; font-size: 14px;">
                    Thank you for your initial payment!<br/>
                    Please complete your remaining <strong>{remaining_percent}%</strong>
                    to fully secure your booking.
                </p>
                {cta_btn('Complete Remaining Payment', '#056690')}
            </div>"""
            urgency_html  = ""
            bottom_msg       = f"Please complete your remaining payment of {remaining_percent}% to finalize your event."
            bottom_cta_label = "Complete Remaining Payment"
            bottom_cta_color = "#056690"

        elif flow_type == 'quote_deposit':
            header_badge  = f'QUOTE #{quote_num}'
            email_subject = f'{company_name} - Quote #{quote_num} - {deposit_percent}% Deposit Due: {amount_str}'
            hero_html = f"""
            <div style="background: #ffef7a; border: 2px solid #fdcd15;
                        padding: 24px 28px; text-align: center;">
                <h2 style="color: #056690; margin: 0 0 14px; font-size: 18px;">
                    Important: This Is a Quote - Not a Reservation
                </h2>
                <ul style="list-style: none; padding: 0; margin: 0 0 16px;
                           color: #555; font-size: 14px; line-height: 2.2;
                           text-align: left; display: inline-block;">
                    <li>&#x2022; This quote does not hold your date yet</li>
                    <li>&#x2022; Your event date is only secured once you complete your order</li>
                    <li>&#x2022; It takes less than a minute to lock in your date</li>
                </ul>
                <p style="color: #555; margin: 0 0 16px;">
                    Click below to pay your <strong>{deposit_percent}% deposit</strong>
                    and confirm your booking.
                </p>
                {cta_btn('Pay Deposit &amp; Confirm Booking', '#056690')}
                <p style="color: #056690; font-size: 13px; margin: 12px 0 0;">
                    &#x1F6E1; Your deposit is always protected by our
                    <strong>Free Rescheduling Promise</strong>
                </p>
            </div>"""
            urgency_html = f"""
            <div style="background: #ffef7a; padding: 24px 32px;
                        border-left: 4px solid #fdcd15; border-right: 1px solid #e0e0e0;">
                <h3 style="color: #056690; margin: 0 0 10px; font-size: 16px;">
                    Dates Fill Fast - Don't Miss Out!
                </h3>
                <p style="margin: 0 0 10px; color: #555; line-height: 1.7;">
                    Most of our customers book within 24-48 hours. Weekends especially go quickly.
                </p>
                <p style="margin: 0; color: #555; line-height: 1.7;">
                    Secure your event now with just a
                    <strong>{deposit_percent}% deposit</strong>, and we'll take care
                    of the rest. Click "Pay Deposit" below and let's make your event amazing.
                </p>
            </div>"""
            bottom_msg       = f"Please pay {deposit_percent}% to confirm your booking."
            bottom_cta_label = f"Pay {deposit_percent}% Deposit &amp; Confirm"
            bottom_cta_color = "#056690"

        else:  # quote_full
            header_badge  = f'QUOTE #{quote_num}'
            email_subject = f'{company_name} - Quote #{quote_num} - Full Payment Request'
            hero_html = f"""
            <div style="background: #ffef7a; border: 2px solid #fdcd15;
                        padding: 24px 28px; text-align: center;">
                <h2 style="color: #056690; margin: 0 0 14px; font-size: 18px;">
                    Important: This Is a Quote - Not a Reservation
                </h2>
                <ul style="list-style: none; padding: 0; margin: 0 0 16px;
                           color: #555; font-size: 14px; line-height: 2.2;
                           text-align: left; display: inline-block;">
                    <li>&#x2022; This quote does not hold your date yet</li>
                    <li>&#x2022; Your event date is only secured once you complete your order</li>
                    <li>&#x2022; It takes less than a minute to lock in your date</li>
                </ul>
                <p style="color: #555; margin: 0 0 16px;">
                    Click below to pay the full amount and confirm your booking.
                </p>
                {cta_btn('Pay in Full &amp; Confirm Booking', '#056690')}
                <p style="color: #056690; font-size: 13px; margin: 12px 0 0;">
                    &#x1F6E1; Your deposit is always protected by our
                    <strong>Free Rescheduling Promise</strong>
                </p>
            </div>"""
            urgency_html = """
            <div style="background: #ffef7a; padding: 24px 32px;
                        border-left: 4px solid #fdcd15; border-right: 1px solid #e0e0e0;">
                <h3 style="color: #056690; margin: 0 0 10px; font-size: 16px;">
                    Dates Fill Fast - Don't Miss Out!
                </h3>
                <p style="margin: 0 0 10px; color: #555; line-height: 1.7;">
                    Most of our customers book within 24-48 hours. Weekends especially go quickly.
                </p>
                <p style="margin: 0; color: #555; line-height: 1.7;">
                    Secure your event today — click "Pay in Full" below and
                    let's make your event amazing.
                </p>
            </div>"""
            bottom_msg       = "Please pay the full amount to proceed and confirm your booking."
            bottom_cta_label = "Pay in Full &amp; Confirm Booking"
            bottom_cta_color = "#056690"

        # ── 12. Build full email ──────────────────────────────
        email_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 680px;
                    margin: 0 auto; color: #333; font-size: 14px;">

            <!-- TOP HEADER -->
            <div style="background: #056690; padding: 20px 32px;
                        border-radius: 6px 6px 0 0; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 22px;
                            letter-spacing: 1px;">{company_name}</h1>
                <p style="color: #bcbcbc; margin: 6px 0 0; font-size: 13px;">
                    {header_badge}
                </p>
            </div>

            <!-- HERO NOTICE (flow-specific) -->
            {hero_html}

            <!-- WELCOME -->
            <div style="background: #ffffff; padding: 32px 32px 24px;
                        border-left: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0;">
                <p style="font-size: 15px; line-height: 1.7; margin: 0 0 14px;">
                    Hi there - welcome to Freedom Fun Sarasota!
                </p>
                <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
                    We're Tom and Ginger, proud local owners of your Freedom Fun USA store
                    here in Sarasota. We're so glad you found us and can't wait to help you
                    create an unforgettable event.
                </p>
                <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
                    We know how stressful planning an event can be. Maybe you've dealt with
                    companies that show up late (or not at all), bring worn-out equipment,
                    or leave you hanging the day of the party.
                </p>
                <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
                    At Freedom Fun, we believe life is too short for a bad party. That's why
                    we bring clean, high-quality equipment, show up on time, and deliver our
                    nationally known, over-the-top 5-star service - right here in your backyard.
                </p>
                <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
                    We've helped thousands of families, schools, and companies celebrate
                    across the U.S., including <strong>Facebook, Tesla, Chick-fil-A, YMCA,
                    Amazon, and LegalZoom</strong>. But what we care most about is
                    <strong>you</strong> - and making your event stress-free and FUN.
                </p>
                <p style="line-height: 1.7; margin: 0;">
                    Want to see us in action?
                    <a href="#" style="color: #056690;">Facebook Photos</a> |
                    <a href="#" style="color: #056690;">Instagram Gallery</a>
                </p>
            </div>

            <!-- RESCHEDULING PROMISE -->
            <div style="background: #e8f4fb; padding: 24px 32px;
                        border-left: 4px solid #056690; border-right: 1px solid #e0e0e0;">
                <h3 style="color: #056690; margin: 0 0 10px; font-size: 16px;">
                    Our Legendary Free Rescheduling Promise
                </h3>
                <p style="margin: 0; color: #056690; line-height: 1.7;">
                    When you place your deposit today, your date is locked in - and you'll
                    never lose it. If anything changes, your deposit becomes a credit that
                    never expires, so you can book with total peace of mind.
                </p>
            </div>

            <!-- URGENCY (quote flows only) -->
            {urgency_html}

            <!-- SIGNATURE -->
            <div style="background: #ffffff; padding: 24px 32px;
                        border-left: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0;">
                <p style="color: #444; line-height: 1.7; font-style: italic; margin: 0;">
                    With joy,<br/>
                    <strong>Tom &amp; Ginger Phelps</strong><br/>
                    Owners, Freedom Fun Sarasota<br/>
                    <span style="color: #888; font-size: 13px;">
                        Proudly part of the Freedom Fun USA family
                    </span>
                </p>
            </div>

            <!-- QUOTE DETAILS -->
            <div style="background: #f9f9f9; padding: 28px 32px;
                        border: 1px solid #e0e0e0; border-top: none;">

                <h2 style="color: #1b1b1b; font-size: 18px; margin: 0 0 20px;
                            border-bottom: 2px solid #fdcd15; padding-bottom: 10px;">
                    Your Quote
                </h2>

                <table style="width: 100%; margin-bottom: 24px; border-collapse: collapse;">
                    <tr>
                        <td style="vertical-align: top; width: 50%; padding-right: 16px;">
                            <p style="margin: 0 0 4px; font-weight: bold;
                                      color: #1b1b1b; font-size: 15px;">{company_name}</p>
                            <p style="margin: 0; color: #666; font-size: 13px; line-height: 1.7;">
                                {cust_name}<br/>
                                {cust_street + '<br/>' if cust_street else ''}
                                {cust_city + '<br/>' if cust_city else ''}
                                {cust_email + '<br/>' if cust_email else ''}
                                {cust_phone}
                            </p>
                        </td>
                        <td style="vertical-align: top; width: 50%; text-align: right;">
                            <p style="margin: 0; color: #666; font-size: 13px; line-height: 1.7;">
                                Quote Created by: {created_by}<br/>
                                {f'Customer Comments: {note}' if note else ''}
                            </p>
                        </td>
                    </tr>
                </table>

                <!-- Line Items -->
                <table style="width: 100%; border-collapse: collapse;
                              background: white; border: 1px solid #e0e0e0;">
                    <thead>
                        <tr style="background: #056690;">
                            <th style="padding:10px 14px; text-align:left;
                                       font-size:13px; font-weight:bold; color:white;">Item</th>
                            <th style="padding:10px 14px; text-align:center;
                                       font-size:13px; font-weight:bold;
                                       color:white; width:60px;">Qty</th>
                            <th style="padding:10px 14px; text-align:right;
                                       font-size:13px; font-weight:bold;
                                       color:white; width:110px;">Price</th>
                        </tr>
                    </thead>
                    <tbody>{lines_html}</tbody>
                </table>

                <!-- Totals -->
                <table style="width: 100%; border-collapse: collapse;
                              background: white; border: 1px solid #e0e0e0; border-top: none;">
                    {totals_rows}
                </table>
            </div>

            <!-- BOTTOM CTA -->
            <div style="background: #056690; padding: 32px;
                        text-align: center; border-radius: 0 0 6px 6px;">
                <p style="color: #bcbcbc; font-size: 14px; margin: 0 0 16px;">
                    {bottom_msg}
                </p>
                {cta_btn(bottom_cta_label, bottom_cta_color)}
                <p style="color: #bcbcbc; font-size: 13px; margin: 16px 0 0;">
                    Your deposit is always protected - it becomes a credit
                    that never expires if plans change.
                </p>
                <p style="margin: 8px 0 0;">
                    <a href="#" style="color: #fdcd15; font-size: 12px;">
                        For details, see our Full Rescheduling &amp; Cancellation Policy.
                    </a>
                </p>
            </div>

        </div>
        """

        # ── 13. Attach invoice PDF ────────────────────────────
        attachment_ids = []
        try:
            report = self.env.ref('account.account_invoices')
            pdf_content, _ = report._render_qweb_pdf([invoice.id])
            attachment = self.env['ir.attachment'].sudo().create({
                'name': f'{invoice.name}.pdf',
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'mimetype': 'application/pdf',
            })
            attachment_ids = [(4, attachment.id)]
        except Exception as e:
            _logger.warning("Could not attach invoice PDF: %s", e)

        # ── 14. Send email ────────────────────────────────────
        email_from = (
            self.env.user.email
            or self.env['ir.config_parameter'].sudo().get_param('mail.catchall.email')
            or 'noreply@example.com'
        )

        mail = self.env['mail.mail'].sudo().create({
            'subject': email_subject,
            'email_to': partner.email,
            'email_from': email_from,
            'body_html': email_body,
            'auto_delete': False,
            'model': 'account.move',
            'res_id': invoice.id,
            'attachment_ids': attachment_ids,
        })

        mail.send()
        _logger.info("Quote email sent to %s for order %s", partner.email, self.name)

        return invoice.id

    def action_send_quote_pos(self):
        """Send a quote email to the customer without creating an invoice.
        The sale order stays as a quotation (state='sent').
        Invoice is created only when the customer initiates payment via the link.
        Returns the order id.
        """
        self.ensure_one()

        # ── 0. Mark as 'sent' (stays quotation, NOT confirmed) ─────
        if self.state == 'draft':
            self.write({'state': 'sent'})

        # ── 1. Ensure portal access token ──────────────────────────
        if not self.access_token:
            self._portal_ensure_token()

        access_token = self.access_token
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
        payment_url      = f"{base_url}/rental/quote/pay/{self.id}?access_token={access_token}"
        accept_quote_url = f"{base_url}/rental/quote/accept_order/{self.id}?access_token={access_token}"

        _logger.info("Quote %s payment URL: %s", self.name, payment_url)

        # ── 2. Partner / currency / amounts ────────────────────────
        partner      = self.partner_id
        currency     = self.currency_id
        sym          = currency.symbol if currency else '$'
        grand_total  = self.amount_total or 0.0
        deposit_30   = (currency.round(grand_total * 0.30) if currency else round(grand_total * 0.30, 2))
        amount_str   = f"{sym}{grand_total:,.2f}"

        # ── 3. Duration helpers ────────────────────────────────────
        def _duration_hours(start_dt, end_dt):
            if not start_dt or not end_dt:
                return 1
            try:
                hours = (end_dt - start_dt).total_seconds() / 3600
                return max(1.0, hours)
            except Exception:
                return 1

        def _fmt_duration(hours):
            return f"{int(hours)} hrs" if hours == int(hours) else f"{hours:.1f} hrs"

        # ── 4. Build order lines HTML ──────────────────────────────
        lines_html = ""
        for line in self.order_line:
            if not line.product_id or line.product_uom_qty == 0 or line.price_unit == 0:
                continue
            date_str = duration_str = ""
            start_dt = end_dt = None
            if hasattr(line, 'start_date') and line.start_date:
                start_dt = line.start_date
                end_dt   = line.return_date if hasattr(line, 'return_date') and line.return_date else None
                try:
                    date_str = start_dt.strftime('%a, %b %-d  %-I:%M %p')
                    if end_dt:
                        date_str += ' \u2192 ' + end_dt.strftime('%-I:%M %p')
                        duration_str = _fmt_duration(_duration_hours(start_dt, end_dt))
                except Exception:
                    date_str = str(start_dt)
            unit_price = line.price_unit or 0
            line_total = unit_price * line.product_uom_qty
            duration_badge = (
                f'<span style="font-size:11px; background:#056690; color:white; '
                f'border-radius:3px; padding:1px 6px; margin-left:6px;">{duration_str}</span>'
            ) if duration_str else ""
            code_row = (
                f'<br/><span style="font-size:12px;color:#999;">{line.product_id.default_code}</span>'
            ) if line.product_id.default_code else ""
            lines_html += f"""
            <tr>
                <td style="padding:10px 14px;border-bottom:1px solid #e8e8e8;vertical-align:top;">
                    <strong style="font-size:14px;color:#222;">{line.product_id.name or ''}</strong>
                    {duration_badge}
                    {f'<br/><span style="font-size:12px;color:#888;">{date_str}</span>' if date_str else ''}
                    {code_row}
                </td>
                <td style="padding:10px 14px;border-bottom:1px solid #e8e8e8;text-align:center;color:#555;font-size:14px;">
                    x {int(line.product_uom_qty)}
                </td>
                <td style="padding:10px 14px;border-bottom:1px solid #e8e8e8;text-align:right;font-weight:bold;font-size:14px;">
                    {sym}{line_total:,.2f}
                </td>
            </tr>"""

        # ── 5. Compute totals ──────────────────────────────────────
        subtotal           = self.amount_untaxed
        travel_fee         = getattr(self, 'override_travel_fee', 0.0) or 0.0
        misc_fees          = getattr(self, 'miscellaneous_fees', 0.0) or 0.0
        gen_discount       = getattr(self, 'general_discount', 0.0) or 0.0
        discount_amount    = subtotal * (gen_discount / 100) if gen_discount > 0 else 0.0
        damage_waiver_opted = getattr(self, 'damage_waiver', 'no') == 'yes'
        damage_waiver_amount = round(subtotal * 0.10, 2) if damage_waiver_opted else 0.0
        event_location_fee = 20.0 if getattr(self, 'event_location', '') == 'yes_20' else 0.0
        setup_surface_fee  = self._SETUP_SURFACE_FEES.get(getattr(self, 'setup_surface', '') or '', 0.0)
        setup_surface_label = self._SETUP_SURFACE_LABELS.get(getattr(self, 'setup_surface', '') or '', 'Surface')
        override_tax_pct   = getattr(self, 'override_tax_amount', 0.0) or 0.0
        taxable_base       = max(0, subtotal - discount_amount + damage_waiver_amount + event_location_fee + setup_surface_fee)
        if override_tax_pct > 0:
            tax_amount = round(taxable_base * (override_tax_pct / 100), 2)
            tax_label  = f"Tax ({override_tax_pct:g}%)"
        elif self.amount_tax and self.amount_tax > 0:
            tax_amount = self.amount_tax
            rate       = round((tax_amount / subtotal * 100) if subtotal else 7, 1)
            tax_label  = f"Tax ({rate}%)"
        else:
            tax_amount = round(taxable_base * 0.07, 2)
            tax_label  = "Tax (7%)"

        def total_row(label, value, color="#555", bold=False, bg="white"):
            fw = "bold" if bold else "normal"
            return f"""
            <tr style="background:{bg};">
                <td style="padding:8px 14px;border-bottom:1px solid #eee;text-align:right;
                           color:{color};font-size:13px;font-weight:{fw};">{label}</td>
                <td style="padding:8px 14px;border-bottom:1px solid #eee;text-align:right;
                           width:110px;font-weight:bold;font-size:13px;color:{color};">
                    {sym}{value:,.2f}
                </td>
            </tr>"""

        totals_rows = total_row("SubTotal", subtotal)
        if discount_amount > 0:
            totals_rows += total_row(f'Discount ({gen_discount}%)', -discount_amount, color="#e74c3c")
        if damage_waiver_amount > 0:
            totals_rows += total_row("&#x1F6E1; Damage Waiver (10%)", damage_waiver_amount, color="#056690")
        if event_location_fee > 0:
            totals_rows += total_row("&#x1F4CD; Non-Residential Location Fee", event_location_fee, color="#056690")
        if setup_surface_fee > 0:
            totals_rows += total_row(f"&#x1F6E0; Setup Surface Fee ({setup_surface_label})", setup_surface_fee, color="#056690")
        if travel_fee > 0:
            totals_rows += total_row("&#x1F697; Travel Fee", travel_fee)
        if misc_fees > 0:
            totals_rows += total_row("Miscellaneous Fees", misc_fees)
        totals_rows += total_row(tax_label, tax_amount)
        totals_rows += f"""
            <tr style="background:#f0f0f0;">
                <td style="padding:10px 14px;text-align:right;font-weight:bold;font-size:15px;color:#1b1b1b;">
                    Grand Total
                </td>
                <td style="padding:10px 14px;text-align:right;font-weight:bold;font-size:16px;color:#1b1b1b;">
                    {sym}{grand_total:,.2f}
                </td>
            </tr>
            <tr style="background:#ffef7a;">
                <td style="padding:8px 14px;text-align:right;color:#056690;font-size:13px;">
                    OR pay 30% deposit today
                </td>
                <td style="padding:8px 14px;text-align:right;font-weight:bold;font-size:13px;color:#056690;">
                    {sym}{deposit_30:,.2f}
                </td>
            </tr>"""

        # ── 6. CTAs ────────────────────────────────────────────────
        def cta_btn(label, url, bg='#056690'):
            return f"""
            <div style="text-align:center;margin:12px 0;">
                <a href="{url}" style="background-color:{bg};color:#ffffff;padding:14px 36px;
                          text-decoration:none;border-radius:4px;font-size:16px;font-weight:bold;
                          display:inline-block;letter-spacing:0.3px;">{label}</a>
            </div>"""

        accept_cta = f"""
            <div style="text-align:center;margin:8px 0 0;">
                <a href="{accept_quote_url}" style="background-color:#056690;color:#ffffff;
                          padding:12px 28px;text-decoration:none;border-radius:4px;font-size:14px;
                          font-weight:bold;display:inline-block;letter-spacing:0.3px;">
                    Pay &amp; Sign Quote (Terms)
                </a>
            </div>
            <p style="color:#666;font-size:12px;margin:10px 0 0;line-height:1.5;text-align:center;">
                Review Freedom Fun USA rental terms and quote acceptance, then continue to secure payment.
            </p>"""

        hero_html = f"""
            <div style="background:#ffef7a;border:2px solid #fdcd15;padding:24px 28px;text-align:center;">
                <h2 style="color:#056690;margin:0 0 14px;font-size:18px;">
                    Your Quote is Ready!
                </h2>
                <p style="color:#555;margin:0 0 8px;font-size:14px;line-height:1.6;">
                    Choose how you'd like to pay on the secure payment page:
                </p>
                <ul style="list-style:none;padding:0;margin:0 0 16px;color:#555;font-size:14px;
                           line-height:2.2;text-align:left;display:inline-block;">
                    <li>&#x2022; Pay <strong>{sym}{grand_total:,.2f}</strong> in full — booking confirmed immediately</li>
                    <li>&#x2022; Pay <strong>{sym}{deposit_30:,.2f}</strong> (30% deposit) — reserve your date now</li>
                </ul>
                {cta_btn('Pay &amp; Confirm Booking', payment_url, '#056690')}
                {accept_cta}
                <p style="color:#056690;font-size:13px;margin:12px 0 0;">
                    &#x1F6E1; Your deposit is always protected by our
                    <strong>Free Rescheduling Promise</strong>
                </p>
            </div>"""

        urgency_html = """
            <div style="background:#ffef7a;padding:24px 32px;
                        border-left:4px solid #fdcd15;border-right:1px solid #e0e0e0;">
                <h3 style="color:#056690;margin:0 0 10px;font-size:16px;">
                    Dates Fill Fast - Don't Miss Out!
                </h3>
                <p style="margin:0 0 10px;color:#555;line-height:1.7;">
                    Most of our customers book within 24-48 hours. Weekends especially go quickly.
                </p>
                <p style="margin:0;color:#555;line-height:1.7;">
                    Secure your event now with just a 30% deposit, and we'll take care of the rest.
                </p>
            </div>"""

        # ── 7. Company + customer info ─────────────────────────────
        company      = self.company_id
        company_name = company.name or 'Freedom Fun USA'
        quote_num    = self.name or ''
        cust_name    = partner.name or ''
        cust_street  = partner.street or ''
        cust_city    = ''
        if partner.city:
            state_name = partner.state_id.name if partner.state_id else ''
            cust_city  = f"{partner.city}, {state_name} {partner.zip or ''}".strip(', ')
        cust_email   = partner.email or ''
        cust_phone   = partner.phone or ''
        created_by   = self.user_id.name if self.user_id else ''
        note         = self.note or ''

        # ── 8. Full email body ─────────────────────────────────────
        email_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;color:#333;font-size:14px;">
            <div style="background:#056690;padding:20px 32px;border-radius:6px 6px 0 0;text-align:center;">
                <h1 style="color:#ffffff;margin:0;font-size:22px;letter-spacing:1px;">{company_name}</h1>
                <p style="color:#bcbcbc;margin:6px 0 0;font-size:13px;">QUOTE #{quote_num}</p>
            </div>
            {hero_html}
            <div style="background:#ffffff;padding:32px 32px 24px;border-left:1px solid #e0e0e0;border-right:1px solid #e0e0e0;">
                <p style="font-size:15px;line-height:1.7;margin:0 0 14px;">
                    Hi there - welcome to Freedom Fun Sarasota!
                </p>
                <p style="line-height:1.7;color:#444;margin:0 0 14px;">
                    We're Tom and Ginger, proud local owners of your Freedom Fun USA store
                    here in Sarasota. We're so glad you found us and can't wait to help you
                    create an unforgettable event.
                </p>
                <p style="line-height:1.7;color:#444;margin:0 0 14px;">
                    At Freedom Fun, we believe life is too short for a bad party. That's why
                    we bring clean, high-quality equipment, show up on time, and deliver our
                    nationally known, over-the-top 5-star service.
                </p>
                <p style="line-height:1.7;margin:0;">
                    Want to see us in action?
                    <a href="#" style="color:#056690;">Facebook Photos</a> |
                    <a href="#" style="color:#056690;">Instagram Gallery</a>
                </p>
            </div>
            <div style="background:#e8f4fb;padding:24px 32px;border-left:4px solid #056690;border-right:1px solid #e0e0e0;">
                <h3 style="color:#056690;margin:0 0 10px;font-size:16px;">
                    Our Legendary Free Rescheduling Promise
                </h3>
                <p style="margin:0;color:#056690;line-height:1.7;">
                    When you place your deposit today, your date is locked in - and you'll
                    never lose it. If anything changes, your deposit becomes a credit that
                    never expires.
                </p>
            </div>
            {urgency_html}
            <div style="background:#ffffff;padding:24px 32px;border-left:1px solid #e0e0e0;border-right:1px solid #e0e0e0;">
                <p style="color:#444;line-height:1.7;font-style:italic;margin:0;">
                    With joy,<br/>
                    <strong>Tom &amp; Ginger Phelps</strong><br/>
                    Owners, Freedom Fun Sarasota<br/>
                    <span style="color:#888;font-size:13px;">Proudly part of the Freedom Fun USA family</span>
                </p>
            </div>
            <div style="background:#f9f9f9;padding:28px 32px;border:1px solid #e0e0e0;border-top:none;">
                <h2 style="color:#1b1b1b;font-size:18px;margin:0 0 20px;border-bottom:2px solid #fdcd15;padding-bottom:10px;">
                    Your Quote
                </h2>
                <table style="width:100%;margin-bottom:24px;border-collapse:collapse;">
                    <tr>
                        <td style="vertical-align:top;width:50%;padding-right:16px;">
                            <p style="margin:0 0 4px;font-weight:bold;color:#1b1b1b;font-size:15px;">{company_name}</p>
                            <p style="margin:0;color:#666;font-size:13px;line-height:1.7;">
                                {cust_name}<br/>
                                {cust_street + '<br/>' if cust_street else ''}
                                {cust_city + '<br/>' if cust_city else ''}
                                {cust_email + '<br/>' if cust_email else ''}
                                {cust_phone}
                            </p>
                        </td>
                        <td style="vertical-align:top;width:50%;text-align:right;">
                            <p style="margin:0;color:#666;font-size:13px;line-height:1.7;">
                                Quote Created by: {created_by}<br/>
                                {f'Customer Comments: {note}' if note else ''}
                            </p>
                        </td>
                    </tr>
                </table>
                <table style="width:100%;border-collapse:collapse;background:white;border:1px solid #e0e0e0;">
                    <thead>
                        <tr style="background:#056690;">
                            <th style="padding:10px 14px;text-align:left;font-size:13px;font-weight:bold;color:white;">Item</th>
                            <th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:bold;color:white;width:60px;">Qty</th>
                            <th style="padding:10px 14px;text-align:right;font-size:13px;font-weight:bold;color:white;width:110px;">Price</th>
                        </tr>
                    </thead>
                    <tbody>{lines_html}</tbody>
                </table>
                <table style="width:100%;border-collapse:collapse;background:white;border:1px solid #e0e0e0;border-top:none;">
                    {totals_rows}
                </table>
            </div>
            <div style="background:#056690;padding:32px;text-align:center;border-radius:0 0 6px 6px;">
                <p style="color:#ccc;font-size:14px;margin:0 0 16px;">
                    Pay in full to lock in your booking, or pay just 30% to reserve your date.
                </p>
                {cta_btn('Pay &amp; Confirm Booking', payment_url, '#056690')}
                {accept_cta}
                <p style="color:#ccc;font-size:13px;margin:16px 0 0;">
                    Your deposit is always protected - it becomes a credit that never expires if plans change.
                </p>
            </div>
        </div>"""

        # ── 9. Send email (no invoice PDF yet) ────────────────────
        email_from = (
            self.env.user.email
            or self.env['ir.config_parameter'].sudo().get_param('mail.catchall.email')
            or 'noreply@example.com'
        )
        mail = self.env['mail.mail'].sudo().create({
            'subject': f'{company_name} - Quote #{quote_num} - Full Payment or 30% Deposit: {amount_str}',
            'email_to': partner.email,
            'email_from': email_from,
            'body_html': email_body,
            'auto_delete': False,
            'model': 'sale.order',
            'res_id': self.id,
        })
        mail.send()
        _logger.info("Quote email sent to %s for order %s", partner.email, self.name)

        return self.id

    def action_create_downpayment_invoice_pos(self, deposit_percent=30):
        """Create a percentage-based downpayment invoice (draft) and return its ID.
        Called by placeOrderAndPay() for 30% / custom splits.
        JS caller adds tip line and posts the invoice itself.
        """
        self.ensure_one()

        wizard = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'percentage',
            'amount': deposit_percent,
            'sale_order_ids': [(6, 0, [self.id])],
        })
        wizard.with_context(
            active_ids=[self.id],
            active_model='sale.order',
        ).create_invoices()

        invoice = self.invoice_ids.filtered(lambda m: m.state == 'draft')[:1]
        if not invoice:
            raise UserError("Downpayment invoice could not be created.")

        # Keep draft invoice aligned with SO order-level fees by applied percentage.
        ratio = (deposit_percent or 0.0) / 100.0
        self._apply_pos_fee_lines_to_invoice(invoice, ratio=ratio, include_tip=False)

        return invoice.id

    def action_send_payment_confirmation_pos(self, invoice_id=None):
        """Send a 'payment received' confirmation email for a fully paid on-spot order.
        No new invoice is created — the already-paid invoice is used for the PDF attachment.
        """
        self.ensure_one()

        invoice = (
            self.env['account.move'].browse(invoice_id)
            if invoice_id
            else self.invoice_ids.filtered(lambda m: m.state == 'posted')[:1]
        )
        if not invoice:
            _logger.warning("action_send_payment_confirmation_pos: no invoice found for order %s", self.name)
            return False

        partner      = invoice.partner_id
        currency     = invoice.currency_id
        sym          = currency.symbol
        company      = self.company_id
        company_name = company.name or 'Freedom Fun USA'
        quote_num    = self.name or ''
        paid_amount_value = invoice.amount_total - invoice.amount_residual
        amount_paid  = f"{sym}{paid_amount_value:,.2f}"

        base_url    = self.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
        if not self.access_token:
            self._portal_ensure_token()
        # Use the public access-token URL for the invoice so customers can open it
        # without needing an Odoo login (the internal /odoo/accounting/... URL is
        # staff-only and returns 404 / redirect-to-login for customers).
        inv_token = invoice.access_token or ''
        if not inv_token:
            import secrets as _s
            inv_token = _s.token_urlsafe(32)
            invoice.sudo().write({'access_token': inv_token})
        invoice_url = f"{base_url}/rental/pay/{invoice.id}?access_token={inv_token}"
        waiver_url  = f"{base_url}/rental/waiver/{self.id}?access_token={self.access_token}"

        email_from = (
            self.env.user.email
            or self.env['ir.config_parameter'].sudo().get_param('mail.catchall.email')
            or 'noreply@example.com'
        )

        email_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 680px;
                    margin: 0 auto; color: #333; font-size: 14px;">

            <!-- HEADER -->
            <div style="background: #056690; padding: 20px 32px;
                        border-radius: 6px 6px 0 0; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 22px;
                            letter-spacing: 1px;">{company_name}</h1>
                <p style="color: #bcbcbc; margin: 6px 0 0; font-size: 13px;">
                    ORDER #{quote_num}
                </p>
            </div>

            <!-- CONFIRMATION BANNER -->
            <div style="background: #e8f4fb; border: 2px solid #056690;
                        padding: 28px; text-align: center;">
                <h2 style="color: #056690; margin: 0 0 10px; font-size: 22px;">
                    &#x2705; Payment Received Successfully!
                </h2>
                <p style="color: #056690; font-size: 15px; margin: 0;">
                    Your full payment of <strong>{amount_paid}</strong> has been received
                    and your booking is confirmed.
                </p>
            </div>

            <!-- BODY -->
            <div style="background: #ffffff; padding: 32px;
                        border-left: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0;">
                <p style="font-size: 15px; line-height: 1.7; margin: 0 0 14px;">
                    Hi {partner.name or 'there'},
                </p>
                <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
                    Thank you for your payment! Your event is now fully booked and confirmed.
                    We're excited to help make your event an unforgettable experience.
                </p>
                <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
                    Invoice reference: <strong>{invoice.name}</strong>
                </p>
            </div>

            <!-- LEGAL WAIVER NOTICE -->
            <div style="background: #ffffff; padding: 20px 32px;
                        border-left: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0;
                        border-top: 1px solid #e0e0e0;">
                <table style="width:100%; border-collapse:collapse;">
                    <tr>
                        <td style="vertical-align:middle; padding-right:16px; width:40px;">
                            <span style="font-size:24px;">&#x1F4CB;</span>
                        </td>
                        <td style="vertical-align:middle;">
                            <p style="margin:0 0 4px; font-size:14px; font-weight:bold; color:#333;">
                                Acknowledgement of Risks &amp; Release of Liability
                            </p>
                            <p style="margin:0; font-size:13px; color:#666; line-height:1.6;">
                                Please review our waiver and liability release document before your event.
                                <a href="{waiver_url}"
                                   style="color:#875A7B; font-weight:bold; text-decoration:none;">
                                    View Legal Document &rarr;
                                </a>
                            </p>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- RESCHEDULING PROMISE -->
            <div style="background: #e8f4fb; padding: 24px 32px;
                        border-left: 4px solid #056690; border-right: 1px solid #e0e0e0;">
                <h3 style="color: #056690; margin: 0 0 10px; font-size: 16px;">
                    Our Legendary Free Rescheduling Promise
                </h3>
                <p style="margin: 0; color: #056690; line-height: 1.7;">
                    If anything changes, your payment becomes a credit that never expires —
                    book with total peace of mind.
                </p>
            </div>

            <!-- SIGNATURE -->
            <div style="background: #ffffff; padding: 24px 32px;
                        border: 1px solid #e0e0e0; border-top: none;
                        border-radius: 0 0 6px 6px;">
                <p style="color: #444; line-height: 1.7; font-style: italic; margin: 0;">
                    With joy,<br/>
                    <strong>Tom &amp; Ginger Phelps</strong><br/>
                    Owners, Freedom Fun Sarasota
                </p>
            </div>

        </div>
        """

        # Attach invoice PDF
        attachment_ids = []
        try:
            report = self.env.ref('account.account_invoices')
            pdf_content, _ = report._render_qweb_pdf([invoice.id])
            attachment = self.env['ir.attachment'].sudo().create({
                'name': f'{invoice.name}.pdf',
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'mimetype': 'application/pdf',
            })
            attachment_ids = [(4, attachment.id)]
        except Exception as e:
            _logger.warning("Could not attach invoice PDF for confirmation: %s", e)

        mail = self.env['mail.mail'].sudo().create({
            'subject': f'{company_name} - Order #{quote_num} - Payment Confirmed ✓',
            'email_to': partner.email,
            'email_from': email_from,
            'body_html': email_body,
            'auto_delete': False,
            'model': 'account.move',
            'res_id': invoice.id,
            'attachment_ids': attachment_ids,
        })
        mail.send()
        _logger.info("Payment confirmation sent to %s for order %s", partner.email, self.name)
        return True