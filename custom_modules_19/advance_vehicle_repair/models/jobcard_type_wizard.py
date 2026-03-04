from odoo import models, fields, api, _

class JobcardBookingTypeWizard(models.TransientModel):
    _name = 'jobcard.booking.type.wizard'
    _description = 'Select Booking Type'

    booking_type = fields.Selection([
        ('vehicle_inspection', 'Vehicle Inspection'),
        ('vehicle_repair', 'Vehicle Repair'),
        ('both', 'Vehicle Inspection + Repair')
    ], string="Booking Type", required=True)

    def action_open_jobcard(self):
        self.ensure_one()

        ctx = {
            'default_booking_type': self.booking_type,
        }

        vehicle_id = self.env.context.get('default_vehicle_register_id')
        customer_id = self.env.context.get('default_customer_id')

        if vehicle_id:
            vehicle = self.env['vehicle.register'].browse(vehicle_id)

            if vehicle.exists():
                ctx.update({
                    'default_vehicle_source': 'register',
                    'default_vehicle_register_id': vehicle.id,
                    'default_customer_id': vehicle.customer_id.id,
                    'default_brand_id': vehicle.brand_id.id,
                    'default_model_id': vehicle.model_id.id,
                    'default_fuel_type_id': vehicle.fuel_type_id.id,
                    'default_registration_no': vehicle.registration_no,
                    'default_vin_no': vehicle.vin_no,
                    'default_transmission_type': vehicle.transmission_type,
                })

        elif customer_id:
            ctx.update({
                'default_customer_id': customer_id,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'New Job Card',
            'res_model': 'vehicle.jobcard',
            'view_mode': 'form',
            'target': 'current',
            'context': ctx,
        }

