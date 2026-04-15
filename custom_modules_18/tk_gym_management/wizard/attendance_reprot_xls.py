import base64
from io import BytesIO

import pytz
import xlwt

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AttendanceExcelReport(models.TransientModel):
    """Attendance Excel Report"""

    _name = "attendance.excel.report"
    _description = __doc__

    attendance_of = fields.Selection(
        [("employee", "Employee"), ("member", "Member")], default="employee"
    )
    member_id = fields.Many2one("res.partner", domain=[("is_member", "=", True)])
    employee_id = fields.Many2one(
        "hr.employee", domain=[("is_trainer", "=", True)]
    )
    start_date = fields.Date()
    end_date = fields.Date()

    @api.constrains("start_date", "end_date")
    def _check_start_end_date(self):
        """check start end date"""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End date cannot be earlier than start date."))

    def print_excel(self):
        """print excel"""
        domain = []
        if self.start_date and not self.end_date:
            domain = [("check_in", ">=", self.start_date)]
        elif self.end_date and not self.start_date:
            domain = [("check_in", "<=", self.end_date)]
        elif self.start_date and self.end_date:
            domain = [("check_in", ">=", self.start_date), ("check_in", "<=", self.end_date)]
        user_timezone = pytz.timezone(self.env.user.partner_id.tz)

        if self.attendance_of == "employee":
            if self.employee_id:
                domain += [("employee_id", "=", self.employee_id.id)]
            records = self.env["employee.attendance"].search(domain)
            workbook = xlwt.Workbook(encoding="utf-8")
            sheet = workbook.add_sheet("Employee Attendance Details", cell_overwrite_ok=True)
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
            date_format.num_format_str = "mm/dd/yyyy hh:mm:ss"
            date_format.font.name = "Century Gothic"
            date_format.borders = border_square
            date_format.alignment = al
            title = xlwt.easyxf(
                "font: height 350, name Century Gothic, bold on, color_index blue_gray;"
                " align: vert center, horz center;"
                "border: bottom thick, bottom_color sea_green;"
                "pattern: pattern solid, fore_colour custom_light_green;"
            )
            sub_title = xlwt.easyxf(
                "font: height 225, name Century Gothic, bold on, color_index gray80; "
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
            border_all_center_bold = xlwt.easyxf(
                "align:horz center, vert center;"
                "font:name Century Gothic, bold on;"
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
            yellow_text = xlwt.easyxf(
                "align:horz center, vert center;"
                "font:name Century Gothic, color_index olive_ega, bold on;"
                "border:  top hair, bottom hair, left hair, right hair, "
                "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )
            blue_text = xlwt.easyxf(
                "align:horz center, vert center;"
                "font:name Century Gothic, color_index dark_blue, bold on;"
                "border:  top hair, bottom hair, left hair, right hair, "
                "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )
            sheet.row(0).height = 1000
            sheet.row(1).height = 600
            sheet.col(0).width = 300
            for i in range(1, 5):
                sheet.col(i).width = 6000
            sheet.col(4).width = 4000
            sheet.write_merge(0, 0, 1, 4, "Employee Attendance Details", title)
            row = 1
            for data in records:
                if data.employee_attendance_line_ids:
                    sheet.row(row).height = 600
                    sheet.row(row + 1).height = 400
                    sheet.row(row + 2).height = 400
                    sheet.row(row + 3).height = 400
                    sheet.row(row + 4).height = 400
                    sheet.write_merge(
                        row, row, 1, 4, f"Employee - {data.employee_id.name}", sub_title
                    )
                    sheet.write_merge(
                        row + 1, row + 1, 1, 2, "Working Hours/Day", border_all_center
                    )
                    sheet.write_merge(
                        row + 1, row + 1, 3, 4, data.working_hours_per_day, border_all_center
                    )
                    sheet.write(row + 2, 1, "Total Hours", border_all_center)
                    sheet.write(row + 2, 2, data.total_hours, border_all_center)
                    sheet.write(row + 2, 3, "Attended Hours", border_all_center)
                    style = ""
                    if data.attended_hours >= data.total_hours:
                        style = border_all_center_green_bg
                    elif data.attended_hours < data.total_hours:
                        style = border_all_center_red_bg
                    sheet.write(row + 2, 4, data.attended_hours, style)
                    sheet.write(row + 3, 1, "Check In", border_all_center_bold)
                    sheet.write(row + 3, 2, "Check Out", border_all_center_bold)
                    sheet.write(row + 3, 3, "Hours", border_all_center_bold)
                    sheet.write(row + 3, 4, "State", border_all_center_bold)
                    new_row = row + 4
                    for rec in data.employee_attendance_line_ids:

                        if not rec.check_in or not rec.check_out:
                            continue

                        check_in = rec.check_in.astimezone(user_timezone)
                        native_check_in = check_in.replace(tzinfo=None)
                        check_out = rec.check_out.astimezone(user_timezone)
                        native_check_out = check_out.replace(tzinfo=None)
                        sheet.row(new_row).height = 400
                        status = ""
                        style = ""
                        style2 = ""
                        if rec.state == "new":
                            status = "New"
                            style = blue_text
                        elif rec.state == "checked_in":
                            status = "Checked In"
                            style = yellow_text
                        elif rec.state == "checked_out":
                            status = "Checked Out"
                            style = green_text
                        sheet.write(new_row, 1, native_check_in, date_format)
                        sheet.write(new_row, 2, native_check_out, date_format)
                        if rec.hours >= rec.working_hours_per_day:
                            style2 = border_all_center_green_bg
                        elif rec.hours < rec.working_hours_per_day:
                            style2 = border_all_center_red_bg
                        sheet.write(new_row, 3, rec.hours, style2)
                        sheet.write(new_row, 4, status, style)
                        new_row += 1
                    row = new_row
                    row += 1
            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())

            attachment = self.env["ir.attachment"].sudo()
            filename = "Employee Attendance Details" + ".xls"
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

        if self.attendance_of == "member":
            if self.member_id:
                domain += [("member_id", "=", self.member_id.id)]
            records = self.env["member.attendance"].search(domain)
            workbook = xlwt.Workbook(encoding="utf-8")
            sheet = workbook.add_sheet("Member Attendance Details", cell_overwrite_ok=True)
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
            date_format.num_format_str = "mm/dd/yyyy hh:mm:ss"
            date_format.font.name = "Century Gothic"
            date_format.borders = border_square
            date_format.alignment = al
            title = xlwt.easyxf(
                "font: height 350, name Century Gothic, bold on, color_index blue_gray;"
                " align: vert center, horz center;"
                "border: bottom thick, bottom_color sea_green;"
                "pattern: pattern solid, fore_colour custom_light_green;"
            )
            sub_title = xlwt.easyxf(
                "font: height 225, name Century Gothic, bold on, color_index gray80; "
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
            border_all_center_bold = xlwt.easyxf(
                "align:horz center, vert center;"
                "font:name Century Gothic, bold on;"
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
            yellow_text = xlwt.easyxf(
                "align:horz center, vert center;"
                "font:name Century Gothic, color_index olive_ega, bold on;"
                "border:  top hair, bottom hair, left hair, right hair, "
                "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )
            blue_text = xlwt.easyxf(
                "align:horz center, vert center;"
                "font:name Century Gothic, color_index dark_blue, bold on;"
                "border:  top hair, bottom hair, left hair, right hair, "
                "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )
            sheet.row(0).height = 1000
            sheet.row(1).height = 600
            sheet.col(0).width = 300
            for i in range(1, 5):
                sheet.col(i).width = 6000
            sheet.col(4).width = 4000
            sheet.write_merge(0, 0, 1, 4, "Member Attendance Details", title)
            row = 1
            for data in records:
                if data.member_attendance_line_ids:
                    sheet.row(row).height = 600
                    sheet.row(row + 1).height = 400
                    sheet.row(row + 2).height = 400
                    sheet.row(row + 3).height = 400
                    sheet.row(row + 4).height = 400
                    sheet.write_merge(row, row, 1, 4, f"Member - {data.member_id.name}", sub_title)
                    sheet.write_merge(
                        row + 1, row + 1, 1, 2, "Working Hours/Day", border_all_center
                    )
                    sheet.write_merge(
                        row + 1, row + 1, 3, 4, data.gym_hours_per_day, border_all_center
                    )
                    sheet.write(row + 2, 1, "Total Hours", border_all_center)
                    sheet.write(row + 2, 2, data.total_hours, border_all_center)
                    sheet.write(row + 2, 3, "Attended Hours", border_all_center)
                    style = ""
                    if data.attended_hours >= data.total_hours:
                        style = border_all_center_green_bg
                    elif data.attended_hours < data.total_hours:
                        style = border_all_center_red_bg
                    sheet.write(row + 2, 4, data.attended_hours, style)
                    sheet.write(row + 3, 1, "Check In", border_all_center_bold)
                    sheet.write(row + 3, 2, "Check Out", border_all_center_bold)
                    sheet.write(row + 3, 3, "Hours", border_all_center_bold)
                    sheet.write(row + 3, 4, "State", border_all_center_bold)
                    new_row = row + 4

                    for rec in data.member_attendance_line_ids:

                        if not rec.check_in or not rec.check_out:
                            continue

                        check_in = rec.check_in.astimezone(user_timezone)
                        native_check_in = check_in.replace(tzinfo=None)
                        check_out = rec.check_out.astimezone(user_timezone)
                        native_check_out = check_out.replace(tzinfo=None)
                        sheet.row(new_row).height = 400
                        status = ""
                        style = ""
                        style2 = ""
                        if rec.state == "new":
                            status = "New"
                            style = blue_text
                        elif rec.state == "checked_in":
                            status = "Checked In"
                            style = yellow_text
                        elif rec.state == "checked_out":
                            status = "Checked Out"
                            style = green_text
                        sheet.write(new_row, 1, native_check_in, date_format)
                        sheet.write(new_row, 2, native_check_out, date_format)
                        if rec.hours >= rec.gym_hours_per_day:
                            style2 = border_all_center_green_bg
                        elif rec.hours < rec.gym_hours_per_day:
                            style2 = border_all_center_red_bg
                        sheet.write(new_row, 3, rec.hours, style2)
                        sheet.write(new_row, 4, status, style)
                        new_row += 1
                    row = new_row
                    row += 1
            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())

            attachment = self.env["ir.attachment"].sudo()
            filename = "Member Attendance Details" + ".xls"
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
