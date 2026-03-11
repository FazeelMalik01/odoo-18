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

    delay_status = fields.Selection(
        [
            ("on_time", "On Time"),
            ("delayed", "Delayed"),
        ],
        string="Lead Status",
        default="on_time",
        store=True,
    )

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
        """Resolve branch company from Page URL (e.g. .../location/lahore -> Lahore company).
        Only looks up existing companies (children of main company id=1)."""
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

            # ---------------------------------------
            # STRICT product name match (not ilike)
            # ---------------------------------------
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

    def _cron_update_lead_delay_status(self):
        now = fields.Datetime.now()

        leads = self.search([
            ("active", "=", True),
            ("stage_id.is_won", "=", False),
        ])

        for rec in leads:
            if not rec.stage_changed_at:
                continue

            time_diff = now - rec.stage_changed_at

            if time_diff > timedelta(seconds=10):
                if rec.delay_status != "delayed":
                    rec.write({"delay_status": "delayed"})
            else:
                if rec.delay_status != "on_time":
                    rec.write({"delay_status": "on_time"})