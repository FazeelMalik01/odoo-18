from odoo import models, fields, api


class MailingList(models.Model):
    _inherit = 'mailing.list'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        # Main company sees all records; branches see only their own
        if self.env.company.id != self.env.ref('base.main_company').id:
            domain = domain + [('company_id', '=', self.env.company.id)]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None,
                        order=None, count_limit=None):
        domain = domain or []
        if self.env.company.id != self.env.ref('base.main_company').id:
            domain = domain + [('company_id', '=', self.env.company.id)]
        return super().web_search_read(domain=domain, specification=specification,
                                    offset=offset, limit=limit, order=order,
                                    count_limit=count_limit)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' not in vals:
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)