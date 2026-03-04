# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
import logging

_logger = logging.getLogger(__name__)


class CustomAuthSignupHome(AuthSignupHome):

    def _prepare_signup_qcontext(self, qcontext):
        """Override to add available zip codes for customer signup"""
        result = super()._prepare_signup_qcontext(qcontext)
        signup_type = request.params.get('signup_type') or request.session.get('signup_type')
        
        if signup_type == 'customer':
            # Get available zip codes
            ZipCodeLine = request.env['laundry.zip.code.line'].sudo()
            zip_codes = ZipCodeLine.search([])
            zip_code_list = [{'id': zc.id, 'code': zc.description} for zc in zip_codes if zc.description]
            qcontext['available_zip_codes'] = zip_code_list
        
        return result
    
    @http.route()
    def web_auth_signup(self, *args, **kw):
        """Override to capture signup_type from URL and store in session"""
        signup_type = kw.get('signup_type') or request.params.get('signup_type')
        if signup_type:
            request.session['signup_type'] = signup_type
        
        # Capture redirect_to_booking flag and product_id if coming from pricing page
        redirect_to_booking = kw.get('redirect_to_booking') or request.params.get('redirect_to_booking')
        if redirect_to_booking:
            request.session['redirect_to_booking'] = '1'
            product_id = kw.get('product_id') or request.params.get('product_id')
            if product_id:
                request.session['signup_product_id'] = str(product_id)
        
        # Also capture social_security_no for partners if provided
        if signup_type == 'partner' and request.httprequest.method == 'POST':
            social_security_no = request.params.get('social_security_no', '').strip()
            if social_security_no:
                request.session['signup_social_security_no'] = social_security_no
        
        # Check redirect flag BEFORE calling parent (to preserve it)
        redirect_to_booking = request.session.get('redirect_to_booking')
        signup_type = request.session.get('signup_type')
        product_id = request.session.get('signup_product_id')
        
        result = super().web_auth_signup(*args, **kw)

        if request.httprequest.method == 'POST' and not request.env.user._is_public():
            # Use the values we captured BEFORE calling parent (in case parent cleared session)
            current_redirect = request.session.get('redirect_to_booking') or redirect_to_booking
            current_signup_type = request.session.get('signup_type') or signup_type
            current_product_id = request.session.get('signup_product_id') or product_id
            
            _logger.info(f"web_auth_signup: redirect_to_booking={current_redirect}, signup_type={current_signup_type}, user={request.env.user.login if request.env.user else 'None'}")
            
            if current_redirect == '1' and current_signup_type == 'customer':
                _logger.info(f"web_auth_signup: Redirecting to booking form with product_id={current_product_id}")
                # Clear redirect flags BEFORE redirecting
                request.session.pop('redirect_to_booking', None)
                request.session.pop('signup_product_id', None)
                request.session.pop('signup_type', None)
                # Redirect to booking form
                booking_url = '/my/appointments/book'
                if current_product_id:
                    booking_url += f'?product_id={current_product_id}'
                _logger.info(f"web_auth_signup: Final redirect URL: {booking_url}")
                return request.redirect(booking_url)
        
        return result

    def do_signup(self, qcontext, do_login=True):
        """Override to capture social_security_no for partners and customer fields"""
        signup_type = request.session.get('signup_type')
        _logger.info(f"do_signup: signup_type={signup_type}, qcontext keys={list(qcontext.keys())}")
        
        # Capture social_security_no from form if partner signup
        if signup_type == 'partner' and 'social_security_no' in qcontext:
            request.session['signup_social_security_no'] = qcontext.get('social_security_no', '').strip()
            _logger.info(f"do_signup: Captured social_security_no for partner")
        
        # Capture fields for customer and partner signup
        if signup_type in ['customer', 'partner']:
            _logger.info(f"do_signup: Processing {signup_type} signup, checking for fields")
            _logger.info(f"do_signup: Request method={request.httprequest.method}")
            _logger.info(f"do_signup: qcontext keys={list(qcontext.keys())}")
            _logger.info(f"do_signup: request.params keys={list(request.params.keys())}")
            if hasattr(request.httprequest, 'form'):
                _logger.info(f"do_signup: request.httprequest.form keys={list(request.httprequest.form.keys())}")
            
            # Helper function to get field value from all possible sources
            def get_field_value(field_name):
                return (qcontext.get(field_name, '') or 
                       request.params.get(field_name, '') or 
                       (request.httprequest.form.get(field_name, '') if hasattr(request.httprequest, 'form') else '')).strip()
            
            # Get all customer fields
            title_selection_value = get_field_value('title_selection')
            middle_name_value = get_field_value('middle_name')
            last_name_value = get_field_value('last_name')
            phone_value = get_field_value('phone')
            mobile_value = get_field_value('mobile')
            zip_value = get_field_value('zip')
            city_1_value = get_field_value('city_1')
            street_value = get_field_value('street')
            street2_value = get_field_value('street2')
            
            # Save to session
            if title_selection_value:
                request.session['signup_title_selection'] = title_selection_value
                _logger.info(f"do_signup: Saved title_selection to session: {title_selection_value}")
            if middle_name_value:
                request.session['signup_middle_name'] = middle_name_value
                _logger.info(f"do_signup: Saved middle_name to session: {middle_name_value}")
            if last_name_value:
                request.session['signup_last_name'] = last_name_value
                _logger.info(f"do_signup: Saved last_name to session: {last_name_value}")
            if phone_value:
                request.session['signup_phone'] = phone_value
                _logger.info(f"do_signup: Saved phone to session: {phone_value}")
            if mobile_value:
                request.session['signup_mobile'] = mobile_value
                _logger.info(f"do_signup: Saved mobile to session: {mobile_value}")
            if zip_value:
                request.session['signup_zip'] = zip_value
                _logger.info(f"do_signup: Saved zip to session: {zip_value}")
            if city_1_value:
                request.session['signup_city_1'] = city_1_value
                _logger.info(f"do_signup: Saved city_1 to session: {city_1_value}")
            if street_value:
                request.session['signup_street'] = street_value
                _logger.info(f"do_signup: Saved street to session: {street_value}")
            if street2_value:
                request.session['signup_street2'] = street2_value
                _logger.info(f"do_signup: Saved street2 to session: {street2_value}")
        
        # Call parent do_signup - this will call _signup_with_values internally
        result = super().do_signup(qcontext, do_login)

        return result

    def _signup_with_values(self, token, values, do_login):
        """Override to add group assignment based on signup_type and save customer fields"""
        signup_type = request.session.get('signup_type')
        _logger.info(f"_signup_with_values: signup_type={signup_type}, values keys={list(values.keys())}")
        
        # Get fields from session before calling parent (for both customer and partner)
        partner_title_selection = None
        partner_middle_name = None
        partner_last_name = None
        partner_phone = None
        partner_mobile = None
        partner_zip = None
        partner_city_1 = None
        partner_street = None
        partner_street2 = None
        if signup_type in ['customer', 'partner']:
            partner_title_selection = request.session.get('signup_title_selection', '').strip()
            partner_middle_name = request.session.get('signup_middle_name', '').strip()
            partner_last_name = request.session.get('signup_last_name', '').strip()
            partner_phone = request.session.get('signup_phone', '').strip()
            partner_mobile = request.session.get('signup_mobile', '').strip()
            partner_zip = request.session.get('signup_zip', '').strip()
            partner_city_1 = request.session.get('signup_city_1', '').strip()
            partner_street = request.session.get('signup_street', '').strip()
            partner_street2 = request.session.get('signup_street2', '').strip()
            
            _logger.info(f"_signup_with_values: Retrieved from session - title_selection={partner_title_selection}, middle_name={partner_middle_name}, last_name={partner_last_name}, phone={partner_phone}, mobile={partner_mobile}, zip={partner_zip}, city_1={partner_city_1}, street={partner_street}, street2={partner_street2}")

        # Call parent method to create user and authenticate
        result = super()._signup_with_values(token, values, do_login)
        
        # Get redirect flag and product_id from session (for redirect after signup)
        redirect_to_booking = request.session.get('redirect_to_booking')
        product_id = request.session.get('signup_product_id')
        
        if signup_type in ['customer', 'partner'] and request.env.user and request.env.user.partner_id:
            partner = request.env.user.partner_id.sudo()
            _logger.info(f"_signup_with_values: Partner found - ID={partner.id}, name={partner.name}")
            zip_info = f"partner_zip_code={partner.partner_zip_code}" if signup_type == 'partner' else f"zip={partner.zip}"
            _logger.info(f"_signup_with_values: Current partner values - title_selection={partner.title_selection}, middle_name={partner.middle_name}, last_name={partner.last_name}, phone={partner.phone}, mobile={partner.mobile}, {zip_info}, city_1={partner.city_1}, street={partner.street}, street2={partner.street2}")
            
            needs_save = False
            partner_vals = {}
            
            # Check if values need to be saved
            if partner_title_selection and partner.title_selection != partner_title_selection:
                partner_vals['title_selection'] = partner_title_selection
                needs_save = True
                _logger.info(f"_signup_with_values: Title selection needs update: current='{partner.title_selection}', new='{partner_title_selection}'")
            if partner_middle_name and partner.middle_name != partner_middle_name:
                partner_vals['middle_name'] = partner_middle_name
                needs_save = True
                _logger.info(f"_signup_with_values: Middle name needs update: current='{partner.middle_name}', new='{partner_middle_name}'")
            if partner_last_name and partner.last_name != partner_last_name:
                partner_vals['last_name'] = partner_last_name
                needs_save = True
                _logger.info(f"_signup_with_values: Last name needs update: current='{partner.last_name}', new='{partner_last_name}'")
            if partner_phone and partner.phone != partner_phone:
                partner_vals['phone'] = partner_phone
                needs_save = True
                _logger.info(f"_signup_with_values: Phone needs update: current='{partner.phone}', new='{partner_phone}'")
            if partner_mobile and partner.mobile != partner_mobile:
                partner_vals['mobile'] = partner_mobile
                needs_save = True
                _logger.info(f"_signup_with_values: Mobile needs update: current='{partner.mobile}', new='{partner_mobile}'")
            # For partners, save zip to partner_zip_code; for customers, save to zip
            if signup_type == 'partner' and partner_zip:
                if partner.partner_zip_code != partner_zip:
                    partner_vals['partner_zip_code'] = partner_zip
                    needs_save = True
                    _logger.info(f"_signup_with_values: Partner zip code needs update: current='{partner.partner_zip_code}', new='{partner_zip}'")
            elif signup_type == 'customer' and partner_zip:
                if partner.zip != partner_zip:
                    partner_vals['zip'] = partner_zip
                    needs_save = True
                    _logger.info(f"_signup_with_values: Zip needs update: current='{partner.zip}', new='{partner_zip}'")
            if partner_city_1 and partner.city_1 != partner_city_1:
                partner_vals['city_1'] = partner_city_1
                needs_save = True
                _logger.info(f"_signup_with_values: City_1 needs update: current='{partner.city_1}', new='{partner_city_1}'")
            if partner_street and partner.street != partner_street:
                partner_vals['street'] = partner_street
                needs_save = True
                _logger.info(f"_signup_with_values: Street needs update: current='{partner.street}', new='{partner_street}'")
            if partner_street2 and partner.street2 != partner_street2:
                partner_vals['street2'] = partner_street2
                needs_save = True
                _logger.info(f"_signup_with_values: Street2 needs update: current='{partner.street2}', new='{partner_street2}'")
            
            if needs_save and partner_vals:
                _logger.info(f"_signup_with_values: Writing partner_vals to partner: {partner_vals}")
                try:
                    # Write to partner record
                    partner.write(partner_vals)
                    _logger.info(f"_signup_with_values: Successfully wrote to partner record")
                    
                    # Commit to database immediately
                    request.env.cr.commit()
                    _logger.info(f"_signup_with_values: Committed to database")
                    
                    # Clear cache to ensure fresh data
                    invalidate_fields = ['title_selection', 'middle_name', 'last_name', 'phone', 'mobile', 'city_1', 'street', 'street2']
                    if signup_type == 'partner':
                        invalidate_fields.append('partner_zip_code')
                    else:
                        invalidate_fields.append('zip')
                    partner.invalidate_recordset(invalidate_fields)
                    # Re-read from database
                    partner.refresh()
                    
                    zip_info_after = f"partner_zip_code={partner.partner_zip_code}" if signup_type == 'partner' else f"zip={partner.zip}"
                    _logger.info(f"_signup_with_values: After save - title_selection={partner.title_selection}, middle_name={partner.middle_name}, last_name={partner.last_name}, phone={partner.phone}, mobile={partner.mobile}, {zip_info_after}, city_1={partner.city_1}, street={partner.street}, street2={partner.street2}")
                except Exception as e:
                    _logger.error(f"_signup_with_values: Error saving partner fields: {str(e)}", exc_info=True)
            else:
                _logger.info(f"_signup_with_values: No partner fields need to be updated (needs_save={needs_save}, partner_vals={partner_vals})")
            
            # Clear session data
            request.session.pop('signup_title_selection', None)
            request.session.pop('signup_middle_name', None)
            request.session.pop('signup_last_name', None)
            request.session.pop('signup_phone', None)
            request.session.pop('signup_mobile', None)
            request.session.pop('signup_zip', None)
            request.session.pop('signup_city_1', None)
            request.session.pop('signup_street', None)
            request.session.pop('signup_street2', None)
            _logger.info(f"_signup_with_values: Cleared session data for {signup_type} fields")
        
        # Assign group and save partner-specific fields
        if signup_type:
            user = request.env.user
            if user:
                group_xmlid = f'custom_laundry_service.group_{signup_type}'
                try:
                    group = request.env.ref(group_xmlid)
                    user.sudo().write({'group_ids': [(4, group.id)]})
                    
                    # Save Social Security Number for partners
                    if signup_type == 'partner':
                        social_security_no = request.session.get('signup_social_security_no', '').strip()
                        if social_security_no:
                            user.partner_id.sudo().write({'social_security_no': social_security_no})
                            request.session.pop('signup_social_security_no', None)
                    
                    # Don't clear signup_type yet - we need it for redirect check
                except ValueError:
                    pass
        
        return result

