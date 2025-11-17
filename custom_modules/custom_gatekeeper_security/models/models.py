from odoo import models, fields, api
from odoo.exceptions import UserError


class ServiceRequestLine(models.Model):
    _name = 'service.request.line'
    _description = 'Service Request Line'
    _order = 'sequence, id'

    service_request_id = fields.Many2one('service.request', string='Service Request', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Product Information
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], required=True, ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]", ondelete='restrict')
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', string='UoM Category', readonly=True)
    
    # Product Details
    name = fields.Text(string='Description', required=True)
    product_template_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', domain=[('sale_ok', '=', True)], readonly=True)
    
    # Quantity and Pricing
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price', default=0.0)
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_amount', store=True)
    price_total = fields.Monetary(string='Total', compute='_compute_amount', store=True)
    
    # Taxes
    tax_id = fields.Many2many('account.tax', string='Taxes', domain="[('type_tax_use','in',['sale', 'all'])]")
    price_tax = fields.Float(string='Total Tax', compute='_compute_amount', store=True)
    
    # Currency
    currency_id = fields.Many2one('res.currency', string='Currency', related='service_request_id.currency_id', readonly=True, store=True, required=True, default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(related='service_request_id.company_id', string='Company', store=True, readonly=True)
    
    # Additional fields
    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', check_company=True)
    product_packaging_qty = fields.Float(string='Packaging Quantity', digits='Product Unit of Measure', default=1.0)
    
    @api.depends('product_uom_qty', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * line.product_uom_qty
            taxes = line.tax_id.compute_all(price, line.currency_id, 1, product=line.product_id, partner=line.service_request_id.customer_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        
        # Set product details
        self.name = self.product_id.get_product_multiline_description_sale()
        self.product_uom_id = self.product_id.uom_id
        self.price_unit = self.product_id.lst_price
        
        # Set taxes
        if self.product_id.taxes_id:
            self.tax_id = self.product_id.taxes_id.filtered(lambda r: not self.company_id or r.company_id == self.company_id)
    
    @api.onchange('product_uom_id', 'product_uom_qty')
    def _onchange_product_uom(self):
        if self.product_id and self.product_uom_id and self.product_id.uom_id != self.product_uom_id:
            self.price_unit = self.product_id.uom_id._compute_price(self.product_id.lst_price, self.product_uom_id)


class ServiceRequest(models.Model):
    _name = 'service.request'
    _description = 'Service Request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: self._get_default_name()
    )
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    company_partner_id = fields.Many2one('res.partner', string='Company', compute='_compute_customer_info', store=True)

    # Customer Information
    service_address = fields.Text(string='Service Address', compute='_compute_customer_info', store=True)
    city = fields.Char(string='City', compute='_compute_customer_info', store=True)
    state_id = fields.Many2one('res.country.state', string='State', compute='_compute_customer_info', store=True)
    zip = fields.Char(string='ZIP', compute='_compute_customer_info', store=True)
    primary_phone = fields.Char(string='Primary Phone', compute='_compute_customer_info', store=True)
    email = fields.Char(string='Email', compute='_compute_customer_info', store=True)
    preferred_contact_method = fields.Selection([
        ('phone', 'Phone'),
        ('text', 'Text'),
        ('email', 'Email')
    ], string='Preferred Contact Method')
    requested_appointment = fields.Datetime(string='Requested Appointment Date/Time')

    # Service Type
    service_type_other_details = fields.Char(string='Other Service Details')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], ondelete='set null', help="Legacy field - use order_line instead")
    order_line = fields.One2many('service.request.line', 'service_request_id', string='Product Lines', copy=True, auto_join=True)
    sale_order_id = fields.Many2one('sale.order', string='Quotation', readonly=True,  ondelete='set null')
    
    # Currency and Company
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    # Computed totals
    amount_untaxed = fields.Monetary(string='Untaxed Amount', compute='_compute_amount_all', store=True)
    amount_tax = fields.Monetary(string='Taxes', compute='_compute_amount_all', store=True)
    amount_total = fields.Monetary(string='Total', compute='_compute_amount_all', store=True)
    
    @api.depends('order_line.price_total')
    def _compute_amount_all(self):
        for request in self:
            amount_untaxed = amount_tax = 0.0
            for line in request.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            request.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    # Service Location
    service_location = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('government', 'Government / Restricted Facility')
    ], string='Service Location')

    # Description
    description = fields.Text(string='Description of Issue or Request')

    # Access Instructions
    gate_code = fields.Char(string='Gate Code / Access Details')
    pets_on_site = fields.Boolean(string='Dogs / Pets on site?')
    technician_notes = fields.Text(string='Important Notes for Technician')

    # Billing
    billing_same_as_service = fields.Boolean(string='Same as service address', default=True)
    billing_address = fields.Text(string='Billing Address')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    @api.model
    def _get_default_name(self):
        return self.env['ir.sequence'].next_by_code('service.request') or 'New'

    def action_submit(self):
        self.write({'state': 'submitted'})
        return True

    def action_in_progress(self):
        self.write({'state': 'in_progress'})
        return True

    def action_complete(self):
        self.write({'state': 'completed'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def _compute_access_url(self):
        for record in self:
            record.access_url = f'/my/service_request/{record.id}'

    @api.depends('customer_id')
    def _compute_customer_info(self):
        for record in self:
            partner = record.customer_id
            if partner:
                record.company_partner_id = partner.parent_id or False
                record.service_address = partner._display_address()
                record.city = partner.city or ''
                record.state_id = partner.state_id
                record.zip = partner.zip or ''
                record.primary_phone = partner.phone or partner.mobile or ''
                record.email = partner.email or ''
            else:
                record.update({
                    'company_partner_id': False,
                    'service_address': '',
                    'city': '',
                    'state_id': False,
                    'zip': '',
                    'primary_phone': '',
                    'email': '',
                })

    def action_create_quotation(self):
        """Create a Sale Order prefilled with the product lines"""
        self.ensure_one()
        if not self.order_line:
            raise UserError('Please add at least one product line before creating a quotation.')

        # Create sale order lines from service request lines
        order_lines = []
        for line in self.order_line:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom_id.id,
                'price_unit': line.price_unit,
                'tax_id': [(6, 0, line.tax_id.ids)],
            }))

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer_id.id,
            'origin': self.name,
            'order_line': order_lines,
        })
        self.sale_order_id = sale_order.id

        return {
            'name': 'Create Quotation',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'view_id': self.env.ref('sale.view_order_form').id,
            'target': 'current',
        }
