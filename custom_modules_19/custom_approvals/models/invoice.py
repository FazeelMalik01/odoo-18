from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Approval stage ──────────────────────────────────────────────────────
    approval_state = fields.Selection(
        selection=[
            ('pending_fm',  'Waiting Finance Manager'),
            ('pending_ceo', 'Waiting CEO'),
            ('approved',    'Approved'),
            ('refused',     'Refused'),
        ],
        string='Approval Stage',
        default=False,
        copy=False,
        tracking=True,
    )

    # Convenience flags used in the view
    show_fm_approve   = fields.Boolean(compute='_compute_approval_buttons')
    show_ceo_buttons  = fields.Boolean(compute='_compute_approval_buttons')

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _get_approval_users(self):
        """Return (fm_user, ceo_user) from system parameters."""
        ICP = self.env['ir.config_parameter'].sudo()
        fm_id  = int(ICP.get_param('custom_approvals.invoice_fm',  0) or 0)
        ceo_id = int(ICP.get_param('custom_approvals.invoice_ceo', 0) or 0)
        Users  = self.env['res.users'].sudo()
        fm  = Users.browse(fm_id)  if fm_id  else self.env['res.users']
        ceo = Users.browse(ceo_id) if ceo_id else self.env['res.users']
        return fm, ceo

    # ── Computed buttons visibility ──────────────────────────────────────────
    @api.depends('approval_state', 'move_type', 'state')
    def _compute_approval_buttons(self):
        fm, ceo = self._get_approval_users()
        uid = self.env.uid
        for move in self:
            is_invoice = move.move_type in (
                'out_invoice', 'out_refund', 'in_invoice', 'in_refund'
            )
            move.show_fm_approve = (
                is_invoice
                and move.approval_state == 'pending_fm'
                and uid == fm.id
            )
            move.show_ceo_buttons = (
                is_invoice
                and move.approval_state == 'pending_ceo'
                and uid == ceo.id
            )

    # ── Override create → trigger workflow ──────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.move_type in (
                'out_invoice', 'out_refund', 'in_invoice', 'in_refund'
            ):
                move._start_approval_workflow()
        return moves

    def _start_approval_workflow(self):
        """Set approval_state and send activity to Finance Manager."""
        fm, _ceo = self._get_approval_users()
        if not fm:
            return  # no FM configured – skip silently

        self.approval_state = 'pending_fm'

        # Activity → Finance Manager
        self._send_approval_activity(
            user=fm,
            summary=_('Invoice Approval Required – Finance Manager'),
            note=_(
                'A new invoice <b>%s</b> has been created and requires your '
                'review before it is sent to the CEO for final approval.'
            ) % self.name,
        )

    # ── FM approves ─────────────────────────────────────────────────────────
    def action_fm_approve(self):
        self.ensure_one()
        fm, ceo = self._get_approval_users()
        if self.env.uid != fm.id:
            raise UserError(_('Only the Finance Manager can perform this action.'))

        # Mark any open FM activity as done
        self._mark_activity_done(fm)

        if not ceo:
            # No CEO configured → go straight to approved
            self.approval_state = 'approved'
            return

        self.approval_state = 'pending_ceo'

        # Activity → CEO
        self._send_approval_activity(
            user=ceo,
            summary=_('Invoice Approval Required – CEO'),
            note=_(
                'Invoice <b>%s</b> has been reviewed by the Finance Manager '
                'and is now awaiting your final approval.'
            ) % self.name,
        )

    # ── CEO confirms (posts) ─────────────────────────────────────────────────
    def action_ceo_approve(self):
        self.ensure_one()
        _fm, ceo = self._get_approval_users()
        if self.env.uid != ceo.id:
            raise UserError(_('Only the CEO can perform this action.'))

        self._mark_activity_done(ceo)
        self.approval_state = 'approved'

        # Actually post the invoice
        self.action_post()

    # ── CEO cancels ─────────────────────────────────────────────────────────
    def action_ceo_refuse(self):
        self.ensure_one()
        _fm, ceo = self._get_approval_users()
        if self.env.uid != ceo.id:
            raise UserError(_('Only the CEO can perform this action.'))

        self._mark_activity_done(ceo)
        self.approval_state = 'refused'

        self.message_post(
            body=_('Invoice <b>%s</b> has been refused by the CEO.') % self.name,
            message_type='notification',
        )

    # ── Activity helpers ─────────────────────────────────────────────────────
    def _send_approval_activity(self, user, summary, note):
        activity_type = self.env.ref(
            'mail.mail_activity_data_todo',
            raise_if_not_found=False,
        )
        self.activity_schedule(
            activity_type_id=activity_type.id if activity_type else False,
            summary=summary,
            note=note,
            user_id=user.id,
        )

    def _mark_activity_done(self, user):
        """Mark all open activities for *user* on this record as done."""
        activities = self.activity_ids.filtered(
            lambda a: a.user_id == user
        )
        activities.action_done()