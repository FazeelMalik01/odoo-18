from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class CommissionTopUpController(http.Controller):

    @http.route('/commission/topup', type='http', auth='user', methods=['POST'], csrf=False)
    def commission_topup(self, **kwargs):
        try:
            # Get parameters from form data
            user_id = kwargs.get('user_id')
            amount = kwargs.get('amount')
            
            if not user_id or not amount:
                _logger.error("Missing required parameters: user_id=%s, amount=%s", user_id, amount)
                return request.make_json_response({'success': False, 'error': "Missing required parameters."})
            
            _logger.info("Top-up request received: user_id=%s, amount=%s", user_id, amount)
            _logger.info("Request method: %s", request.httprequest.method)
            _logger.info("Request content type: %s", request.httprequest.content_type)
            _logger.info("All kwargs: %s", kwargs)

            user = request.env['res.users'].browse(int(user_id))
            if not user or user != request.env.user:
                _logger.warning("Top-up not allowed for user_id=%s", user_id)
                return request.make_json_response({'success': False, 'error': "Not allowed."})
            
            # Check if user is a coach
            if not user.is_coach:
                _logger.warning("Top-up not allowed for non-coach user_id=%s", user_id)
                return request.make_json_response({'success': False, 'error': "Commission top-up is only available for coaches."})

            # Find all closed commission tracks for this user
            tracks = request.env['user.commission.track'].sudo().search([
                ('user_id', '=', user.id),
                ('status', '=', 'closed')
            ])
            if not tracks:
                _logger.warning("No closed commission tracks found for user_id=%s", user_id)
                return request.make_json_response({'success': False, 'error': "No closed commissions available."})

            # Calculate available commission balance
            total_commission = sum(tracks.mapped('commission'))
            total_transferred = sum(tracks.mapped('commission_transferred'))
            available_balance = total_commission - total_transferred

            if available_balance <= 0:
                _logger.warning("No current balance for user_id=%s", user_id)
                return request.make_json_response({'success': False, 'error': "No current balance available."})

            topup_amount = float(amount)
            if topup_amount > available_balance:
                _logger.warning(
                    "Top-up amount exceeds current balance for user_id=%s: requested=%s, available=%s",
                    user_id, topup_amount, available_balance
                )
                return request.make_json_response({'success': False, 'error': f"Amount exceeds current balance ({available_balance})."})

            # Find "eWallet" loyalty program
            program = request.env['loyalty.program'].sudo().search([('program_type', '=', 'ewallet')], limit=1)
            if not program:
                _logger.error("No eWallet program found for user_id=%s", user_id)
                return request.make_json_response({'success': False, 'error': "eWallet program not found."})

            # Find or create loyalty card for eWallet
            card = request.env['loyalty.card'].sudo().search([
                ('partner_id', '=', user.partner_id.id),
                ('program_id', '=', program.id)
            ], limit=1)

            if not card:
                card = request.env['loyalty.card'].sudo().create({
                    'program_id': program.id,
                    'partner_id': user.partner_id.id,
                    'points': 0.0,
                })
                _logger.info("Created new eWallet card for user_id=%s, card_id=%s", user_id, card.id)

            # Add points to eWallet
            card.sudo().write({'points': card.points + topup_amount})
            request.env['loyalty.history'].sudo().create({
                'card_id': card.id,
                'description': "Top-up from Commission Balance",
                'issued': topup_amount,
                'used': 0.0,
            })
            _logger.info("Added %s points to eWallet card_id=%s for user_id=%s", topup_amount, card.id, user_id)

            # Update transferred commission on the latest closed track (simple version)
            latest_track = tracks[0]
            latest_track.sudo().write({
                'commission_transferred': latest_track.commission_transferred + topup_amount
            })

            # Force recomputation of current_balance for all tracks
            tracks.refresh_current_balance()
            
            # Recompute new balance across all closed tracks
            new_total_transferred = sum(tracks.mapped('commission_transferred'))
            new_balance = total_commission - new_total_transferred

            _logger.info(
                "Transferred %s from commission to wallet for user_id=%s | new_balance=%s | wallet_points=%s",
                topup_amount, user_id, new_balance, card.points
            )

            return request.make_json_response({
                'success': True,
                'amount': topup_amount,
                'new_balance': new_balance,
                'wallet_balance': card.points,
            })
        except Exception as e:
            _logger.error("Error in commission topup: %s", str(e))
            return request.make_json_response({'success': False, 'error': f"An error occurred: {str(e)}"})