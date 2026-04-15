from odoo import fields, models

class AutoServiceBundle(models.Model):
    _name = 'auto.service.bundle'
    _description = "Auto Service Bundle"

    name = fields.Char(string="Bundle Name", required=True)

    # Separate One2many for services and spares
    service_line_ids = fields.One2many(
        'auto.service.bundle.service.line',
        'bundle_id',
        string="Service Lines"
    )
    spare_line_ids = fields.One2many(
        'auto.service.bundle.spare.line',
        'bundle_id',
        string="Spare Lines"
    )


class AutoServiceBundleServiceLine(models.Model):
    _name = 'auto.service.bundle.service.line'
    _description = "Auto Service Bundle Service Line"

    bundle_id = fields.Many2one(
        'auto.service.bundle',
        string="Bundle",
        ondelete="cascade"
    )

    service_id = fields.Many2one(
        'vehicle.services',
        string="Service",
        required=True
    )


class AutoServiceBundleSpareLine(models.Model):
    _name = 'auto.service.bundle.spare.line'
    _description = "Auto Service Bundle Spare Line"

    bundle_id = fields.Many2one(
        'auto.service.bundle',
        string="Bundle",
        ondelete="cascade"
    )

    spare_id = fields.Many2one(
        'product.product',
        string="Spare Part",
        domain=[('spare_part','=',True)],
        required=True
    )

    quantity = fields.Float(
        string="Quantity",
        default=1
    )


class VehicleJobcardBundleLine(models.Model):
    _name = 'vehicle.jobcard.bundle.line'
    _description = "Vehicle Jobcard Bundle Line"

    jobcard_id = fields.Many2one(
        'vehicle.jobcard',
        string="Job Card",
        ondelete="cascade"
    )
    bundle_id = fields.Many2one(
        'auto.service.bundle',
        string="Bundle",
        required=True
    )
    # Optional: pull through for display
    service_line_ids = fields.One2many(
        related='bundle_id.service_line_ids',
        string="Services"
    )
    spare_line_ids = fields.One2many(
        related='bundle_id.spare_line_ids',
        string="Spares"
    )