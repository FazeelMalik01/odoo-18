# -*- coding: utf-8 -*-

from odoo import models, fields
import logging
from zk import ZK
from datetime import datetime,time,timedelta
import pytz
_logger = logging.getLogger(__name__)


class ZKTecoAttendance(models.Model):
    _name = 'zkteco_attendance'
    _description = 'zkteco attendance'
    _inherit = "mail.thread"
    
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    attendance_time = fields.Datetime(string="Attendance Time", required=True)
    status = fields.Selection([('in', 'Check In'), ('out', 'Check Out')], string="Status", required=True)
    device_uid = fields.Integer(string="Device UID", required=True, help="Employee ID in Biometric Machine")
    def fetch_attendance(self):
        """Fetch attendance records from the biometric device and store them in Odoo."""
        ip_address = '192.168.1.201'  # Replace with actual IP
        port = 4370  # Default ZKTeco port
        zk = ZK(ip_address, port=port, timeout=10)

        check_in_start = time(8, 0)      # 08:00 AM
        check_in_end = time(12, 00)      # 12:30 PM
        check_out_start = time(15, 0)    # 03:00 PM
        check_out_end = time(23, 59)     # 11:59 PM
        try:
            conn = zk.connect()
            conn.disable_device()  # Prevent punching during sync
            logs = conn.get_attendance()
            users = conn.get_users()

            for user in users:
                print(f"{user.name}")
            
            if not logs:
                _logger.warning("No attendance logs found in the device.")
                conn.enable_device()
                conn.disconnect()
                return

            for log in logs:
                print(f"Fetching attendance: User ID {log.user_id}, Time {log.timestamp}, Status: {log.status}, Punch: {log.punch}")

                atten_time = log.timestamp 

                # Find employee by device_id
                employee = self.env['hr.employee'].search([('biometric_employee_id', '=', log.user_id)], limit=1)
                # _logger.info(f"biometric_employee_id {employee.biometric_employee_id}")

                if employee:
                    _logger.info("Employee Found")
                    # Prevent duplicate records
                    existing_attendance = self.env['hr.attendance'].search([
                        ('employee_id', '=', employee.id),
                        ('check_in', '<=', log.timestamp),
                        ('check_out', '>=', log.timestamp),
                    ], limit=1)

                    # _logger.info(f"Existing attendance records for {employee.name}: {existing_attendance.check_out},{existing_attendance.check_in}")
                    if existing_attendance:
                        _logger.info("Existing Attendace Found For Today")

                    if not existing_attendance:
                        _logger.info("No Existing Attendace For Today")
                        if check_in_start <= atten_time.time() <= check_in_end:  # Check-in
                            _logger.info("Entering in Check In")

                            last_attendance = self.env['hr.attendance'].search([
                                ('employee_id', '=', employee.id),
                                ('check_out', '=', False)
                            ], order="check_in desc", limit=1)
                            _logger.info(f"Last attendance records for {employee.name}: {last_attendance.check_in}, {last_attendance.check_out} ")

                            if last_attendance:
                                _logger.info("Employee already checked in. Skipping duplicate check-in.")

                            if not last_attendance:
                                _logger.info(f"Checking In at {atten_time}")
                                self.env['hr.attendance'].create({
                                    'employee_id': employee.id,
                                    'check_in': atten_time- timedelta(hours=5)
                                })
                        elif check_out_start <= atten_time.time() <= check_out_end:  # Check-out
                            _logger.info("Entering in Check Out")

                            last_attendance = self.env['hr.attendance'].search([
                                ('employee_id', '=', employee.id),
                                ('check_out', '=', False)
                            ], order="check_in desc", limit=1) 
                            _logger.info(f"Last attendance records for {employee.name}: {last_attendance.check_in}, {last_attendance.check_out} ")

                            
                            if last_attendance:
                                
                                _logger.info(f"Checking Out at {atten_time}")
                                last_attendance.write({'check_out': atten_time- timedelta(hours=5)})  # Update check-out time
                            else:
                                _logger.warning("No previous check-in found. Skipping check-out.")
                
    
                    else:
                        _logger.info(f"Skipping duplicate entry for User {log.user_id} at {atten_time}.")
                else:
                    _logger.warning(f"Employee with device ID {log.user_id} not found in Odoo!")

            conn.enable_device()
            conn.disconnect()

        except Exception as e:
            _logger.error(f"Error connecting to biometric device: {str(e)}")
            raise models.ValidationError(f"Error connecting to device: {str(e)}")
    
    def _cron_fetch_attendance(self):
        """
        Cron job method to fetch attendance automatically
        This method will be called by the scheduled action
        """
        try:
            self.fetch_attendance()
            _logger.info("Successfully fetched attendance via cron job")
        except Exception as e:
            _logger.error(f"Cron job failed to fetch attendance: {str(e)}")
    
    
