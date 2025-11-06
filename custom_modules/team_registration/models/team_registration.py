from odoo import models, fields, api

class TeamRegistration(models.Model):
    _name = 'team.registration'
    _description = 'Team Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Full Name', required=True)
    phone = fields.Char(required=True)
    email = fields.Char()
    password = fields.Char(required=True)
    role = fields.Selection([
        ('coach', 'Coach'),
        ('nutritionist', 'Nutritionist'),
        ('owner', 'Owner'),
    ], required=True)
    years_experience = fields.Integer()
    fitness_center = fields.Char()
    city = fields.Char()
    address = fields.Char()
    degree = fields.Selection([
        ('high_school', 'High School'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('phd', 'PhD'),
    ])
    cert_file = fields.Binary(string='Certificate of Practice')
    cert_filename = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft')
    referred_by = fields.Many2one('res.users', string="Referred By")
    invitation_link = fields.Char(string='Invitation Link', readonly=True)
    user_id = fields.Many2one('res.users', string="Created User", readonly=True)

    def action_approve(self):
        for rec in self:
            password = rec.password if isinstance(rec.password, str) and rec.password.strip() else "123"
            normalized_phone = rec.phone.lstrip("+")

            portal_group = self.env.ref('base.group_portal')

            # Create user with only portal group
            user = self.env['res.users'].sudo().create({
                'name': rec.name,
                'login': rec.phone,
                'email': rec.email,
                'mobile': normalized_phone,
                'password': password,
                'groups_id': [(6, 0, [portal_group.id])],
                'referred_by': rec.referred_by.id,
            })

            rec.user_id = user

            # Assign flags
            user.is_coach = rec.role == 'coach'
            user.is_nutritionist = rec.role == 'nutritionist'
            user.is_owner = rec.role == 'owner'

            # Generate invitation link
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            rec.invitation_link = f"{base_url}/web/signup?mobile_field=true&ref={user.id}"
            user.referral_link = f"{base_url}/web/signup?mobile_field=true&ref={user.id}"
            rec.state = 'approved'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    @api.model
    def create(self, vals):
        record = super().create(vals)

        team_registration_group = self.env.ref('team_registration.group_team_registration_manager')
        users = self.env['res.users'].sudo().search([('groups_id', 'in', team_registration_group.id)])
        model_id = self.env['ir.model']._get_id('team.registration')

        for user in users:
            self.env['mail.activity'].sudo().create({
                'res_model_id': model_id,
                'res_id': record.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': 'Team Registration Approval Needed',
                'note': 'A new registration is awaiting your approval.',
                'user_id': user.id,
            })

        return record



