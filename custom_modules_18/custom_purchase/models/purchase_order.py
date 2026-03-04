# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # --------------------------
    # Vendor Information
    # --------------------------
    vendor_no = fields.Char(string="Vendor No")
    vendor_contact = fields.Char(string="Vendor Contact")
    # CHANGED: Remove related and readonly to make them editable
    vendor_phone = fields.Char(string="Vendor Phone")  # Removed related and readonly
    vendor_email = fields.Char(string="Vendor Email")  # Removed related and readonly
    vendor_address_display = fields.Html(string="Vendor Address")

    # --------------------------
    # Shipping Details (Employee-based)
    # --------------------------
    ship_employee_id = fields.Many2one(
        'hr.employee',
        string="Shipping Employee",
        help="Employee responsible for shipping",
        ondelete="set null"
    )
    ship_phone = fields.Char(string="Ship Phone")
    ship_email = fields.Char(string="Ship Email")
    ship_to = fields.Many2one('res.company', string="Ship To", default=lambda self: self.env.company)
    ship_address_display = fields.Html(string="Shipping Address")

    # --------------------------
    # Billing Details (Employee-based)
    # --------------------------
    bill_employee_id = fields.Many2one(
        'hr.employee',
        string="Billing Employee",
        help="Employee responsible for billing",
        ondelete="set null"
    )
    bill_phone = fields.Char(string="Bill Phone")
    bill_email = fields.Char(string="Bill Email")
    bill_to = fields.Many2one('res.company', string="Bill To", default=lambda self: self.env.company)
    bill_address_display = fields.Html(string="Billing Address")

    # --------------------------
    # Onchange methods for auto-fill with manual editing capability
    # --------------------------

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Auto-fill vendor information when partner is selected, but keep it editable."""
        for rec in self:
            if rec.partner_id:
                # Auto-fill vendor details, but user can still edit them manually
                rec.vendor_address_display = rec.partner_id._display_address(without_company=True) if rec.partner_id else ""
                rec.vendor_phone = rec.partner_id.phone or ""
                rec.vendor_email = rec.partner_id.email or ""
            else:
                # Clear the fields if no partner is selected
                rec.vendor_address_display = ""
                rec.vendor_phone = ""
                rec.vendor_email = ""

    @api.onchange('ship_to')
    def _onchange_ship_to(self):
        """Auto-fill shipping address when company is selected, but keep it editable."""
        for rec in self:
            if rec.ship_to:
                # Auto-fill the shipping address, but user can still edit it manually
                rec.ship_address_display = rec.ship_to.partner_id._display_address(without_company=True) if rec.ship_to else ""
            else:
                # Clear the field if no company is selected
                rec.ship_address_display = ""

    @api.onchange('ship_employee_id')
    def _onchange_ship_employee_id(self):
        """Auto-fill shipping contact fields when employee is selected, but keep them editable."""
        for rec in self:
            if rec.ship_employee_id:
                # Auto-fill the values, but user can still edit them manually
                rec.ship_phone = rec.ship_employee_id.work_phone or ""
                rec.ship_email = rec.ship_employee_id.work_email or ""
            else:
                # Clear the fields if no employee is selected
                rec.ship_phone = ""
                rec.ship_email = ""

    @api.onchange('bill_to')
    def _onchange_bill_to(self):
        """Auto-fill billing address when company is selected, but keep it editable."""
        for rec in self:
            if rec.bill_to:
                # Auto-fill the billing address, but user can still edit it manually
                rec.bill_address_display = rec.bill_to.partner_id._display_address(without_company=True) if rec.bill_to else ""
            else:
                # Clear the field if no company is selected
                rec.bill_address_display = ""

    @api.onchange('bill_employee_id')
    def _onchange_bill_employee_id(self):
        """Auto-fill billing contact fields when employee is selected, but keep them editable."""
        for rec in self:
            if rec.bill_employee_id:
                # Auto-fill the values, but user can still edit them manually
                rec.bill_phone = rec.bill_employee_id.work_phone or ""
                rec.bill_email = rec.bill_employee_id.work_email or ""
            else:
                # Clear the fields if no employee is selected
                rec.bill_phone = ""
                rec.bill_email = ""