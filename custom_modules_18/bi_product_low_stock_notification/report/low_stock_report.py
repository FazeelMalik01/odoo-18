from odoo import models, api


class LowStockTemplateReport(models.AbstractModel):
    _name = 'report.bi_product_low_stock_notification.low_stock_template'
    _description = "Low Stock Template"

    @api.model
    def _get_report_values(self, docids, data=None):

        lines = self.env.company.low_stock_products_ids

        # ── Category filter ────────────────────────────────────────────────────
        # If a category is selected in Settings, restrict lines to that category
        # (including all child categories). If none is selected, show everything.
        filter_category = self.env.company.report_category_id
        filtered_category_name = filter_category.complete_name if filter_category else None

        groups = {}
        order = []

        for line in lines:

            # ── Forecast / minimum quantity guard ─────────────────────────────
            # Only include lines where the forecast is below the minimum qty
            if line.orderpoint_qty_forecast >= line.orderpoint_min_qty:
                continue

            # ── Resolve the product category ──────────────────────────────────
            product = self.env['product.template'].search(
                [('name', '=', line.name)], limit=1
            )
            cat_obj  = product.categ_id if product and product.categ_id else None
            cat_name = cat_obj.complete_name if cat_obj else 'Uncategorized'

            # ── Apply category filter ──────────────────────────────────────────
            if filter_category:
                # Accept the product if its category or any ancestor matches
                # the selected category.
                if not cat_obj or not _is_child_of(cat_obj, filter_category):
                    continue

            # ── Group by category name ─────────────────────────────────────────
            if cat_name not in groups:
                groups[cat_name] = []
                order.append(cat_name)
            groups[cat_name].append(line)

        grouped_data = [
            {'category': cat, 'lines': groups[cat]}
            for cat in sorted(order)
            if groups[cat]          # skip categories that ended up empty
        ]

        return {
            'doc_ids'              : docids,
            'data'                 : data,
            'docs'                 : self.env.company.id,
            'rec_ids'              : lines,
            'grouped_data'         : grouped_data,
            'filtered_category'    : filtered_category_name,   # used in XML header
        }


# ── Helper ─────────────────────────────────────────────────────────────────────

def _is_child_of(category, parent):
    """
    Return True if *category* is equal to *parent* or is a descendant of it.
    Walks the parent chain without an extra SQL query.
    """
    current = category
    while current:
        if current.id == parent.id:
            return True
        current = current.parent_id
    return False