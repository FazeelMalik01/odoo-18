from odoo import models, fields

class VehicleServiceReminder(models.Model):
    _name = "vehicle.service.reminder"
    _description = "Vehicle Service Reminder"
    _order = "id desc"

    customer_id = fields.Many2one('res.partner', string="Customer", required=True)
    jobcard_id = fields.Many2one('vehicle.jobcard', string="Jobcard")
    service_id = fields.Many2one('vehicle.services', string="Service", required=True)

    done_date = fields.Date(string="Service Done On", required=True)
    next_due_date = fields.Date(string="Next Due Date", required=True)

    recurring_days = fields.Integer(string="Recurring Days")

    vehicle_id = fields.Many2one('vehicle.register', string="Vehicle")  # optional if you have

    note = fields.Char(string="Notes")