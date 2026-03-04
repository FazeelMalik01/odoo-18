from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ['purchase.request', 'portal.mixin']

    def _compute_access_url(self):
        super(PurchaseRequest, self)._compute_access_url()
        for purchase_request in self:
            purchase_request.access_url = '/my/purchase_requests/%s' % purchase_request.id

    def can_edit(self):
        self.ensure_one()
        return self.state == 'draft'

    def _get_report_base_filename(self):
        return "%s" % (self.name.replace('/', '_').replace('.', '-'))

    # New fields for requirements
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        tracking=True,
        help='Select the project for this purchase request',
    )
    
    stage_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Stage',
        tracking=True,
        domain="[('plan_id.name', '=', 'Stage')]",
        help='Select the stage from Analytic Plan "Stage"',
    )
    
    request_type = fields.Selection(
        [
            ('materials', 'Materials'),
            ('labor', 'Labor'),
            ('equipment_rental', 'Equipment Rental'),
        ],
        string='Request Type',
        tracking=True,
        help='Type of purchase request',
    )
    
    # Override picking_type_id to make it optional with default
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Picking Type",
        required=False,  # Make optional - will use default from base module
    )
    
    # Expected Delivery Date - applies to all lines
    date_required = fields.Date(
        string='Expected Delivery Date',
        tracking=True,
        help='Expected delivery date for all items in this purchase request',
    )
    
    def write(self, vals):
        """Override write to sync date_required to all lines"""
        result = super().write(vals)
        if 'date_required' in vals and vals['date_required']:
            # Update all lines with the new date_required
            for request in self:
                request.line_ids.write({'date_required': vals['date_required']})
        return result
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to sync date_required to lines"""
        requests = super().create(vals_list)
        for request, vals in zip(requests, vals_list):
            if 'date_required' in vals and vals['date_required']:
                # Update all lines with the date_required
                request.line_ids.write({'date_required': vals['date_required']})
        return requests