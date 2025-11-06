from odoo import http, fields
from odoo.http import request
from math import radians, sin, cos, sqrt, atan2
from pluscodes import decoder  # Ensure this library is installed


class RemoteAttendance(http.Controller):

    @http.route("/remote_attendance/check", type="json", auth="user", methods=["POST"])
    def check_remote_attendance(self, lat, long):
        try:
            employee = (
                request.env["hr.employee"]
                .sudo()
                .search([("user_id", "=", request.uid)], limit=1)
            )

            if not employee:
                return {"success": False, "message": "Employee record not found"}

            if not employee.remote_plus_code:
                return {"success": False, "message": "Remote work location not set"}

            # Decode employee's location from Plus Code
            try:
                employee_location = decoder.decode(employee.remote_plus_code)
                sw = getattr(employee_location, "sw", None)
                ne = getattr(employee_location, "ne", None)

                if not sw or not ne:
                    return {
                        "success": False,
                        "message": "Error decoding Plus Code: Missing location attributes",
                    }

                emp_lat = (sw.lat + ne.lat) / 2
                emp_long = (sw.lon + ne.lon) / 2
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error decoding Plus Code: {str(e)}",
                }

            # Calculate distance
            distance = self.calculate_distance(lat, long, emp_lat, emp_long)
            if distance > 500:  # 500m range check
                return {
                    "success": False,
                    "message": f"Out of range ({distance:.2f}m). Attendance not marked.",
                }

            # Fetch last attendance record
            last_attendance = (
                request.env["hr.attendance"]
                .sudo()
                .search(
                    [("employee_id", "=", employee.id)], order="check_in desc", limit=1
                )
            )

            if last_attendance and not last_attendance.check_out:
                return {
                    "success": False,
                    "message": "Already checked in. Please check out before new check-in.",
                }

            # Mark new check-in
            request.env["hr.attendance"].sudo().create(
                {"employee_id": employee.id, "check_in": fields.Datetime.now()}
            )
            request.env.cr.commit()
            return {"success": True, "message": "Check-in marked successfully"}

        except Exception as e:
            return {"success": False, "message": f"Server error: {str(e)}"}

    @http.route(
        "/remote_attendance/checkout", type="json", auth="user", methods=["POST"]
    )
    def mark_checkout(self):
        try:
            employee = (
                request.env["hr.employee"]
                .sudo()
                .search([("user_id", "=", request.uid)], limit=1)
            )

            if not employee:
                return {"success": False, "message": "Employee record not found"}

            last_attendance = (
                request.env["hr.attendance"]
                .sudo()
                .search(
                    [("employee_id", "=", employee.id), ("check_out", "=", False)],
                    order="check_in desc",
                    limit=1,
                )
            )

            if not last_attendance:
                return {
                    "success": False,
                    "message": "No active check-in found. Please check in first.",
                }

            # Mark checkout
            last_attendance.sudo().write({"check_out": fields.Datetime.now()})
            request.env.cr.commit()
            return {"success": True, "message": "Check-out marked successfully"}

        except Exception as e:
            return {"success": False, "message": f"Server error: {str(e)}"}

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two latitude/longitude points using Haversine formula."""
        R = 6371000  # Radius of Earth in meters

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c  # Distance in meters
