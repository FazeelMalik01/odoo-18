from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


def validate_mandatory_fields(mandate_fields, kw):
    """validate mandatory fields"""
    error, data = None, {}
    for key, value in mandate_fields.items():
        if not kw.get(key):
            error = "Mandatory fields " + value + " Missing"
            break
        data[key] = kw.get(key)
    return error, data


def validate_optional_fields(opt_fields, kw):
    """validate optional fields"""
    data = {}
    for fld in opt_fields:
        if kw.get(fld):
            data[fld] = kw.get(fld)
    return data


class DietRequest(Website):
    """diet request"""

    def _get_initial_values(self):
        """get initial values"""
        diet_category = request.env['diet.category'].sudo().search([])
        diet_type = request.env['diet.type'].sudo().search([])
        return {
            'diet_category': diet_category,
            'diet_type': diet_type,
        }

    @http.route('/diet-request', auth='public', website=True, type='http')
    def diet_request(self):
        """diet request"""
        ctx = self._get_initial_values()
        return request.render('tk_gym_management.diet_request_form', ctx)

    @http.route('/done-request', auth='public', website=True, type='http')
    def done_diet_request(self, **kw):
        """done diet request"""
        values = self._get_initial_values()
        mandatory_fields = {'name': "Title", 'contact_name': 'Name', 'email_from': 'Email',
                            'birthdate': 'Birthdate',
                            'gender': 'Gender', 'diet_category_id': 'Diet Category',
                            'diet_type_id': 'Diet Type',
                            'goals_details': 'Description'}
        optional_fields = ['phone']
        error, quotation_data = validate_mandatory_fields(mandatory_fields, kw)
        if error:
            values['error'] = error
            kw.update(values)
            return request.render('tk_gym_management.diet_request_form', kw)
        opt_data = validate_optional_fields(optional_fields, kw)
        quotation_data.update(opt_data)
        quotation_data['is_form_website'] = True
        quotation_data['type'] = 'lead'
        quotation_data['user_id'] = False
        lead_id = request.env['crm.lead'].sudo().create(quotation_data)
        ctx = {}
        if lead_id:
            return request.render('tk_gym_management.thank_you_page', ctx)
        return request.render('/', ctx)
