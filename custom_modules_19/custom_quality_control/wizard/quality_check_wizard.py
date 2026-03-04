# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QualityCheckWizard(models.TransientModel):
    _inherit = 'quality.check.wizard'

    image_ids = fields.One2many(
        related='current_check_id.image_ids',
        readonly=False,
        string='Images'
    )

    def do_pass(self):
        # Override to check for at least one image when test_type is 'picture'
        if self.test_type == 'picture' and not self.image_ids:
            raise UserError(_('You must provide at least one image before validating'))
        return super().do_pass()

    def do_submit(self):
        """Submit the quality check and move to next window"""
        self.current_check_id.do_submit()
        return self.action_generate_next_window()
