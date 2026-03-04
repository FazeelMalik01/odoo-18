from odoo import http, _
from odoo.http import request
import base64
from werkzeug.urls import url_encode
from odoo.exceptions import UserError
from odoo.addons.auth_signup.models.res_users import SignupError
from markupsafe import Markup
import werkzeug
import logging
from datetime import timedelta
from odoo import fields
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.web.controllers.home import Home

_logger = logging.getLogger(__name__)


class CustomHome(Home):

    @http.route('/web/login', type='http', auth='public', website=True, sitemap=False)
    def web_login(self, redirect=None, **kw):
        # Call the original login logic
        response = super().web_login(redirect=redirect, **kw)

        # Only POST requests with successful login
        if request.httprequest.method == 'POST' and request.session.uid:
            user = request.env['res.users'].sudo().browse(request.session.uid)
            # Check if user is portal only (no access rights to backend)
            if user.has_group('base.group_portal') and not user.has_group('base.group_user'):
                return request.redirect('/shop')

        return response




class MyPortalHome(CustomerPortal):

    @http.route(['/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):

        user = request.env.user.sudo()
        
        # Only show commission data for coaches
        track = None
        if user.is_coach:
            track = request.env['user.commission.track'].sudo().search([
                ('user_id', '=', user.id),
                ('status', '=', 'active')
            ], limit=1)

        # Get wallet balance from loyalty card
        wallet_balance = 0.0
        program = request.env['loyalty.program'].sudo().search([('program_type', '=', 'ewallet')], limit=1)
        card = False
        if program:
            card = request.env['loyalty.card'].sudo().search([
                ('partner_id', '=', user.partner_id.id),
                ('program_id', '=', program.id)
            ], limit=1)
            if card:
                wallet_balance = card.points or 0.0
        
        # Force refresh of current balance to ensure we have latest values
        if track:
            track.refresh_current_balance()

        values = {
            'user_id': user,
            'track': track,
            'commission_rate': track.commission_rate or 0.0 if track else 0.0,
            'commission': track.commission or 0.0 if track else 0.0,
            'direct_purchase': track.direct_purchase or 0.0 if track else 0.0,
            'indirect_purchase': track.indirect_purchase or 0.0 if track else 0.0,
            'total_purchase': track.total_purchase or 0.0 if track else 0.0,
            'currency': track.currency_id or request.env.company.currency_id if track else request.env.company.currency_id,
            'current_balance' : track.current_balance or 0.0 if track else 0.0,
            'wallet_balance': wallet_balance,
        }
        return request.render("portal.portal_my_home", values)


class WebsiteTeamRegistration(http.Controller):

    @http.route(['/team/submit'], type='http', auth='public', website=True)
    def show_form(self, **kw):
        return request.render('team_registration.team_form_template', {})

    @http.route(['/team/submit/create'], type='http', auth='public', website=True, csrf=False)
    def create_form(self, **post):
        file_data = post.get('cert_file')
        cert_encoded = False
        filename = False
        if file_data:
            file_content = file_data.read()
            cert_encoded = base64.b64encode(file_content)
            filename = file_data.filename

        email = post.get('email')
        phone = post.get('phone')
        full_phone = '+962' + phone if phone else False

        existing = request.env['team.registration'].sudo().search([
            ('phone', '=', full_phone)
        ], limit=1)

        if existing:
            return request.redirect('/user-exists')  # Redirect to custom error page

        referrer_id = post.get('referrer_id')
        referred_user = int(referrer_id) if referrer_id and referrer_id.isdigit() else None

        request.env['team.registration'].sudo().create({
            'name': post.get('full_name'),
            'phone': full_phone,
            'email': email,
            'password': post.get('password'),
            'role': post.get('role'),
            'years_experience': post.get('experience'),
            'fitness_center': post.get('center'),
            'city': post.get('city'),
            'address': post.get('address'),
            'degree': post.get('degree'),
            'cert_file': cert_encoded,
            'cert_filename': filename,
            'referred_by': referred_user,
        })

        return request.redirect('/thank-you')

    @http.route('/user-exists', type='http', auth='public', website=True)
    def user_exists(self):
        return request.render('team_registration.user_already_exists_template')




    @http.route(['/team/register'], type='http', auth='public', website=True)
    def team_register(self, ref=None):
        return request.render('team_registration.team_form_template', {
            'referrer_id': ref,
        })

    @http.route('/thank-you', type='http', auth='public', website=True)
    def thank_you(self):
        return request.render('team_registration.team_thank_you_template')

    def get_auth_signup_config(self):
        get_param = request.env['ir.config_parameter'].sudo().get_param
        return {
            'disable_database_manager': False,
            'signup_enabled': request.env['res.users']._get_signup_invitation_scope() == 'b2c',
            'reset_password_enabled': get_param('auth_signup.reset_password') == 'True',
        }

    def get_auth_signup_qcontext(self):
        qcontext = {k: v for (k, v) in request.params.items()}
        qcontext.update(self.get_auth_signup_config())
        if not qcontext.get('token') and request.session.get('auth_signup_token'):
            qcontext['token'] = request.session.get('auth_signup_token')
        return qcontext

    def do_signup(self, qcontext):
        values = {key: qcontext.get(key) for key in ('login', 'name', 'password')}
        if not values.get('login') or not values.get('password') or not values.get('name'):
            raise UserError("Please fill in all required fields.")
        if values.get('password') != qcontext.get('confirm_password'):
            raise UserError("Passwords do not match.")
        values['lang'] = request.context.get('lang', 'en_US')
        self._signup_with_values(qcontext.get('token'), values)
        request.env.cr.commit()

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        # Store ?ref=265 in session for later use
        referrer_id = request.params.get('ref')
        if referrer_id and referrer_id.isdigit():
            request.session['referred_by'] = int(referrer_id)

        mobile_field = request.params.get('mobile_field')
        if mobile_field:
            request.session['mobile_field'] = mobile_field


        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)

                # Update session to public if still not logged in
                if request.session.uid is None:
                    public_user = request.env.ref('base.public_user')
                    request.update_env(user=public_user)

                # Email notification
                user = request.env['res.users'].sudo().search([('login', '=', qcontext.get('login'))], limit=1)
                template = request.env.ref('auth_signup.mail_template_user_signup_account_created',
                                           raise_if_not_found=False)
                if user and template:
                    template.sudo().send_mail(user.id, force_send=True)

                return request.redirect('/shop')


            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                _logger.warning("Signup error: %s", e)
                qcontext['error'] = _("Could not create a new account.") + Markup('<br/>') + str(e)

        return request.render('auth_signup.signup', qcontext)

    def _signup_with_values(self, token, values):
        referred_by_id = request.session.pop('referred_by', None)
        referral_link = request.session.pop('referral_link', None)

        if referred_by_id:
            values['referred_by'] = referred_by_id  # Inject referral during creation
        if referral_link:
            values['referral_link'] = referral_link

        login, password = request.env['res.users'].sudo().signup(values, token)
        request.env.cr.commit()

        request.session.authenticate(request.db, {'type': 'password', 'login': login, 'password': password})

    @http.route('/my/team', type='http', auth='user', website=True)
    def my_team(self):
        user = request.env.user
        members = user.referred_users.sudo()
        Invoice = request.env['account.move'].sudo()
        CommissionTrack = request.env['user.commission.track'].sudo()

        # Get all closed tracks for this user
        closed_tracks = CommissionTrack.search([
            ('user_id', '=', user.id),
            ('status', '=', 'closed')
        ])

        # Prepare a dictionary to accumulate team purchase per member
        member_totals = {m.id: 0.0 for m in members}

        for track in closed_tracks:
            start_date = track.start_date
            close_date = track.close_date

            for m in members:
                invoices = Invoice.search([
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('partner_id', '=', m.partner_id.id),
                    ('payment_state', 'in', ['paid', 'in_payment']),
                    ('invoice_date', '>=', start_date),
                    ('invoice_date', '<=', close_date),
                ])
                # Sum without tax
                member_totals[m.id] += sum(inv.amount_untaxed for inv in invoices)

        # Prepare data for the template
        team_data = []
        for m in members:
            team_data.append({
                'name': m.name,
                'email': m.email,
                'mobile':m.mobile,
                'total_purchase': round(member_totals[m.id], 2),
            })

        currency = request.env.company.currency_id

        return request.render('team_registration.portal_my_team_template', {
            'team_data': team_data,
            'currency': currency,
        })


    @http.route(['/my/commission-details'], type='http', auth='user', website=True)
    def my_commission_details(self, **kw):
        user = request.env.user.sudo()
        
        # Only allow coaches to access commission details
        if not user.is_coach:
            return request.redirect('/my/home')
        
        # Get filter parameters
        status_filter = kw.get('status', 'all')
        page = int(kw.get('page', 1))
        per_page = 10
        
        # Build domain for filtering
        domain = [('user_id', '=', user.id)]
        if status_filter != 'all':
            domain.append(('status', '=', status_filter))
        
        # Get total count for pagination
        total_tracks = request.env['user.commission.track'].sudo().search_count(domain)
        
        # Calculate pagination
        total_pages = (total_tracks + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Get paginated tracks
        tracks = request.env['user.commission.track'].sudo().search(
            domain, 
            order='seq desc', 
            limit=per_page, 
            offset=offset
        ) or request.env['user.commission.track'].sudo().browse()
        
        # Get wallet balance from loyalty card
        wallet_balance = 0.0
        program = request.env['loyalty.program'].sudo().search([('program_type', '=', 'ewallet')], limit=1)
        if program:
            card = request.env['loyalty.card'].sudo().search([
                ('partner_id', '=', user.partner_id.id),
                ('program_id', '=', program.id)
            ], limit=1)
            if card:
                wallet_balance = card.points or 0.0
        
        # Calculate summary data (for all tracks, not just paginated ones)
        all_tracks = request.env['user.commission.track'].sudo().search([('user_id', '=', user.id)]) or request.env['user.commission.track'].sudo().browse()
        total_commission = sum(all_tracks.mapped('commission')) if all_tracks else 0.0
        total_transferred = sum(all_tracks.mapped('commission_transferred')) if all_tracks else 0.0
        available_balance = total_commission - total_transferred
        
        # Loyalty history (only debits/used > 0)
        loyalty_history = request.env['loyalty.history'].sudo().search([
            ('card_id', '=', card.id if card else 0),
            ('used', '>', 0)
        ], order='id desc') if card else request.env['loyalty.history'].sudo().browse()

        values = {
            'user_id': user,
            'tracks': tracks,
            'wallet_balance': wallet_balance,
            'total_commission': total_commission,
            'total_transferred': total_transferred,
            'available_balance': available_balance,
            'currency': request.env.company.currency_id,
            'status_filter': status_filter,
            'current_page': page,
            'total_pages': total_pages,
            'total_tracks': total_tracks,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_page': page - 1 if page > 1 else None,
            'next_page': page + 1 if page < total_pages else None,
            'loyalty_history': loyalty_history,
        }
        return request.render('team_registration.portal_commission_details_template', values)
