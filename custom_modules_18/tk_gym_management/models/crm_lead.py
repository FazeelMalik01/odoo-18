from odoo import fields, models, tools, api


class CrmLeadInherit(models.Model):
    """crm lead inherit"""

    _inherit = "crm.lead"
    _description = __doc__

    birthdate = fields.Date()
    gender = fields.Selection([("m", "Male"), ("f", "Female"), ("o", "Other")])
    diet_category_id = fields.Many2one("diet.category")
    diet_type_id = fields.Many2one("diet.type")
    goals_details = fields.Text(string="Goals Description")
    is_form_website = fields.Boolean(string="Is Created From Website")
    is_won = fields.Boolean(related="stage_id.is_won")
    diet_plan_id = fields.Many2one("diet.plan")

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        """Extract data from lead to create a partner.

        :param name : furtur name of the partner
        :param is_company : True if the partner is a company
        :param parent_id : id of the parent partner (False if no parent)

        :return: dictionary of values to give at res_partner.create()
        """
        email_parts = tools.email_split(self.email_from)
        res = {
            "name": partner_name,
            "user_id": self.env.context.get("default_user_id") or self.user_id.id,
            "comment": self.description,
            "team_id": self.team_id.id,
            "parent_id": parent_id,
            "phone": self.phone,
            "mobile": self.mobile,
            "email": email_parts[0] if email_parts else False,
            "title": self.title.id,
            "function": self.function,
            "street": self.street,
            "street2": self.street2,
            "zip": self.zip,
            "city": self.city,
            "country_id": self.country_id.id,
            "state_id": self.state_id.id,
            "website": self.website,
            "is_company": is_company,
            "type": "contact",
        }
        if self.lang_id.active:
            res["lang"] = self.lang_id.code
        if self.is_form_website:
            res["is_member"] = True
            res["birthdate"] = self.birthdate
            res["gender"] = self.gender
        return res

    def action_diet_plan(self):
        """action diet plan"""
        return {
            "type": "ir.actions.act_window",
            "name": "Diet Plan",
            "res_model": "diet.plan",
            "res_id": self.diet_plan_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.onchange("birthdate")
    def _onchange_birthdate(self):
        """onchange birthdate"""
        for rec in self:
            if rec.partner_id:
                rec.partner_id.birthdate = rec.birthdate

    @api.onchange("gender")
    def _onchange_gender(self):
        """onchange gender"""
        for rec in self:
            if rec.partner_id:
                rec.partner_id.gender = rec.gender

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """ Onchange Partner ID """
        for rec in self:
            if rec.partner_id:
                rec.birthdate = rec.partner_id.birthdate
                rec.gender = rec.partner_id.gender
