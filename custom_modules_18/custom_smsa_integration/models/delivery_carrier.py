import base64
import logging
import math
import requests
from datetime import datetime

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('smsa', 'SMSA')],
        ondelete={'smsa': 'set default'}
    )

    smsa_api_key = fields.Char("SMSA API Key")
    smsa_rate_first_order = fields.Float(
        "Rate for first kg",
        default=2.0,
        help="Price for the first kg (in company currency). e.g. 2 BD",
    )
    smsa_rate_other_orders = fields.Float(
        "Rate per additional kg",
        default=1.0,
        help="Price per additional kg after the first (in company currency). e.g. 1 BD per kg",
    )

    # -------------------------------
    # RATE SHIPMENT (WEIGHT-BASED)
    # First kg: rate_first (e.g. 2 BD) | Each additional kg: rate_other (e.g. 1 BD)
    # < 1 kg = 2 BD, 1–2 kg = 3 BD, 2–3 kg = 4 BD, etc.
    # -------------------------------
    def smsa_rate_shipment(self, order):
        """Return tiered price: first kg at rate_first, each additional kg at rate_other."""
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _('Error: this delivery method is not available for this address.'),
                'warning_message': False,
            }

        weight = self._smsa_get_order_weight(order)
        weight_kg = max(0.0, weight)
        weight_tiers = max(1, math.ceil(weight_kg))  # 0–1 kg = 1 tier, 1–2 kg = 2 tiers, etc.

        # First kg at smsa_rate_first_order, each extra kg at smsa_rate_other_orders
        price_company = self.smsa_rate_first_order + (weight_tiers - 1) * self.smsa_rate_other_orders

        # Convert to order/pricelist currency
        price = self._compute_currency(order, price_company, 'company_to_pricelist')

        return {
            'success': True,
            'price': price,
            'error_message': False,
            'warning_message': False,
        }

    def _smsa_get_order_weight(self, order):
        """Get total weight of order in kg (excludes delivery lines)."""
        weight = 0.0
        for line in order.order_line:
            if line.state == 'cancel' or not line.product_id or line.is_delivery:
                continue
            if line.product_id.type == "service":
                continue
            qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            weight += (line.product_id.weight or 0.0) * qty
        # Use context (wizard) or saved shipping_weight as fallback
        weight = self.env.context.get('order_weight') or order.shipping_weight or weight
        return weight

    def _apply_margins(self, price):
        """For SMSA, use fixed price without applying margin (same as Fixed Price carrier)."""
        if self.delivery_type == 'smsa':
            return float(price)
        return super()._apply_margins(price)
    
    def smsa_get_tracking_link(self, picking):
        """Return SMSA tracking URL for the waybill."""
        if picking.carrier_tracking_ref:
            awb = picking.carrier_tracking_ref
            return f"https://www.smsaexpress.com/bh/trackingdetails?tracknumbers%5B0%5D={awb}"
        return False

    def _format_smsa_phone(self, phone):
        """Format phone to SMSA required format (9665XXXXXXXX)."""
        if not phone:
            return ""

        phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")

        # If starts with 05 → convert to 9665
        if phone.startswith("05") and len(phone) == 10:
            phone = "966" + phone[1:]

        # If starts with 5 and length 9 → add 966
        elif phone.startswith("5") and len(phone) == 9:
            phone = "966" + phone

        return phone

    # -------------------------------
    # CREATE SHIPMENT ONLY (NO PRICE)
    # -------------------------------
    def smsa_send_shipping(self, pickings):
        api_url = "https://ecomapis.smsaexpress.com/api/shipment/b2c/new"

            # Map country/city to service code (can be extended)
        service_code_default = "EDDL"  # safest default

        results = []

        for picking in pickings:

            # Prevent duplicate shipments
            if picking.carrier_tracking_ref:
                _logger.info("SMSA: Shipment already exists for %s", picking.name)
                continue

            order = picking.sale_id
            partner = picking.partner_id
            warehouse = picking.picking_type_id.warehouse_id
            shipper = warehouse.partner_id


            api_key = self.smsa_api_key or "8cf57c0dea6548e09f3f8b076e29531e"
            # Determine service code based on destination
            # Domestic vs International
            if partner.country_id.code == shipper.country_id.code:
                service_code = "EDDL"  # Domestic light shipment
            else:
                service_code = "EIDL"  # International light shipment

            consignee_addr = {
                "ContactName": partner.name or "",
                "ContactPhoneNumber": self._format_smsa_phone(partner.phone or partner.mobile),
                "Country": partner.country_id.code or "SA",
                "City": partner.city or "",
                "District": partner.state_id.name or "",
                "PostalCode": partner.zip or "",
                "AddressLine1": partner.street or "",
                "AddressLine2": partner.street2 or "",
            }
            if partner.country_id.code == "SA" and partner.national_address:
                consignee_addr["ShortCode"] = (partner.national_address or "").strip().upper()[:8]

            shipper_addr = {
                "ContactName": shipper.name or "",
                "ContactPhoneNumber": self._format_smsa_phone(
                    shipper.phone or shipper.mobile
                ),
                "Country": shipper.country_id.code or "SA",
                "City": shipper.city or "",
                "District": shipper.state_id.name or "",
                "PostalCode": shipper.zip or "",
                "AddressLine1": shipper.street or "",
                "AddressLine2": shipper.street2 or "",
            }
            if shipper.country_id.code == "SA" and shipper.national_address:
                shipper_addr["ShortCode"] = (shipper.national_address or "").strip().upper()[:8]

            payload = {
                "ConsigneeAddress": consignee_addr,
                "ShipperAddress": shipper_addr,
                "OrderNumber": order.name,
                "DeclaredValue": order.amount_total,
                "CODAmount": 0,
                "Parcels": 1,
                "ShipDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "ShipmentCurrency": order.currency_id.name,
                "SMSARetailID": "0",
                "WaybillType": "PDF",
                "Weight": 1,
                "WeightUnit": "KG",
                "ContentDescription": "Odoo Order Shipment",
                "VatPaid": True,
                "DutyPaid": False,
                "ServiceCode": service_code,
            }

            headers = {
                "apikey": api_key,
                "Content-Type": "application/json"
            }

            _logger.info("========== SMSA SHIPMENT REQUEST ==========")
            _logger.info("Picking: %s | Order: %s", picking.name, order.name)
            _logger.info("Payload: %s", payload)

            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=60)

                _logger.info("SMSA Status Code: %s", response.status_code)
                _logger.info("SMSA Raw Response: %s", response.text)

                if response.status_code != 200:
                    _logger.error("SMSA RESPONSE ERROR: %s", response.text)
                    raise Exception(f"SMSA HTTP ERROR {response.status_code}")

                data = response.json()

                # Extract AWB safely
                awb = None

                if data.get("sawb"):
                    awb = data.get("sawb")
                elif data.get("waybills"):
                    waybills = data.get("waybills")
                    if isinstance(waybills, list) and waybills:
                        awb = waybills[0].get("awb")
                elif data.get("AwbNumber"):
                    awb = data.get("AwbNumber")
                elif data.get("awb"):
                    awb = data.get("awb")

                if not awb:
                    _logger.error("SMSA RESPONSE WITHOUT AWB: %s", data)
                    raise Exception("SMSA did not return AWB")

                picking.carrier_tracking_ref = awb

                # Save PDF waybill - try multiple response keys (awbFile, AwbFile, etc.)
                awb_file = (
                    data.get("awbFile")
                    or data.get("AwbFile")
                    or data.get("awb_file")
                    or data.get("waybillPdf")
                    or data.get("pdf")
                )
                if data.get("waybills") and isinstance(data["waybills"], list) and data["waybills"]:
                    first_wb = data["waybills"][0]
                    if isinstance(first_wb, dict):
                        awb_file = awb_file or first_wb.get("awbFile") or first_wb.get("AwbFile")

                if awb_file:
                    try:
                        # Ensure base64: APIs may return raw string or base64
                        pdf_data = awb_file
                        if isinstance(pdf_data, str) and pdf_data.startswith("http"):
                            # URL - fetch the PDF
                            pdf_resp = requests.get(pdf_data, timeout=30)
                            if pdf_resp.status_code == 200:
                                pdf_data = base64.b64encode(pdf_resp.content).decode()
                        elif isinstance(pdf_data, bytes):
                            pdf_data = base64.b64encode(pdf_data).decode()

                        attachment = self.env['ir.attachment'].create({
                            'name': f'Waybill_{awb}.pdf',
                            'datas': pdf_data,
                            'res_model': 'stock.picking',
                            'res_id': picking.id,
                            'mimetype': 'application/pdf',
                        })
                        picking.carrier_waybill_attachment_id = attachment
                        _logger.info("SMSA Waybill PDF saved for %s", picking.name)
                    except Exception as e:
                        _logger.warning("SMSA: Could not save waybill PDF: %s", e)
                else:
                    _logger.info("SMSA Response keys: %s (no awbFile found)", list(data.keys()))

                _logger.info("SMSA AWB CREATED: %s", awb)

                results.append({
                    'tracking_number': awb,
                })

            except Exception:
                _logger.exception("SMSA SHIPPING FAILED")
                raise

        return results


# ---------------------------------
# TRIGGER AFTER PAYMENT (ORDER CONFIRM)
# ---------------------------------
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()

        for order in self:
            carrier = order.carrier_id
            if carrier and carrier.delivery_type == 'smsa':
                _logger.info("SMSA: Order confirmed → creating shipment for %s", order.name)

                for picking in order.picking_ids:
                    carrier.smsa_send_shipping(picking)

        return res
