from odoo import http
from odoo.http import Controller, request, route, SessionExpiredException
from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from collections import OrderedDict
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from operator import itemgetter
# from odoo.osv.expression import OR
from odoo.addons.web.models.models import OR
from odoo.tools import date_utils, groupby as groupbyelem


class VehicleBooking (http.Controller):

    @http.route('/advance_vehicle_repair/get_vehicle_models', type='jsonrpc', auth='public')
    def get_vehicle_models(self, brand_id):
        if not brand_id:
            return False
        models = request.env['vehicle.model'].sudo().search_read([('brand_id', '=', int(brand_id))],['id', 'name'])
        if not models:
            return False
        return models

    @http.route('/advance_vehicle_repair/get_vehicle_appointments', type='jsonrpc', auth='public')
    def get_vehicle_appointments(self, dayOfWeek):
        if not dayOfWeek:
            return False
        models = request.env['vehicle.appointment'].sudo().search_read([('name', '=', dayOfWeek)], ['id', 'name'])
        if not models:
            return False
        return models

    @http.route('/advance_vehicle_repair/get_appointments_slot', type='jsonrpc', auth='public')
    def get_appointments_slot(self, appointmentId):
        if not appointmentId:
            return False
        models = request.env['vehicle.appointment.line'].sudo().search_read([('appointment_id', '=', appointmentId)], ['id', 'time_slot'])
        if not models:
            return False
        return models
    
    @http.route('/advance_vehicle_repair/bookingrequest', type='http', auth='public', website=True)
    def vehicle_booking_request(self, **post):
        values = {}
        brands = request.env['vehicle.brand'].sudo().search([])
        fuel_types = request.env['vehicle.fuel.type'].sudo().search([])
        models = request.env['vehicle.model'].sudo().search([])
        users = request.env['res.users'].sudo().search([('share', '=', False), ('company_ids', 'in', [request.env.company.id])])
        values.update({
            'brands':brands,
            'fuel_types':fuel_types,
            'models':models,
            'users':users,
        })
        return request.render('advance_vehicle_repair.vehicle_booking_request_form', values)
    
    @http.route('/advance_vehicle_repair/bookingrequest/form/', type='http', auth='public', methods=['POST'], website=True)
    def vehicle_booking_request_form(self, **post):
        VehicleBooking = request.env['vehicle.booking.request'].sudo()
        vehicle_register_id = post.get('vehicle_registration_no')
        if vehicle_register_id:
            customer_name = post.get('customer_name')
            customer_mobile = post.get('customer_mobile')
            customer_email = post.get('customer_email')
            brand_id = post.get('vehicle_brand_id')
            model_id = post.get('vehicle_model_id')
            fuel_type_id = post.get('vehicle_fuel_type_id')
            transmission_type = post.get('vehicle_transmission_type')
            registration_no = post.get('vehicle_registration_no')
            vin_no = post.get('vehicle_vin_no')
            booking_date = post.get('booking_date')
            vehicle_responsible_id = post.get('vehicle_responsible_id')

            VehicleBooking.create({
                'customer_name': customer_name,
                'customer_mobile': customer_mobile,
                'customer_email': customer_email,
                'brand_id': brand_id,
                'model_id': model_id,
                'fuel_type_id': fuel_type_id,
                'transmission_type': transmission_type,
                'registration_no' : registration_no,                
                'vin_no' : vin_no,
                'booking_date': booking_date,
                'responsible_id': vehicle_responsible_id,
            })
        return request.render('advance_vehicle_repair.vehicle_booking_request_form_thanks')

    @http.route('/advance_vehicle_repair/create_vehicle', type='http', auth="public", methods=['POST'], website=True)
    def create_vehicle_register(self, **post):
        VehicleRegister = request.env['vehicle.register'].sudo()
        vehicle_registration_no = post.get('vehicle_registration_no')
        customer = request.env.user.partner_id

        if not customer:
            return request.redirect('/web/login')
        if vehicle_registration_no:
            VehicleRegister.create({
                'registration_no' : post.get('vehicle_registration_no'),
                'vin_no': post.get('vehicle_vin_no'),
                'customer_id':customer.id,
                'brand_id': post.get('vehicle_brand_id'),
                'model_id' : post.get('vehicle_model_id'),
                'fuel_type_id' : post.get('vehicle_fuel_type_id'),
                'transmission_type' : post.get('vehicle_transmission_type'),
                'state' : 'active',
            })
            return request.redirect('/my/vehicle_registers')

    @http.route('/advance_vehicle_repair/create_booking', type='http', auth="public", methods=['POST'], website=True)
    def create_vehicle_booking(self, **post):
        VehicleBooking = request.env['vehicle.booking'].sudo()
        VehicleRegister = request.env['vehicle.register'].sudo()

        vehicle_register_id = post.get('vehicle_register_id')
        if vehicle_register_id:
            vehicle = VehicleRegister.search([('id','=', vehicle_register_id)],limit=1)

            booking_type = post.get('booking_type')
            booking_date = post.get('booking_date')
            available_slot = post.get('available_slot')
            observations = post.get('observations')

            VehicleBooking.create({
                'vehicle_register_id' : vehicle.id,
                'registration_no': vehicle.registration_no,
                'brand_id': vehicle.brand_id.id,
                'model_id': vehicle.model_id.id,
                'fuel_type_id': vehicle.fuel_type_id.id,
                'vin_no': vehicle.vin_no,
                'transmission_type': vehicle.transmission_type,
                'booking_type' : booking_type,
                'booking_date' : booking_date,
                'available_slot' : available_slot,
                'observations' : observations,
                'booking_source': 'portal',
                'customer_id': request.env.user.partner_id.id,
            })
        return request.redirect('/my/vehicle_bookings')

class PortalVehicleBooking(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        VehicleBooking = request.env['vehicle.booking']
        VehicleRegister = request.env['vehicle.register']
        if 'vehicle_booking_count' in counters:
            vehicle_booking_count = VehicleBooking.sudo().search_count([
                ('customer_id','=', int(partner.id))
            ])     
            values['vehicle_booking_count'] = vehicle_booking_count or '0'
        if 'vehicle_register_count' in counters:
            vehicle_register_count = VehicleRegister.sudo().search_count([
                ('customer_id','=', int(partner.id)),
            ])     
            values['vehicle_register_count'] = vehicle_register_count or '0'
        return values

    @http.route(['/my/vehicle_registers', '/my/vehicle_registers/page/<int:page>'], type='http', auth="user", website=True)
    def booking_my_vehicle_registers(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        VehicleRegister = request.env['vehicle.register']

        domain = [
            ('customer_id', '=', partner.id),
        ]

        searchbar_inputs = { 
            'state': {'input': 'state', 'label': _('Search in State')},
            'registration_no': {'input': 'registration_no', 'label': _('Search in Registration No')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'state': {'input': 'state', 'label': _('State')},
        }

        searchbar_sortings = {
            'state': {'label': _('State'), 'order': 'state'},
            'registration_no': {'label': _('Registration No'), 'order': 'registration_no'},
        }

        # default sortby order
        if not sortby:
            sortby = 'state'
        sort_order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'active': {'label': _('Active'), 'domain': [('state', '=', 'active')]},
            'canceled': {'label': _('Cancelled'), 'domain': [('state', '=', 'canceled')]},
            'all': {'label': _('All'), 'domain': [('state', 'in', ['active', 'canceled'])]},
        }

        # default filterby value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>=', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('registration_no', 'all'):
                search_domain = OR([search_domain, [('registration_no', 'ilike', search)]])
            if search_in in ('state', 'all'):
                search_domain = OR([search_domain, [('state', 'ilike', search)]])
            domain += search_domain

        # count for pager
        register_count = VehicleRegister.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/vehicle_registers",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total=register_count,
            page=page,
            step=self._items_per_page
        )

        if groupby == 'state':
            sort_order = "state, %s" % sort_order

        # search the records according to the pager data
        registers = VehicleRegister.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        # group the records if needed
        if groupby == 'none':
            grouped_registers = [registers] if registers else []
        else:
            grouped_registers = [VehicleRegister.sudo().concat(*g) for k, g in groupbyelem(registers, itemgetter('state'))]

        request.session['vehicle_register'] = registers.ids[:100]

        brands = request.env['vehicle.brand'].sudo().search([])
        fuel_types = request.env['vehicle.fuel.type'].sudo().search([])
        models = request.env['vehicle.model'].sudo().search([])

        values.update({
            'vehicle_registers': registers.sudo(),
            'page_name': 'vehicle_registers',
            'grouped_registers': grouped_registers,
            'date': date_begin,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'filterby': filterby,
            'search_in': search_in,
            'groupby': groupby,
            'search': search,
            'default_url': '/my/vehicle_registers',
            'brands':brands,
            'fuel_types':fuel_types,
            'models':models,
        })

        return request.render("advance_vehicle_repair.register_list_view_portal", values)

    
    @http.route(['/my/vehicle_bookings', '/my/vehicle_bookings/page/<int:page>'], type='http', auth="user", website=True)
    def booking_my_vehicle_bookings(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id        
        VehicleBooking = request.env['vehicle.booking']
        
        domain = [
            ('customer_id','=', int(partner.id)),
        ]

        searchbar_inputs = {
            'booking': {'input': 'booking', 'label': _('Search in Booking Ref')},        
            'date': {'input': 'date', 'label': _('Search in Booking Date')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'state': {'input': 'state', 'label': _('State')},
        }

        searchbar_sortings = {
            'state': {'label': _('State'), 'booking': 'state'},
            'booking_ref': {'label': _('Booking Ref'), 'booking': 'sequence'},
            'date': {'label': _('Date'), 'booking': 'create_date desc'},
        }

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['booking']

        searchbar_filters = {
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'create': {'label': _('Created'), 'domain': [('state', '=', 'create')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
            'all': {'label': _('All'), 'domain': [('state', 'in', ['draft','create','cancel'])]},
        }

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        
        # search
        if search and search_in:
            search_domain = []
            if search_in in ('booking', 'all'):                
                search_domain = OR([search_domain, [('sequence', 'ilike', search)]])
            if search_in in ('date', 'all'):
                search_domain = OR([search_domain, [('create_date', 'ilike', search)]])
            domain += search_domain


        # count for pager
        pos_order_count = VehicleBooking.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/vehicle_bookings",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total=pos_order_count,
            page=page,
            step=self._items_per_page
        )

        if groupby == 'state':
            sort_order = "state, %s" % sort_order

        # search the count to display, according to the pager data
        bookings = VehicleBooking.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        if groupby == 'none':
            grouped_bookings = []
            if bookings:
                grouped_bookings = [bookings]
        else:
            grouped_bookings = [VehicleBooking.sudo().concat(*g) for k, g in groupbyelem(bookings, itemgetter('state'))]

        request.session['visit_history'] = bookings.ids[:100]


        vehicles = request.env['vehicle.register'].sudo().search_read(  [('customer_id', '=', int(partner.id))],
                                                                      ['id', 'registration_no'])

        values.update({
            'vehicle_bookings': bookings.sudo(),
            'page_name': 'vehicle_bookings',
            'grouped_bookings': grouped_bookings,
            'date': date_begin,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'filterby': filterby,
            'search_in': search_in,
            'groupby': groupby,
            'search': search,
            'default_url': '/my/vehicle_bookings',
            'vehicles': vehicles,
        })
        return request.render("advance_vehicle_repair.booking_list_view_portal", values)

    @http.route(['/my/vehicle_booking/<int:booking>'], type='http', auth="public", website=True)
    def booking_my_vehicle_booking(self, booking, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            booking = self._document_check_access('vehicle.booking', booking, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if booking:
            now = fields.Date.context_today(request.env.user).isoformat()
            session_obj_date = request.session.get(f'view_visit_{booking.id}')
            if session_obj_date != now and request.env.user.share and access_token:
                request.session[f'view_visit_{booking.id}'] = now
                body = _('Booking viewed by customer %s') % booking.customer_id.user_id.sudo().partner_id.name
                request.env['mail.message']._message_post(
                    model="vehicle.booking",
                    res_id=booking.id,
                    body=body,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=booking.customer_id.user_id.sudo().partner_id.ids,
                    access_token=booking.access_token,
                )

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=booking, report_type=report_type, report_ref='advance_vehicle_repair.action_report_booking', download=download)

        values = {
            'vehicle_booking': booking,
            'page_name': 'vehicle_booking',
            'bootstrap_formatting': True,
            'token': access_token,
            'report_type': 'html',
            'partner_id': booking.customer_id.id,
            'action': booking._get_portal_return_action(),
        }        
        return request.render('advance_vehicle_repair.booking_form_view_portal', values)


