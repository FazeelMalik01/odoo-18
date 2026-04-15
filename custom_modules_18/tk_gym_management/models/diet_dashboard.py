from odoo import models, api, fields


class DietDashboard(models.Model):
    """Dashboard stats for diet and nutrients"""
    _name = 'diet.dashboard'
    _description = __doc__

    @api.model
    def get_diet_stats(self):
        """get diet stats"""
        members = self.env['res.partner'].sudo().search_count([('is_member', '=', True)])
        leads = self.env['crm.lead'].sudo().search_count(
            [('type', '=', 'lead'), ('is_form_website', '=', True)])
        opportunities = self.env['crm.lead'].sudo().search_count(
            [('type', '=', 'opportunity'), ('is_form_website', '=', True)])
        diet_plans = self.env['diet.plan'].sudo().search_count([])
        diet_plan_templates = self.env['diet.plan.template'].sudo().search_count([])
        invoice_count = self.env['account.move'].sudo().search_count(
            [('diet_plan_id', '!=', False)])

        data = {
            'members': members,
            'leads': leads,
            'opportunities': opportunities,
            'diet_plans': diet_plans,
            'diet_plan_templates': diet_plan_templates,
            'invoice_count': invoice_count,
            'invoices': self.get_month_invoice(),
            'gender_diet_plan': self.diet_plan_person()
        }
        return data

    def diet_plan_person(self):
        """diet plan person"""
        diet_plans = self.env['diet.plan'].sudo().search([])
        male_count = 0
        female_count = 0
        others_count = 0
        for rec in diet_plans:
            if rec.member_id.gender == 'm':
                male_count += 1
            elif rec.member_id.gender == 'f':
                female_count += 1
            elif rec.member_id.gender == 'o':
                others_count += 1
        return [male_count, female_count, others_count]

    def get_month_invoice(self):
        """get month invoice"""
        year = fields.date.today().year
        bill_dict = {'January': 0,
                     'February': 0,
                     'March': 0,
                     'April': 0,
                     'May': 0,
                     'June': 0,
                     'July': 0,
                     'August': 0,
                     'September': 0,
                     'October': 0,
                     'November': 0,
                     'December': 0,
                     }
        bill = self.env['account.move'].sudo().search(
            [('diet_plan_id', '!=', False)])
        for data in bill:
            if data.invoice_date:
                if data.invoice_date.year == year:
                    bill_dict[data.invoice_date.strftime("%B")] = bill_dict[
                                                                      data.invoice_date.strftime(
                                                                          "%B")] + data.amount_total
        return [list(bill_dict.keys()), list(bill_dict.values())]
