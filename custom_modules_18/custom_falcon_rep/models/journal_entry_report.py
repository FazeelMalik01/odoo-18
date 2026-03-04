# -*- coding: utf-8 -*-

from odoo import models, api


class ReportJournalEntry(models.AbstractModel):
    _name = 'report.custom_falcon_rep.journal_entry_report_template'
    _description = 'Journal Entry Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'env': self.env,
        }
