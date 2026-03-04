# -*- coding: utf-8 -*-
from odoo import models, fields, api


class QualityCheck(models.Model):
    _inherit = 'quality.check'

    image_ids = fields.One2many(
        'quality.check.image',
        'quality_check_id',
        string='Images',
        copy=True
    )
    # Keep picture field for backward compatibility but make it computed
    picture = fields.Binary('Picture', attachment=True, compute='_compute_picture', store=False, inverse='_inverse_picture')
    
    # Add 'submitted' stage after 'none' (To do)
    # Note: selection_add adds at the end, but statusbar displays in definition order
    # We'll override the entire selection to maintain order: none, submitted, pass, fail
    quality_state = fields.Selection(
        selection=[
            ('none', 'To do'),
            ('submitted', 'Submitted'),
            ('pass', 'Passed'),
            ('fail', 'Failed')
        ],
        string='Status',
        tracking=True,
        default='none',
        copy=False
    )
    
    def do_submit(self):
        """Set quality check to submitted state"""
        from datetime import datetime
        self.write({
            'quality_state': 'submitted',
            'user_id': self.env.user.id,
            'control_date': datetime.now()
        })

    @api.depends('image_ids', 'image_ids.image')
    def _compute_picture(self):
        """Keep first image for backward compatibility with existing code"""
        for check in self:
            if check.image_ids:
                check.picture = check.image_ids[0].image
            else:
                check.picture = False

    def _inverse_picture(self):
        """When picture is set, create/update first image for backward compatibility"""
        for check in self:
            if check.picture:
                if check.image_ids:
                    check.image_ids[0].image = check.picture
                else:
                    self.env['quality.check.image'].create({
                        'name': check.name or 'Image',
                        'image': check.picture,
                        'quality_check_id': check.id,
                        'sequence': 10,
                    })


class QualityPoint(models.Model):
    _inherit = 'quality.point'

    service = fields.Boolean(string='Service', default=False)
    custom_worksheet_id = fields.Many2one(
        'custom.worksheet',
        string='Custom Worksheet',
        help='Select a custom worksheet',
        domain="[('active', '=', True)]",
        check_company=True
    )
    picking_type_ids = fields.Many2many(
        'stock.picking.type', string='Operation Types', required=False, check_company=True)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    custom_worksheet_id = fields.Many2one(
        'custom.worksheet',
        string='Custom Worksheet',
        help='Select a custom worksheet for this task',
        domain="[('active', '=', True)]"
    )

    def action_view_custom_worksheet(self):
        self.ensure_one()
        if self.custom_worksheet_id:
            return {
                'name': 'Custom Worksheet',
                'type': 'ir.actions.act_window',
                'res_model': 'custom.worksheet',
                'res_id': self.custom_worksheet_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'name': 'Custom Worksheets',
                'type': 'ir.actions.act_window',
                'res_model': 'custom.worksheet',
                'view_mode': 'list,form',
                'target': 'current',
                'context': {'default_company_id': self.company_id.id if self.company_id else False},
            }
