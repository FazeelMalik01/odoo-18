from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class PosSessionInherit(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        """Extend Sale Details Report to include Employee Sales, Pricelist, Refund,
        and Cash In/Out (from both Payments & Manual Cash Movements)."""
        res = super().get_sale_details(date_start, date_stop, config_ids, session_ids, **kwargs)

        orders = self.env['pos.order'].search(
            self._get_domain(date_start, date_stop, config_ids, session_ids, **kwargs)
        )

        employee_orders = {}
        pricelist_summary = {}
        refund_summary = {}
        cash_summary = {}
        currency_symbol = self.env.company.currency_id.symbol or ''

        # ---------------- EMPLOYEE SALES ----------------
        for order in orders:
            emp_name = order.employee_id.name or 'No Employee'
            employee_orders.setdefault(emp_name, []).append({
                'order_name': order.name,
                'receipt_number': order.pos_reference,
                'total': order.amount_total,
                'state': order.state,
            })

            # Pricelist Summary
            pricelist_name = order.pricelist_id.name or 'No Pricelist'
            pricelist_summary.setdefault(pricelist_name, {'count': 0, 'total': 0.0})
            pricelist_summary[pricelist_name]['count'] += 1
            pricelist_summary[pricelist_name]['total'] += order.amount_total

            # Refund Summary
            is_refund = order.amount_total < 0 or any(line.qty < 0 for line in order.lines)
            if is_refund:
                refund_user = (
                    order.employee_id.name
                    or (order.create_uid and order.create_uid.name)
                    or (order.user_id and order.user_id.name)
                    or 'Unknown User'
                )
                refund_summary.setdefault(refund_user, {'count': 0, 'total': 0.0, 'orders': []})
                refund_summary[refund_user]['count'] += 1
                refund_summary[refund_user]['total'] += float(order.amount_total or 0.0)
                refund_summary[refund_user]['orders'].append({
                    'order_name': order.name,
                    'total': float(order.amount_total or 0.0),
                })

        # ---------------- CASH IN / OUT SUMMARY ----------------
        session_domain = []
        if session_ids:
            session_domain.append(('id', 'in', session_ids))
        if date_start:
            session_domain.append(('start_at', '>=', date_start))
        if date_stop:
            session_domain.append(('stop_at', '<=', date_stop))

        sessions = self.env['pos.session'].search(session_domain)

        for session in sessions:
            # 💵 1. Include Cash Payments from Orders
            for order in session.order_ids:
                emp_name = order.employee_id.name or order.user_id.name or 'Unknown Employee'
                cash_summary.setdefault(emp_name, {'cash_in': 0.0, 'cash_out': 0.0, 'lines': []})

                for payment in order.payment_ids:
                    if payment.payment_method_id.type != 'cash':
                        continue

                    amount = payment.amount
                    if amount > 0:
                        cash_summary[emp_name]['cash_in'] += amount
                        cash_summary[emp_name]['lines'].append({
                            'type': 'IN',
                            'reason': f"Order {order.name}",
                            'amount': amount,
                        })
                    else:
                        cash_summary[emp_name]['cash_out'] += abs(amount)
                        cash_summary[emp_name]['lines'].append({
                            'type': 'OUT',
                            'reason': f"Order {order.name}",
                            'amount': abs(amount),
                        })

            # 💵 2. Include Manual Cash In/Out from Bank Statements
            for statement_line in session.statement_line_ids:
                if not statement_line.amount:
                    continue

                # Try to get the employee name from related chatter if possible
                emp_name = (
                    statement_line.create_uid.name
                    or session.user_id.name
                    or 'Unknown Employee'
                )

                cash_summary.setdefault(emp_name, {'cash_in': 0.0, 'cash_out': 0.0, 'lines': []})

                if statement_line.amount > 0:
                    cash_summary[emp_name]['cash_in'] += statement_line.amount
                    cash_summary[emp_name]['lines'].append({
                        'type': 'IN',
                        'reason': statement_line.name or 'Cash In (Manual)',
                        'amount': statement_line.amount,
                    })
                else:
                    cash_summary[emp_name]['cash_out'] += abs(statement_line.amount)
                    cash_summary[emp_name]['lines'].append({
                        'type': 'OUT',
                        'reason': statement_line.name or 'Cash Out (Manual)',
                        'amount': abs(statement_line.amount),
                    })

        # ---------------- FORMAT OUTPUT LISTS ----------------
        employee_orders_list = [
            {
                'employee': name,
                'orders': data,
                'total': round(sum(o['total'] for o in data), 2),
                'count': len(data),
            }
            for name, data in employee_orders.items()
        ]

        pricelist_summary_list = [
            {'name': name, 'count': d['count'], 'total': round(d['total'], 2)}
            for name, d in pricelist_summary.items()
        ]

        refund_summary_list = [
            {'user': name, 'count': d['count'], 'total': round(d['total'], 2), 'orders': d['orders']}
            for name, d in refund_summary.items()
        ]

        cash_summary_list = [
            {
                'user': emp,
                'cash_in': round(v['cash_in'], 2),
                'cash_out': round(v['cash_out'], 2),
                'net': round(v['cash_in'] - v['cash_out'], 2),
                'lines': v['lines'],
            }
            for emp, v in cash_summary.items()
        ]

        # ---------------- FINAL RESPONSE ----------------
        res.update({
            'employee_orders_list': employee_orders_list,
            'pricelist_summary_list': pricelist_summary_list,
            'refund_summary_list': refund_summary_list,
            'cash_summary_list': cash_summary_list,
            'currency_symbol': currency_symbol,
        })

        _logger.info("✅ Sale Details Extended — Including Payments + Manual Cash In/Out.")
        return res
