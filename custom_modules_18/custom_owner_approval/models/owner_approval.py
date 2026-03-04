# models/owner_approval.py

from odoo import models, fields, api, _
from datetime import timedelta


class OwnerApproval(models.Model):
    _name = 'owner.approval'
    _description = 'Owner Approval Log (Contractor)'
    _order = 'submission_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(
        string="Reference",
        readonly=True,
        copy=False,
        tracking=True,
    )

    title = fields.Char(
        string="Title",
        required=True,
        tracking=True
    )

    approval_type = fields.Selection([
        ('drawing', 'Drawing'),
        ('material', 'Material'),
        ('method', 'Method Statement'),
        ('rfi', 'RFI'),
        ('other', 'Other'),
    ], string="Approval Type", required=True, tracking=True)

    description = fields.Text(
        string="Description"
    )

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        required=True,
        tracking=True
    )

    task_stage_id = fields.Many2one(
        'project.task.type',
        string="Project Stage",
        tracking=True
    )

    task_id = fields.Many2one(
        'project.task',
        string="Task",
        tracking=True,
        domain="[('project_id', '=', project_id)]"
    )

    boq_ref = fields.Char(
        string="BOQ Reference",
        tracking=True
    )

    location = fields.Char(
        string="Approval Description",
        tracking=True
    )

    owner_partner_id = fields.Many2one(
        'res.partner',
        string="Owner / Consultant",
        required=True,
        tracking=True
    )

    responsible_user_id = fields.Many2one(
        'res.users',
        string="Responsible (Internal)",
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revise', 'Revise'),
        ('late', 'Late Approved'),
    ], string="Status", default='draft', tracking=True)

    submission_date = fields.Datetime(
        string="Submission Date", tracking=True
    )

    required_response_days = fields.Integer(
        string="Required Response Days",
        required=True, 
        tracking=True
    )

    due_date = fields.Datetime(
        string="Due Date",
        compute="_compute_due_date",
        store=True,
    )

    is_overdue = fields.Boolean(
        string="Overdue",
        default=False,
        store=True,
    )

    days_late = fields.Integer(
        string="Days Late",
        default=0,
        store=True,
    )

    decision = fields.Selection([
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revise', 'Revise'),
    ], string="Decision", tracking=True)

    owner_response_date = fields.Datetime(
        string="Owner Response Date",
        tracking=True
    )

    owner_comments = fields.Text(
        string="Owner Comments", tracking=True
    )

    internal_notes = fields.Text(
        string="Internal Notes", tracking=True
    )

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string="Attachments",
        tracking=True
    )

    revision_no = fields.Integer(
        string="Revision No",
        default=0,
        tracking=True
    )

    previous_approval_id = fields.Many2one(
        'owner.approval',
        string="Previous Submission",
        tracking=True
    )
    responsible_signature = fields.Binary(
        string="Responsible User Signature"
    )

    owner_signature = fields.Binary(
        string="Owner Signature"
    )

    @api.model
    def create(self, vals):
        # Sequence
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'owner.approval'
            ) or _('New')

        if not vals.get('submission_date'):
            vals['submission_date'] = fields.Datetime.now()

        rec = super().create(vals)
 
        if rec.owner_partner_id:
            rec.message_subscribe(partner_ids=[rec.owner_partner_id.id])

        return rec
        
    def write(self, vals):
        if "submission_date" not in vals and not any(rec.submission_date for rec in self):
            vals["submission_date"] = fields.Datetime.now()

        return super().write(vals)

    @api.depends('submission_date', 'required_response_days')
    def _compute_due_date(self):
        for rec in self:
            if rec.submission_date and rec.required_response_days:
                rec.due_date = rec.submission_date + timedelta(days=rec.required_response_days)
            else:
                rec.due_date = False

    @api.model
    def  _cron_update_overdue_status(self):
        now = fields.Datetime.now()

        records = self.search([
            ('due_date', '!=', False),
            ('state', '=', 'submitted')
        ])

        for rec in records:
            if now > rec.due_date:
                rec.write({
                    'is_overdue': True,
                    'days_late': (now - rec.due_date).days
                })
            else:
                rec.write({
                    'is_overdue': False,
                    'days_late': 0
            })

    def action_submit(self):
        for rec in self:
            if rec.state not in ('draft', 'revise'):
                continue

            vals = {
                'state': 'submitted',
                'submission_date': fields.Datetime.now(),
            }

            if rec.state == 'revise':
                vals['revision_no'] = rec.revision_no + 1

            rec.write(vals)

            if rec.owner_partner_id and rec.owner_partner_id.email:
                portal_url = f"/my/owner-approval/{rec.id}"
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                link = f"{base_url}{portal_url}"

                subject = f"Owner Approval Submitted: {rec.name or rec.id}"
                body_html = f"""
                <p>Dear {rec.owner_partner_id.name},</p>
                <p>The following Owner Approval has been submitted:</p>
                <p>
                    <a href="{link}">Click here to view the record</a>
                </p>
                <p>Regards,<br/>Your Company</p>
                """

                self.env['mail.mail'].sudo().create({
                    'subject': subject,
                    'body_html': body_html,
                    'email_to': rec.owner_partner_id.email,
                }).send()

    @api.onchange('decision')
    def _onchange_decision(self):
        for rec in self:
            if rec.decision == 'approved':
                rec.state = 'approved'
                rec.owner_response_date = fields.Datetime.now()
                if rec.responsible_user_id and rec.responsible_user_id.sign_signature:
                    rec.responsible_signature = rec.responsible_user_id.sign_signature

            elif rec.decision == 'rejected':
                rec.state = 'rejected'
                rec.owner_response_date = fields.Datetime.now()

            elif rec.decision == 'revise':
                rec.state = 'revise'
                rec.owner_response_date = fields.Datetime.now()
