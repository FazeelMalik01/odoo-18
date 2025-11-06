from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def write(self, vals):
        res = super(AccountMove, self).write(vals)

        for move in self:
            # 1️⃣ Check if the invoice partner is a coach
            coach = self.env['res.users'].search([
                ('partner_id', '=', move.partner_id.id),
                ('is_coach', '=', True)
            ], limit=1)

            # 2️⃣ If not a coach, check if partner is a referred player
            if not coach:
                coach = self.env['res.users'].search([
                    ('referred_users.partner_id', '=', move.partner_id.id)
                ], limit=1)

            # 3️⃣ Trigger _compute_purchases for coach's active tracks
            if coach:
                tracks = self.env['user.commission.track'].sudo().search([
                    ('user_id', '=', coach.id),
                    ('status', '=', 'active')
                ])
                if tracks:
                    tracks._compute_purchases()

        return res

    @api.model
    def create(self, vals):
        invoice = super(AccountMove, self).create(vals)

        if invoice.move_type == 'out_invoice' and invoice.partner_id:
            user = self.env['res.users'].search([('partner_id', '=', invoice.partner_id.id)], limit=1)
            
            if user and user.is_coach:
                today = fields.Date.today()

                CommissionTrack = self.env['user.commission.track'].sudo()

                # 1. Try to find any active track still valid today
                existing_track = CommissionTrack.search([
                    ('user_id', '=', user.id),
                    ('status', '=', 'active'),
                    ('start_date', '<=', today),
                    ('close_date', '>=', today),
                ], limit=1)

                # 2. If no active, check if there’s already a future active track
                if not existing_track:
                    future_track = CommissionTrack.search([
                        ('user_id', '=', user.id),
                        ('status', '=', 'active'),
                        ('start_date', '>', today),
                    ], limit=1)

                    if future_track:
                        _logger.info(
                            "Future active commission track already exists for %s from %s to %s",
                            user.name, future_track.start_date, future_track.close_date
                        )
                        return invoice

                    # 3. If neither active nor future exists, create a new one
                    last_track = CommissionTrack.search([
                        ('user_id', '=', user.id)
                    ], order='close_date desc', limit=1)

                    if last_track:
                        start_date = last_track.close_date + timedelta(days=1)
                        seq = last_track.seq + 1
                    else:
                        start_date = today
                        seq = 1

                    close_date = start_date + timedelta(days=90)

                    CommissionTrack.create({
                        'user_id': user.id,
                        'seq': seq,
                        'start_date': start_date,
                        'close_date': close_date,
                        'status': 'active',
                    })

                    _logger.info("New commission track created for coach %s (%s)", user.name, user.id)
                else:
                    _logger.info("Existing active commission track still valid for coach %s", user.name)
            else:
                _logger.info(
                    "Invoice created for non-coach user or no linked user found. Skipping commission logic for partner: %s",
                    invoice.partner_id.name,
                )

        return invoice