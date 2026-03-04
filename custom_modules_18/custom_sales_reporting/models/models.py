# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SaleReport(models.Model):
    _inherit = 'sale.report'

    standard_price = fields.Float(
        string="Cost Price",
        readonly=True,
        aggregator='avg',
        help="Product standard cost price (unit cost)"
    )

    def _select_additional_fields(self):
        """Add standard_price (Cost Price) field to the SQL query for sale orders"""
        _logger.info("=== SALE REPORT: _select_additional_fields called ===")
        res = super()._select_additional_fields()
        _logger.info(f"SALE REPORT: Base additional fields: {list(res.keys())}")
        
        # Handle cost price for sale orders
        # Following the exact same pattern as price_unit (line 109-113 in sale_report.py)
        # Get standard_price from product table, then apply currency conversion
        # Use AVG to match price_unit aggregator='avg' behavior
        standard_price_sql = f"""CASE 
            WHEN l.product_id IS NOT NULL THEN 
                AVG(
                    COALESCE(
                        (p.standard_price -> COALESCE(s.company_id, 1)::text)::float,
                        (p.standard_price -> '1'::text)::float,
                        0.0
                    )
                    / {self._case_value_or_one('s.currency_rate')}
                    * {self._case_value_or_one('account_currency_table.rate')}
                )
            ELSE 0 
        END"""
        
        res['standard_price'] = standard_price_sql
        _logger.info(f"SALE REPORT: Added standard_price SQL for sale orders")
        _logger.debug(f"SALE REPORT: standard_price SQL: {standard_price_sql}")
        _logger.info(f"SALE REPORT: Final additional fields: {list(res.keys())}")
        return res
    
    def _available_additional_pos_fields(self):
        """Provide POS-specific SQL for standard_price field"""
        _logger.info("=== POS REPORT: _available_additional_pos_fields called ===")
        # For POS orders, use l.total_cost (cost price stored in pos.order.line)
        # Following the same pattern as price_unit in _select_pos()
        res = super()._available_additional_pos_fields()
        _logger.info(f"POS REPORT: Base POS fields from parent: {list(res.keys())}")
        
        standard_price_sql = f"""CASE 
            WHEN l.product_id IS NOT NULL THEN 
                AVG(
                    COALESCE(l.total_cost, 0.0)
                )
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('account_currency_table.rate')}
            ELSE 0 
        END"""
        
        res['standard_price'] = standard_price_sql
        _logger.info(f"POS REPORT: Added standard_price SQL for POS orders using l.total_cost")
        _logger.debug(f"POS REPORT: standard_price SQL: {standard_price_sql}")
        _logger.info(f"POS REPORT: Final POS fields: {list(res.keys())}")
        return res
    
    def _fill_pos_fields(self, additional_fields):
        """Override to log and ensure standard_price is handled for POS"""
        _logger.info(f"=== POS REPORT: _fill_pos_fields called with fields: {list(additional_fields.keys())}")
        filled_fields = super()._fill_pos_fields(additional_fields)
        _logger.info(f"POS REPORT: Filled POS fields result: {list(filled_fields.keys())}")
        _logger.info(f"POS REPORT: standard_price in filled_fields: {'standard_price' in filled_fields}")
        if 'standard_price' in filled_fields:
            _logger.info(f"POS REPORT: standard_price value: {filled_fields['standard_price'][:100] if len(str(filled_fields['standard_price'])) > 100 else filled_fields['standard_price']}")
        return filled_fields
    
    def _select_pos(self):
        """Override to log POS query generation"""
        _logger.info("=== POS REPORT: _select_pos called ===")
        select_pos = super()._select_pos()
        _logger.info(f"POS REPORT: _select_pos generated SQL (length: {len(select_pos)} chars)")
        if 'standard_price' in select_pos.lower():
            _logger.info("POS REPORT: standard_price found in _select_pos SQL")
        else:
            _logger.warning("POS REPORT: standard_price NOT found in _select_pos SQL!")
        return select_pos
    
    def _query(self):
        """Override to log the generated SQL query"""
        query = super()._query()
        _logger.info("=== SALE REPORT: _query called ===")
        _logger.debug(f"SALE REPORT: Generated SQL query length: {len(query)} characters")
        # Check if UNION is present (indicates POS orders are included)
        if 'UNION ALL' in query.upper():
            _logger.info("SALE REPORT: UNION ALL found - POS orders should be included")
        else:
            _logger.warning("SALE REPORT: UNION ALL NOT found - POS orders may not be included!")
        # Log a portion of the query to see if standard_price is included
        if 'standard_price' in query.lower():
            _logger.info("SALE REPORT: standard_price found in SQL query")
            # Count occurrences
            count = query.lower().count('standard_price')
            _logger.info(f"SALE REPORT: standard_price appears {count} times in query")
            # Find and log the standard_price part
            import re
            matches = re.finditer(r'standard_price.*?END', query, re.IGNORECASE | re.DOTALL)
            for i, match in enumerate(matches):
                _logger.debug(f"SALE REPORT: standard_price SQL snippet #{i+1}: {match.group()[:200]}...")
        else:
            _logger.warning("SALE REPORT: standard_price NOT found in SQL query!")
        return query


    

