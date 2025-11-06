from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class UserCommissionTrack(models.Model):
    _name = "user.commission.track"
    _description = "User Commission Tracking"
    _order = "seq"

    user_id = fields.Many2one("res.users", string="User", required=True)
    seq = fields.Integer("Sequence")
    start_date = fields.Date("Start Date", required=True)
    close_date = fields.Date("Close Date", required=True)
    status = fields.Selection([
        ("inactive", "Inactive"),
        ("active", "Active"),
        ("closed", "Closed"),
    ], string="Status", default="inactive")

    direct_purchase = fields.Float("Direct Purchase", compute="_compute_purchases", store=True)
    indirect_purchase = fields.Float("Team Purchase", compute="_compute_purchases", store=True)
    total_purchase = fields.Float("Total Purchase", compute="_compute_purchases", store=True)
    commission = fields.Float("Earned Commission", compute="_compute_purchases", store=True)
    commission_rate = fields.Float("Commission Rate (%)", compute="_compute_purchases", store=True)
    current_balance = fields.Float("Current Balance", compute="_compute_purchases", store=True)
    commission_transferred = fields.Float("Transferred to Wallet", default=0.0)

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    @api.constrains('user_id')
    def _check_user_is_coach(self):
        """Ensure only coaches can have commission tracks"""
        for track in self:
            if track.user_id and not track.user_id.is_coach:
                raise ValidationError("Commission tracking is only available for coaches. User '%s' is not a coach." % track.user_id.name)

    @api.model
    def create(self, vals):
        """Override create to validate coach status"""
        if 'user_id' in vals:
            user = self.env['res.users'].browse(vals['user_id'])
            if not user.is_coach:
                raise ValidationError("Commission tracking can only be created for coaches. User '%s' is not a coach." % user.name)
        return super().create(vals)

    @api.depends('user_id', 'user_id.partner_id', 'user_id.referred_users',
                'start_date', 'close_date', 'status', 'commission_transferred')
    def _compute_purchases(self):
        """Compute all purchases and commissions for the current cycle,
        isolated to that track's start_date → close_date window.
        """
        # today = fields.Date.today()
        # today = fields.Date.from_string('2032-06-22') 
        today = self.env.company.test_today or fields.Date.today()

        for track in self:
            user = track.user_id

            # default values if no transactions
            direct_purchase = 0.0
            indirect_purchase = 0.0
            total_purchase = 0.0
            commission = 0.0
            rate = 0.0

            if user and track.start_date and track.close_date:
                # --- Direct purchases in this period ---
                direct_invoices = self.env['account.move'].sudo().search([
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ['paid', 'in_payment']),
                    ('partner_id', '=', user.partner_id.id),
                    ('invoice_date', '>=', track.start_date),
                    ('invoice_date', '<=', track.close_date),
                ])
                direct_purchase = sum(inv.amount_untaxed for inv in direct_invoices)


                # --- Indirect (team) purchases ---
                for ref_user in user.referred_users:
                    _logger.info("Processing referred user: %s (ID: %s, Partner ID: %s)", 
                                ref_user.name, ref_user.id, ref_user.partner_id.id)

                    invoices = self.env['account.move'].sudo().search([
                        ('move_type', '=', 'out_invoice'),
                        ('state', '=', 'posted'),
                        ('payment_state', 'in', ['paid', 'in_payment']),
                        ('partner_id', '=', ref_user.partner_id.id),
                        ('invoice_date', '>=', track.start_date),
                        ('invoice_date', '<=', track.close_date),
                    ])

                    _logger.info("Found %s invoices for referred user %s", len(invoices), ref_user.name)

                    for inv in invoices:
                        _logger.info("Invoice %s | Date: %s | Untaxed: %s | Paid: %s", 
                                    inv.name, inv.invoice_date, inv.amount_untaxed, inv.payment_state)

                    indirect_purchase += sum(inv.amount_untaxed for inv in invoices)

                _logger.info("Total indirect purchase so far: %s", indirect_purchase)

                total_purchase = direct_purchase + indirect_purchase
                _logger.info("Final total purchase (Direct + Indirect): %s + %s = %s",
                            direct_purchase, indirect_purchase, total_purchase)


                # --- Commission slice ---
                commission_slice = self.env['commission.slices'].sudo().search([
                    ('from_amount', '<=', total_purchase),
                    ('to_amount', '>=', total_purchase),
                ], limit=1)

                rate = (commission_slice.commission_percentage or 0.0) if commission_slice else 0.0
                _logger.info(
                    "User: %s | Commission Percentage from slice: %s | Calculated rate: %s",
                    user.name,
                    commission_slice.commission_percentage if commission_slice else 0.0,
                    rate
                )
                commission = total_purchase * rate

            # --- Set computed values ---
            track.direct_purchase = direct_purchase
            track.indirect_purchase = indirect_purchase
            track.total_purchase = total_purchase
            track.commission = commission
            track.commission_rate = rate * 100

            # --- Auto-close active cycles when needed ---
            if track.status == "active" and track.close_date and track.close_date < today:
                track.status = "closed"
                _logger.info("Closing cycle for %s (seq %s)", user.name, track.seq)
                cycle_days = track.user_id.company_id.commission_cycle_days or 90

                # Create next cycle
                last_seq = track.seq
                next_start = track.close_date + timedelta(days=1)
                next_close = next_start + timedelta(days=cycle_days)
                self.create({
                    "user_id": user.id,
                    "seq": last_seq + 1,
                    "start_date": next_start,
                    "close_date": next_close,
                    "status": "active",
                })

            # --- Current balance = sum of closed commissions minus transferred amount ---
            if track.user_id:
                closed_tracks = self.search([
                    ('user_id', '=', track.user_id.id),
                    ('status', '=', 'closed')
                ])
                total_commission = sum(closed_tracks.mapped('commission'))
                total_transferred = sum(closed_tracks.mapped('commission_transferred'))

                track.current_balance = max(total_commission - total_transferred, 0.0)
    
    def refresh_current_balance(self):
        """Manually refresh current balance for a user"""
        for track in self:
            if track.user_id:
                closed_tracks = self.search([
                    ('user_id', '=', track.user_id.id),
                    ('status', '=', 'closed')
                ])
                total_commission = sum(closed_tracks.mapped('commission'))
                total_transferred = sum(closed_tracks.mapped('commission_transferred'))
                track.current_balance = max(total_commission - total_transferred, 0.0)

    @api.model
    def cron_process_commission_tracks(self):
        """Daily cron: close expired active tracks and create next cycles.

        Reuses the existing _compute_purchases auto-close logic by invoking it on
        active tracks whose close_date has passed.
        """
        today = self.env.company.test_today or fields.Date.today()
        expired_active = self.search([
            ('status', '=', 'active'),
            ('close_date', '<', today),
        ])
        if not expired_active:
            _logger.info("Commission cron: no expired active tracks found.")
            return

        # Trigger compute to execute the auto-close + next-cycle creation logic
        _logger.info("Commission cron: processing %s expired active tracks", len(expired_active))
        expired_active._compute_purchases()
        _logger.info("Commission cron: processing completed.")

    @api.model
    def cron_auto_commission_topup(self):
        """Automatic commission top-up cron job.
        
        This method automatically transfers available commission balance to eWallet
        for all coaches who have closed commission tracks with available balance.
        """
        _logger.info("Starting automatic commission top-up cron job")
        
        try:
            # Find all coaches with closed commission tracks
            coaches = self.env['res.users'].sudo().search([('is_coach', '=', True)])
            processed_count = 0
            total_amount = 0.0
            
            for coach in coaches:
                # Find all closed commission tracks for this coach
                closed_tracks = self.search([
                    ('user_id', '=', coach.id),
                    ('status', '=', 'closed')
                ])
                
                if not closed_tracks:
                    continue
                
                # Calculate available commission balance
                total_commission = sum(closed_tracks.mapped('commission'))
                total_transferred = sum(closed_tracks.mapped('commission_transferred'))
                available_balance = total_commission - total_transferred
                
                if available_balance <= 0:
                    continue
                
                _logger.info("Processing auto top-up for coach %s (ID: %s) with balance: %s", 
                           coach.name, coach.id, available_balance)
                
                # Find "eWallet" loyalty program
                program = self.env['loyalty.program'].sudo().search([('program_type', '=', 'ewallet')], limit=1)
                if not program:
                    _logger.error("No eWallet program found for auto top-up")
                    continue
                
                # Find or create loyalty card for eWallet
                card = self.env['loyalty.card'].sudo().search([
                    ('partner_id', '=', coach.partner_id.id),
                    ('program_id', '=', program.id)
                ], limit=1)
                
                if not card:
                    card = self.env['loyalty.card'].sudo().create({
                        'program_id': program.id,
                        'partner_id': coach.partner_id.id,
                        'points': 0.0,
                    })
                    _logger.info("Created new eWallet card for coach %s, card_id=%s", coach.name, card.id)
                
                # Add points to eWallet
                card.sudo().write({'points': card.points + available_balance})
                self.env['loyalty.history'].sudo().create({
                    'card_id': card.id,
                    'description': "Automatic Top-up from Commission Balance (Cron)",
                    'issued': available_balance,
                    'used': 0.0,
                })
                
                # Update transferred commission on all closed tracks
                for track in closed_tracks:
                    remaining_to_transfer = track.commission - track.commission_transferred
                    if remaining_to_transfer > 0:
                        track.sudo().write({
                            'commission_transferred': track.commission
                        })
                
                # Force recomputation of current_balance for all tracks
                closed_tracks.refresh_current_balance()
                
                processed_count += 1
                total_amount += available_balance
                
                _logger.info(
                    "Auto top-up completed for coach %s: transferred %s to wallet (total wallet points: %s)",
                    coach.name, available_balance, card.points
                )
            
            _logger.info(
                "Automatic commission top-up cron completed: processed %s coaches, total amount: %s",
                processed_count, total_amount
            )
            
        except Exception as e:
            _logger.error("Error in automatic commission top-up cron: %s", str(e))

