from odoo import models, fields, api
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    # --------------------------------------------------
    # CUSTOM APPROVAL FIELDS
    # We avoid 'approval_state' — Odoo 19 core already uses it internally
    # as an alias that feeds into 'state', causing ValueError if we write
    # our own selection values into it.
    # --------------------------------------------------
    expense_approval_state = fields.Selection(
        [
            ("draft",    "Draft"),
            ("manager",  "Waiting Manager Approval"),
            ("fm",       "Waiting Finance Approval"),
            ("ceo",      "Waiting CEO Approval"),
            ("approved", "Approved"),
        ],
        default="draft",
        string="Approval Status",
        tracking=True,
    )

    manager_approved = fields.Boolean(default=False)
    fm_approved      = fields.Boolean(default=False)
    ceo_approved     = fields.Boolean(default=False)

    # Integer mirrors of configured approver IDs for view visibility checks
    expense_fm_id   = fields.Integer(compute="_compute_approver_ids")
    expense_ceo_id  = fields.Integer(compute="_compute_approver_ids")
    current_user_id = fields.Integer(compute="_compute_current_user_id")

    # --------------------------------------------------
    # SETTINGS
    # --------------------------------------------------
    def _get_expense_approval_settings(self):
        """Returns (amount_limit: float, fm_user_id: int, ceo_user_id: int)."""
        params = self.env["ir.config_parameter"].sudo()
        amount = float(params.get_param("custom_approvals.expense_amount", default=0) or 0)
        fm_id  = int(params.get_param("custom_approvals.expense_fm",     default=0) or 0)
        ceo_id = int(params.get_param("custom_approvals.expense_ceo",    default=0) or 0)
        return amount, fm_id, ceo_id

    def _needs_ceo(self):
        """True when total_amount_currency >= configured limit (and limit > 0)."""
        self.ensure_one()
        limit, _, _ = self._get_expense_approval_settings()
        return bool(limit) and self.total_amount_currency >= limit

    # --------------------------------------------------
    # COMPUTE
    # --------------------------------------------------
    def _compute_current_user_id(self):
        for exp in self:
            exp.current_user_id = self.env.user.id

    def _compute_approver_ids(self):
        for exp in self:
            _, fm_id, ceo_id = exp._get_expense_approval_settings()
            exp.expense_fm_id  = fm_id
            exp.expense_ceo_id = ceo_id

    # --------------------------------------------------
    # ACTION: Submit
    # --------------------------------------------------
    def action_submit_expense(self):
        for expense in self:
            if not expense.manager_id:
                raise UserError(
                    "Please assign a Manager on the expense before submitting."
                )
            expense.expense_approval_state = "manager"
            expense.sudo().write({"state": "submitted"})
            expense._send_activity_to_user(expense.manager_id.id)

    # --------------------------------------------------
    # ACTION: Manager Approve
    # --------------------------------------------------
    def action_manager_approve(self):
        for expense in self:
            if not expense.manager_id:
                raise UserError("No manager is assigned to this expense.")
            if self.env.user.id != expense.manager_id.id:
                raise UserError(
                    "Only the assigned manager (%s) can approve this step."
                    % expense.manager_id.name
                )
            if expense.expense_approval_state != "manager":
                raise UserError("This expense is not waiting for manager approval.")

            expense.manager_approved = True
            expense._mark_activity_done(expense.manager_id.id)

            _, fm_id, _ = expense._get_expense_approval_settings()
            if not fm_id:
                raise UserError(
                    "Finance Manager is not configured in Settings. "
                    "Please configure it under Expenses → Configuration → Settings."
                )
            expense.expense_approval_state = "fm"
            expense._send_activity_to_user(fm_id)

    # --------------------------------------------------
    # ACTION: Finance Manager Approve
    # --------------------------------------------------
    def action_fm_approve(self):
        for expense in self:
            _, fm_id, ceo_id = expense._get_expense_approval_settings()

            if not fm_id:
                raise UserError("No Finance Manager is configured for approval.")
            if self.env.user.id != fm_id:
                raise UserError(
                    "Only the configured Finance Manager can approve this step."
                )
            if expense.expense_approval_state != "fm":
                raise UserError("This expense is not waiting for Finance Manager approval.")

            expense.fm_approved = True
            expense._mark_activity_done(fm_id)

            if expense._needs_ceo():
                if not ceo_id:
                    raise UserError(
                        "The expense amount exceeds the approval limit but "
                        "no CEO approver is configured in Settings."
                    )
                expense.expense_approval_state = "ceo"
                expense._send_activity_to_user(ceo_id)
            else:
                expense._finalize_and_post()

    # --------------------------------------------------
    # ACTION: CEO Approve
    # --------------------------------------------------
    def action_ceo_approve(self):
        for expense in self:
            _, _, ceo_id = expense._get_expense_approval_settings()

            if not ceo_id:
                raise UserError("No CEO is configured for approval.")
            if self.env.user.id != ceo_id:
                raise UserError("Only the configured CEO can approve this step.")
            if expense.expense_approval_state != "ceo":
                raise UserError("This expense is not waiting for CEO approval.")

            expense.ceo_approved = True
            expense._mark_activity_done(ceo_id)
            expense._finalize_and_post()

    # --------------------------------------------------
    # FINALIZE: approved → posted
    # Uses sudo() to bypass Odoo's native group check on action_approve
    # ("You are neither a Manager nor a HR Officer").
    # Our own approval chain has already validated all steps before this
    # method is ever called.
    # --------------------------------------------------
    def _finalize_and_post(self):
        for expense in self:
            expense.expense_approval_state = "approved"
            # sudo() bypasses hr_expense group checks inside action_approve
            sudo_expense = expense.sudo()
            super(HrExpense, sudo_expense).action_approve()
            # Post journal entries
            if sudo_expense.state == "approved":
                sudo_expense.action_post()

    # --------------------------------------------------
    # BLOCK native action_approve from being used directly
    # --------------------------------------------------
    def action_approve(self, **kwargs):
        for expense in self:
            if expense.expense_approval_state != "approved":
                raise UserError(
                    "This expense must go through the custom approval chain. "
                    "Current status: %s"
                    % dict(expense._fields["expense_approval_state"].selection).get(
                        expense.expense_approval_state
                    )
                )
        return super().action_approve(**kwargs)

    # --------------------------------------------------
    # ACTIVITY HELPERS
    # --------------------------------------------------
    def _send_activity_to_user(self, user_id):
        for expense in self:
            already = self.env["mail.activity"].search([
                ("res_model",        "=", "hr.expense"),
                ("res_id",           "=", expense.id),
                ("user_id",          "=", user_id),
                ("activity_type_id", "=", self.env.ref("mail.mail_activity_data_todo").id),
            ], limit=1)
            if not already:
                expense.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=user_id,
                    note="Expense approval required: %s" % expense.name,
                )

    def _mark_activity_done(self, user_id):
        activities = self.env["mail.activity"].search([
            ("res_model",        "=", "hr.expense"),
            ("res_id",           "in", self.ids),
            ("user_id",          "=", user_id),
            ("activity_type_id", "=", self.env.ref("mail.mail_activity_data_todo").id),
        ])
        activities.action_done()