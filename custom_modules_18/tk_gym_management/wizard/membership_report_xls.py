import base64
from io import BytesIO

import xlwt

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MembershipReportWizard(models.TransientModel):
    """Membership xls Report Wizard"""

    _name = "membership.report.wizard"
    _description = __doc__

    start_date = fields.Date()
    end_date = fields.Date()

    @api.constrains("start_date", "end_date")
    def _check_start_end_date(self):
        """check start end date"""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End date cannot be earlier than start date."))

    def print_membership_xls(self):
        """print membership xls"""
        domain = []
        if self.start_date and not self.end_date:
            domain = [("start_date", ">=", self.start_date)]
        elif self.end_date and not self.start_date:
            domain = [("start_date", "<=", self.end_date)]
        elif self.start_date and self.end_date:
            domain = [("start_date", ">=", self.start_date), ("start_date", "<=", self.end_date)]
        records = self.env["memberships.member"].search(domain)
        closed_records = self.env["memberships.member"].search(domain + [("stages", "=", "close")])
        active_records = self.env["memberships.member"].search(domain + [("stages", "=", "active")])
        expired_records = self.env["memberships.member"].search(
            domain + [("stages", "=", "expired")]
        )
        cancelled_records = self.env["memberships.member"].search(
            domain + [("stages", "=", "cancel")]
        )
        workbook = xlwt.Workbook(encoding="utf-8")
        sheet = workbook.add_sheet("Memberships", cell_overwrite_ok=True)
        sheet1 = workbook.add_sheet("Active Memberships", cell_overwrite_ok=True)
        sheet2 = workbook.add_sheet("Closed Memberships", cell_overwrite_ok=True)
        sheet3 = workbook.add_sheet("Expired Memberships", cell_overwrite_ok=True)
        sheet4 = workbook.add_sheet("Cancelled Memberships", cell_overwrite_ok=True)
        self.make_sheet(
            sheet=sheet, workbook=workbook, records=records, heading="Membership Details"
        )
        self.make_sheet(
            sheet=sheet1,
            workbook=workbook,
            records=active_records,
            heading="Active Membership Details",
        )
        self.make_sheet(
            sheet=sheet2,
            workbook=workbook,
            records=closed_records,
            heading="Closed Membership Details",
        )
        self.make_sheet(
            sheet=sheet3,
            workbook=workbook,
            records=expired_records,
            heading="Expired Membership Details",
        )
        self.make_sheet(
            sheet=sheet4,
            workbook=workbook,
            records=cancelled_records,
            heading="Cancelled Membership Details",
        )
        stream = BytesIO()
        workbook.save(stream)
        out = base64.encodebytes(stream.getvalue())

        attachment = self.env["ir.attachment"].sudo()
        filename = "Membership Details" + ".xls"
        attachment_id = attachment.create(
            {"name": filename, "type": "binary", "public": False, "datas": out}
        )
        report = {}
        if attachment_id:
            report = {
                "type": "ir.actions.act_url",
                "url": f"/web/content/{attachment_id.id}?download=true",
                "target": "self",
            }
        return report

    def make_sheet(self, sheet, workbook, records, heading):
        """make sheet"""
        sheet.show_grid = False
        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(2)
        sheet.set_vert_split_pos(1)
        xlwt.add_palette_colour("custom_light_green", 0x21)
        workbook.set_colour_RGB(0x21, 247, 255, 250)
        xlwt.add_palette_colour("custom_normal_red", 0x22)
        workbook.set_colour_RGB(0x22, 250, 234, 232)
        xlwt.add_palette_colour("custom_normal_green", 0x23)
        workbook.set_colour_RGB(0x23, 235, 255, 242)
        border_squre = xlwt.Borders()
        border_squre.top = xlwt.Borders.HAIR
        border_squre.left = xlwt.Borders.HAIR
        border_squre.right = xlwt.Borders.HAIR
        border_squre.bottom = xlwt.Borders.HAIR
        border_squre.top_colour = xlwt.Style.colour_map["gray50"]
        border_squre.bottom_colour = xlwt.Style.colour_map["gray50"]
        border_squre.right_colour = xlwt.Style.colour_map["gray50"]
        border_squre.left_colour = xlwt.Style.colour_map["gray50"]
        al = xlwt.Alignment()
        al.horz = xlwt.Alignment.HORZ_CENTER
        al.vert = xlwt.Alignment.VERT_CENTER
        date_format = xlwt.XFStyle()
        date_format.num_format_str = "mm/dd/yyyy"
        date_format.font.name = "Century Gothic"
        date_format.borders = border_squre
        date_format.alignment = al
        title = xlwt.easyxf(
            "font: height 440, name Century Gothic, bold on, color_index blue_gray;"
            " align: vert center, horz center;"
            "border: bottom thick, bottom_color sea_green;"
            "pattern: pattern solid, fore_colour custom_light_green;"
        )
        sub_title = xlwt.easyxf(
            "font: height 185, name Century Gothic, bold on, color_index gray80; "
            "align: vert center, horz center; "
            "border: top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        border_all_center = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        border_all_center_green_bg = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50;"
            "pattern: pattern solid, fore_colour custom_normal_green;"
        )
        border_all_center_red_bg = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50;"
            "pattern: pattern solid, fore_colour custom_normal_red;"
        )
        green_text = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic, color_index sea_green, bold on;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        red_text = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:bold on, name Century Gothic, color_index dark_red;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        blue_text = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic, color_index dark_blue, bold on;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        yellow_text = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic, color_index olive_ega, bold on;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        gray_text = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic, color_index gray80, bold on;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        sheet.row(0).height = 1000
        sheet.row(1).height = 600
        sheet.col(0).width = 300
        for i in range(1, 12):
            sheet.col(i).width = 4500
        sheet.col(1).width = 5000
        sheet.col(2).width = 5000
        sheet.col(3).width = 5000
        sheet.col(11).width = 6000
        sheet.col(12).width = 5000
        sheet.write_merge(0, 0, 1, 12, heading, title)
        sheet.write(1, 1, "Membership Ref.", sub_title)
        sheet.write(1, 2, "Member", sub_title)
        sheet.write(1, 3, "Membership Type", sub_title)
        sheet.write(1, 4, "Start Date", sub_title)
        sheet.write(1, 5, "End Date", sub_title)
        sheet.write(1, 6, "Duration", sub_title)
        sheet.write(1, 7, "Invoice Ref.", sub_title)
        sheet.write(1, 8, "Charges", sub_title)
        sheet.write(1, 9, "Tax Amount", sub_title)
        sheet.write(1, 10, "Paid Amount", sub_title)
        sheet.write(1, 11, "Remaining Amount", sub_title)
        sheet.write(1, 12, "Status", sub_title)
        row = 2
        tax_amount = 0.0
        paid_amount = 0.0
        total_remain_amount = 0.0
        total_charges = 0.0
        for rec in records:
            invoice = "Not Invoiced"
            remain_amount = rec.invoice_membership_id.amount_residual_signed
            sheet.row(row).height = 400
            if rec.invoice_membership_id.state == "posted":
                invoice = rec.invoice_membership_id.name
            elif rec.invoice_membership_id.state == "draft":
                invoice = "Draft"
            elif rec.invoice_membership_id.state == "cancel":
                invoice = "Cancelled"

            if not rec.invoice_membership_id:
                remain_amount = rec.price

            status = ""
            style = ""
            if rec.stages == "draft":
                status = "Draft"
                style = blue_text
            elif rec.stages == "active":
                status = "In Progress"
                style = yellow_text
            elif rec.stages == "expired":
                status = "Expired"
                style = red_text
            elif rec.stages == "cancel":
                status = "Cancel"
                style = red_text
            elif rec.stages == "close":
                status = "Close"
                style = green_text
            elif rec.stages == "renewal":
                status = "Renew"
                style = gray_text

            sheet.write(row, 1, rec.gym_membership_number, border_all_center)
            sheet.write(row, 2, rec.gym_member_id.name, border_all_center)
            sheet.write(row, 3, rec.gym_membership_type_id.name, border_all_center)
            sheet.write(row, 4, rec.start_date, date_format)
            sheet.write(row, 5, rec.end_date, date_format)
            sheet.write(row, 6, rec.duration_id.name, border_all_center)
            sheet.write(row, 7, invoice, border_all_center)
            sheet.write(row, 8, f"{rec.price} {rec.currency_id.symbol}", border_all_center)
            sheet.write(
                row,
                9,
                f"{rec.invoice_membership_id.amount_tax_signed} {rec.currency_id.symbol}",
                border_all_center,
            )
            sheet.write(
                row,
                10,
                f"{rec.invoice_membership_id.amount_total_signed - rec.invoice_membership_id.amount_residual_signed} {rec.currency_id.symbol}",
                border_all_center,
            )
            sheet.write(row, 11, f"{remain_amount} {rec.currency_id.symbol}", border_all_center)
            sheet.write(row, 12, status, style)
            row += 1
            tax_amount += rec.invoice_membership_id.amount_tax_signed
            paid_amount += (
                    rec.invoice_membership_id.amount_total_signed
                    - rec.invoice_membership_id.amount_residual_signed
            )
            total_remain_amount += remain_amount
            total_charges += rec.price
        sheet.write(row, 7, "Total", sub_title)
        sheet.row(row).height = 400
        sheet.write(
            row, 8, f"{total_charges} {self.env.company.currency_id.symbol}", border_all_center
        )
        sheet.write(
            row, 9, f"{tax_amount} {self.env.company.currency_id.symbol}", border_all_center
        )
        sheet.write(
            row,
            10,
            f"{paid_amount} {self.env.company.currency_id.symbol}",
            border_all_center_green_bg,
        )
        sheet.write(
            row,
            11,
            f"{total_remain_amount} {self.env.company.currency_id.symbol}",
            border_all_center_red_bg,
        )
