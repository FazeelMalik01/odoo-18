from odoo import api, fields, models


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id), ('project_id', '!=', False)]",
        compute='_compute_task_id',
        store=True,
        readonly=False,
        copy=True,
    )

    @api.depends('project_id')
    def _compute_task_id(self):
        """Clear task when project changes."""
        for slot in self:
            if slot.task_id and slot.task_id.project_id != slot.project_id:
                slot.task_id = False

    # ----------------------------------------------------------------
    # Override create: send email + subscribe employee to the task
    # ----------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        slots = super().create(vals_list)
        for slot in slots:
            if slot.task_id and slot.employee_id:
                slot._subscribe_employee_to_task()
                slot._send_task_assignment_email()
        return slots

    def write(self, vals):
        result = super().write(vals)
        # Re-trigger if task or employee changed
        if 'task_id' in vals or 'resource_id' in vals:
            for slot in self:
                if slot.task_id and slot.employee_id:
                    slot._subscribe_employee_to_task()
        return result

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------
    def _subscribe_employee_to_task(self):
        """Add the employee's related user/partner as follower of the task."""
        self.ensure_one()
        partner = self.employee_id.user_id.partner_id or self.employee_id.work_contact_id
        if partner and partner not in self.task_id.message_partner_ids:
            self.task_id.sudo().message_subscribe(partner_ids=[partner.id])

    def _send_task_assignment_email(self):
        """Send a plain SMTP email to the employee about the planning slot."""
        self.ensure_one()
        email_to = self.employee_id.work_email
        if not email_to:
            return

        task = self.task_id
        project = self.project_id
        slot_date = ''
        if self.start_datetime and self.end_datetime:
            slot_date = '%s → %s' % (
                self.start_datetime.strftime('%Y-%m-%d %H:%M'),
                self.end_datetime.strftime('%Y-%m-%d %H:%M'),
            )

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        task_url = '%s%s' % (base_url.rstrip('/'), task.access_url)

        body = """
<div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
  <p>Hello <strong>%(employee)s</strong>,</p>
  <p>You have been assigned to a planning shift linked to the following task.</p>
  <table style="border-collapse:collapse;width:100%%;max-width:500px;">
    <tr>
      <td style="padding:6px 12px;border:1px solid #ddd;background:#f5f5f5;font-weight:bold;">Project</td>
      <td style="padding:6px 12px;border:1px solid #ddd;">%(project)s</td>
    </tr>
    <tr>
      <td style="padding:6px 12px;border:1px solid #ddd;background:#f5f5f5;font-weight:bold;">Task</td>
      <td style="padding:6px 12px;border:1px solid #ddd;">%(task)s</td>
    </tr>
    <tr>
      <td style="padding:6px 12px;border:1px solid #ddd;background:#f5f5f5;font-weight:bold;">Shift Time</td>
      <td style="padding:6px 12px;border:1px solid #ddd;">%(slot_date)s</td>
    </tr>
  </table>
  <p style="margin-top:16px;">
    <a href="%(task_url)s"
       style="display:inline-block;padding:10px 20px;background:#875A7B;color:#fff;
              text-decoration:none;border-radius:4px;font-weight:bold;">
      View Task
    </a>
  </p>
  <p style="font-size:12px;color:#888;">
    Or copy this link: <a href="%(task_url)s">%(task_url)s</a>
  </p>
</div>""" % {
            'employee':  self.employee_id.name,
            'project':   project.name if project else '—',
            'task':      task.name,
            'slot_date': slot_date or '—',
            'task_url':  task_url,
        }

        self.env['mail.mail'].sudo().create({
            'subject':     'New Planning Shift: %s' % task.name,
            'body_html':   body,
            'email_to':    email_to,
            'auto_delete': True,
        }).send()
