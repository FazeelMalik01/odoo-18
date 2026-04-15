from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_required = fields.Boolean(compute="_compute_approval_required")

    pm_approved = fields.Boolean(string="PM Approved")
    fm_approved = fields.Boolean(string="Finance Approved")
    ceo_approved = fields.Boolean(string="CEO Approved")

    approval_state = fields.Selection([
        ('no', 'No Approval Needed'),
        ('pm', 'Waiting PM Approval'),
        ('fm', 'Waiting Finance Approval'),
        ('ceo', 'Waiting CEO Approval'),
        ('approved', 'Fully Approved')
    ], default='no')

    current_user_id = fields.Integer(compute="_compute_current_user_id")
    pm_id = fields.Integer(compute="_compute_approver_ids", depends=['approval_required'])
    fm_id = fields.Integer(compute="_compute_approver_ids", depends=['approval_required'])
    ceo_id = fields.Integer(compute="_compute_approver_ids", depends=['approval_required'])

    # --------------------------------------------------
    # SETTINGS FETCH
    # --------------------------------------------------
    def _get_purchase_settings(self):
        params = self.env['ir.config_parameter'].sudo()
        amount = float(params.get_param('custom_approvals.purchase_amount', default=0))
        pm_id = int(params.get_param('custom_approvals.purchase_pm', default=0) or 0)
        fm_id = int(params.get_param('custom_approvals.purchase_fm', default=0) or 0)
        ceo_id = int(params.get_param('custom_approvals.purchase_ceo', default=0) or 0)
        return amount, pm_id, fm_id, ceo_id

    def _requires_full_amount_approval(self):
        self.ensure_one()
        amount_limit, _, _, _ = self._get_purchase_settings()
        return self.amount_total >= amount_limit

    def _get_approval_chain(self):
        """Returns ordered list of (state_key, user_id) based on PO amount policy."""
        _, pm_id, fm_id, ceo_id = self._get_purchase_settings()

        if not self._requires_full_amount_approval():
            return [('pm', pm_id)] if pm_id else []

        chain = []
        if pm_id:
            chain.append(('pm', pm_id))
        if fm_id:
            chain.append(('fm', fm_id))
        if ceo_id:
            chain.append(('ceo', ceo_id))
        return chain

    def _get_first_approval_state(self):
        """Returns the first approval state in chain, or 'approved' if chain is empty."""
        chain = self._get_approval_chain()
        if not chain:
            return None  # No approvers configured
        return chain[0][0]

    def _get_next_approval_state(self, current_state):
        """Returns the next state after current_state, or 'approved' if last in chain."""
        chain = self._get_approval_chain()
        keys = [c[0] for c in chain]
        if current_state in keys:
            idx = keys.index(current_state)
            if idx + 1 < len(keys):
                return chain[idx + 1][0], chain[idx + 1][1]
        return 'approved', None

    # --------------------------------------------------
    # COMPUTE
    # --------------------------------------------------
    @api.depends('amount_total')
    def _compute_approval_required(self):
        for order in self:
            order.approval_required = order._requires_full_amount_approval() or bool(order._get_approval_chain())

            if order.approval_required and order.approval_state == 'no':
                first_state = order._get_first_approval_state()
                if first_state:
                    order.approval_state = first_state

    def _compute_current_user_id(self):
        for order in self:
            order.current_user_id = self.env.user.id

    def _compute_approver_ids(self):
        for order in self:
            _, pm_id, fm_id, ceo_id = order._get_purchase_settings()
            order.pm_id = pm_id
            order.fm_id = fm_id
            order.ceo_id = ceo_id

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)

        for order in orders:
            order._compute_approval_required()

            if order.approval_required:
                chain = order._get_approval_chain()

                if not chain:
                    raise UserError(
                        "This Purchase Order requires approval but no approvers are "
                        "configured. Please set up approvers in Settings."
                    )

                first_state, first_user_id = chain[0]
                if order.approval_state == 'no':
                    order.approval_state = first_state

                order._send_activity_to_user(first_user_id)

        return orders

    # --------------------------------------------------
    # APPROVAL ACTIONS
    # --------------------------------------------------
    def action_pm_approve(self):
        for order in self:
            _, pm_id, _, _ = order._get_purchase_settings()

            if not pm_id:
                raise UserError("No Project Manager is configured for approval.")
            if self.env.user.id != pm_id:
                raise UserError("Only the configured Project Manager can approve this step.")

            order.pm_approved = True
            next_state, next_user_id = order._get_next_approval_state('pm')
            order.approval_state = next_state
            if next_user_id:
                order._send_activity_to_user(next_user_id)

    def action_fm_approve(self):
        for order in self:
            _, _, fm_id, _ = order._get_purchase_settings()

            if not fm_id:
                raise UserError("No Finance Manager is configured for approval.")
            if self.env.user.id != fm_id:
                raise UserError("Only the configured Finance Manager can approve this step.")

            order.fm_approved = True
            next_state, next_user_id = order._get_next_approval_state('fm')
            order.approval_state = next_state
            if next_user_id:
                order._send_activity_to_user(next_user_id)

    def action_ceo_approve(self):
        for order in self:
            _, _, _, ceo_id = order._get_purchase_settings()

            if not ceo_id:
                raise UserError("No CEO is configured for approval.")
            if self.env.user.id != ceo_id:
                raise UserError("Only the configured CEO can approve this step.")

            order.ceo_approved = True
            order.approval_state = 'approved'

    # --------------------------------------------------
    # ACTIVITY
    # --------------------------------------------------
    def _send_activity_to_user(self, user_id):
        for order in self:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'purchase.order'),
                ('res_id', '=', order.id),
                ('user_id', '=', user_id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id)
            ], limit=1)

            if not existing:
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user_id,
                    note=f"Approval required for Purchase Order: {order.name}"
                )

    # --------------------------------------------------
    # CONFIRMATION BLOCK
    # --------------------------------------------------
    def button_confirm(self):
        for order in self:
            if order.approval_required and order.approval_state != 'approved':
                raise UserError("This Purchase Order requires full approval before confirmation.")
        return super().button_confirm()