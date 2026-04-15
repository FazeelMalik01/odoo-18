from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VehicleJobcardInnerCondition(models.Model):
    _name = 'vehicle.jobcard.inner.condition'
    _description = 'Vehicle Inner Body Inspection Notebook'
    _rec_name = 'vehicle_item_id'

    vehicle_item_id = fields.Many2one('vehicle.items', string='Vehicle Item', tracking=True, domain=[('vehicle_category_id.name', '=', 'Interior')])
    state = fields.Selection(
        selection=[
            ('worn', 'Worn'),
            ('ripped', 'Ripped'),
            ('good', 'Good'),
            ('other', 'Other')
        ], string='Condition State', required=True)
    image = fields.Binary(string='Image', tracking=True)
    description = fields.Text(string="Note")
    jobcard_id=fields.Many2one('vehicle.jobcard', string='Inner Inspection Id')

class VehicleJobcardOuterCondition(models.Model):
    _name = 'vehicle.jobcard.outer.condition'
    _description = 'Vehicle Body Outer Condition'
    _rec_name = 'vehicle_outer_id'

    vehicle_outer_id = fields.Many2one('vehicle.condition', string='Vehicle Condition')
    vehicle_location_id=fields.Many2one('vehicle.location', string='Vehicle Location')
    short_code = fields.Char(related='vehicle_outer_id.short_code', string="Short Code")
    state = fields.Selection(
        selection=[
            ('left', 'Left Side View'),
            ('right', 'Right Side View'),
            ('top', 'Top View'),
            ('front', 'Front View'),
            ('back', 'Back View')
        ], string='Damage Area', required=True)
    image = fields.Binary(string='Image', tracking=True)
    description = fields.Text(string='Note')
    jobcard_id = fields.Many2one('vehicle.jobcard', string='Outer Inspection Id')


class VehicleJobcardMechanicalNotebook(models.Model):
    _name = 'vehicle.jobcard.mechanical.condition'
    _description = 'Vehicle Mechanical Condition'
    _rec_name = 'vehicle_item_id'

    vehicle_category_id = fields.Many2one('vehicle.item.category', string=' Item Category', required=True)
    vehicle_item_id = fields.Many2one(
        'vehicle.items',
        string='Vehicle Item',
        tracking=True,
        domain="[('vehicle_category_id', '=', vehicle_category_id)]"
    )
    state = fields.Selection(
        selection=[
            ('not_working', 'Not Working'),
            ('average', 'Average'),
            ('good', 'Good')
        ], string='Condition State', required=True)
    image = fields.Binary(string='Image', tracking=True)
    description = fields.Text(string="Note")
    jobcard_id = fields.Many2one('vehicle.jobcard', string='Mechanical Inspection Id')

class VehicleJobcardComponents(models.Model):
    _name = 'vehicle.jobcard.components'
    _description = 'Vehicle Components Inspection'
    _rec_name = 'vehicle_components_id'

    vehicle_components_id = fields.Many2one('vehicle.components', string='Vehicle Component')
    component_side = fields.Selection(related='vehicle_components_id.side', string='Vehicle Side')
    state = fields.Selection(
        selection=[
            ('future_attention', 'Require Future Attention'),
            ('immediate_attention', 'Require Immediate Attention'),
            ('checked_and_okay', 'Checked and Okey at this Time')
        ], string='Checking Status', required=True)
    image = fields.Binary(string='Image', tracking=True)
    condition_remark = fields.Text(string='Remarks')
    jobcard_id = fields.Many2one('vehicle.jobcard', string='Components Inspection Id')


class VehicleJobcardFluidsNotebook(models.Model):
    _name = 'vehicle.jobcard.fluids'
    _description = 'Vehicle Fluids'
    _rec_name = 'vehicle_fluids_id'

    vehicle_fluids_id = fields.Many2one('vehicle.fluids', string='Vehicle Fluids')
    component_side = fields.Selection(related='vehicle_fluids_id.component_side', string='Vehicle Fluids')
    state = fields.Selection(
        selection=[
            ('future_attention', 'Require Future Attention'),
            ('immediate_attention', 'Require Immediate Attention'),
            ('checked_and_okay', 'Checked and Okey at this Time')
        ], string='Inspection Status', required=True)
    image = fields.Binary(string='Image', tracking=True)
    condition_remark = fields.Text(string='Note')
    jobcard_id = fields.Many2one('vehicle.jobcard', string='Fluid Inspection Id')


class VehicleJobcardTyreCondition(models.Model):
    _name = 'vehicle.jobcard.tyre.condition'
    _description = 'Vehicle Tyre Condition'
    _rec_name = 'tyre_side'

    tyre_side = fields.Selection(selection=[
        ('front_right', 'Front Right'),
        ('front_left', 'Front Left'),
        ('back_right', 'Rear Right'),
        ('back_left', 'Rear Left')
    ], string='Tyre Location', required=True)
    state = fields.Selection(
        selection=[
            ('future_attention', 'Require Future Attention'),
            ('immediate_attention', 'Require Immediate Attention'),
            ('checked_and_okay', 'Checked and Okey at this Time')
        ], string='Present Condition', required=True)
    tread_wear=fields.Float(string="Tread Wear(mm)")
    tread_depth=fields.Float(string="Tread Depth(mm)")
    pressure=fields.Float(string="Tyre Pressure(psi)")
    brake_pads=fields.Float(string='Brake Pads(%)')
    description = fields.Text(string='Note')
    jobcard_id = fields.Many2one('vehicle.jobcard', string='Tyre Inspection Id')


class VechicleInspectionImage(models.Model):
    _name = 'vehicle.jobcard.inspection.image'
    _description = 'Vehicle Inspection Images'
    _rec_name = 'note'

    image = fields.Binary(string='Image', tracking=True)
    note = fields.Text(string="Description")
    jobcard_id = fields.Many2one('vehicle.jobcard', string='Image Inspection Id')
