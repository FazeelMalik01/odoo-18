from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    approval_required = fields.Boolean(compute="_compute_approval_required")

    pm_approved = fields.Boolean(string="PM Approved")
    fm_approved = fields.Boolean(string="Finance Approved")
    ceo_approved = fields.Boolean(string="CEO Approved")

    approval_state = fields.Selection(
        [
            ("no", "No Approval Needed"),
            ("pm", "Waiting PM Approval"),
            ("fm", "Waiting Finance Approval"),
            ("ceo", "Waiting CEO Approval"),
            ("approved", "Fully Approved"),
        ],
        default="no",
    )

    current_user_id = fields.Integer(compute="_compute_current_user_id")
    is_creator = fields.Boolean(compute="_compute_is_creator")
    pm_id = fields.Integer(compute="_compute_approver_ids")
    fm_id = fields.Integer(compute="_compute_approver_ids")
    ceo_id = fields.Integer(compute="_compute_approver_ids")

    # --------------------------------------------------
    # SETTINGS FETCH
    # --------------------------------------------------
    def _get_approval_settings(self):
        params = self.env["ir.config_parameter"].sudo()
        discount = float(params.get_param("custom_approvals.discount", default=0))
        pm_id = int(params.get_param("custom_approvals.pm", default=0) or 0)
        fm_id = int(params.get_param("custom_approvals.fm", default=0) or 0)
        ceo_id = int(params.get_param("custom_approvals.ceo", default=0) or 0)
        return discount, pm_id, fm_id, ceo_id

    def _get_below_limit_pm_approver_id(self):
        """PM for discounts under the limit: Purchase settings PM first, then Sales PM."""
        params = self.env["ir.config_parameter"].sudo()
        purchase_pm = int(params.get_param("custom_approvals.purchase_pm", default=0) or 0)
        _, sales_pm, _, _ = self._get_approval_settings()
        return purchase_pm or sales_pm

    def _get_pm_approver_user_id(self):
        """User allowed to approve the PM step for this order (depends on discount vs limit)."""
        self.ensure_one()
        if not self._has_any_discount():
            return 0
        _, sales_pm, _, _ = self._get_approval_settings()
        if self._requires_full_discount_approval():
            return sales_pm
        return self._get_below_limit_pm_approver_id()

    def _has_any_discount(self):
        self.ensure_one()
        return any(line.discount > 0 for line in self.order_line)

    def _requires_full_discount_approval(self):
        self.ensure_one()
        discount_limit, _, _, _ = self._get_approval_settings()
        return any(line.discount >= discount_limit for line in self.order_line)

    def _get_approval_chain(self):
        """Returns ordered list of (state_key, user_id) based on discount policy."""
        self.ensure_one()
        _, pm_id, fm_id, ceo_id = self._get_approval_settings()
        if not self._has_any_discount():
            return []

        if not self._requires_full_discount_approval():
            below_pm = self._get_below_limit_pm_approver_id()
            return [('pm', below_pm)] if below_pm else []

        chain = []
        if pm_id:
            chain.append(('pm', pm_id))
        if fm_id:
            chain.append(('fm', fm_id))
        if ceo_id:
            chain.append(('ceo', ceo_id))
        return chain

    def _get_next_approval_state(self, current_state):
        """Returns (next_state, next_user_id) after current_state, or ('approved', None)."""
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
    def _compute_current_user_id(self):
        for order in self:
            order.current_user_id = self.env.user.id

    def _compute_is_creator(self):
        for order in self:
            order.is_creator = order.create_uid.id == self.env.user.id

    @api.depends("order_line.discount")
    def _compute_approver_ids(self):
        for order in self:
            order.pm_id = order._get_pm_approver_user_id()
            _, _, fm_id, ceo_id = order._get_approval_settings()
            order.fm_id = fm_id
            order.ceo_id = ceo_id

    @api.depends("order_line.discount")
    def _compute_approval_required(self):
        for order in self:
            order.approval_required = order._requires_full_discount_approval() or bool(order._get_approval_chain())

    def _sync_discount_approval_state(self):
        """Persist approval state and notify when discounts require workflow (create/write)."""
        self.ensure_one()
        if not self._has_any_discount():
            if (
                self.approval_state != "no"
                or self.pm_approved
                or self.fm_approved
                or self.ceo_approved
            ):
                self.with_context(skip_discount_approval_sync=True).write(
                    {
                        "approval_state": "no",
                        "pm_approved": False,
                        "fm_approved": False,
                        "ceo_approved": False,
                    }
                )
            return

        chain = self._get_approval_chain()
        if not chain:
            if self._requires_full_discount_approval():
                raise UserError(
                    "This Sale Order requires approval due to discount limits, "
                    "but no approvers are configured. Please set up approvers in Settings."
                )
            if (
                self.approval_state != "no"
                or self.pm_approved
                or self.fm_approved
                or self.ceo_approved
            ):
                self.with_context(skip_discount_approval_sync=True).write(
                    {
                        "approval_state": "no",
                        "pm_approved": False,
                        "fm_approved": False,
                        "ceo_approved": False,
                    }
                )
            return
        if self.approval_state == "no":
            first_state, first_user_id = chain[0]
            self.with_context(skip_discount_approval_sync=True).write(
                {"approval_state": first_state}
            )
            self._send_activity_to_user(first_user_id)

    # --------------------------------------------------
    # CREATE / WRITE
    # --------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            order._sync_discount_approval_state()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("skip_discount_approval_sync"):
            return res
        for order in self:
            order._sync_discount_approval_state()
        return res

    # --------------------------------------------------
    # APPROVAL ACTIONS
    # --------------------------------------------------
    def action_pm_approve(self):
        for order in self:
            pm_id = order._get_pm_approver_user_id()

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
            _, _, fm_id, _ = order._get_approval_settings()

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
            _, _, _, ceo_id = order._get_approval_settings()

            if not ceo_id:
                raise UserError("No CEO is configured for approval.")
            if self.env.user.id != ceo_id:
                raise UserError("Only the configured CEO can approve this step.")

            order.ceo_approved = True
            order.approval_state = "approved"

    # --------------------------------------------------
    # ACTIVITY
    # --------------------------------------------------
    def _send_activity_to_user(self, user_id):
        for order in self:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
                ('user_id', '=', user_id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id)
            ], limit=1)

            if not existing:
                order.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=user_id,
                    note=f"Approval required for Sale Order: {order.name}",
                )

    # --------------------------------------------------
    # CONFIRMATION BLOCK
    # --------------------------------------------------
    def action_confirm(self):
        for order in self:
            if order.approval_required and order.approval_state != "approved":
                raise UserError("This order requires full approval before confirmation.")
            if order.approval_required:
                if self.env.user.id != order.create_uid.id:
                    raise UserError("Only the quotation creator can confirm this quotation.")
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get("skip_discount_approval_sync"):
            for order in lines.order_id:
                order._sync_discount_approval_state()
        return lines

    def write(self, vals):
        orders_before = self.order_id
        res = super().write(vals)
        orders = orders_before | self.order_id
        if not self.env.context.get("skip_discount_approval_sync"):
            for order in orders:
                order._sync_discount_approval_state()
        return res

    def unlink(self):
        orders = self.order_id
        res = super().unlink()
        if not self.env.context.get("skip_discount_approval_sync"):
            for order in orders:
                order._sync_discount_approval_state()
        return res