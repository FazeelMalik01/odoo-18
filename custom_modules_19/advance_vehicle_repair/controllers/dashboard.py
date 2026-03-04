from odoo import http, fields
from odoo.http import request
from datetime import date


class LicensingManagementDashboard(http.Controller):

    @http.route('/advance_vehicle_repair/dashboard_data', type="jsonrpc", auth='user')
    def vehicle_dashboard_data(self):
        user = request.env.user

        has_group_manager = user.has_group('advance_vehicle_repair.group_vehicle_repair_manager')
        has_group_user = user.has_group('advance_vehicle_repair.group_vehicle_repair_user')

        Booking = request.env['vehicle.booking'].sudo()
        JobCard = request.env['vehicle.jobcard'].sudo()
        Teams = request.env['vehicle.teams'].sudo()

        booking_domain = [('state', '=', 'create')]
        if has_group_user and not has_group_manager:
            booking_domain.append(('responsible_id', '=', user.id))
        bookings = Booking.search(booking_domain)
        total_bookings = bookings.filtered(lambda b: b).ids
        total_bookings_count = len(total_bookings)

        total_customers_ids = list({b.customer_id.id for b in bookings if b.customer_id})
        total_customers_count = len(total_customers_ids)

        teams = Teams.search([])
        total_teams_ids = teams.ids
        total_teams_count = len(total_teams_ids)

        def get_jobcards_count(booking_type):
            domain = [('booking_type', '=', booking_type)]
            if has_group_user and not has_group_manager:
                domain.append(('responsible_id', '=', user.id))
            jobcards = JobCard.search(domain)
            return jobcards.ids, len(jobcards)

        total_inspection_jobcards_ids, total_inspection_jobcards = get_jobcards_count('vehicle_inspection')
        total_repair_jobcards_ids, total_repair_jobcards = get_jobcards_count('vehicle_repair')
        total_job_cards_ids, total_job_cards = get_jobcards_count('both')

        # Today's bookings
        today = fields.Date.today()
        today_domain = [('state', '=', 'create'), ('booking_date', '=', today)]
        if has_group_user and not has_group_manager:
            today_domain.append(('responsible_id', '=', user.id))
        tbookings = Booking.search(today_domain)
        total_todays_bookings_ids = tbookings.ids
        total_todays_bookings = len(tbookings)

        groupby_advance_vehicle_repair = []
        group_domain = [('state', '=', 'create')]
        if has_group_user and not has_group_manager:
            group_domain.append(('responsible_id', '=', user.id))

        read_group = Booking.sudo()._read_group(
            domain=group_domain,
            groupby=['model_id'],
            aggregates=['model_id:count']
        )

        groupby_advance_vehicle_repair = []
        for model, count in read_group:
            groupby_advance_vehicle_repair.append({
                'model_name': model.display_name if model else '',
                'model_name_count': count,
            })

        results = {
            'total_bookings': total_bookings_count,
            'total_bookings_ids': total_bookings,
            'total_customers': total_customers_count,
            'total_customers_ids': total_customers_ids,
            'total_teams': total_teams_count,
            'total_teams_ids': total_teams_ids,
            'total_inspection_jobcards': total_inspection_jobcards,
            'total_inspection_jobcards_ids': total_inspection_jobcards_ids,
            'total_repair_jobcards': total_repair_jobcards,
            'total_repair_jobcards_ids': total_repair_jobcards_ids,
            'total_job_cards': total_job_cards,
            'total_job_cards_ids': total_job_cards_ids,
            'total_todays_bookings': total_todays_bookings,
            'total_todays_bookings_ids': total_todays_bookings_ids,
            'groupby_advance_vehicle_repair': groupby_advance_vehicle_repair,
        }

        return results

    # @http.route('/advance_vehicle_repair/search_customers', type="json", auth='user')
    # def search_customers(self, term='', limit=15):
    #     """Search partners (customers) by name or phone for dashboard dropdown."""
    #     # Params may come as single dict from jsonrpc
    #     if isinstance(term, dict):
    #         limit = term.get('limit', 15)
    #         term = term.get('term', '')
    #     term = (term or '').strip() if isinstance(term, str) else ''
    #     if not term or len(term) < 1:
    #         return []
    #     limit = int(limit) if limit else 15
    #     Partner = request.env['res.partner'].with_context(active_test=False)
    #     domain = ['|', ('name', 'ilike', term), ('phone', 'ilike', term)]
    #     partners = Partner.search(domain, limit=limit)
    #     return [{'id': p.id, 'name': p.name or '', 'phone': p.phone or ''} for p in partners]
    @http.route('/advance_vehicle_repair/search_customers', type="json", auth='user')
    def search_customers(self, term='', limit=15):
        """Search partners (customers) by name, phone or vehicle registration_no for dashboard dropdown."""
        # Handle dict-style params
        if isinstance(term, dict):
            limit = term.get('limit', 15)
            term = term.get('term', '')
        term = (term or '').strip() if isinstance(term, str) else ''
        if not term or len(term) < 1:
            return []
        limit = int(limit) if limit else 15

        Partner = request.env['res.partner'].with_context(active_test=False)
        Vehicle = request.env['vehicle.register'].with_context(active_test=False)

        # Search partners
        partner_domain = ['|', ('name', 'ilike', term), ('phone', 'ilike', term)]
        partners = Partner.search(partner_domain, limit=limit)

        # Search vehicles by registration_no and get linked partner
        vehicle_domain = [('registration_no', 'ilike', term)]
        vehicles = Vehicle.search(vehicle_domain, limit=limit)
        vehicle_partners = vehicles.mapped('customer_id')  # Assuming vehicle has customer_id field

        # Merge results (avoid duplicates)
        all_partners = partners | vehicle_partners

        return [
            {'id': p.id, 'name': p.name or '', 'phone': p.phone or ''}
            for p in all_partners[:limit]
        ]
