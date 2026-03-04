from odoo import models, fields, api
import base64
import os
import re


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _get_report_values(self, docids, data=None):
        """Override to check state before generating report"""
        res = super()._get_report_values(docids, data)

        # Check if this is a sale.order report
        if self.model == 'sale.order' and docids:
            sale_order = self.env['sale.order'].browse(docids[0])
            if sale_order.exists():
                # Tax Quotation: available for draft and sale
                if self.report_name == 'custom_reports.tax_quotation_report' and sale_order.state not in ('draft', 'sale'):
                    raise ValueError("Tax Quotation is only available for draft or Confirmed Sale Orders.")
                # Proforma Invoice: available for draft and sale
                elif self.report_name == 'custom_reports.proforma_invoice_report' and sale_order.state not in ('draft', 'sale'):
                    raise ValueError("Proforma Invoice is only available for draft or Confirmed Sale Orders.")

        return res

    # REMOVE THIS METHOD - it's causing the error
    # def _get_readable_fields(self):
    #     """Override to filter reports based on domain"""
    #     res = super()._get_readable_fields()
    #     res.append('domain')
    #     return res


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    subject = fields.Char(string='Subject')
    att = fields.Char(string='Att')
    location = fields.Char(string='Location')
    customer_trn = fields.Char(string="Customer's TRN")
    # Automatically reflects the last time the quotation was updated
    date_revised = fields.Date(
        string='Date Revised',
        compute='_compute_date_revised',
        store=True,
        readonly=True,
    )
    site = fields.Char(string='Site')
    payment_method = fields.Char(string='Payment Method')
    payment_type = fields.Selection([('half', 'HALF'), ('full', 'FULL')], string='Payment Type', default='full')
    cheque_no = fields.Char(string='Cheque No.')
    bank_name = fields.Char(string='Bank Name')

    def get_date_created_formatted(self):
        """Format date_order as YYYYMMDD"""
        if self.date_order:
            if isinstance(self.date_order, str):
                return self.date_order.replace('-', '').replace(' ', '').replace(':', '')[:8]
            return self.date_order.strftime('%Y%m%d')
        return ''

    def get_date_created_formatted_proforma(self):
        """Format date_order as M/D/YYYY for Proforma Invoice"""
        if self.date_order:
            if isinstance(self.date_order, str):
                try:
                    from datetime import datetime
                    dt = datetime.strptime(self.date_order[:10], '%Y-%m-%d')
                    # Use # to remove leading zeros on Windows, or use manual formatting
                    day = dt.day
                    month = dt.month
                    year = dt.year
                    return f"{month}/{day}/{year}"
                except:
                    return self.date_order[:10]
            # Manual formatting to avoid platform-specific strftime issues
            day = self.date_order.day
            month = self.date_order.month
            year = self.date_order.year
            return f"{month}/{day}/{year}"
        return ''

    def get_date_revised_formatted(self):
        """Format date_revised (auto from last modification date) as readable date."""
        if self.date_revised:
            # date_revised is a date, safe to format directly
            return self.date_revised.strftime('%Y-%m-%d')
        return ''

    @api.depends('write_date', 'date_order')
    def _compute_date_revised(self):
        """Keep date_revised in sync with the last update date of the quotation.

        - On first creation, fall back to the order date.
        - On subsequent edits, use write_date (date component only).
        """
        for order in self:
            if order.write_date:
                # write_date is a datetime; use date component
                order.date_revised = order.write_date.date()
            elif order.date_order:
                # Fallback for records without write_date yet
                order.date_revised = order.date_order.date()
            else:
                order.date_revised = False

    def _get_amount_in_words(self, amount):
        """Convert amount to words"""

        def number_to_words(num):
            ones = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN',
                    'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN', 'SEVENTEEN',
                    'EIGHTEEN', 'NINETEEN']
            tens = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY']

            if num == 0:
                return 'ZERO'
            if num < 20:
                return ones[num]
            if num < 100:
                return tens[num // 10] + (' ' + ones[num % 10] if num % 10 else '')
            if num < 1000:
                return ones[num // 100] + ' HUNDRED' + (' ' + number_to_words(num % 100) if num % 100 else '')
            if num < 1000000:
                return number_to_words(num // 1000) + ' THOUSAND' + (
                    ' ' + number_to_words(num % 1000) if num % 1000 else '')
            if num < 1000000000:
                return number_to_words(num // 1000000) + ' MILLION' + (
                    ' ' + number_to_words(num % 1000000) if num % 1000000 else '')
            return number_to_words(num // 1000000000) + ' BILLION' + (
                ' ' + number_to_words(num % 1000000000) if num % 1000000000 else '')

        # Split amount into integer and decimal parts
        integer_part = int(amount)
        decimal_part = int(round((amount - integer_part) * 100))

        words = number_to_words(integer_part)
        if decimal_part > 0:
            words += ' AND ' + number_to_words(decimal_part) + ' FILS'

        return words + ' DIRHAMS ONLY/-'

    def get_hmd_logo(self):
        """Get HMD logo as base64"""
        try:
            module_path = os.path.dirname(os.path.dirname(__file__))
            for ext in ['png', 'PNG']:
                logo_path = os.path.join(module_path, 'static', 'src', 'img', f'hmd.{ext}')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            pass
        return ''

    def get_qr_logo(self):
        """Get QR code image as base64 for Proforma Invoice"""
        try:
            module_path = os.path.dirname(os.path.dirname(__file__))
            for ext in ['png', 'PNG']:
                qr_path = os.path.join(module_path, 'static', 'src', 'img', f'qr.{ext}')
                if os.path.exists(qr_path):
                    with open(qr_path, 'rb') as f:
                        return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            pass
        return ''

    def get_instagram_logo(self):
        """Get Instagram icon as base64 for Proforma Invoice footer (URL path fails with html_container)"""
        try:
            module_path = os.path.dirname(os.path.dirname(__file__))
            for ext in ['png', 'PNG']:
                img_path = os.path.join(module_path, 'static', 'src', 'img', f'instagram.{ext}')
                if os.path.exists(img_path):
                    with open(img_path, 'rb') as f:
                        return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            pass
        return ''

    def get_hmd1_logo(self):
        """Get HMD1 logo (hmd1.png) as base64 for Tax Quotation"""
        try:
            module_path = os.path.dirname(os.path.dirname(__file__))
            for ext in ['png', 'PNG']:
                logo_path = os.path.join(module_path, 'static', 'src', 'img', f'hmd1.{ext}')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            pass
        return ''

    def get_order_lines_with_sr(self):
        """
        Return order lines with hierarchical serial numbers for Tax Quotation report.
        - Section rows get 1, 2, 3, ...
        - Products under a section get 1.1, 1.2, 2.1, 2.2, ...
        - Standalone product (no section before it) gets 1; next section gets 2, etc.
        """
        section_no = 0
        item_index = 0
        after_section = False
        result = []
        # Respect the on-screen order (sequence, then id) so the report
        # matches the ordering the user sees in the sale order.
        for line in self.order_line.sorted(key=lambda l: (l.sequence, l.id)):
            if line.display_type == 'line_section':
                section_no += 1
                item_index = 0
                after_section = True
                # Odoo already computes the subtotal for section lines (price_subtotal),
                # so we reuse it to stay in sync with the UI.
                result.append({
                    'line': line,
                    'sr': str(section_no),
                    'is_section': True,
                    'subtotal': float(line.price_subtotal or 0.0),
                })
            elif line.display_type not in ('line_section', 'line_note'):
                if after_section:
                    item_index += 1
                    result.append({'line': line, 'sr': f'{section_no}.{item_index}', 'is_section': False})
                else:
                    section_no += 1
                    result.append({'line': line, 'sr': str(section_no), 'is_section': False})
                    after_section = False
        return result

    def get_line_product_image_src(self, order_line=None, product_id=None):
        """Return data URL for product image for report. Accepts order_line (record) or product_id (int)."""
        if product_id:
            product = self.env['product.product'].sudo().browse(product_id)
        elif order_line and order_line.product_id:
            product = order_line.product_id.sudo()
        else:
            return ''
        if not product.exists():
            return ''
        product = product.with_context(bin_size=False)
        tmpl = product.product_tmpl_id.with_context(bin_size=False)

        # 1) ir.attachment + filestore first (custom uploads are here; default is often in ORM cache)
        for res_model, res_id in (('product.template', tmpl.id), ('product.product', product.id)):
            for res_field in ('image_1920', 'image_1024', 'image_512'):
                if res_model == 'product.template' and 'variant' in res_field:
                    continue
                att = self.env['ir.attachment'].sudo().search([
                    ('res_model', '=', res_model), ('res_id', '=', res_id), ('res_field', '=', res_field),
                ], limit=1)
                if not att:
                    continue
                att = att.with_context(bin_size=False)
                raw = self._get_attachment_raw(att)
                if raw and len(raw) >= 50:
                    return 'data:image/png;base64,' + base64.b64encode(raw).decode('ascii')
                data = getattr(att, 'datas', None)
                out = self._image_to_base64_string(data)
                if out and len(out) >= 50:
                    return 'data:image/png;base64,' + out

        # 2) ORM fields (default / cached)
        for field in ('image_1920', 'image_1024', 'image_512', 'image_256', 'image_128'):
            val = getattr(tmpl, field, None)
            out = self._image_to_base64_string(val)
            if out and len(out) >= 20:
                return 'data:image/png;base64,' + out
        for field in ('image_variant_1920', 'image_variant_512', 'image_variant_256', 'image_variant_128'):
            val = getattr(product, field, None)
            out = self._image_to_base64_string(val)
            if out and len(out) >= 20:
                return 'data:image/png;base64,' + out
        return ''

    def _get_attachment_raw(self, att):
        """Get raw bytes for an attachment (filestore or db_datas)."""
        if not att:
            return None
        if att.store_fname:
            raw = self._read_attachment_filestore(att.store_fname)
            if raw:
                return raw
        try:
            raw = att.raw
            if raw and isinstance(raw, bytes):
                return raw
            if raw and isinstance(raw, str):
                return base64.b64decode(raw)
        except Exception:
            pass
        return None

    def _read_attachment_filestore(self, store_fname):
        """Read attachment content from filestore. Returns bytes or None."""
        if not store_fname:
            return None
        # Sanitize like Odoo (ir_attachment._full_path)
        path = re.sub(r'[.:]', '', store_fname)
        path = path.strip('/\\')
        if not path:
            return None
        # Normalize to OS path (Odoo stores with '/' in DB; Windows needs backslash for join)
        path_os = path.replace('/', os.sep)
        candidates = []
        dbname = self.env.cr.dbname
        # Optional: force filestore root (Settings > Technical > Parameters: custom_reports.filestore_root)
        try:
            custom_root = self.env['ir.config_parameter'].sudo().get_param('custom_reports.filestore_root', '').strip()
            if custom_root:
                candidates.append(os.path.join(custom_root, dbname, path_os))
        except Exception:
            pass
        try:
            Attachment = self.env['ir.attachment'].sudo()
            candidates.append(Attachment._full_path(store_fname))
        except (TypeError, AttributeError):
            pass
        try:
            from odoo.tools import config
            root = config.filestore(dbname)
            if root:
                candidates.append(os.path.join(root, path_os))
        except Exception:
            pass
        # Windows: common Odoo filestore when config.data_dir differs (e.g. report context)
        try:
            for base in (
                os.path.join(os.environ.get('APPDATA', ''), '..', 'Local', 'OpenERP S.A.', 'Odoo', 'filestore', dbname),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'OpenERP S.A.', 'Odoo', 'filestore', dbname),
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'OpenERP S.A.', 'Odoo', 'filestore', dbname),
            ):
                if base:
                    base = os.path.normpath(base)
                    candidates.append(os.path.join(base, path_os))
        except Exception:
            pass
        for full_path in candidates:
            try:
                if full_path and os.path.isfile(full_path):
                    with open(full_path, 'rb') as f:
                        return f.read()
            except OSError:
                continue
        return None

    def _image_to_base64_string(self, img):
        """Convert image field value (bytes or base64 str) to clean base64 string, or None."""
        if not img:
            return None
        if isinstance(img, bytes):
            # May be raw binary or already base64-encoded bytes (e.g. from ir.attachment .datas)
            try:
                return img.decode('ascii')
            except UnicodeDecodeError:
                return base64.b64encode(img).decode('ascii')
        if isinstance(img, str):
            raw = img.replace('\n', '').replace('\r', '').strip()
            if raw.startswith('data:'):
                # Already a data URL; extract base64 part if needed for consistency
                if ';base64,' in raw:
                    raw = raw.split(';base64,', 1)[-1]
                else:
                    return None
            if len(raw) >= 10:
                return raw
        return None

    def debug_product_image_fields(self, product_id=None):
        """Verify which DB/attachment image fields have data. Call from shell or server action.
        Optional product_id: id of product.product to check; if None, uses first product from order lines.
        Returns dict with field names and whether they have data (and type/length)."""
        product = None
        if product_id:
            product = self.env['product.product'].sudo().browse(product_id)
        if not product or not product.exists():
            for line in self.order_line:
                if line.product_id:
                    product = line.product_id.sudo()
                    break
        if not product or not product.exists():
            return {'error': 'No product found'}
        tmpl = product.product_tmpl_id
        result = {'product_id': product.id, 'product_name': product.name, 'template_id': tmpl.id}
        ctx = {'bin_size': False}
        for name in ('image_variant_1920', 'image_variant_512', 'image_1920', 'image_512'):
            rec = product if 'variant' in name else tmpl
            val = rec.with_context(**ctx).read([name])[0].get(name)
            typ = type(val).__name__
            length = len(val) if val else 0
            result[name] = {'has_data': bool(val and length > 10), 'type': typ, 'length': length}
        # Attachments that store product/template images
        atts = self.env['ir.attachment'].sudo().search([
            ('res_model', 'in', ('product.product', 'product.template')),
            ('res_id', 'in', [product.id, tmpl.id]),
            ('res_field', 'ilike', 'image%'),
        ])
        result['attachments'] = [{'res_model': a.res_model, 'res_id': a.res_id, 'res_field': a.res_field, 'datas_length': len(a.datas or '') or 0} for a in atts]
        return result

    def get_tax_quotation_filename(self):
        """Generate custom filename for Tax Quotation: HMD Q (quotation no) - customer name"""
        quotation_no = self.name or ''
        customer_name = self.partner_id.name or ''
        # Remove special characters that might cause issues in filenames
        customer_name = customer_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace(
            '?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        return f"HMD Q ({quotation_no}) - {customer_name}".strip()

    def get_proforma_invoice_filename(self):
        """Generate custom filename for Proforma Invoice: HMD Perfoma Invoice (invoice no) - customer name"""
        invoice_no = self.name or ''
        customer_name = self.partner_id.name or ''
        # Remove special characters that might cause issues in filenames
        customer_name = customer_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace(
            '?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        return f"HMD Perfoma Invoice {invoice_no} - {customer_name}".strip()

    def _get_amount_in_words_proforma(self, amount):
        """Convert amount to words for Proforma Invoice (DIRHAM'S instead of DIRHAMS)"""
        words = self._get_amount_in_words(amount)
        return words.replace('DIRHAMS', 'DIRHAM\'S')


class SaleCustomOperation(models.Model):
    _name = 'sale.custom.operation'
    _description = 'Custom Operation for Sale Orders'

    name = fields.Char(string='Operation Name', required=True)
    line_ids = fields.One2many('sale.custom.operation.line', 'operation_id', string='Operation Lines')


class SaleCustomOperationLine(models.Model):
    _name = 'sale.custom.operation.line'
    _description = 'Custom Operation Line'

    operation_id = fields.Many2one('sale.custom.operation', string='Operation', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Description')
    product_uom_qty = fields.Float(string='Quantity', default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float(string='Unit Price')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Set price_unit from product's list_price (product.template)."""
        if self.product_id:
            self.price_unit = self.product_id.lst_price


class SaleCustomOperationWizard(models.TransientModel):
    _name = 'sale.custom.operation.wizard'
    _description = 'Add Operations to Sale Order'

    order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    operation_ids = fields.Many2many('sale.custom.operation', string='Operations')

    def action_apply(self):
        """Create section and product lines on the sale order for the selected operations.

        New lines should appear AFTER existing ones, not at the top. We achieve this
        by explicitly managing the 'sequence' field and appending after the current max.
        """
        self.ensure_one()
        order = self.order_id
        SaleOrderLine = self.env['sale.order.line']

        # Compute starting sequence so new lines are appended at the bottom
        max_sequence = 0
        if order.order_line:
            max_sequence = max(order.order_line.mapped('sequence') or [0])

        for operation in self.operation_ids:
            max_sequence += 10
            # Section line for the operation
            section_vals = {
                'order_id': order.id,
                'display_type': 'line_section',
                'name': operation.name,
                'sequence': max_sequence,
            }
            section_line = SaleOrderLine.create(section_vals)

            # Product lines under the section
            for op_line in operation.line_ids:
                max_sequence += 10
                product = op_line.product_id
                vals = {
                    'order_id': order.id,
                    'product_id': product.id,
                    'name': op_line.name or (product and product.name) or '',
                    'product_uom_qty': op_line.product_uom_qty or 1.0,
                    'price_unit': op_line.price_unit or (product and product.lst_price) or 0.0,
                    'sequence': max_sequence,
                }
                # Unit of measure
                if op_line.product_uom_id:
                    vals['product_uom_id'] = op_line.product_uom_id.id
                elif product and product.uom_id:
                    vals['product_uom_id'] = product.uom_id.id

                SaleOrderLine.create(vals)


class SaleOrderOperationsMixin(models.Model):
    _inherit = 'sale.order'

    def action_open_add_operations_wizard(self):
        """Open wizard to select operations and add their products to the order."""
        self.ensure_one()
        return {
            'name': 'Add Operations',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.custom.operation.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('custom_reports.view_sale_custom_operation_wizard').id,
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            },
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def action_open_add_operations_wizard(self):
        """Delegate toolbar button to the related sale order (supports multiple lines)."""
        # When clicking from the control toolbar, self can be multiple lines or empty.
        orders = self.mapped('order_id')
        order = orders[:1]
        if not order and self._context.get('order_id'):
            order = self.env['sale.order'].browse(self._context['order_id'])
        if not order and self._context.get('active_id'):
            order = self.env['sale.order'].browse(self._context['active_id'])
        if not order:
            return False
        return order.action_open_add_operations_wizard()


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Allow entering cheque/bank details directly on the invoice
    cheque_no = fields.Char(string='Cheque No.')
    bank_name = fields.Char(string='Bank Name')

    def _get_linked_sale_order(self):
        """Get the first linked sale order from invoice lines (for invoices from SO)"""
        self.ensure_one()
        sale_orders = self.invoice_line_ids.sale_line_ids.order_id
        return sale_orders[:1] if sale_orders else self.env['sale.order']

    def get_customer_vat(self):
        """Return customer's TRN from the partner's VAT field."""
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            so = self._get_linked_sale_order()
            if so and so.partner_id:
                partner = so.partner_id
        return partner.vat or '' if partner else ''

    def get_hmd_logo(self):
        """Get HMD logo as base64"""
        try:
            module_path = os.path.dirname(os.path.dirname(__file__))
            for ext in ['png', 'PNG']:
                logo_path = os.path.join(module_path, 'static', 'src', 'img', f'hmd.{ext}')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            pass
        return ''

    def get_qr_logo(self):
        """Get QR code image as base64"""
        try:
            module_path = os.path.dirname(os.path.dirname(__file__))
            for ext in ['png', 'PNG']:
                qr_path = os.path.join(module_path, 'static', 'src', 'img', f'qr.{ext}')
                if os.path.exists(qr_path):
                    with open(qr_path, 'rb') as f:
                        return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            pass
        return ''

    def get_hmd1_logo(self):
        """Get HMD1 logo (hmd1.png) as base64 for shared header."""
        try:
            module_path = os.path.dirname(os.path.dirname(__file__))
            for ext in ['png', 'PNG']:
                logo_path = os.path.join(module_path, 'static', 'src', 'img', f'hmd1.{ext}')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            pass
        return ''

    def get_instagram_logo(self):
        """Get Instagram icon as base64 for Tax Invoice / Account Statement footer"""
        try:
            module_path = os.path.dirname(os.path.dirname(__file__))
            for ext in ['png', 'PNG']:
                img_path = os.path.join(module_path, 'static', 'src', 'img', f'instagram.{ext}')
                if os.path.exists(img_path):
                    with open(img_path, 'rb') as f:
                        return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            pass
        return ''

    def get_invoice_date_formatted(self):
        """Format invoice_date as M/D/YYYY for Tax Invoice"""
        if self.invoice_date:
            day = self.invoice_date.day
            month = self.invoice_date.month
            year = self.invoice_date.year
            return f"{month}/{day}/{year}"
        return ''

    def get_sale_partner_name(self):
        """Get customer name from linked sale.order, fallback to invoice partner"""
        so = self._get_linked_sale_order()
        if so and so.partner_id:
            return so.partner_id.name or ''
        return (self.partner_id and self.partner_id.name) or ''

    def get_sale_site(self):
        """Site from SO or fallback to customer's country."""
        so = self._get_linked_sale_order()
        site = (so.site or so.location or '') if so else ''
        if not site:
            partner = (so.partner_id if so else None) or self.partner_id
            if partner and partner.country_id:
                site = partner.country_id.name or ''
        return site

    def get_sale_att(self):
        so = self._get_linked_sale_order()
        return so.att or '' if so else ''

    def get_sale_subject(self):
        so = self._get_linked_sale_order()
        return so.subject or '' if so else ''

    def get_sale_customer_trn(self):
        """Backward-compatible helper for reports: use partner VAT as customer's TRN."""
        self.ensure_one()
        so = self._get_linked_sale_order()
        partner = so.partner_id if so and so.partner_id else self.partner_id
        return partner.vat or '' if partner else ''

    def get_sale_payment_method(self):
        so = self._get_linked_sale_order()
        return so.payment_method or '' if so else ''

    def get_sale_cheque_no(self):
        so = self._get_linked_sale_order()
        return so.cheque_no or '' if so else ''

    def get_sale_bank_name(self):
        so = self._get_linked_sale_order()
        return so.bank_name or '' if so else ''

    def get_invoice_payment_method(self):
        """Return payment method for the invoice based on reconciled payments.

        Concatenates journal and payment method line of the first relevant payment,
        as requested (e.g., "Bank - Manual").
        """
        self.ensure_one()
        payments = self.reconciled_payment_ids.filtered(
            lambda p: p.state in ('paid', 'in_process')
        )
        payment = payments[:1]
        if not payment:
            return ''

        payment = payment[0]
        parts = []
        if payment.journal_id and payment.journal_id.name:
            parts.append(payment.journal_id.name)
        if payment.payment_method_line_id and payment.payment_method_line_id.name:
            parts.append(payment.payment_method_line_id.name)
        return ' - '.join(parts)

    def get_tax_invoice_description(self):
        """Build item description for Tax Invoice from sale order or invoice data"""
        so = self._get_linked_sale_order()
        if so:
            payment_type_text = 'FULL' if so.payment_type == 'full' else 'HALF'
            return f"{payment_type_text} Payment: Reff. Quotation # {so.name or ''} - {so.subject or ''} (Total Quotation Amount AED: {self.amount_total:,.2f}/-)"
        # Fallback for non-SO invoices
        return f"Invoice #{self.name or ''} - {self.partner_id.name or ''}"

    def _get_amount_in_words_invoice(self, amount):
        """Convert amount to words for Tax Invoice (DIRHAM'S instead of DIRHAMS)"""
        so = self._get_linked_sale_order()
        if so:
            return so._get_amount_in_words_proforma(amount)
        # Fallback: use sale.order helper
        words = self.env['sale.order'].new({})._get_amount_in_words(amount)
        return words.replace('DIRHAMS', 'DIRHAM\'S') if words else ''

    def get_tax_invoice_filename(self):
        """Generate filename for Tax Invoice"""
        inv_no = self.name or ''
        customer = (self.partner_id.name or '').replace('/', '_').replace('\\', '_').replace(':', '_')
        return f"Tax Invoice {inv_no} - {customer}".strip()

    def get_proforma_invoice_filename(self):
        """Generate filename for Proforma Invoice printed from Accounting.

        Uses linked sale order when available to keep a meaningful name.
        """
        so = self._get_linked_sale_order()
        if so and so.exists():
            invoice_no = so.name or ''
            customer_name = so.partner_id.name or ''
        else:
            invoice_no = self.name or ''
            customer_name = self.partner_id.name or ''
        customer_name = (customer_name or '').replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_')\
            .replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        return f"HMD Perfoma Invoice {invoice_no} - {customer_name}".strip()

    def get_tax_invoice_amount_untaxed(self):
        """Formatted subtotal for Tax Invoice report (ensures value shows in PDF)."""
        try:
            return '{:,.2f}'.format(float(self.amount_untaxed))
        except (TypeError, ValueError):
            return '0.00'

    def get_tax_invoice_amount_tax(self):
        """Formatted VAT amount for Tax Invoice report."""
        try:
            return '{:,.2f}'.format(float(self.amount_tax))
        except (TypeError, ValueError):
            return '0.00'

    def get_tax_invoice_amount_total(self):
        """Formatted total for Tax Invoice report (ensures value shows in PDF)."""
        try:
            return '{:,.2f}'.format(float(self.amount_total))
        except (TypeError, ValueError):
            return '0.00'

    # --- Account Statement helpers (for posted invoices) ---

    def get_account_statement_date_formatted(self):
        """Format invoice_date as M/D/YYYY (legacy helper, kept for compatibility)."""
        if self.invoice_date:
            return f"{self.invoice_date.month}/{self.invoice_date.day}/{self.invoice_date.year}"
        return ''

    def get_account_statement_print_date(self):
        """Date the Account Statement is printed (today) as M/D/YYYY."""
        today = fields.Date.context_today(self)
        if today:
            return f"{today.month}/{today.day}/{today.year}"
        return ''

    def get_account_statement_quoted_description(self):
        """Description for Quoted Amount section: Reff Quotation # X - SUBJECT"""
        so = self._get_linked_sale_order()
        if so:
            return f"Reff Quotation # {so.name or ''} - {so.subject or ''}"
        return f"Invoice #{self.name or ''}"

    def get_account_statement_payments(self):
        """List of reconciled payments: [{'date': 'DD-MM-YYYY', 'method': str, 'amount': float}, ...]
        Uses date and payment_method_line_id from account.payment."""
        self.ensure_one()
        # Odoo 19: account.payment uses 'paid'/'in_process', not 'posted'
        payments = self.reconciled_payment_ids.filtered(
            lambda p: p.state in ('paid', 'in_process')
        )
        result = []
        for pay in payments.sorted('date'):
            date_str = pay.date.strftime('%d-%m-%Y') if pay.date else ''
            method = pay.payment_method_line_id.name if pay.payment_method_line_id else ''
            result.append({
                'date': date_str,
                'method': method,
                'amount': pay.amount,
            })
        return result

    def get_account_statement_amount_received(self):
        """Total amount received (amount_total - amount_residual)"""
        return self.amount_total - abs(self.amount_residual)

    def get_account_statement_remaining_balance(self):
        """Remaining balance (amount_residual)"""
        return abs(self.amount_residual)

    def get_account_statement_filename(self):
        """Generate filename for Account Statement"""
        inv_no = self.name or ''
        customer = (self.partner_id.name or '').replace('/', '_').replace('\\', '_').replace(':', '_')
        return f"Account Statement {inv_no} - {customer}".strip()

    def get_proforma_payment_type_text(self):
        """Return 'Full' or 'Half' based on linked sale order payment_type."""
        self.ensure_one()
        so = self._get_linked_sale_order()
        if so and so.payment_type == 'half':
            return 'Half'
        return 'Full'