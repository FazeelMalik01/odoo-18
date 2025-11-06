# from odoo import models, fields, api
# import logging
# from zk import ZK

# _logger = logging.getLogger(__name__)

# class RegisterEmployeeInBiometric(models.Model):
#     _inherit = "hr.employee"

#     biometric_employee_id = fields.Char(
#         string="Biometric Employee ID", 
#         help="Stores the employee's ID in the biometric machine."
#     )

#     def _register_employee_in_biometric(self):
#         """ Registers the employee in the ZKTeco biometric machine """
#         ip_address = '192.168.1.201'  # Update with your device's IP
#         port = 4370  # Default ZKTeco port
#         zk = ZK(ip_address, port=port, timeout=10)

#         try:
#             conn = zk.connect()
#             if not conn:
#                 _logger.error("ZKTeco Connection Failed: Unable to establish connection.")
#                 return
            
#             conn.disable_device()
#             conn.set_user(
#                 uid=int(self.id), 
#                 name=self.name, 
#                 privilege=0, 
#                 password='', 
#                 card=0
#             )
#             _logger.info(f"Employee {self.name} registered in ZKTeco with ID {self.id}")

#         except Exception as e:
#             _logger.error(f"Failed to register {self.name} in ZKTeco: {str(e)}")

#         finally:
#             if 'conn' in locals() and conn:
#                 conn.enable_device()
#                 conn.disconnect()

#     # @api.model
#     # def create(self, vals):
#     #     _logger.info(f"Registering Employee: {vals}")
#     #     employees = super(RegisterEmployeeInBiometric, self).create(vals)
        
#     #     for employee in employees:
#     #         try:
#     #             employee._register_employee_in_biometric()
#     #             employee.biometric_employee_id = str(employee.id)  # Ensure it's stored as a string
#     #         except Exception as e:
#     #             _logger.error(f"Error registering employee {employee.name}: {e}")

#     #     return employees
#     @api.model_create_multi
#     def create(self, vals_list):
#         _logger.info(f"Registering Employees: {vals_list}")
        
#         employees = super(RegisterEmployeeInBiometric, self).create(vals_list)
        
#         for employee in employees:
#             try:
#                 employee._register_employee_in_biometric()
#                 employee.biometric_employee_id = str(employee.id)  # Ensure it's stored as a string
#             except Exception as e:
#                 _logger.error(f"Error registering employee {employee.name}: {e}")

#         return employees


# Fix for demo data registration error in ZKTeco module

from odoo import models, fields, api
import logging
from zk import ZK
import os

_logger = logging.getLogger(__name__)

class RegisterEmployeeInBiometric(models.Model):
    _inherit = "hr.employee"

    biometric_employee_id = fields.Char(
        string="Biometric Employee ID", 
        help="Stores the employee's ID in the biometric machine."
    )

    def _should_skip_biometric_registration(self):
        """
        Determine if biometric registration should be skipped (e.g. on demo or install)
        """
        return (
            self.env.context.get('install_mode') or
            self.env.context.get('demo') or
            os.environ.get('ON_ODOO_SH') == '1'
        )

    def _register_employee_in_biometric(self):
        if self._should_skip_biometric_registration():
            _logger.info(f"Skipping biometric registration for {self.name} due to install/demo mode or Odoo.sh.")
            return

        ip_address = '192.168.1.201'
        port = 4370
        zk = ZK(ip_address, port=port, timeout=10, omit_ping=True)

        try:
            conn = zk.connect()
            if not conn:
                _logger.error("ZKTeco Connection Failed: Unable to establish connection.")
                return
            
            conn.disable_device()
            conn.set_user(
                uid=int(self.id), 
                name=self.name, 
                privilege=0, 
                password='', 
                card=0
            )
            _logger.info(f"Employee {self.name} registered in ZKTeco with ID {self.id}")

        except Exception as e:
            _logger.error(f"Failed to register {self.name} in ZKTeco: {str(e)}")

        finally:
            if 'conn' in locals() and conn:
                conn.enable_device()
                conn.disconnect()

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info(f"Registering Employees: {vals_list}")
        employees = super(RegisterEmployeeInBiometric, self).create(vals_list)

        for employee in employees:
            try:
                employee._register_employee_in_biometric()
                employee.biometric_employee_id = str(employee.id)
            except Exception as e:
                _logger.error(f"Error registering employee {employee.name}: {e}")

        return employees
