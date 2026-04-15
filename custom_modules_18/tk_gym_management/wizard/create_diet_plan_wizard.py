from odoo import models, fields


class CreateDietPlan(models.TransientModel):
    """Create Diet Plan Wizard"""
    _name = 'create.diet.plan'
    _description = __doc__

    name = fields.Char(string='Title')
    member_id = fields.Many2one('res.partner', domain=[('is_member', '=', True)])
    date = fields.Date(default=fields.Date.today())
    dietitian_id = fields.Many2one('res.users')
    diet_category_id = fields.Many2one('diet.category')
    diet_type_id = fields.Many2one('diet.type')

    def default_get(self, fields_list):
        """default get"""
        active_id = self._context.get('active_id')
        lead_id = self.env['crm.lead'].browse(active_id)
        res = super().default_get(fields_list)
        if lead_id:
            res['member_id'] = lead_id.partner_id.id
            res['diet_category_id'] = lead_id.diet_category_id.id
            res['diet_type_id'] = lead_id.diet_type_id.id
            res['name'] = lead_id.name
        return res

    def create_plan(self):
        """create plan"""
        data = {
            'member_id': self.member_id.id,
            'date': self.date,
            'dietitian_id': self.dietitian_id.id,
            'name': self.name,
            'diet_category_id': self.diet_category_id.id,
            'diet_type_id': self.diet_type_id.id,
        }
        active_id = self._context.get('active_id')
        lead_id = self.env['crm.lead'].browse(active_id)
        lead_id.action_set_won_rainbowman()
        diet_plan_id = self.env['diet.plan'].sudo().create(data)
        lead_id.diet_plan_id = diet_plan_id.id
        return {
            'type': "ir.actions.act_window",
            'name': 'Diet Plan',
            'res_model': 'diet.plan',
            'res_id': diet_plan_id.id,
            'view_mode': 'form',
            'target': 'current'
        }
