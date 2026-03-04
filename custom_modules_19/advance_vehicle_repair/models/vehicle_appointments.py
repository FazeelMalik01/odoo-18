from odoo import models, fields, api

class VehicleAppointments(models.Model):
    _name = 'vehicle.appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vehicle Appointment'

    name = fields.Char(string="Appointment Day", required=True, tracking=True)
    appointment_line_ids = fields.One2many('vehicle.appointment.line', 'appointment_id', string="appointment line ids", tracking=True)


class VehicleAppointmentsLine(models.Model):
    _name = 'vehicle.appointment.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vehicle Appointment Line'
    _rec_name = 'time_slot'

    time_slot = fields.Char(string="Slots", required=True, tracking=True)
    time_starting = fields.Float(string="Starting Time")
    time_closing = fields.Float(string="Closing Time")
    appointment_id = fields.Many2one('vehicle.appointment', string="Appointment Id", tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'time_slot' in vals:
                vals['time_slot'] = vals['time_slot'].title()
        return super(VehicleAppointmentsLine, self).create(vals_list)

    def write(self, vals):
        if 'time_slot' in vals:
            vals['time_slot'] = vals['time_slot'].title()
        return super(VehicleAppointmentsLine, self).write(vals)
