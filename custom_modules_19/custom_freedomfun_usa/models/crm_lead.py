import logging
import re
from odoo import models, fields, api
from datetime import timedelta

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    event_type = fields.Char("Event Type")
    party_notes = fields.Text("Party Notes")
    page_url = fields.Char("Page URL")
    contact_type = fields.Char("Preferred Contact")
    submitted_at = fields.Datetime("Submitted Date", readonly=True)
    stage_changed_at = fields.Datetime("Stage Changed At", readonly=True)
    collection_id = fields.Char()
    locale_id = fields.Char()
    catalog_id = fields.Char()
    location_id = fields.Char()
    delay_status = fields.Selection(
        [
            ("on_time", "On Time"),
            ("delayed", "Delayed"),
        ],
        string="Lead Status",
        default="on_time",
        store=True,
    )
    delay_sms_sent_at = fields.Datetime(string="Delay SMS Sent At", readonly=True)

    def _normalize_branch_name(self, name):
        """Normalize branch name for matching (same logic as webhook)."""
        if not name:
            return ""
        name = re.sub(r"\(.*?\)", "", name)
        name = re.sub(r"[^a-zA-Z0-9\s]", " ", name)
        name = name.lower()
        name = " ".join(name.split())
        return name.strip()

    def _company_from_page_url(self, page_url):

        if not page_url or "/location/" not in page_url:
            return self.env["res.company"].browse()
        slug = page_url.split("/location/")[-1].strip("/")
        branch_name = slug.replace("-", " ").title()
        normalized_slug = self._normalize_branch_name(branch_name)
        branches = self.env["res.company"].sudo().search([("parent_id", "=", 1)])
        for company in branches:
            if self._normalize_branch_name(company.name) == normalized_slug:
                return company
        return self.env["res.company"].browse()

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()

        for vals in vals_list:
            vals.setdefault("submitted_at", now)
            vals.setdefault("stage_changed_at", now)
            vals.setdefault("delay_status", "on_time")

        leads = super().create(vals_list)

        for lead in leads:

            if not lead.event_type:
                continue

            company = lead.company_id or self.env.company

            # IMPORTANT: switch environment to branch company
            env = self.env['product.product'].with_company(company)

            product = env.search([
                ('name', '=ilike', lead.event_type.strip()),
                '|',
                ('company_id', '=', False),
                ('company_id', '=', company.id),
            ], limit=1)

            if not product:
                _logger.info("No product found for event_type: %s", lead.event_type)
                continue

            if product.qty_available <= 0:
                _logger.info(
                    "Product %s found but no stock available (qty=%s)",
                    product.name, product.qty_available
                )
                continue

            _logger.info(
                "Auto converting Lead %s → Won + Sale Order (Product=%s, Qty=%s, Company=%s)",
                lead.name, product.name, product.qty_available, company.name
            )

            try:
                if lead.type != 'opportunity':
                    lead.write({'type': 'opportunity'})

                sale_order = self.env['sale.order'].with_company(company).create({
                    'partner_id': lead.partner_id.id if lead.partner_id else False,
                    'company_id': company.id,
                    'opportunity_id': lead.id,
                    'origin': lead.name,
                    'order_line': [(0, 0, {
                        'product_id': product.id,
                        'product_uom_qty': 1,
                        'price_unit': product.lst_price,
                    })],
                })
                 # Mark Won AFTER order success
                lead.action_set_won()
                sale_order.action_confirm()

            except Exception as e:
                _logger.exception(
                    "Failed auto order creation for lead %s: %s",
                    lead.name, e
                )

        return leads

    def write(self, vals):
        for rec in self:
            # Skip Won/Lost or inactive
            if not rec.active or rec.probability in (0, 100):
                continue

            # Only update stage_changed_at if stage_id is changing
            if "stage_id" in vals and rec.stage_id.id != vals.get("stage_id"):
                vals["stage_changed_at"] = fields.Datetime.now()
                vals.setdefault("delay_status", "on_time")  # only set if not already in vals

        return super().write(vals)

    import logging
    _logger = logging.getLogger(__name__)

    def _cron_update_lead_delay_status(self):
        now = fields.Datetime.now()
        _logger.info("=== CRON START: _cron_update_lead_delay_status | now=%s ===", now)

        leads = self.search([
            ("active", "=", True),
            ("stage_id.is_won", "=", False),
        ])

        _logger.info("Total leads found: %d", len(leads))

        if not leads:
            _logger.warning("No active, non-won leads found. Exiting cron.")
            return

        for rec in leads:
            _logger.info("--- Processing Lead ID=%s | Name=%s ---", rec.id, rec.name)

            if not rec.stage_changed_at:
                _logger.warning("Lead ID=%s has no stage_changed_at. Skipping.", rec.id)
                continue

            time_diff = now - rec.stage_changed_at
            total_seconds = time_diff.total_seconds()

            _logger.info(
                "Lead ID=%s | stage_changed_at=%s | time_diff=%s | total_seconds=%.2f | current delay_status=%s",
                rec.id, rec.stage_changed_at, time_diff, total_seconds, rec.delay_status
            )

            if time_diff > timedelta(seconds=120):
                _logger.info("Lead ID=%s | CONDITION MET: time_diff > 10s", rec.id)

                if rec.delay_status != "delayed":
                    _logger.info(
                        "Lead ID=%s | Status changing from '%s' → 'delayed'. Sending SMS.",
                        rec.id, rec.delay_status
                    )
                    rec.write({"delay_status": "delayed"})
                    _logger.info("Lead ID=%s | write({'delay_status': 'delayed'}) done.", rec.id)
                    rec._send_delay_sms(reminder=False)

                else:
                    _logger.info("Lead ID=%s | Already 'delayed'. Checking 2-hour reminder.", rec.id)

                    if rec.delay_sms_sent_at:
                        sms_diff = now - rec.delay_sms_sent_at
                        _logger.info(
                            "Lead ID=%s | delay_sms_sent_at=%s | time since SMS=%.2f seconds (%.2f hours)",
                            rec.id, rec.delay_sms_sent_at,
                            sms_diff.total_seconds(),
                            sms_diff.total_seconds() / 3600
                        )
                        if sms_diff >= timedelta(seconds=120):
                            _logger.info("Lead ID=%s | 2-hour threshold reached. Sending reminder SMS.", rec.id)
                            rec._send_delay_sms(reminder=True)
                        else:
                            _logger.info(
                                "Lead ID=%s | Not yet 2 hours. %.2f minutes remaining.",
                                rec.id,
                                (timedelta(hours=2) - sms_diff).total_seconds() / 60
                            )
                    else:
                        _logger.warning(
                            "Lead ID=%s | delay_status='delayed' but delay_sms_sent_at is NOT set. "
                            "SMS may have been skipped previously. Sending now.",
                            rec.id
                        )
                        rec._send_delay_sms(reminder=False)

            else:
                _logger.info(
                    "Lead ID=%s | CONDITION NOT MET: time_diff=%.2fs <= 10s",
                    rec.id, total_seconds
                )
                if rec.delay_status != "on_time":
                    _logger.info(
                        "Lead ID=%s | Status changing from '%s' → 'on_time'. Resetting SMS timestamp.",
                        rec.id, rec.delay_status
                    )
                    rec.write({
                        "delay_status": "on_time",
                        "delay_sms_sent_at": False,
                    })
                    _logger.info("Lead ID=%s | Reset to on_time done.", rec.id)
                else:
                    _logger.info("Lead ID=%s | Already 'on_time'. No change needed.", rec.id)

        _logger.info("=== CRON END: _cron_update_lead_delay_status ===")

    def _send_delay_sms(self, reminder=False):
        """Send SMS via Twilio-configured Odoo SMS to the salesperson (user_id) phone."""
        _logger.info(
            "=== _send_delay_sms | Lead ID=%s | reminder=%s ===",
            self.id, reminder
        )

        salesperson = self.user_id
        phone = salesperson.phone if salesperson else False
        _logger.info(
            "Lead ID=%s | salesperson=%s | phone=%s",
            self.id, salesperson.name if salesperson else None, phone
        )

        if not phone:
            _logger.warning(
                "Lead ID=%s | No salesperson or no phone on salesperson. SMS aborted.",
                self.id,
            )
            return

        if reminder:
            message = (
                f"Reminder: Lead '{self.name}' is still delayed "
                f"and has not progressed. Please take action."
            )
        else:
            message = (
                f"Alert: Lead '{self.name}' has entered a delayed status. "
                f"Please review and update the pipeline."
            )
            _logger.info("Lead ID=%s | Recording delay_sms_sent_at timestamp.", self.id)
            self.write({"delay_sms_sent_at": fields.Datetime.now()})

        # Resolve company — prefer lead's company, fall back to current env company
        company = self.company_id or self.env.company
        _logger.info(
            "Lead ID=%s | Resolved company: ID=%s | Name=%s | sms_provider=%s",
            self.id, company.id, company.name,
            company.sms_provider if hasattr(company, 'sms_provider') else 'N/A'
        )

        _logger.info("Lead ID=%s | SMS message: %s", self.id, message)

        try:
            sms_record = self.env['sms.sms'].sudo().create({
                'number': phone,
                'body': message,
                'state': 'outgoing',
                'record_company_id': company.id,  # ← forces Twilio routing
            })
            _logger.info(
                "Lead ID=%s | sms.sms record created | ID=%s | record_company_id=%s",
                self.id, sms_record.id, sms_record.record_company_id.id
            )

            # Verify it will actually route via Twilio before sending
            resolved_company = sms_record._get_sms_company()
            _logger.info(
                "Lead ID=%s | _get_sms_company() resolved to: ID=%s | sms_provider=%s",
                self.id, resolved_company.id,
                resolved_company.sms_provider if hasattr(resolved_company, 'sms_provider') else 'N/A'
            )

            sms_record.send()
            _logger.info("Lead ID=%s | sms_record.send() called successfully.", self.id)

        except Exception as e:
            _logger.error(
                "Lead ID=%s | SMS sending FAILED | Error: %s",
                self.id, str(e), exc_info=True
            )
