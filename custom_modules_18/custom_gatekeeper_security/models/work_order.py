from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Link back to service request & sale order
    service_request_id = fields.Many2one(
        'service.request',
        string='Service Request',
        ondelete='set null',
        index=True
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Related Sale Order',
        ondelete='set null',
        index=True
    )

    # Secure Notes (security restricted)
    secure_notes = fields.Text(
        string='Secure Notes',
        groups='custom_gatekeeper_security.group_service_secure_notes'
    )

    # Photos (attachments)
    photo_ids = fields.One2many(
        'ir.attachment', 'res_id',
        string='Photos',
        domain=[('res_model', '=', 'project.task')]
    )

    # Customer SMS Thread
    sms_thread = fields.Text(string="Customer SMS Thread")

    # Estimate Reference
    estimate_id = fields.Many2one('sale.order', string='Estimate / Quotation')

    # Deposit Status
    deposit_status = fields.Selection([
        ('not_requested', 'Not Requested'),
        ('requested', 'Requested'),
        ('paid', 'Paid'),
    ], string='Deposit Status', default='not_requested')

    # Gating Status
    gating_status = fields.Selection([
        ('pending', 'Pending'),
        ('blocked', 'Blocked'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
    ], string="Gating Status", default='pending')

    # Editable by technician
    work_images = fields.Many2many('ir.attachment', 'work_order_images_rel', 'task_id', 'attachment_id', 
                                   string="Work Images", copy=False, help="Images uploaded by technician")
    material_used = fields.Text(string="Material Used")
    work_notes = fields.Text(string="Work Notes")
    sms_message = fields.Text(string="SMS Update")
    
    # Worksheets
    worksheet_ids = fields.One2many('work.order.worksheet', 'task_id', string='Worksheets')
    worksheet_count = fields.Integer(string='Worksheet Count', compute='_compute_worksheet_count')
    
    @api.depends('worksheet_ids')
    def _compute_worksheet_count(self):
        for task in self:
            task.worksheet_count = len(task.worksheet_ids)

    # Timer fields for accurate time tracking
    timer_running = fields.Boolean(string="Timer Running", default=False, copy=False, store=True)
    timer_start = fields.Datetime(string="Timer Start Time", copy=False, store=True)
    elapsed_seconds = fields.Integer(string="Elapsed Seconds", default=0, copy=False, store=True, help="Total elapsed seconds recorded (previous sessions)")

    # Allocated hours - manually set field (NOT affected by timer)
    allocated_hours = fields.Float(string="Allocated Hours", default=0.0, copy=False, store=True, help="Manually allocated hours for this task (not affected by timer)")
    
    # Timer hours - computed from timer (separate from allocated_hours)
    timer_hours = fields.Float(string="Timer Hours", compute='_compute_timer_hours', store=True, help="Hours tracked by timer (elapsed_seconds + current session)")

    @api.depends('elapsed_seconds', 'timer_running', 'timer_start')
    def _compute_timer_hours(self):
        """Timer hours = elapsed_seconds/3600 + running session if any"""
        import logging
        _logger = logging.getLogger(__name__)
        
        for task in self:
            total_secs = task.elapsed_seconds or 0
            if task.timer_running and task.timer_start:
                # compute additional seconds between timer_start and now
                try:
                    # parse server timezone aware
                    fmt = DEFAULT_SERVER_DATETIME_FORMAT
                    start_dt = fields.Datetime.from_string(task.timer_start)
                    now_dt = fields.Datetime.context_timestamp(task, fields.Datetime.now())
                    # difference in seconds
                    delta = (fields.Datetime.to_datetime(now_dt) - fields.Datetime.to_datetime(
                        start_dt)).total_seconds()
                except Exception:
                    delta = 0
                total_secs += int(delta)
            
            # Use more precision to avoid rounding errors (round to 6 decimal places for accuracy)
            # This ensures seconds are preserved accurately
            task.timer_hours = round((total_secs / 3600.0), 6)
            
            _logger.debug(f"_compute_timer_hours for task {task.id}: elapsed_seconds={task.elapsed_seconds}, timer_running={task.timer_running}, total_secs={total_secs}, timer_hours={task.timer_hours}")

    # -------- Portal-safe timer actions used by controller ----------
    def portal_start_timer(self):
        """Start timer — called from portal. Records server start time and marks running."""
        import logging
        _logger = logging.getLogger(__name__)
        
        self = self.sudo()
        for task in self:
            if not task.timer_running:
                timer_start_time = fields.Datetime.now()
                _logger.info(f"Attempting to start timer for task {task.id} with start_time: {timer_start_time}")
                
                # Use write() to ensure the values are saved
                task.write({
                    'timer_running': True,
                    'timer_start': timer_start_time,
                })
                
                # Force flush to ensure write is processed
                self.env.cr.flush()
                
                # Invalidate cache to force reload
                task.invalidate_recordset(['timer_running', 'timer_start'])
                
                # Log to verify the write - read values after write
                _logger.info(f"Timer started for task {task.id}: timer_running={task.timer_running}, timer_start={task.timer_start}, elapsed_seconds={task.elapsed_seconds}")
        return True

    def portal_stop_timer(self):
        """Stop timer: compute session seconds, accumulate, create timesheet entry, and stop."""
        import logging
        _logger = logging.getLogger(__name__)
        
        # Preserve the user context before using sudo
        current_user = self.env.user
        
        self = self.sudo()
        for task in self:
            if task.timer_running and task.timer_start:
                try:
                    start_dt = fields.Datetime.from_string(task.timer_start)
                    # convert now to server datetime
                    now_dt = fields.Datetime.now()
                    delta = (fields.Datetime.to_datetime(now_dt) - fields.Datetime.to_datetime(
                        start_dt)).total_seconds()
                    add_seconds = int(delta)
                except Exception:
                    add_seconds = 0
                
                # Update elapsed seconds and stop timer
                task.write({
                    'elapsed_seconds': (task.elapsed_seconds or 0) + add_seconds,
                    'timer_running': False,
                    'timer_start': False,
                })
                
                # Create timesheet entry if time was recorded
                if add_seconds > 0:
                    self._create_timesheet_entry(task, add_seconds, start_dt, current_user)
        
        return True
    
    def _get_dispatcher_employee(self):
        """Get an employee from the dispatcher group."""
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            # Find dispatcher group
            dispatcher_group = self.env['res.groups'].sudo().search([
                ('name', '=', 'Dispatcher')
            ], limit=1)
            
            if not dispatcher_group:
                _logger.error("Dispatcher group not found. Please upgrade the module to create the 'Dispatcher' group, then add a user with an employee record to it.")
                return self.env['hr.employee']  # Return empty recordset
            
            # Find employees in the dispatcher group
            dispatcher_users = dispatcher_group.users
            if not dispatcher_users:
                _logger.error("No users found in Dispatcher group. Please add at least one user to the Dispatcher group (Settings → Users & Companies → Groups → Dispatcher).")
                return self.env['hr.employee']  # Return empty recordset
            
            # Get employee for any dispatcher user
            for dispatcher_user in dispatcher_users:
                employee = self.env['hr.employee'].sudo().search([
                    ('user_id', '=', dispatcher_user.id),
                    ('active', '=', True)
                ], limit=1)
                if employee:
                    _logger.info(f"Found dispatcher employee: {employee.name} (ID: {employee.id})")
                    return employee
            
            _logger.error("No active employee found for users in Dispatcher group. Please ensure the user in the Dispatcher group has an associated employee record in HR.")
            return self.env['hr.employee']  # Return empty recordset
            
        except Exception as e:
            _logger.error(f"Error getting dispatcher employee: {str(e)}", exc_info=True)
            return self.env['hr.employee']  # Return empty recordset
    
    def _get_user_employee(self, user):
        """Get employee record for a given user."""
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            if not user:
                _logger.error("No user provided to _get_user_employee")
                return self.env['hr.employee']
            
            employee = self.env['hr.employee'].sudo().search([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ], limit=1)
            
            if employee:
                _logger.info(f"Found employee for user {user.name}: {employee.name} (ID: {employee.id})")
                return employee
            else:
                _logger.error(f"No active employee found for user {user.name} (ID: {user.id}). Please ensure the user has an associated employee record in HR.")
                return self.env['hr.employee']
        except Exception as e:
            _logger.error(f"Error getting employee for user {user.name if user else 'None'}: {str(e)}", exc_info=True)
            return self.env['hr.employee']
    
    def _create_timesheet_entry(self, task, seconds, start_datetime, user):
        """Create a timesheet entry for the timer session."""
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            # Get employee for the current user (technician)
            employee = task._get_user_employee(user)
            
            if not employee or not employee.exists():
                _logger.error(f"No employee found for user {user.name if user else 'None'}. Cannot create timesheet entry. Please ensure the user has an associated employee record in HR.")
                return False
            
            # Calculate hours from seconds
            hours = round(seconds / 3600.0, 2)
            
            # Get project from task
            project = task.project_id
            if not project:
                _logger.warning(f"Task {task.id} has no project. Cannot create timesheet entry.")
                return False
            
            # Create timesheet entry
            timesheet_vals = {
                'project_id': project.id,
                'task_id': task.id,
                'employee_id': employee.id,
                'name': f'Timer session - {task.name}',
                'unit_amount': hours,
                'date': fields.Date.today(),
            }
            
            # Try to get analytic account from project (if field exists)
            try:
                if hasattr(project, 'analytic_account_id') and project.analytic_account_id:
                    timesheet_vals['account_id'] = project.analytic_account_id.id
                elif hasattr(project, 'analytic_account_id') and not project.analytic_account_id:
                    _logger.warning(f"Project {project.id} has no analytic account. Timesheet entry will be created without it.")
            except AttributeError:
                # Field doesn't exist on project model, skip it
                _logger.info(f"Project model doesn't have analytic_account_id field. Creating timesheet without it.")
            
            timesheet = self.env['account.analytic.line'].sudo().create(timesheet_vals)
            _logger.info(f"Created timesheet entry {timesheet.id} for task {task.id}: {hours} hours (employee: {employee.name})")
            
            return True
            
        except Exception as e:
            _logger.error(f"Error creating timesheet entry for task {task.id}: {str(e)}", exc_info=True)
            return False
    
    def portal_save_timesheet(self, hours, description, user):
        """Save timer time to timesheet with custom description."""
        import logging
        import time
        _logger = logging.getLogger(__name__)
        
        save_id = f"{int(time.time() * 1000)}-{self.id}"
        _logger.info(f"=== portal_save_timesheet CALLED [ID: {save_id}] ===")
        _logger.info(f"[{save_id}] Parameters: task_id={self.id}, hours={hours}, description={description}, user={user.name}")
        _logger.info(f"[{save_id}] Call timestamp: {fields.Datetime.now()}")
        
        self = self.sudo()
        self.ensure_one()
        
        try:
            # Check for duplicate entries created in the last 30 seconds (prevent double-save)
            # Check by task_id, date, and unit_amount (hours) - more reliable than description
            check_time = fields.Datetime.now() - timedelta(seconds=30)
            _logger.info(f"[{save_id}] Checking for duplicates created after: {check_time}")
            
            # Round hours to 2 decimal places for comparison (avoid floating point issues)
            rounded_hours = round(float(hours), 2)
            
            recent_entries = self.env['account.analytic.line'].sudo().search([
                ('task_id', '=', self.id),
                ('date', '=', fields.Date.today()),
                ('unit_amount', '=', rounded_hours),
                ('create_date', '>=', check_time)
            ], order='create_date desc', limit=1)
            
            _logger.info(f"[{save_id}] Checking for duplicates: task_id={self.id}, date={fields.Date.today()}, hours={rounded_hours}")
            _logger.info(f"[{save_id}] Found {len(recent_entries)} recent entries within last 30 seconds with same hours")
            
            if recent_entries:
                for entry in recent_entries:
                    _logger.info(f"[{save_id}] Recent entry: ID={entry.id}, hours={entry.unit_amount}, created={entry.create_date}, description={entry.name}")
            
            if recent_entries:
                _logger.warning(f"[{save_id}] Duplicate timesheet entry detected for task {self.id} within last 30 seconds (entry ID: {recent_entries[0].id}, hours={rounded_hours}). Skipping creation to prevent duplicates.")
                return True  # Return True to indicate "success" (entry already exists)
            
            # Get employee for the current user (technician)
            employee = self._get_user_employee(user)
            
            if not employee or not employee.exists():
                _logger.error(f"[{save_id}] No employee found for user {user.name if user else 'None'}. Cannot create timesheet entry. Please ensure the user has an associated employee record in HR.")
                return False
            
            # Get project from task
            project = self.project_id
            if not project:
                _logger.warning(f"Task {self.id} has no project. Cannot create timesheet entry.")
                return False
            
            # Create timesheet entry
            # Round hours to 2 decimal places to match duplicate check
            rounded_hours = round(float(hours), 2)
            timesheet_vals = {
                'project_id': project.id,
                'task_id': self.id,
                'employee_id': employee.id,
                'name': description or 'Timer session',
                'unit_amount': rounded_hours,
                'date': fields.Date.today(),
            }
            
            # Try to get analytic account from project (if field exists)
            try:
                if hasattr(project, 'analytic_account_id') and project.analytic_account_id:
                    timesheet_vals['account_id'] = project.analytic_account_id.id
                elif hasattr(project, 'analytic_account_id') and not project.analytic_account_id:
                    _logger.warning(f"Project {project.id} has no analytic account. Timesheet entry will be created without it.")
            except AttributeError:
                # Field doesn't exist on project model, skip it
                _logger.info(f"Project model doesn't have analytic_account_id field. Creating timesheet without it.")
            
            _logger.info(f"[{save_id}] Creating timesheet entry with values: {timesheet_vals}")
            timesheet = self.env['account.analytic.line'].sudo().create(timesheet_vals)
            _logger.info(f"[{save_id}] Created timesheet entry ID: {timesheet.id} for task {self.id}: {hours} hours (employee: {employee.name}, description: {description})")
            _logger.info(f"[{save_id}] Timesheet entry created at: {timesheet.create_date}")
            
            # Verify the entry was created
            created_entry = self.env['account.analytic.line'].sudo().browse(timesheet.id)
            if created_entry.exists():
                _logger.info(f"[{save_id}] Verification: Timesheet entry {timesheet.id} exists in database")
            else:
                _logger.error(f"[{save_id}] Verification FAILED: Timesheet entry {timesheet.id} does not exist in database!")
            
            return True
            
        except Exception as e:
            _logger.error(f"Error creating timesheet entry for task {self.id}: {str(e)}", exc_info=True)
            return False

    def portal_reset_timer(self):
        """Reset timer fully to zero."""
        self = self.sudo()
        for task in self:
            task.write({
                'elapsed_seconds': 0,
                'timer_running': False,
                'timer_start': False,
            })
        return True

    # small helper to return timer payload
    def get_timer_payload(self):
        self.ensure_one()
        return {
            'timer_running': bool(self.timer_running),
            'timer_start': fields.Datetime.to_string(self.timer_start) if self.timer_start else False,
            'elapsed_seconds': int(self.elapsed_seconds or 0),
            'allocated_hours': float(self.allocated_hours or 0.0),
        }