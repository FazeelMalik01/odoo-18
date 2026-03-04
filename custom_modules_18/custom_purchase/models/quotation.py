from odoo import models, fields, api

class FalconQuotation(models.Model):
    _name = 'quotations'
    _description = 'Falcon Quotation'

    name = fields.Char(string="Quotation Ref", required=True)
    rfq_ref = fields.Char (string="RFQ REF")
    quotation_date = fields.Date (string="Quotation Date")
    #customer info
    customer = fields.Many2one('res.partner', string="Customer")
    contact_person_customer = fields.Many2one('res.partner', string="Customer Contact Person")
    title_customer = fields.Char(string="Customer Title")
    email_customer = fields.Char(string="Customer Email")
    mobile_customer = fields.Char(string="Customer Mobile")
    #company info
    contact_person_company = fields.Many2one('res.partner', string="Company Contact Person")
    title_company = fields.Char(string="Company Title")
    email_company = fields.Char(string="Company Email")
    mobile_company = fields.Char(string="Company Mobile")
    #other info
    terms_and_conditions = fields.Text(string="Terms and Conditions")
    notes = fields.Text(string="Notes")
    #for quotation Lines
    total_amount = fields.Float(string="Total Price", compute="_compute_totals", store=True)
    vat_amount = fields.Float(string="VAT (15%)", compute="_compute_totals", store=True)
    total_with_vat = fields.Float(string="Total Price with VAT", compute="_compute_totals", store=True)

    quotation_line_ids = fields.One2many('quotation.line', 'quotation_id', string="Quotation Lines")

    #quotation lines calculations
    @api.depends('quotation_line_ids.total_price')
    def _compute_totals(self):
        for record in self:
            total = sum(line.total_price for line in record.quotation_line_ids)
            vat = total * 0.15
            record.total_amount = total
            record.vat_amount = vat
            record.total_with_vat = total + vat
    # # --- Auto populate from selected Customer ---
    @api.onchange('contact_person_customer')
    def _onchange_customer(self):
        if self.contact_person_customer:
            self.email_customer = self.contact_person_customer.email
            self.mobile_customer = self.contact_person_customer.mobile
        else:
            self.email_customer = False
            self.mobile_customer = False

    # # --- Auto populate from selected Company ---
    @api.onchange('contact_person_company')
    def _onchange_company(self):
        if self.contact_person_company:
            self.email_company = self.contact_person_company.email
            self.mobile_company = self.contact_person_company.mobile
        else:
            self.email_company = False
            self.mobile_company = False


class QuotationLine(models.Model):
    _name = 'quotation.line'
    _description = 'Quotation Line'

    quotation_id = fields.Many2one('quotations', string="Quotation Reference", ondelete='cascade')

    product_id = fields.Many2one('product.product', string="Item", required=True)
    description = fields.Text(string="Description")
    uom_id = fields.Many2one('uom.uom', string="UOM")
    quantity = fields.Float(string="Quantity", default=1.0)
    unit_price = fields.Float(string="Unit Price")
    total_price = fields.Float(string="Total Price", compute="_compute_total_price", store=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto fill fields when product is selected"""
        for line in self:
            if line.product_id:
                line.description = line.product_id.display_name or ''
                line.uom_id = line.product_id.uom_id.id
                line.unit_price = line.product_id.lst_price

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        """Compute total price"""
        for line in self:
            line.total_price = line.quantity * line.unit_price