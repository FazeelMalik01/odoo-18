from odoo import models, fields, api
from odoo.exceptions import ValidationError

class VehicleBookingRequest(models.Model):
    _name = 'vehicle.booking.request'
    _rec_name = 'registration_no' 
    _description = 'Vehicle Booking Request'
    _order = "id desc"

    customer_name = fields.Char(string="Customer Name", required=True)
    customer_email = fields.Char(string="Customer Email", required=True)
    customer_mobile = fields.Char(string="Customer Mobile", required=True)
    brand_id = fields.Many2one('vehicle.brand', string="Vehicle Brand", required=True)
    model_id = fields.Many2one('vehicle.model', string="Vehicle Model", required=True, domain="[('brand_id', '=', brand_id)]")
    fuel_type_id = fields.Many2one('vehicle.fuel.type', string="Fuel Type", required=True)
    transmission_type = fields.Selection([
        ('manual', "Manual"),
        ('automatic', "Automatic"),
        ('cvt', "CVT")
        ], string='Transmission Type', default='manual', tracking=True)
    registration_no = fields.Char(string="Registration Number", required=True)
    vin_no = fields.Char(string="VIN Number", required=True)
    request_date = fields.Datetime(string="Request Date", default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('create', 'Booking Created'),
        ('cancel', 'Cancelled')
        ], string="State", default="draft")
    booking_date = fields.Date(string="Booking Date", required=True, tracking=True)
    customer_id = fields.Many2one('res.partner', string="Customer", required=False, tracking=True, )
    vehicle_register_id = fields.Many2one('vehicle.register', string="Vehicle", required=False, tracking=True, domain="[('state', '=', 'active')]")
    booking_id = fields.Many2one('vehicle.booking', string="Booking ID")
    responsible_id = fields.Many2one('res.users', string='Responsible', tracking=True)


    def action_find_and_update_customer(self):
        customer = self.env['res.partner'].search([('phone', 'ilike', self.customer_mobile)], limit=1)

        if not customer:
            customer = self.env['res.partner'].search([('email', 'ilike', self.customer_email)], limit=1)

        if not customer:
            customer = self.env['res.partner'].search([('name', 'ilike', self.customer_name)], limit=1)

        if customer:
            self.customer_id = customer.id
        else:
            customer = self.env['res.partner'].create({
                'name': self.customer_name,
                'email': self.customer_email,
                # 'mobile': self.customer_mobile,
                'phone': self.customer_mobile,
            })
            self.customer_id = customer.id
    
    def action_find_and_update_vehicle(self):
        if not self.customer_id:
            raise ValidationError("Customer ID is not set. Please ensure the customer exists or is correctly identified.")
        
        vehicle = self.env['vehicle.register'].search(['|',('registration_no', 'ilike', self.registration_no),('vin_no', 'ilike', self.vin_no)], limit=1)

        if vehicle:
            self.vehicle_register_id = vehicle.id
        else:
            vehicle = self.env['vehicle.register'].create({
                'registration_no' : self.registration_no,
                'vin_no': self.vin_no,
                'customer_id': self.customer_id.id,
                'brand_id': self.brand_id.id,
                'model_id' : self.model_id.id,
                'fuel_type_id' : self.fuel_type_id.id,
                'transmission_type' : self.transmission_type,
                'state' : 'active',
            })
            self.vehicle_register_id = vehicle.id
    
    def action_create_booking(self):
        if not self.customer_id:
            raise ValidationError("Customer ID is not set. Please ensure the customer exists or is correctly identified.")
        if not self.vehicle_register_id:
            raise ValidationError("Vehicle ID is not set. Please ensure the vehicle exists or is correctly identified.")
        
        VehicleBooking = self.env['vehicle.booking'].sudo()
        if self.vehicle_register_id:
            booking = VehicleBooking.create({
                'vehicle_register_id' : self.vehicle_register_id.id,
                'registration_no': self.registration_no,
                'brand_id': self.brand_id.id,
                'model_id': self.model_id.id,
                'vin_no': self.vin_no,
                'fuel_type_id': self.fuel_type_id.id,
                'transmission_type': self.transmission_type,
                'booking_type' : 'vehicle_inspection',
                'booking_date' : self.booking_date,
                'booking_source': 'website',
                'customer_id': self.customer_id.id,
                'responsible_id': self.responsible_id.id,
            })
            self.sudo().write({
                'booking_id' : booking.id,
                'state' : 'create'
            })
        return True
    
    def action_cancel_button(self):
        self.write({
            'state' : 'cancel'
        })
