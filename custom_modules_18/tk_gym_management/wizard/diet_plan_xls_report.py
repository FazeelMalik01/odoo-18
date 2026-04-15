import base64
from io import BytesIO

import xlwt

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class DietPlanExcel(models.TransientModel):
    """Diet Plan Excel"""
    _name = 'diet.plan.excel'
    _description = __doc__

    start_date = fields.Date()
    end_date = fields.Date()

    @api.constrains('start_date', 'end_date')
    def _check_start_end_date(self):
        """check start end date"""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End date cannot be earlier than start date."))

    def print_excel(self):
        """print excel"""
        domain = []
        if self.start_date and not self.end_date:
            domain = [('date', '>=', self.start_date)]
        elif self.end_date and not self.start_date:
            domain = [('date', '<=', self.end_date)]
        elif self.start_date and self.end_date:
            domain = [('date', '>=', self.start_date), ('date', '<=', self.end_date)]
        records = self.env['diet.plan'].search(domain)
        workbook = xlwt.Workbook(encoding='utf-8', style_compression=1)
        sheet = workbook.add_sheet('Diet Plans', cell_overwrite_ok=True)
        sheet.show_grid = False
        xlwt.add_palette_colour("custom_light_green", 0x21)
        workbook.set_colour_RGB(0x21, 247, 255, 250)
        xlwt.add_palette_colour("custom_normal_red", 0x22)
        workbook.set_colour_RGB(0x22, 250, 234, 232)
        xlwt.add_palette_colour("custom_normal_green", 0x23)
        workbook.set_colour_RGB(0x23, 235, 255, 242)
        border_square = xlwt.Borders()
        border_square.top = xlwt.Borders.HAIR
        border_square.left = xlwt.Borders.HAIR
        border_square.right = xlwt.Borders.HAIR
        border_square.bottom = xlwt.Borders.HAIR
        border_square.top_colour = xlwt.Style.colour_map["gray50"]
        border_square.bottom_colour = xlwt.Style.colour_map["gray50"]
        border_square.right_colour = xlwt.Style.colour_map["gray50"]
        border_square.left_colour = xlwt.Style.colour_map["gray50"]
        al = xlwt.Alignment()
        al.horz = xlwt.Alignment.HORZ_CENTER
        al.vert = xlwt.Alignment.VERT_CENTER
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'mm/dd/yyyy'
        date_format.font.name = "Century Gothic"
        date_format.borders = border_square
        date_format.alignment = al
        title = xlwt.easyxf(
            "font: height 350, name Century Gothic, bold on, color_index blue_gray;"
            " align: vert center, horz center;"
            "border: bottom thick, bottom_color sea_green;"
            "pattern: pattern solid, fore_colour custom_light_green;")
        sub_title = xlwt.easyxf(
            "font: height 215, name Century Gothic, bold on, color_index gray80; "
            "align: vert center, horz center; "
            "border: top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50")
        border_all_center = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50")
        green_text = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic, color_index sea_green, bold on;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50")
        red_text = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:bold on, name Century Gothic, color_index dark_red;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50")
        yellow_text = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic, color_index olive_ega, bold on;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50")
        blue_text = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic, color_index dark_blue, bold on;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50")
        sheet.row(0).height = 1000
        sheet.row(1).height = 600
        sheet.col(0).width = 300
        for i in range(1, 10):
            sheet.col(i).width = 5000
        sheet.write_merge(0, 0, 1, 9, 'Diet Plans', title)
        sheet.write(1, 1, "Title", sub_title)
        sheet.write(1, 2, "Member", sub_title)
        sheet.write(1, 3, "Dietitian", sub_title)
        sheet.write(1, 4, "Date", sub_title)
        sheet.write(1, 5, "Diet Category", sub_title)
        sheet.write(1, 6, "Diet Type", sub_title)
        sheet.write(1, 7, "Diet Template", sub_title)
        sheet.write(1, 8, "Charges", sub_title)
        sheet.write(1, 9, "Invoice", sub_title)
        row = 2
        for rec in records:
            sheet.row(row).height = 400
            invoice = ""
            style = border_all_center
            if rec.invoice_id:
                if rec.invoice_id.state == 'draft':
                    invoice = 'Draft Invoice'
                    style = blue_text
                elif rec.invoice_id.state == 'posted':
                    invoice = rec.invoice_id.name
                    style = green_text
                elif rec.invoice_id.state == 'cancel':
                    invoice = 'Cancelled'
                    style = red_text
            else:
                invoice = 'Not Invoiced'
                style = yellow_text
            sheet.write(row, 1, rec.name, border_all_center)
            sheet.write(row, 2, rec.member_id.name, border_all_center)
            sheet.write(row, 3, rec.dietitian_id.name, border_all_center)
            sheet.write(row, 4, rec.date, date_format)
            sheet.write(row, 5, rec.diet_category_id.name, border_all_center)
            sheet.write(row, 6, rec.diet_type_id.name, border_all_center)
            if rec.diet_plan_template_id:
                plan = rec.diet_plan_template_id.name
            else:
                plan = ""
            sheet.write(row, 7, plan, border_all_center)
            sheet.write(row, 8, f'{rec.charges} {rec.currency_id.symbol}', border_all_center)
            sheet.write(row, 9, invoice, style)
            row += 1
        stream = BytesIO()
        workbook.save(stream)
        out = base64.encodebytes(stream.getvalue())

        attachment = self.env['ir.attachment'].sudo()
        filename = 'Diet Plans Details' + ".xls"
        attachment_id = attachment.create(
            {'name': filename,
             'type': 'binary',
             'public': False,
             'datas': out})
        report = {}
        if attachment_id:
            report = {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment_id.id}?download=true',
                'target': 'self',
            }
        return report
