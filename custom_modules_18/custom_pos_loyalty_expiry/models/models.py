from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class LoyaltyCardHistory(models.Model):
    _inherit = "loyalty.history"

    expiry_date = fields.Datetime(string="Expiry Date")

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically set expiry_date to create_date + 6 months"""
        records = super(LoyaltyCardHistory, self).create(vals_list)
        
        # Set expiry_date to create_date + 6 months for each record
        for record in records:
            if record.create_date and not record.expiry_date:
                expiry_date = record.create_date + relativedelta(months=6)
                record.write({'expiry_date': expiry_date})
        
        return records

    def write(self, vals):
        """Override write to trigger card points recalculation when issued changes"""
        result = super(LoyaltyCardHistory, self).write(vals)
        
        # If issued or used field is being changed, recalculate card points
        if 'issued' in vals or 'used' in vals:
            cards_to_update = self.mapped('card_id').filtered(lambda c: c)
            if cards_to_update:
                # Recalculate points from history for each card
                cards_to_update._recompute_points_from_history()
        
        return result

    def _check_and_update_expired_issued(self):
        """Check if expiry_date has passed and set issued to 0 for expired records"""
        now = fields.Datetime.now()
        for record in self:
            if record.expiry_date and record.expiry_date < now and record.issued != 0:
                # Set issued to 0 - this will trigger write() which will update the card
                record.write({'issued': 0})

    def read(self, fields=None, load='_classic_read'):
        """Override read to update expired issued points before reading"""
        self._check_and_update_expired_issued()
        return super(LoyaltyCardHistory, self).read(fields=fields, load=load)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to update expired issued points before reading"""
        records = self.search(domain or [], offset=offset, limit=limit, order=order)
        if records:
            records._check_and_update_expired_issued()
        return super(LoyaltyCardHistory, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )


class LoyaltyCard(models.Model):
    _inherit = "loyalty.card"

    def _recompute_points_from_history(self):
        """Recalculate points field from history records (issued - used)"""
        if not self:
            return
        for card in self:
            # Calculate total points from all history records
            total_points = sum(card.history_ids.mapped(lambda h: h.issued - h.used))
            # Update the points field - this will automatically trigger points_display recomputation
            # since points_display depends on points
            card.write({'points': total_points})

    def _check_and_update_expired_points(self):
        """Check for expired points in history and update card balance"""
        if not self:
            return
        for card in self:
            # Check and update expired issued points in history
            if card.history_ids:
                card.history_ids._check_and_update_expired_issued()
                # Recalculate points after updating expired records
                card._recompute_points_from_history()

    def read(self, fields=None, load='_classic_read'):
        """Override read to check for expired points before reading"""
        self._check_and_update_expired_points()
        return super(LoyaltyCard, self).read(fields=fields, load=load)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **kwargs):
        """Override search_read to check for expired points before reading"""
        records = self.search(domain or [], offset=offset, limit=limit, order=order)
        if records:
            records._check_and_update_expired_points()
        # Pass only the expected parameters, ignore any extra kwargs like 'load'
        return super(LoyaltyCard, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )
