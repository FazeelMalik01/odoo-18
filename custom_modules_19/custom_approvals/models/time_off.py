from odoo import models, fields, api
from odoo.exceptions import UserError


class CustomTimeOffApproval(models.Model):
    _name = 'custom.time.off.approval'
    _description = 'Custom Time Off Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Description',
        related='holiday_id.name',
        store=True,
    )
    holiday_id = fields.Many2one(
        'hr.leave', string='Time Off Request',
        required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        related='holiday_id.employee_id', store=True,
    )
    department_id = fields.Many2one(
        'hr.department', string='Department',
        related='holiday_id.department_id', store=True,
    )
    holiday_status_id = fields.Many2one(
        'hr.leave.type', string='Time Off Type',
        related='holiday_id.holiday_status_id', store=True,
    )
    date_from = fields.Datetime(
        related='holiday_id.date_from', store=True, string='Start Date',
    )
    date_to = fields.Datetime(
        related='holiday_id.date_to', store=True, string='End Date',
    )
    duration_display = fields.Char(
        related='holiday_id.duration_display', string='Duration',
    )

    manager_id = fields.Many2one(
        'res.users', string='Employee Manager',
        compute='_compute_manager_id', store=True,
    )
    hr_manager_id = fields.Many2one(
        'res.users', string='HR Manager',
        compute='_compute_hr_manager_id', store=True,
    )

    state = fields.Selection([
        ('pending_manager', 'Pending Manager Approval'),
        ('pending_hr',      'Pending HR Approval'),
        ('approved',        'Approved'),
        ('refused',         'Refused'),
    ], string='Status', default='pending_manager', tracking=True)

    refusal_reason = fields.Text('Refusal Reason')

    # computed booleans for view button visibility
    can_approve = fields.Boolean(compute='_compute_can_approve_refuse')
    can_refuse  = fields.Boolean(compute='_compute_can_approve_refuse')

    # ----------------------------------------------------------------
    # Computes
    # ----------------------------------------------------------------
    @api.depends('employee_id')
    def _compute_manager_id(self):
        for rec in self:
            rec.manager_id = rec.employee_id.parent_id.user_id or False

    @api.depends('employee_id')
    def _compute_hr_manager_id(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'custom_approvals.hr'
        )
        hr_user = False
        if param:
            try:
                hr_user = self.env['res.users'].sudo().browse(int(param))
                if not hr_user.exists():
                    hr_user = False
            except (ValueError, TypeError):
                pass
        for rec in self:
            rec.hr_manager_id = hr_user

    @api.depends('state', 'manager_id', 'hr_manager_id')
    def _compute_can_approve_refuse(self):
        uid = self.env.uid
        for rec in self:
            if rec.state == 'pending_manager' and rec.manager_id.id == uid:
                rec.can_approve = True
                rec.can_refuse  = True
            elif rec.state == 'pending_hr' and rec.hr_manager_id.id == uid:
                rec.can_approve = True
                rec.can_refuse  = True
            else:
                rec.can_approve = False
                rec.can_refuse  = False

    # ----------------------------------------------------------------
    # Actions
    # ----------------------------------------------------------------
    def action_approve(self):
        self.ensure_one()
        user = self.env.user

        if self.state == 'pending_manager':
            if user != self.manager_id:
                raise UserError("Only the employee's manager can approve at this stage.")
            self._mark_activity_done(user.id)
            self.state = 'pending_hr'
            self._send_activity(self.hr_manager_id, stage='hr')
            self.message_post(
                body=(
                    "<b>Manager approved.</b> Request forwarded to HR Manager "
                    "<b>%s</b> for final approval." % (self.hr_manager_id.name or '—')
                ),
                partner_ids=[self.employee_id.user_id.partner_id.id],
            )

        elif self.state == 'pending_hr':
            if user != self.hr_manager_id:
                raise UserError("Only the HR Manager can give final approval.")
            self._mark_activity_done(user.id)
            self.state = 'approved'
            # Validate the underlying hr.leave through both Odoo stages
            if self.holiday_id.state == 'confirm':
                self.holiday_id.sudo().action_approve()
            if self.holiday_id.state == 'validate1':
                self.holiday_id.sudo().action_validate()
            self.message_post(
                body="<b>HR Manager approved.</b> Time off request is fully approved.",
                partner_ids=[self.employee_id.user_id.partner_id.id],
            )

        else:
            raise UserError("This request cannot be approved in its current state.")

    def action_refuse(self):
        self.ensure_one()
        user = self.env.user

        allowed = (
            (self.state == 'pending_manager' and user == self.manager_id) or
            (self.state == 'pending_hr'      and user == self.hr_manager_id)
        )
        if not allowed:
            raise UserError("You are not authorised to refuse this request.")

        self._mark_activity_done(user.id)
        self.state = 'refused'
        self.holiday_id.sudo().action_refuse()
        body = "<b>Request refused</b> by %s." % user.name
        if self.refusal_reason:
            body += "<br/>Reason: %s" % self.refusal_reason
        self.message_post(
            body=body,
            partner_ids=[self.employee_id.user_id.partner_id.id],
        )

    # ----------------------------------------------------------------
    # Activity helpers
    # ----------------------------------------------------------------
    def _send_activity(self, user, stage='manager'):
        self.ensure_one()
        if not user:
            return
        note = (
            "Time off approval required — "
            "Employee: <b>%s</b>, Type: <b>%s</b>, Duration: <b>%s</b>"
            % (
                self.employee_id.name,
                self.holiday_status_id.name,
                self.duration_display or '',
            )
        )
        existing = self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id',    '=', self.id),
            ('user_id',   '=', user.id),
        ], limit=1)
        if not existing:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                note=note,
            )

    def _mark_activity_done(self, user_id):
        activities = self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id',    'in', self.ids),
            ('user_id',   '=', user_id),
        ])
        activities.action_done()


class HrLeaveInherit(models.Model):
    _inherit = 'hr.leave'

    has_custom_approval = fields.Boolean(
        string='Has Custom Approval',
        default=False,
        copy=False,
    )

    def _create_custom_approval(self):
        """Create a custom.time.off.approval record if one doesn't exist yet."""
        Approval = self.env['custom.time.off.approval'].sudo()
        for leave in self:
            existing = Approval.search([('holiday_id', '=', leave.id)], limit=1)
            if existing:
                continue

            approval = Approval.create({'holiday_id': leave.id})
            # Flag the leave so it is excluded from the standard Management menu
            leave.sudo().write({'has_custom_approval': True})

            if approval.manager_id:
                approval._send_activity(approval.manager_id, stage='manager')
            else:
                # No manager — skip straight to HR
                approval.state = 'pending_hr'
                approval._send_activity(approval.hr_manager_id, stage='hr')

    def activity_update(self):
        """
        Block Odoo's default activity-to-responsible-group behaviour
        for leaves that are handled by our custom approval flow.
        """
        custom_managed = self.filtered('has_custom_approval')
        standard = self - custom_managed
        if standard:
            return super(HrLeaveInherit, standard).activity_update()
        return True

    # ------------------------------------------------------------------
    # Hook 1: Confirm button on form
    # ------------------------------------------------------------------
    def action_confirm(self):
        res = super().action_confirm()
        self._create_custom_approval()
        return res

    # ------------------------------------------------------------------
    # Hook 2: Programmatic state change to 'confirm'
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'confirm':
            self._create_custom_approval()
        return res

    # ------------------------------------------------------------------
    # Hook 3: Record created already in 'confirm' state
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        confirmed = records.filtered(lambda r: r.state == 'confirm')
        if confirmed:
            confirmed._create_custom_approval()
        return records