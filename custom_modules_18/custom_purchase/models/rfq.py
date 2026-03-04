from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Contact Person fields for Column 1
    contact_person_1_id = fields.Many2one('hr.employee', string='Contact Person')
    title_1_id = fields.Many2one('hr.job', string='Title')
    mobile_1 = fields.Char(string='Mobile')

    # Contact Person fields for Column 2
    contact_person_2_id = fields.Many2one('hr.employee', string="Vendor's Contact Person")
    title_2_id = fields.Many2one('hr.job', string="Vendor's Title")
    email_2 = fields.Char(string="Vendor's Email")
    mobile_2 = fields.Char(string="Vendor's Mobile")

    @api.onchange('contact_person_1_id')
    def _onchange_contact_person_1_id(self):
        """Auto-fill contact person 1 details when an employee is selected"""
        if self.contact_person_1_id:
            self.title_1_id = self.contact_person_1_id.job_id.id
            self.mobile_1 = self.contact_person_1_id.work_phone
        else:
            self.title_1_id = False
            self.mobile_1 = False

    @api.onchange('contact_person_2_id')
    def _onchange_contact_person_2_id(self):
        """Auto-fill contact person 2 details when an employee is selected"""
        if self.contact_person_2_id:
            self.title_2_id = self.contact_person_2_id.job_id.id
            self.email_2 = self.contact_person_2_id.work_email
            self.mobile_2 = self.contact_person_2_id.work_phone
        else:
            self.title_2_id = False
            self.email_2 = False
            self.mobile_2 = False