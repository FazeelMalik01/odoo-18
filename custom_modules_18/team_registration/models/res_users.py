from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = 'res.users'

    is_coach = fields.Boolean()
    is_nutritionist = fields.Boolean()
    is_owner = fields.Boolean()
    role = fields.Char()

    referred_by = fields.Many2one('res.users', string="Referred By")
    referred_users = fields.One2many('res.users', 'referred_by', string="Referred Users")
    referral_link = fields.Char(string="Referral Link", readonly=True, store=True)



    @api.model
    def create(self, vals):
        user = super().create(vals)
   
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        referral_link = f"{base_url}/web/signup?mobile_field=true&ref={user.id}"
        user.write({'referral_link': referral_link})  # this saves it
        return user


    @api.constrains('is_coach', 'is_nutritionist', 'is_owner')
    def _check_single_role(self):
        for rec in self:
            if sum(1 for x in [rec.is_coach, rec.is_nutritionist, rec.is_owner] if x) > 1:
                raise ValidationError("Only one of Coach, Nutritionist, or Owner can be selected.")
