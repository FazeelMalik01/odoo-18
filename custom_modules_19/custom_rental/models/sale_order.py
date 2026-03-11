# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import logging
import secrets

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Customer display fields (readonly, with labels like Event information)
    partner_company_display = fields.Char(
        related="partner_id.commercial_company_name", string="Company", readonly=True
    )
    partner_email_display = fields.Char(
        related="partner_id.email", string="Email", readonly=True
    )
    partner_phone_display = fields.Char(
        related="partner_id.phone", string="Phone", readonly=True
    )
    partner_phone_secondary_display = fields.Char(
        related="partner_id.phone_secondary", string="Secondary Phone", readonly=True
    )
    partner_street_display = fields.Char(
        related="partner_id.street", string="Address", readonly=True
    )
    partner_street2_display = fields.Char(
        related="partner_id.street2", string="Address (cont.)", readonly=True
    )
    partner_city_display = fields.Char(
        related="partner_id.city", string="City", readonly=True
    )
    partner_state_id_display = fields.Many2one(
        related="partner_id.state_id", string="State", readonly=True
    )
    partner_zip_display = fields.Char(
        related="partner_id.zip", string="Zip/Postal code", readonly=True
    )
    partner_country_id_display = fields.Many2one(
        related="partner_id.country_id", string="Country", readonly=True
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

    @api.depends("event_zip", "company_id")
    def _compute_event_zip_verification_id(self):
        """Set matching rental.zipcode from EVENT zip so status persists after save."""
        RentalZip = self.env["rental.zipcode"]
        for order in self:
            if not order.event_zip:
                order.event_zip_verification_id = False
                continue
            domain = [("name", "=", order.event_zip)]
            if order.company_id:
                domain.append(("company_id", "in", [False, order.company_id.id]))
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
        """When creating with Same as billing checked, fill event address from partner if not provided."""
        for vals in vals_list:
            if vals.get("event_same_as_billing") and vals.get("partner_id"):
                partner = self.env["res.partner"].browse(vals["partner_id"])
                if partner and "event_street" not in vals:
                    vals.update(
                        {
                            "event_street": partner.street,
                            "event_street2": partner.street2,
                            "event_city": partner.city,
                            "event_state_id": (
                                partner.state_id.id if partner.state_id else False
                            ),
                            "event_zip": partner.zip,
                            "event_country_id": (
                                partner.country_id.id if partner.country_id else False
                            ),
                        }
                    )
        return super().create(vals_list)

    def write(self, vals):
        """When saving with Same as billing checked, ensure event address is synced from partner (readonly fields may be sent empty)."""
        if len(self) == 1 and self.event_same_as_billing and self.partner_id:
            vals = dict(vals)

            # When same-as-billing: inject partner address for any field missing or empty so we don't save blanks
            def _set_if_missing_or_empty(key, value):
                if key not in vals or vals.get(key) in (None, False, ""):
                    vals[key] = value

            _set_if_missing_or_empty("event_street", self.partner_id.street)
            _set_if_missing_or_empty("event_street2", self.partner_id.street2)
            _set_if_missing_or_empty("event_city", self.partner_id.city)
            _set_if_missing_or_empty(
                "event_state_id",
                self.partner_id.state_id.id if self.partner_id.state_id else False,
            )
            _set_if_missing_or_empty("event_zip", self.partner_id.zip)
            _set_if_missing_or_empty(
                "event_country_id",
                self.partner_id.country_id.id if self.partner_id.country_id else False,
            )
        return super().write(vals)

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

    # def action_create_and_send_invoice_pos(self, deposit_percent=0):
    #     """Create invoice and send Freedom Fun quote email with payment link"""
    #     self.ensure_one()

    #     # ── 0. Confirm the sale order if still draft ──────────
    #     if self.state in ('draft', 'sent'):
    #         self.action_confirm()

    #     # ── 1. Create wizard & invoice ────────────────────────
    #     if deposit_percent > 0:
    #         wizard = self.env['sale.advance.payment.inv'].create({
    #             'advance_payment_method': 'percentage',
    #             'amount': deposit_percent,
    #             'sale_order_ids': [(6, 0, [self.id])],
    #         })
    #     else:
    #         wizard = self.env['sale.advance.payment.inv'].create({
    #             'advance_payment_method': 'percentage',
    #             'amount': 100,
    #             'sale_order_ids': [(6, 0, [self.id])],
    #         })

    #     wizard.with_context(
    #         active_ids=[self.id],
    #         active_model='sale.order'
    #     ).create_invoices()

    #     # ── 2. Find the created draft invoice ─────────────────
    #     invoice = self.env['account.move'].search([
    #         ('invoice_origin', '=', self.name),
    #         ('move_type', '=', 'out_invoice'),
    #         ('state', '=', 'draft'),
    #     ], limit=1)

    #     if not invoice:
    #         raise UserError("Invoice could not be created.")

    #     # ── 3. Confirm the invoice ────────────────────────────
    #     invoice.action_post()

    #     # ── 4. Ensure access token exists ─────────────────────
    #     if not invoice.access_token:
    #         invoice.sudo().write({'access_token': secrets.token_urlsafe(32)})

    #     access_token = invoice.access_token
    #     base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
    #     payment_url = f"{base_url}/rental/pay/{invoice.id}?access_token={access_token}"

    #     _logger.info("Invoice %s payment URL: %s", invoice.name, payment_url)

    #     # ── 5. Partner / currency / symbol ────────────────────
    #     partner  = invoice.partner_id
    #     currency = invoice.currency_id
    #     sym      = currency.symbol

    #     # ── 6. Duration helpers ───────────────────────────────
    #     def _duration_hours(start_dt, end_dt):
    #         if not start_dt or not end_dt:
    #             return 1
    #         try:
    #             hours = (end_dt - start_dt).total_seconds() / 3600
    #             return max(1.0, hours)
    #         except Exception:
    #             return 1

    #     def _fmt_duration(hours):
    #         return f"{int(hours)} hrs" if hours == int(hours) else f"{hours:.1f} hrs"

    #     # ── 7. Build order lines HTML ─────────────────────────
    #     lines_html = ""
    #     for line in self.order_line:
    #         date_str     = ""
    #         duration_str = ""
    #         start_dt     = None
    #         end_dt       = None

    #         if hasattr(line, 'start_date') and line.start_date:
    #             start_dt = line.start_date
    #             end_dt   = line.return_date if hasattr(line, 'return_date') and line.return_date else None
    #             try:
    #                 date_str = start_dt.strftime('%a, %b %-d  %-I:%M %p')
    #                 if end_dt:
    #                     date_str += ' \u2192 ' + end_dt.strftime('%-I:%M %p')
    #                     duration_str = _fmt_duration(_duration_hours(start_dt, end_dt))
    #             except Exception:
    #                 date_str = str(start_dt)

    #         unit_price     = line.price_unit or 0
    #         duration_hours = _duration_hours(start_dt, end_dt) if (start_dt and end_dt) else 1
    #         line_total     = unit_price * duration_hours * line.product_uom_qty

    #         duration_badge = (
    #             f'<span style="font-size:11px; background:#875A7B; color:white; '
    #             f'border-radius:3px; padding:1px 6px; margin-left:6px;">'
    #             f'{duration_str}</span>'
    #         ) if duration_str else ""

    #         price_detail = (
    #             f'<span style="font-size:11px; color:#888;">'
    #             f'{sym}{unit_price:,.2f} &times; {_fmt_duration(duration_hours)}'
    #             f'</span><br/>'
    #         ) if duration_hours > 1 else ""

    #         code_row = (
    #             f'<br/><span style="font-size: 12px; color: #999;">'
    #             f'{line.product_id.default_code}</span>'
    #         ) if line.product_id.default_code else ""

    #         lines_html += f"""
    #         <tr>
    #             <td style="padding: 10px 14px; border-bottom: 1px solid #e8e8e8; vertical-align: top;">
    #                 <strong style="font-size: 14px; color: #222;">{line.product_id.name or ''}</strong>
    #                 {duration_badge}
    #                 {f'<br/><span style="font-size: 12px; color: #888;">{date_str}</span>' if date_str else ''}
    #                 {f'<br/>{price_detail}' if price_detail else ''}
    #                 {code_row}
    #             </td>
    #             <td style="padding: 10px 14px; border-bottom: 1px solid #e8e8e8;
    #                        text-align: center; color: #555; font-size: 14px;">
    #                 x {int(line.product_uom_qty)}
    #             </td>
    #             <td style="padding: 10px 14px; border-bottom: 1px solid #e8e8e8;
    #                        text-align: right; font-weight: bold; font-size: 14px;">
    #                 {sym}{line_total:,.2f}
    #             </td>
    #         </tr>
    #         """

    #     # ── 8. Compute totals ─────────────────────────────────
    #     subtotal   = self.amount_untaxed
    #     travel_fee = getattr(self, 'override_travel_fee', 0.0) or 0.0
    #     misc_fees  = getattr(self, 'miscellaneous_fees', 0.0) or 0.0

    #     # Discount
    #     gen_discount     = getattr(self, 'general_discount', 0.0) or 0.0
    #     discount_amount  = subtotal * (gen_discount / 100) if gen_discount > 0 else 0.0

    #     # Coupon — read from sale order note or field if available
    #     coupon_discount = 0.0  # not stored on sale.order currently

    #     # Tax
    #     override_tax = getattr(self, 'override_tax_amount', 0.0) or 0.0
    #     if override_tax > 0:
    #         tax_amount = override_tax
    #         tax_label  = "Tax (Override)"
    #     elif self.amount_tax and self.amount_tax > 0:
    #         tax_amount = self.amount_tax
    #         rate       = round((tax_amount / subtotal * 100) if subtotal else 7, 1)
    #         tax_label  = f"Tax ({rate}%)"
    #     else:
    #         # Fallback: 7% of subtotal after discount
    #         tax_amount = max(0, subtotal - discount_amount) * 0.07
    #         tax_label  = "Tax (7%)"

    #     # Grand total = subtotal - discount + travel + misc + tax
    #     grand_total = subtotal - discount_amount + travel_fee + misc_fees + tax_amount
    #     deposit_amt = invoice.amount_residual
    #     remaining   = grand_total - deposit_amt

    #     # ── 9. Company + customer info ────────────────────────
    #     company      = self.company_id
    #     company_name = company.name or 'Freedom Fun USA'
    #     quote_num    = self.name or ''

    #     cust_name   = partner.name or ''
    #     cust_street = partner.street or ''
    #     cust_city   = ''
    #     if partner.city:
    #         state_name = partner.state_id.name if partner.state_id else ''
    #         cust_city  = f"{partner.city}, {state_name} {partner.zip or ''}".strip(', ')
    #     cust_email  = partner.email or ''
    #     cust_phone  = partner.phone or ''
    #     created_by  = self.user_id.name if self.user_id else ''
    #     note        = self.note or ''

    #     # ── 10. Conditional totals rows ───────────────────────
    #     def total_row(label, value, color="#555", bold=False, bg="white"):
    #         fw = "bold" if bold else "normal"
    #         return f"""
    #         <tr style="background:{bg};">
    #             <td style="padding:8px 14px; border-bottom:1px solid #eee;
    #                        text-align:right; color:{color};
    #                        font-size:13px; font-weight:{fw};">{label}</td>
    #             <td style="padding:8px 14px; border-bottom:1px solid #eee;
    #                        text-align:right; width:110px;
    #                        font-weight:bold; font-size:13px; color:{color};">
    #                 {sym}{value:,.2f}
    #             </td>
    #         </tr>"""

    #     totals_rows = total_row("SubTotal", subtotal)

    #     if discount_amount > 0:
    #         totals_rows += total_row(
    #             f'Discount ({gen_discount}%)', -discount_amount, color="#e74c3c"
    #         )

    #     if coupon_discount > 0:
    #         totals_rows += total_row("Coupon Discount", -coupon_discount, color="#e74c3c")

    #     if travel_fee > 0:
    #         totals_rows += total_row("Travel Fee", travel_fee)

    #     if misc_fees > 0:
    #         totals_rows += total_row("Miscellaneous Fees", misc_fees)

    #     # Tax always shown
    #     totals_rows += total_row(tax_label, tax_amount)

    #     # Grand total row
    #     totals_rows += f"""
    #         <tr style="background:#f0f0f0;">
    #             <td style="padding:10px 14px; text-align:right;
    #                        font-weight:bold; font-size:15px; color:#1a1a2e;">
    #                 Grand Total
    #             </td>
    #             <td style="padding:10px 14px; text-align:right;
    #                        font-weight:bold; font-size:16px; color:#1a1a2e;">
    #                 {sym}{grand_total:,.2f}
    #             </td>
    #         </tr>"""

    #     # Deposit row — only if deposit_percent > 0
    #     if deposit_percent > 0:
    #         totals_rows += f"""
    #         <tr style="background:#fff3e0;">
    #             <td style="padding:10px 14px; text-align:right;
    #                        font-weight:bold; color:#e65100; font-size:14px;">
    #                 Due Today ({deposit_percent}% Deposit)
    #             </td>
    #             <td style="padding:10px 14px; text-align:right;
    #                        font-weight:bold; color:#e65100; font-size:15px;">
    #                 {sym}{deposit_amt:,.2f}
    #             </td>
    #         </tr>
    #         <tr style="background:#fafafa;">
    #             <td style="padding:8px 14px; text-align:right;
    #                        color:#888; font-size:12px;">
    #                 Remaining after deposit
    #             </td>
    #             <td style="padding:8px 14px; text-align:right;
    #                        color:#888; font-size:12px;">
    #                 {sym}{remaining:,.2f}
    #             </td>
    #         </tr>"""

    #     # ── 11. CTA button helper ─────────────────────────────
    #     def cta_btn(bg='#c0392b'):
    #         return f"""
    #         <div style="text-align: center; margin: 20px 0;">
    #             <a href="{payment_url}"
    #                style="background-color: {bg}; color: #ffffff;
    #                       padding: 14px 36px; text-decoration: none;
    #                       border-radius: 4px; font-size: 16px; font-weight: bold;
    #                       display: inline-block; letter-spacing: 0.3px;">
    #                 Click here to Complete your Order
    #             </a>
    #         </div>"""

    #     # ── 12. Build full email ──────────────────────────────
    #     email_body = f"""
    #     <div style="font-family: Arial, sans-serif; max-width: 680px;
    #                 margin: 0 auto; color: #333; font-size: 14px;">

    #         <!-- TOP HEADER -->
    #         <div style="background: #1a1a2e; padding: 20px 32px;
    #                     border-radius: 6px 6px 0 0; text-align: center;">
    #             <h1 style="color: #ffffff; margin: 0; font-size: 22px;
    #                         letter-spacing: 1px;">{company_name}</h1>
    #             <p style="color: #aaa; margin: 6px 0 0; font-size: 13px;">
    #                 QUOTE #{quote_num}
    #             </p>
    #         </div>

    #         <!-- URGENT NOTICE -->
    #         <div style="background: #fff8e1; border: 2px solid #f9a825;
    #                     padding: 24px 28px; text-align: center;">
    #             <h2 style="color: #e65100; margin: 0 0 14px; font-size: 18px;">
    #                 Important: This Is a Quote - Not a Reservation
    #             </h2>
    #             <ul style="list-style: none; padding: 0; margin: 0 0 16px;
    #                        color: #555; font-size: 14px; line-height: 2.2;
    #                        text-align: left; display: inline-block;">
    #                 <li>&#x2022; This quote does not hold your date yet</li>
    #                 <li>&#x2022; Your event date is only secured once you complete your order</li>
    #                 <li>&#x2022; It takes less than a minute to lock in your date</li>
    #             </ul>
    #             <p style="color: #555; margin: 0 0 16px;">
    #                 Click below to complete your order and secure your date.
    #             </p>
    #             {cta_btn('#c0392b')}
    #             <p style="color: #2e7d32; font-size: 13px; margin: 12px 0 0;">
    #                 &#x1F6E1; Your deposit is always protected by our
    #                 <strong>Free Rescheduling Promise</strong>
    #             </p>
    #         </div>

    #         <!-- WELCOME -->
    #         <div style="background: #ffffff; padding: 32px 32px 24px;
    #                     border-left: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0;">
    #             <p style="font-size: 15px; line-height: 1.7; margin: 0 0 14px;">
    #                 Hi there - welcome to Freedom Fun Sarasota!
    #             </p>
    #             <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
    #                 We're Tom and Ginger, proud local owners of your Freedom Fun USA store
    #                 here in Sarasota. We're so glad you found us and can't wait to help you
    #                 create an unforgettable event.
    #             </p>
    #             <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
    #                 We know how stressful planning an event can be. Maybe you've dealt with
    #                 companies that show up late (or not at all), bring worn-out equipment,
    #                 or leave you hanging the day of the party.
    #             </p>
    #             <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
    #                 At Freedom Fun, we believe life is too short for a bad party. That's why
    #                 we bring clean, high-quality equipment, show up on time, and deliver our
    #                 nationally known, over-the-top 5-star service - right here in your backyard.
    #             </p>
    #             <p style="line-height: 1.7; color: #444; margin: 0 0 14px;">
    #                 We've helped thousands of families, schools, and companies celebrate
    #                 across the U.S., including <strong>Facebook, Tesla, Chick-fil-A, YMCA,
    #                 Amazon, and LegalZoom</strong>. But what we care most about is
    #                 <strong>you</strong> - and making your event stress-free and FUN.
    #             </p>
    #             <p style="line-height: 1.7; margin: 0;">
    #                 Want to see us in action?
    #                 <a href="#" style="color: #c0392b;">Facebook Photos</a> |
    #                 <a href="#" style="color: #c0392b;">Instagram Gallery</a>
    #             </p>
    #         </div>

    #         <!-- RESCHEDULING PROMISE -->
    #         <div style="background: #e8f5e9; padding: 24px 32px;
    #                     border-left: 4px solid #2e7d32; border-right: 1px solid #e0e0e0;">
    #             <h3 style="color: #1b5e20; margin: 0 0 10px; font-size: 16px;">
    #                 Our Legendary Free Rescheduling Promise
    #             </h3>
    #             <p style="margin: 0; color: #2e7d32; line-height: 1.7;">
    #                 When you place your deposit today, your date is locked in - and you'll
    #                 never lose it. If anything changes, your deposit becomes a credit that
    #                 never expires, so you can book with total peace of mind.
    #             </p>
    #         </div>

    #         <!-- URGENCY -->
    #         <div style="background: #fff3e0; padding: 24px 32px;
    #                     border-left: 4px solid #e65100; border-right: 1px solid #e0e0e0;">
    #             <h3 style="color: #bf360c; margin: 0 0 10px; font-size: 16px;">
    #                 Dates Fill Fast - Don't Miss Out!
    #             </h3>
    #             <p style="margin: 0 0 10px; color: #555; line-height: 1.7;">
    #                 Most of our customers book within 24-48 hours. Weekends especially go quickly.
    #             </p>
    #             <p style="margin: 0; color: #555; line-height: 1.7;">
    #                 Secure your event now with just a
    #                 <strong>{deposit_percent}% deposit</strong>, and we'll take care
    #                 of the rest. Click "Complete Your Order" below and let's make your event amazing.
    #             </p>
    #         </div>

    #         <!-- SIGNATURE -->
    #         <div style="background: #ffffff; padding: 24px 32px;
    #                     border-left: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0;">
    #             <p style="color: #444; line-height: 1.7; font-style: italic; margin: 0;">
    #                 With joy,<br/>
    #                 <strong>Tom &amp; Ginger Phelps</strong><br/>
    #                 Owners, Freedom Fun Sarasota<br/>
    #                 <span style="color: #888; font-size: 13px;">
    #                     Proudly part of the Freedom Fun USA family
    #                 </span>
    #             </p>
    #         </div>

    #         <!-- QUOTE DETAILS -->
    #         <div style="background: #f9f9f9; padding: 28px 32px;
    #                     border: 1px solid #e0e0e0; border-top: none;">

    #             <h2 style="color: #1a1a2e; font-size: 18px; margin: 0 0 20px;
    #                         border-bottom: 2px solid #875A7B; padding-bottom: 10px;">
    #                 Your Quote
    #             </h2>

    #             <table style="width: 100%; margin-bottom: 24px; border-collapse: collapse;">
    #                 <tr>
    #                     <td style="vertical-align: top; width: 50%; padding-right: 16px;">
    #                         <p style="margin: 0 0 4px; font-weight: bold;
    #                                   color: #1a1a2e; font-size: 15px;">{company_name}</p>
    #                         <p style="margin: 0; color: #666; font-size: 13px; line-height: 1.7;">
    #                             {cust_name}<br/>
    #                             {cust_street + '<br/>' if cust_street else ''}
    #                             {cust_city + '<br/>' if cust_city else ''}
    #                             {cust_email + '<br/>' if cust_email else ''}
    #                             {cust_phone}
    #                         </p>
    #                     </td>
    #                     <td style="vertical-align: top; width: 50%; text-align: right;">
    #                         <p style="margin: 0; color: #666; font-size: 13px; line-height: 1.7;">
    #                             Quote Created by: {created_by}<br/>
    #                             {f'Customer Comments: {note}' if note else ''}
    #                         </p>
    #                     </td>
    #                 </tr>
    #             </table>

    #             <!-- Line Items -->
    #             <table style="width: 100%; border-collapse: collapse;
    #                           background: white; border: 1px solid #e0e0e0;">
    #                 <thead>
    #                     <tr style="background: #875A7B;">
    #                         <th style="padding:10px 14px; text-align:left;
    #                                    font-size:13px; font-weight:bold; color:white;">Item</th>
    #                         <th style="padding:10px 14px; text-align:center;
    #                                    font-size:13px; font-weight:bold;
    #                                    color:white; width:60px;">Qty</th>
    #                         <th style="padding:10px 14px; text-align:right;
    #                                    font-size:13px; font-weight:bold;
    #                                    color:white; width:110px;">Price</th>
    #                     </tr>
    #                 </thead>
    #                 <tbody>{lines_html}</tbody>
    #             </table>

    #             <!-- Totals — only non-zero rows shown -->
    #             <table style="width: 100%; border-collapse: collapse;
    #                           background: white; border: 1px solid #e0e0e0; border-top: none;">
    #                 {totals_rows}
    #             </table>
    #         </div>

    #         <!-- BOTTOM CTA -->
    #         <div style="background: #1a1a2e; padding: 32px;
    #                     text-align: center; border-radius: 0 0 6px 6px;">
    #             {cta_btn('#875A7B')}
    #             <p style="color: #ccc; font-size: 13px; margin: 16px 0 6px;">
    #                 Only a deposit is required to lock in your date.
    #             </p>
    #             <p style="color: #ccc; font-size: 13px; margin: 0 0 6px;">
    #                 Your deposit is always protected - it becomes a credit
    #                 that never expires if plans change.
    #             </p>
    #             <p style="color: #ccc; font-size: 13px; margin: 0 0 20px;">
    #                 Book now while your preferred date is still available!
    #             </p>
    #             <p style="margin: 0;">
    #                 <a href="#" style="color: #875A7B; font-size: 12px;">
    #                     For details, see our Full Rescheduling &amp; Cancellation Policy.
    #                 </a>
    #             </p>
    #         </div>

    #     </div>
    #     """

    #     # ── 13. Attach invoice PDF ────────────────────────────
    #     attachment_ids = []
    #     try:
    #         report = self.env.ref('account.account_invoices')
    #         pdf_content, _ = report._render_qweb_pdf([invoice.id])
    #         attachment = self.env['ir.attachment'].sudo().create({
    #             'name': f'{invoice.name}.pdf',
    #             'type': 'binary',
    #             'datas': base64.b64encode(pdf_content),
    #             'res_model': 'account.move',
    #             'res_id': invoice.id,
    #             'mimetype': 'application/pdf',
    #         })
    #         attachment_ids = [(4, attachment.id)]
    #     except Exception as e:
    #         _logger.warning("Could not attach invoice PDF: %s", e)

    #     # ── 14. Send email ────────────────────────────────────
    #     email_from = (
    #         self.env.user.email
    #         or self.env['ir.config_parameter'].sudo().get_param('mail.catchall.email')
    #         or 'noreply@example.com'
    #     )

    #     amount_str = f"{sym}{invoice.amount_residual:,.2f}"

    #     mail = self.env['mail.mail'].sudo().create({
    #         'subject': f'{company_name} - Quote #{quote_num} - Deposit Due: {amount_str}',
    #         'email_to': partner.email,
    #         'email_from': email_from,
    #         'body_html': email_body,
    #         'auto_delete': False,
    #         'model': 'account.move',
    #         'res_id': invoice.id,
    #         'attachment_ids': attachment_ids,
    #     })

    #     mail.send()
    #     _logger.info("Quote email sent to %s for order %s", partner.email, self.name)

    #     return invoice.id
    def action_create_and_send_invoice_pos(self, deposit_percent=0):
        """Create invoice and send Freedom Fun quote email with payment link"""
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
        wizard.with_context(
            active_ids=[self.id],
            active_model='sale.order'
        ).create_invoices()

        invoice = self.invoice_ids.filtered(lambda m: m.state == 'draft')[:1]

        if not invoice:
            raise UserError("Invoice could not be created.")

        # ── 3. Confirm the invoice ────────────────────────────
        invoice.action_post()

        # ── 4. Ensure access token exists ─────────────────────
        if not invoice.access_token:
            invoice.sudo().write({'access_token': secrets.token_urlsafe(32)})

        access_token = invoice.access_token
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
        payment_url = f"{base_url}/rental/pay/{invoice.id}?access_token={access_token}"

        _logger.info("Invoice %s payment URL: %s", invoice.name, payment_url)

        # ── 5. Partner / currency / symbol ────────────────────
        partner  = invoice.partner_id
        currency = invoice.currency_id
        sym      = currency.symbol

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
        # ── 7. Build order lines HTML ─────────────────────────
        lines_html = ""
        for line in self.order_line:

            # ── Skip ghost lines (no product, zero qty, or $0) ──
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

            # price_unit already includes base price + time charge — do NOT multiply by hours
            line_total = unit_price * line.product_uom_qty

            duration_badge = (
                f'<span style="font-size:11px; background:#875A7B; color:white; '
                f'border-radius:3px; padding:1px 6px; margin-left:6px;">'
                f'{duration_str}</span>'
            ) if duration_str else ""

            # price_detail removed — unit_price already bakes in time charge,
            # showing "X × Y hrs" would be misleading and mathematically wrong
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
        gen_discount     = getattr(self, 'general_discount', 0.0) or 0.0
        discount_amount  = subtotal * (gen_discount / 100) if gen_discount > 0 else 0.0

        # Coupon — read from sale order note or field if available
        coupon_discount = 0.0  # not stored on sale.order currently

        # Tax
        override_tax = getattr(self, 'override_tax_amount', 0.0) or 0.0
        if override_tax > 0:
            tax_amount = override_tax
            tax_label  = "Tax (Override)"
        elif self.amount_tax and self.amount_tax > 0:
            tax_amount = self.amount_tax
            rate       = round((tax_amount / subtotal * 100) if subtotal else 7, 1)
            tax_label  = f"Tax ({rate}%)"
        else:
            # Fallback: 7% of subtotal after discount
            tax_amount = max(0, subtotal - discount_amount) * 0.07
            tax_label  = "Tax (7%)"

        # Grand total = subtotal - discount + travel + misc + tax
        grand_total = subtotal - discount_amount + travel_fee + misc_fees + tax_amount
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

        # ── 10. Conditional totals rows ───────────────────────
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

        if coupon_discount > 0:
            totals_rows += total_row("Coupon Discount", -coupon_discount, color="#e74c3c")

        if travel_fee > 0:
            totals_rows += total_row("Travel Fee", travel_fee)

        if misc_fees > 0:
            totals_rows += total_row("Miscellaneous Fees", misc_fees)

        # Tax always shown
        totals_rows += total_row(tax_label, tax_amount)

        # Grand total row
        totals_rows += f"""
            <tr style="background:#f0f0f0;">
                <td style="padding:10px 14px; text-align:right;
                           font-weight:bold; font-size:15px; color:#1a1a2e;">
                    Grand Total
                </td>
                <td style="padding:10px 14px; text-align:right;
                           font-weight:bold; font-size:16px; color:#1a1a2e;">
                    {sym}{grand_total:,.2f}
                </td>
            </tr>"""

        # Deposit row — only if deposit_percent > 0
        if deposit_percent > 0:
            totals_rows += f"""
            <tr style="background:#fff3e0;">
                <td style="padding:10px 14px; text-align:right;
                           font-weight:bold; color:#e65100; font-size:14px;">
                    Due Today ({deposit_percent}% Deposit)
                </td>
                <td style="padding:10px 14px; text-align:right;
                           font-weight:bold; color:#e65100; font-size:15px;">
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

        # ── 11. CTA button helper ─────────────────────────────
        def cta_btn(bg='#c0392b'):
            return f"""
            <div style="text-align: center; margin: 20px 0;">
                <a href="{payment_url}"
                   style="background-color: {bg}; color: #ffffff;
                          padding: 14px 36px; text-decoration: none;
                          border-radius: 4px; font-size: 16px; font-weight: bold;
                          display: inline-block; letter-spacing: 0.3px;">
                    Click here to Complete your Order
                </a>
            </div>"""

        # ── 12. Build full email ──────────────────────────────
        email_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 680px;
                    margin: 0 auto; color: #333; font-size: 14px;">

            <!-- TOP HEADER -->
            <div style="background: #1a1a2e; padding: 20px 32px;
                        border-radius: 6px 6px 0 0; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 22px;
                            letter-spacing: 1px;">{company_name}</h1>
                <p style="color: #aaa; margin: 6px 0 0; font-size: 13px;">
                    QUOTE #{quote_num}
                </p>
            </div>

            <!-- URGENT NOTICE -->
            <div style="background: #fff8e1; border: 2px solid #f9a825;
                        padding: 24px 28px; text-align: center;">
                <h2 style="color: #e65100; margin: 0 0 14px; font-size: 18px;">
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
                    Click below to complete your order and secure your date.
                </p>
                {cta_btn('#c0392b')}
                <p style="color: #2e7d32; font-size: 13px; margin: 12px 0 0;">
                    &#x1F6E1; Your deposit is always protected by our
                    <strong>Free Rescheduling Promise</strong>
                </p>
            </div>

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
                    <a href="#" style="color: #c0392b;">Facebook Photos</a> |
                    <a href="#" style="color: #c0392b;">Instagram Gallery</a>
                </p>
            </div>

            <!-- RESCHEDULING PROMISE -->
            <div style="background: #e8f5e9; padding: 24px 32px;
                        border-left: 4px solid #2e7d32; border-right: 1px solid #e0e0e0;">
                <h3 style="color: #1b5e20; margin: 0 0 10px; font-size: 16px;">
                    Our Legendary Free Rescheduling Promise
                </h3>
                <p style="margin: 0; color: #2e7d32; line-height: 1.7;">
                    When you place your deposit today, your date is locked in - and you'll
                    never lose it. If anything changes, your deposit becomes a credit that
                    never expires, so you can book with total peace of mind.
                </p>
            </div>

            <!-- URGENCY -->
            <div style="background: #fff3e0; padding: 24px 32px;
                        border-left: 4px solid #e65100; border-right: 1px solid #e0e0e0;">
                <h3 style="color: #bf360c; margin: 0 0 10px; font-size: 16px;">
                    Dates Fill Fast - Don't Miss Out!
                </h3>
                <p style="margin: 0 0 10px; color: #555; line-height: 1.7;">
                    Most of our customers book within 24-48 hours. Weekends especially go quickly.
                </p>
                <p style="margin: 0; color: #555; line-height: 1.7;">
                    Secure your event now with just a
                    <strong>{deposit_percent}% deposit</strong>, and we'll take care
                    of the rest. Click "Complete Your Order" below and let's make your event amazing.
                </p>
            </div>

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

                <h2 style="color: #1a1a2e; font-size: 18px; margin: 0 0 20px;
                            border-bottom: 2px solid #875A7B; padding-bottom: 10px;">
                    Your Quote
                </h2>

                <table style="width: 100%; margin-bottom: 24px; border-collapse: collapse;">
                    <tr>
                        <td style="vertical-align: top; width: 50%; padding-right: 16px;">
                            <p style="margin: 0 0 4px; font-weight: bold;
                                      color: #1a1a2e; font-size: 15px;">{company_name}</p>
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
                        <tr style="background: #875A7B;">
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

                <!-- Totals — only non-zero rows shown -->
                <table style="width: 100%; border-collapse: collapse;
                              background: white; border: 1px solid #e0e0e0; border-top: none;">
                    {totals_rows}
                </table>
            </div>

            <!-- BOTTOM CTA -->
            <div style="background: #1a1a2e; padding: 32px;
                        text-align: center; border-radius: 0 0 6px 6px;">
                {cta_btn('#875A7B')}
                <p style="color: #ccc; font-size: 13px; margin: 16px 0 6px;">
                    Only a deposit is required to lock in your date.
                </p>
                <p style="color: #ccc; font-size: 13px; margin: 0 0 6px;">
                    Your deposit is always protected - it becomes a credit
                    that never expires if plans change.
                </p>
                <p style="color: #ccc; font-size: 13px; margin: 0 0 20px;">
                    Book now while your preferred date is still available!
                </p>
                <p style="margin: 0;">
                    <a href="#" style="color: #875A7B; font-size: 12px;">
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

        amount_str = f"{sym}{invoice.amount_residual:,.2f}"

        mail = self.env['mail.mail'].sudo().create({
            'subject': f'{company_name} - Quote #{quote_num} - Deposit Due: {amount_str}',
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