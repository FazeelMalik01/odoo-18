from odoo import models, fields, api

class FalconDeliveryNote(models.Model):
    _name = 'delivery.note'
    _description = 'Falcon Delivery Note'

    name = fields.Char(string="Delivery Note Ref", required=True)
    delivery_date = fields.Date(string="Delivery Date")
    coordinated_by = fields.Many2one('res.partner', string="Coordinated By")
    title = fields.Char(string="Title")
    email = fields.Char(string="Email")
    mobile = fields.Char(string="Mobile")
    delivered_to = fields.Char(string="Delivered To")
    buyer_name = fields.Many2one('res.partner', string="Buyer Name")
    buyer_email = fields.Char(string="Buyer Email")
    customer_notes_line_ids = fields.One2many(
        'delivery.customer.notes.line', 'delivery_note_id', string="Customer Notes"
    )
    delivery_terms_line_ids = fields.One2many(
        'delivery.terms.line', 'delivery_note_id', string="Delivery Terms"
    )

    line_ids = fields.One2many(
        'delivery.note.line', 
        'delivery_note_id', 
        string="Delivery Items"
    )

class DeliveryNoteLine(models.Model):
    _name = 'delivery.note.line'
    _description = 'Delivery Note Line'

    delivery_note_id = fields.Many2one('delivery.note', string="Delivery Note", ondelete='cascade')
    item = fields.Many2one('product.product', string="Item", required=True)
    description = fields.Text(string="Description")
    uom = fields.Many2one('uom.uom', string="UoM")
    quantity = fields.Float(string="Quantity")
    notes = fields.Text(string="Notes")

    @api.onchange('item')
    def _onchange_item(self):
        """When user selects a product, auto-fill description and UoM"""
        for rec in self:
            if rec.item:
                rec.description = rec.item.name or ''
                rec.uom = rec.item.uom_id.id
            else:
                rec.description = ''
                rec.uom = False

class DeliveryCustomerNotesLine(models.Model):
    _name = 'delivery.customer.notes.line'
    _description = 'Customer Notes Line'

    delivery_note_id = fields.Many2one('delivery.note', string="Delivery Note Ref", ondelete='cascade')
    note = fields.Char(string="Note")


class DeliveryTermsLine(models.Model):
    _name = 'delivery.terms.line'
    _description = 'Delivery Terms Line'

    delivery_note_id = fields.Many2one('delivery.note', string="Delivery Note Ref", ondelete='cascade')
    term = fields.Char(string="Term")