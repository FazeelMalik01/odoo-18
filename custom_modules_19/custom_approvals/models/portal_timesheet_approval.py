from odoo import models, fields, api
from odoo.exceptions import UserError


class PortalTimesheetApproval(models.Model):
    _name = 'portal.timesheet.approval'
    _description = 'Portal Timesheet Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Description', required=True, default='/')
    task_id = fields.Many2one('project.task', 'Task', required=True, ondelete='cascade')
    project_id = fields.Many2one(
        'project.project', related='task_id.project_id', store=True, readonly=True
    )
    portal_user_id = fields.Many2one('res.users', 'Portal User', required=True)
    employee_id = fields.Many2one(
        'hr.employee', 'Employee', compute='_compute_employee_id', store=True
    )
    date = fields.Date('Date', required=True, default=fields.Date.today)
    unit_amount = fields.Float('Hours', digits=(16, 2))
    timer_start = fields.Datetime('Timer Started')
    timer_stop = fields.Datetime('Timer Stopped')
    rejection_reason = fields.Text('Rejection Reason')
    timesheet_id = fields.Many2one(
        'account.analytic.line', 'Created Timesheet', readonly=True
    )

    state = fields.Selection(
        [
            ('timing',   'Timer Running'),
            ('pending',  'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending',
        string='Status',
        tracking=True,
    )

    # ----------------------------------------------------------------
    # Compute
    # ----------------------------------------------------------------
    @api.depends('portal_user_id')
    def _compute_employee_id(self):
        for rec in self:
            rec.employee_id = self.env['hr.employee'].sudo().search(
                [('user_id', '=', rec.portal_user_id.id)], limit=1
            )

    # ----------------------------------------------------------------
    # Settings helper
    # ----------------------------------------------------------------
    def _get_timesheet_manager(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'custom_approvals.timesheet_manager'
        )
        if param:
            try:
                uid = int(param)
                user = self.env['res.users'].sudo().browse(uid)
                if user.exists():
                    return user
            except (ValueError, TypeError):
                pass
        return self.env['res.users']

    # ----------------------------------------------------------------
    # Actions
    # ----------------------------------------------------------------
    def action_submit_for_approval(self):
        """Backend button: submit pending request and REQUIRE manager to be set."""
        self.ensure_one()
        manager = self._get_timesheet_manager()
        if not manager:
            raise UserError(
                "Timesheet Manager is not configured. "
                "Please configure it under Settings > Timesheets."
            )
        self.state = 'pending'
        self._notify_manager(manager)

    def _notify_manager_best_effort(self):
        """
        Portal entry point: record is already in 'pending' state.
        Notify the manager if one is configured — silently skip if not.
        """
        self.ensure_one()
        manager = self._get_timesheet_manager()
        if not manager:
            return
        self._notify_manager(manager)

    def _notify_manager(self, manager):
        """Send activity + email to the given manager user.

        Uses mail.mail directly so:
        - email_from is always the configured SMTP sender (never a broken template value)
        - No mail.template rendering involved — no inline_template errors
        """
        self.ensure_one()
        self._send_activity_to_manager(manager.id)
        if not manager.email:
            return

        desc = self.name if self.name != '/' else '(no description)'
        body = """
<div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
  <p>Hello,</p>
  <p>A new timesheet entry from portal user <strong>%(user)s</strong> requires your approval.</p>
  <table style="border-collapse:collapse;width:100%%;max-width:500px;">
    <tr><td style="padding:6px 12px;border:1px solid #ddd;background:#f5f5f5;font-weight:bold;">Task</td>
        <td style="padding:6px 12px;border:1px solid #ddd;">%(task)s</td></tr>
    <tr><td style="padding:6px 12px;border:1px solid #ddd;background:#f5f5f5;font-weight:bold;">Project</td>
        <td style="padding:6px 12px;border:1px solid #ddd;">%(project)s</td></tr>
    <tr><td style="padding:6px 12px;border:1px solid #ddd;background:#f5f5f5;font-weight:bold;">Description</td>
        <td style="padding:6px 12px;border:1px solid #ddd;">%(desc)s</td></tr>
    <tr><td style="padding:6px 12px;border:1px solid #ddd;background:#f5f5f5;font-weight:bold;">Date</td>
        <td style="padding:6px 12px;border:1px solid #ddd;">%(date)s</td></tr>
    <tr><td style="padding:6px 12px;border:1px solid #ddd;background:#f5f5f5;font-weight:bold;">Hours</td>
        <td style="padding:6px 12px;border:1px solid #ddd;">%(hours).2f h</td></tr>
  </table>
  <p style="margin-top:16px;">
    Please review under <strong>Timesheets → Portal Timesheet Approvals</strong>.
  </p>
</div>""" % {
            'user':    self.portal_user_id.name,
            'task':    self.task_id.name,
            'project': self.project_id.name or '—',
            'desc':    desc,
            'date':    str(self.date),
            'hours':   self.unit_amount,
        }

        self.env['mail.mail'].sudo().create({
            'subject':     'Timesheet Approval Required — %s' % self.portal_user_id.name,
            'body_html':   body,
            'email_to':    manager.email,
            'auto_delete': True,
        }).send()

    def action_approve(self):
        self.ensure_one()
        manager = self._get_timesheet_manager()
        if not manager or self.env.user.id != manager.id:
            raise UserError(
                "Only the configured Timesheet Manager can approve this request."
            )
        if self.state != 'pending':
            raise UserError("This request is not waiting for approval.")

        timesheet_vals = {
            'name': self.name if self.name != '/' else self.task_id.name,
            'task_id': self.task_id.id,
            'project_id': self.project_id.id,
            'date': self.date,
            'unit_amount': self.unit_amount,
            'user_id': self.portal_user_id.id,
        }
        if self.employee_id:
            timesheet_vals['employee_id'] = self.employee_id.id

        timesheet = self.env['account.analytic.line'].sudo().create(timesheet_vals)
        self.write({'timesheet_id': timesheet.id, 'state': 'approved'})
        self._mark_activity_done(manager.id)
        self.message_post(
            body="Your timesheet request has been <b>approved</b> and recorded.",
            partner_ids=[self.portal_user_id.partner_id.id],
        )

    def action_reject(self):
        self.ensure_one()
        manager = self._get_timesheet_manager()
        if not manager or self.env.user.id != manager.id:
            raise UserError(
                "Only the configured Timesheet Manager can reject this request."
            )
        if self.state != 'pending':
            raise UserError("This request is not waiting for approval.")

        self.state = 'rejected'
        self._mark_activity_done(manager.id)
        body = "Your timesheet request has been <b>rejected</b>."
        if self.rejection_reason:
            body += "<br/>Reason: %s" % self.rejection_reason
        self.message_post(
            body=body,
            partner_ids=[self.portal_user_id.partner_id.id],
        )

    # ----------------------------------------------------------------
    # Activity helpers
    # ----------------------------------------------------------------
    def _send_activity_to_manager(self, manager_user_id):
        self.ensure_one()
        existing = self.env['mail.activity'].search([
            ('res_model', '=', 'portal.timesheet.approval'),
            ('res_id',    '=', self.id),
            ('user_id',   '=', manager_user_id),
        ], limit=1)
        if not existing:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=manager_user_id,
                note=(
                    "Timesheet approval required — "
                    "User: <b>%s</b>, Task: <b>%s</b>, Hours: <b>%.2f</b>"
                    % (self.portal_user_id.name, self.task_id.name, self.unit_amount)
                ),
            )

    def _mark_activity_done(self, manager_user_id):
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'portal.timesheet.approval'),
            ('res_id',    'in', self.ids),
            ('user_id',   '=', manager_user_id),
        ])
        activities.action_done()
