from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class ProjectTaskQualityCheckProblemImage(models.Model):
    """Model to store multiple images of problem"""
    _name = 'project.task.quality.check.problem.image'
    _description = 'Quality Check Problem Image'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade')
    image = fields.Binary(string='Image', required=True)
    image_filename = fields.Char(string='Image Filename')


class ProjectTaskQualityCheckAfterImage(models.Model):
    """Model to store multiple images after problem solved"""
    _name = 'project.task.quality.check.after.image'
    _description = 'Quality Check After Problem Solved Image'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade')
    image = fields.Binary(string='Image', required=True)
    image_filename = fields.Char(string='Image Filename')


class ProjectTask(models.Model):
    """Extend project.task model with quality check fields"""
    _inherit = 'project.task'

    # Quality Check Fields - Direct fields on task
    quality_check_state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Quality Check Status',
        tracking=True
    )
    quality_check_description = fields.Text(string='Description')
    quality_check_optical_power = fields.Selection(
        selection=[
            ('value1', 'Value 1'),
            ('value2', 'Value 2'),
            ('value3', 'Value 3'),
            ('value4', 'Value 4'),
        ],
        string='Optical Power Values'
    )
    quality_check_dns_setting = fields.Boolean(string='DNS Setting', default=False)
    
    field_service_manager_id = fields.Many2one(
        'res.users',
        string='Field Service Manager',
        help='Select a Field Service Manager from the Field Service Manager group',
    )
    
    # Date tracking fields
    task_creation_date = fields.Datetime(string='Creation Date', readonly=True, default=fields.Datetime.now, help='Date when the task was created')
    task_completion_date = fields.Datetime(string='Completion Date', readonly=True, help='Date when the task was marked as done')
    
    # Quality Check Image Fields - One2many relationships
    quality_check_problem_images = fields.One2many(
        'project.task.quality.check.problem.image',
        'task_id',
        string='Images of Problem'
    )
    quality_check_after_problem_images = fields.One2many(
        'project.task.quality.check.after.image',
        'task_id',
        string='Pictures after Problem Solved'
    )
    
    # Computed fields for list view display
    quality_check_problem_images_count = fields.Integer(
        string='Problem Images Count',
        compute='_compute_quality_check_images_count',
        store=False
    )
    
    quality_check_after_images_count = fields.Integer(
        string='After Images Count',
        compute='_compute_quality_check_images_count',
        store=False
    )
    
    # Stored computed fields for search/filter
    has_problem_images = fields.Boolean(
        string='Has Problem Images',
        compute='_compute_has_images',
        store=True
    )
    
    has_after_images = fields.Boolean(
        string='Has After Images',
        compute='_compute_has_images',
        store=True
    )

    # Daily Fiber Usage & Work Record fields
    # Header information
    daily_fiber_company_project = fields.Char(string='Company/Project Name')
    daily_fiber_technician_name = fields.Char(string='Technician Name')
    daily_fiber_date = fields.Date(string='Date')

    # 1. Fiber used today
    daily_fiber_total_length_m = fields.Float(string='Total Length Used (Meters)')
    daily_fiber_start_point = fields.Char(string='Starting Point (Location)')
    daily_fiber_end_point = fields.Char(string='Ending Point (Location)')
    daily_fiber_purpose = fields.Char(string='Purpose of Use')

    # 2. Work location details
    daily_fiber_area_street = fields.Char(string='Area/Street Worked')
    daily_fiber_landmark = fields.Char(string='Specific Spot / Landmark')
    daily_fiber_work_type = fields.Selection(
        selection=[
            ('new_installation', 'New Installation'),
            ('maintenance', 'Maintenance'),
            ('repair', 'Repair'),
            ('replacement', 'Replacement'),
            ('splicing', 'Splicing'),
        ],
        string='Type of Work'
    )

    # 3. Pole (NguZO) information
    daily_fiber_pole_number = fields.Char(string='Pole Number / Identifier')
    daily_fiber_gps_location = fields.Char(string='GPS Location')
    daily_fiber_pole_condition = fields.Char(string='Condition of Pole')
    daily_fiber_pole_notes = fields.Text(string='Pole Notes')

    # 4. Remarks / additional notes
    daily_fiber_remarks = fields.Text(string='Remarks / Additional Notes')

    # 5. Daily confirmation
    daily_fiber_technician_signature = fields.Char(string='Technician Signature')
    daily_fiber_supervisor_signature = fields.Char(string='Supervisor Signature')
    daily_fiber_signed_date = fields.Date(string='Date Signed')

    # 6. For office use only
    daily_fiber_verified_by = fields.Char(string='Verified By')
    daily_fiber_verified_date = fields.Date(string='Verification Date')
    daily_fiber_office_comments = fields.Text(string='Office Comments')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to capture creation date"""
        for vals in vals_list:
            if 'task_creation_date' not in vals:
                vals['task_creation_date'] = fields.Datetime.now()
        return super(ProjectTask, self).create(vals_list)
    
    def write(self, vals):
        """Override write to capture completion date when task is marked as done"""
        # Check if stage is being changed to a "Done" stage
        if 'stage_id' in vals:
            stage = self.env['project.task.type'].browse(vals['stage_id'])
            # Check if the stage is marked as "done" - check fold field (fold=True means done/closed)
            # Also check if stage name contains "done" (case insensitive)
            stage_is_done = stage.fold or 'done' in (stage.name or '').lower()
            
            if stage_is_done:
                # Set completion date for tasks that don't have it yet
                tasks_to_complete = self.filtered(lambda t: not t.task_completion_date)
                if tasks_to_complete:
                    # Write completion date only to tasks that need it
                    tasks_to_complete.write({'task_completion_date': fields.Datetime.now()})
                    # Remove from vals to avoid double write
            else:
                # If moving away from done stage, optionally clear completion date
                # (You might want to keep the date even if moved back, so this is optional)
                pass
        
        return super(ProjectTask, self).write(vals)
    
    @api.depends('quality_check_problem_images', 'quality_check_after_problem_images')
    def _compute_quality_check_images_count(self):
        for task in self:
            task.quality_check_problem_images_count = len(task.quality_check_problem_images)
            task.quality_check_after_images_count = len(task.quality_check_after_problem_images)
    
    @api.depends('quality_check_problem_images', 'quality_check_after_problem_images')
    def _compute_has_images(self):
        for task in self:
            task.has_problem_images = bool(task.quality_check_problem_images)
            task.has_after_images = bool(task.quality_check_after_problem_images)
    
    def action_quality_check_approve(self):
        """Approve the quality check"""
        self.write({'quality_check_state': 'approved'})
        return True
    
    def action_quality_check_reject(self):
        """Reject the quality check"""
        self.write({'quality_check_state': 'rejected'})
        return True
    
    def action_fsm_validate(self, stop_running_timers=False):
        """Override to also set stage to Done when marking task as done"""
        result = super(ProjectTask, self).action_fsm_validate(stop_running_timers=stop_running_timers)
        
        # If result is a wizard (dict), return it - don't change stage yet
        if isinstance(result, dict):
            return result
        
        # Find the "Done" stage for each task's project
        for task in self:
            # First, try to find stage with exact name "Done" in the project
            done_stage = self.env['project.task.type'].search([
                ('project_ids', 'in', [task.project_id.id] if task.project_id else []),
                ('name', '=', 'Done')
            ], limit=1)
            
            # If not found, search for stage with name containing "done" (but not "cancelled")
            if not done_stage:
                done_stage = self.env['project.task.type'].search([
                    ('project_ids', 'in', [task.project_id.id] if task.project_id else []),
                    ('name', 'ilike', 'done'),
                    ('name', 'not ilike', 'cancelled')
                ], limit=1, order='sequence desc')
            
            # If still not found in project, search globally for exact "Done" name
            if not done_stage:
                done_stage = self.env['project.task.type'].search([
                    ('name', '=', 'Done')
                ], limit=1)
            
            # If still not found, search globally for "done" (but not "cancelled")
            if not done_stage:
                done_stage = self.env['project.task.type'].search([
                    ('name', 'ilike', 'done'),
                    ('name', 'not ilike', 'cancelled')
                ], limit=1, order='sequence desc')
            
            # Set the stage to done if found (completion date will be set by write method)
            if done_stage:
                task.write({'stage_id': done_stage.id})
            else:
                # If no done stage found, just set completion date directly
                if not task.task_completion_date:
                    task.write({'task_completion_date': fields.Datetime.now()})
        
        return result
    
    def action_print_pdf(self):
        """Print PDF report for selected tasks"""
        if not self:
            raise UserError("Please select at least one task to print.")
        
        # Return the report action
        return self.env.ref('custom_field_service.action_task_report_pdf').report_action(self)