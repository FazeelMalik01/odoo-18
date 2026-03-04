# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
import logging
import json
import base64
from datetime import timedelta

_logger = logging.getLogger(__name__)


class TechnicianPortal(http.Controller):
    """
    Portal Controller for Technicians to view assigned work orders
    """

    @http.route(['/my/gate_lock_assigned', '/my/gate_lock_assigned/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_technician_work_orders(self, page=1, **kw):
        """
        List view of assigned work orders for technicians
        """
        # Check if user is in technician group
        if not request.env.user.has_group('custom_gatekeeper_security.group_gatekeeper_technician'):
            return request.redirect('/my')

        # Use sudo() to bypass field security for now
        Task = request.env['project.task'].sudo()
        domain = [
            ('user_ids', 'in', [request.env.user.id]),
            ('service_request_id', '!=', False)
        ]

        # Pagination
        tasks_per_page = 20
        total_tasks = Task.search_count(domain)
        pager = request.website.pager(
            url='/my/gate_lock_assigned',
            total=total_tasks,
            page=page,
            step=tasks_per_page,
            scope=7
        )

        tasks = Task.search(
            domain,
            limit=tasks_per_page,
            offset=(page - 1) * tasks_per_page,
            order='date_deadline asc, id desc'
        )

        values = {
            'tasks': tasks,
            'pager': pager,
            'page_name': 'gate_lock_assigned',
        }

        return request.render('custom_gatekeeper_security.portal_technician_work_orders_list', values)

    @http.route(['/my/gate_lock_assigned/<int:task_id>'], type='http', auth='user', website=True)
    def portal_technician_work_order_form(self, task_id, **kw):
        """
        Form view for individual work order
        """
        # Check if user is in technician group
        if not request.env.user.has_group('custom_gatekeeper_security.group_gatekeeper_technician'):
            return request.redirect('/my')

        # Verify the task exists and user is assigned to it
        task = request.env['project.task'].sudo().search([
            ('id', '=', task_id),
            ('user_ids', 'in', [request.env.user.id]),
            ('service_request_id', '!=', False)
        ])

        if not task:
            return request.redirect('/my/gate_lock_assigned')

        # Log timer state when page loads to debug
        _logger.info(f"Page load for task {task_id}: timer_running={task.timer_running}, timer_start={task.timer_start}, elapsed_seconds={task.elapsed_seconds}, allocated_hours={task.allocated_hours}")

        values = {
            'task': task,
            'page_name': 'gate_lock_assigned_detail',
        }

        return request.render('custom_gatekeeper_security.portal_technician_work_order_form', values)

    @http.route(['/my/gate_lock_assigned/<int:task_id>/update'],
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_technician_work_order_update(self, task_id, **post):
        """
        Handle work order updates from technicians
        """
        # Check if user is in technician group
        if not request.env.user.has_group('custom_gatekeeper_security.group_gatekeeper_technician'):
            return request.redirect('/my')

        # Verify the task exists and user is assigned to it
        task = request.env['project.task'].sudo().search([
            ('id', '=', task_id),
            ('user_ids', 'in', [request.env.user.id]),
            ('service_request_id', '!=', False)
        ])

        if not task:
            return request.redirect('/my/gate_lock_assigned')

        # Prepare update values
        update_vals = {}

        # Handle state updates
        if post.get('state'):
            update_vals['state'] = post.get('state')

        # Handle gating status updates
        if post.get('gating_status'):
            update_vals['gating_status'] = post.get('gating_status')

        # Handle deposit status updates
        if post.get('deposit_status'):
            update_vals['deposit_status'] = post.get('deposit_status')

        # Handle text field updates
        if post.get('material_used'):
            update_vals['material_used'] = post.get('material_used')

        if post.get('work_notes'):
            update_vals['work_notes'] = post.get('work_notes')

        if post.get('sms_message'):
            update_vals['sms_message'] = post.get('sms_message')

        # Handle image uploads
        uploaded_attachment_ids = []
        if request.httprequest.files.getlist('work_images'):
            for file_storage in request.httprequest.files.getlist('work_images'):
                if file_storage.filename:
                    try:
                        # Read file content
                        file_data = file_storage.read()
                        # Encode to base64
                        file_base64 = base64.b64encode(file_data).decode('utf-8')
                        
                        # Create attachment
                        attachment = request.env['ir.attachment'].sudo().create({
                            'name': file_storage.filename,
                            'type': 'binary',
                            'datas': file_base64,
                            'res_model': 'project.task',
                            'res_id': task_id,
                            'mimetype': file_storage.content_type or 'image/jpeg',
                        })
                        uploaded_attachment_ids.append(attachment.id)
                        _logger.info(f"Created attachment {attachment.id} for task {task_id}: {file_storage.filename}")
                    except Exception as e:
                        _logger.error(f"Error uploading image {file_storage.filename} for task {task_id}: {str(e)}", exc_info=True)
        
        # Add uploaded images to existing images
        if uploaded_attachment_ids:
            # Get current image IDs
            current_image_ids = task.work_images.ids if task.work_images else []
            # Combine with new uploads (avoid duplicates)
            all_image_ids = list(set(current_image_ids + uploaded_attachment_ids))
            update_vals['work_images'] = [(6, 0, all_image_ids)]
            _logger.info(f"Updated work_images for task {task_id}: {len(uploaded_attachment_ids)} new images, total: {len(all_image_ids)}")

        # Apply updates if any
        if update_vals:
            task.write(update_vals)
            _logger.info(f"Technician {request.env.user.id} updated task {task_id} with values: {update_vals}")

        # Create worksheet with all form data
        try:
            # Get timer hours from form (saved before reset) or from task
            # The form includes saved_timer_hours which was captured before timer reset
            saved_timer_hours = post.get('saved_timer_hours')
            if saved_timer_hours:
                timer_hours_val = float(saved_timer_hours)
            else:
                # Fallback to task timer_hours if not in form
                timer_hours_val = task.timer_hours or 0.0
            
            worksheet_vals = {
                'task_id': task_id,
                'state': post.get('state') or task.state,
                'material_used': post.get('material_used') or task.material_used or '',
                'work_notes': post.get('work_notes') or task.work_notes or '',
                'sms_message': post.get('sms_message') or '',
                'timer_hours': timer_hours_val,
                'allocated_hours': task.allocated_hours or 0.0,
                'technician_id': request.env.user.id,
                'completion_date': fields.Datetime.now(),
            }
            
            _logger.info(f"Creating worksheet for task {task_id} with timer_hours: {timer_hours_val} (from form: {saved_timer_hours is not None})")
            
            # Add work images to worksheet
            if task.work_images:
                worksheet_vals['work_images'] = [(6, 0, task.work_images.ids)]
            
            worksheet = request.env['work.order.worksheet'].sudo().create(worksheet_vals)
            _logger.info(f"Created worksheet {worksheet.name} (ID: {worksheet.id}) for task {task_id}")
            
            # Clear form fields after saving to worksheet (form will be empty on reload)
            clear_vals = {
                'material_used': '',
                'work_notes': '',
                'sms_message': '',
                'work_images': [(5, 0, 0)],  # Clear all work images (they're saved in worksheet)
            }
            task.write(clear_vals)
            _logger.info(f"Cleared form fields and work images for task {task_id} after worksheet creation")
        except Exception as e:
            _logger.error(f"Error creating worksheet for task {task_id}: {str(e)}", exc_info=True)
            # Don't fail the whole save if worksheet creation fails

        # Redirect to list view after saving
        return request.redirect('/my/gate_lock_assigned')

    @http.route('/my/gate_lock_assigned/timer_action', type='http', auth='user', methods=['POST'], csrf=True)
    def technician_timer(self, **post):

        task_id = post.get('task_id')
        action = post.get('action')

        if not task_id:
            return request.redirect('/my')

        task = request.env['project.task'].sudo().browse(int(task_id))
        if not task.exists():
            return request.redirect('/my')

        # Perform the timer action
        if action == 'start':
            # Directly write to ensure it's saved
            timer_start_time = fields.Datetime.now()
            _logger.info(f"About to write timer_start: {timer_start_time} for task {task_id}")
            
            # Write using the task record directly (not sudo on write, but use sudo record)
            task.write({
                'timer_running': True,
                'timer_start': timer_start_time,
            })
            
            # Force flush immediately
            request.env.cr.flush()
            
            # Read back immediately to verify
            task.invalidate_recordset(['timer_running', 'timer_start'])
            _logger.info(f"After write - task_id: {task_id}, timer_running: {task.timer_running}, timer_start: {task.timer_start}, type: {type(task.timer_start)}")
            
        elif action == 'stop':
            task.portal_stop_timer()
        elif action == 'reset':
            task.portal_reset_timer()
        
        # Force flush to ensure changes are in database
        request.env.cr.flush()
        
        # Check if request is AJAX (JSON response expected)
        if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Commit the transaction to ensure changes are saved to database
            request.env.cr.commit()
            
            # Read from database using a fresh cursor
            with request.env.registry.cursor() as new_cr:
                new_env = request.env(cr=new_cr)
                fresh_task = new_env['project.task'].sudo().browse(int(task_id))
                
                # Invalidate to force fresh read
                fresh_task.invalidate_recordset(['timer_running', 'timer_start', 'elapsed_seconds', 'timer_hours'])
                
                # Access the field to trigger recomputation
                timer_hours = fresh_task.timer_hours
                elapsed_seconds_val = int(fresh_task.elapsed_seconds or 0)
                
                # Calculate timer_hours from elapsed_seconds for accuracy (avoid rounding issues)
                # Use elapsed_seconds as source of truth when timer is stopped
                if not fresh_task.timer_running:
                    # Timer is stopped - use elapsed_seconds directly for accuracy
                    calculated_timer_hours = elapsed_seconds_val / 3600.0
                    _logger.info(f"Timer stopped - using elapsed_seconds for accuracy: elapsed_seconds={elapsed_seconds_val}, calculated_timer_hours={calculated_timer_hours}, computed_timer_hours={timer_hours}")
                    timer_hours = calculated_timer_hours
                else:
                    # Timer is running - use computed value (includes current session)
                    _logger.info(f"Timer running - using computed timer_hours: {timer_hours}")
                
                # Log for debugging - log the actual database values
                _logger.info(f"Timer action '{action}' - task_id: {task_id}, timer_hours: {timer_hours}, elapsed_seconds: {elapsed_seconds_val}, timer_running: {fresh_task.timer_running}, timer_start: {fresh_task.timer_start}")
                
                timer_start_str = fields.Datetime.to_string(fresh_task.timer_start) if fresh_task.timer_start else False
                
                return request.make_response(
                    json.dumps({
                        'success': True,
                        'timer_hours': timer_hours,
                        'timer_running': fresh_task.timer_running,
                        'timer_start': timer_start_str,
                        'elapsed_seconds': elapsed_seconds_val,
                    }),
                    headers=[('Content-Type', 'application/json')]
                )

            return request.redirect(f"/my/gate_lock_assigned/{task.id}")

    @http.route('/my/gate_lock_assigned/timer_save', type='http', auth='user', methods=['POST'], csrf=True)
    def timer_save(self, **post):
        """Save timer time to timesheet with description from work notes."""
        import time
        request_id = f"{int(time.time() * 1000)}-{request.env.user.id}"
        
        task_id = post.get('task_id')
        hours = post.get('hours')
        description = post.get('description', 'Timer session')

        _logger.info(f"=== TIMER SAVE REQUEST RECEIVED [ID: {request_id}] ===")
        _logger.info(f"[{request_id}] Request details: task_id={task_id}, hours={hours}, description={description}")
        _logger.info(f"[{request_id}] User: {request.env.user.name} (ID: {request.env.user.id})")
        _logger.info(f"[{request_id}] Request timestamp: {fields.Datetime.now()}")

        if not task_id or not hours:
            _logger.warning(f"[{request_id}] Missing task_id or hours in timer_save request")
            return request.make_response(
                json.dumps({'success': False, 'error': 'Missing task_id or hours'}),
                headers=[('Content-Type', 'application/json')]
            )

        try:
            task = request.env['project.task'].sudo().browse(int(task_id))
            if not task.exists():
                _logger.warning(f"[{request_id}] Task {task_id} not found in timer_save")
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Task not found'}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Check existing timesheet entries before creating (additional check at controller level)
            try:
                rounded_hours = round(float(hours), 2)
                existing_entries = request.env['account.analytic.line'].sudo().search_count([
                    ('task_id', '=', task.id),
                    ('date', '=', fields.Date.today()),
                    ('unit_amount', '=', rounded_hours),
                    ('create_date', '>=', fields.Datetime.now() - timedelta(seconds=30))
                ])
                _logger.info(f"[{request_id}] Existing timesheet entries for today with same hours ({rounded_hours}): {existing_entries}")
                
                if existing_entries > 0:
                    _logger.warning(f"[{request_id}] Duplicate timesheet entry already exists. Skipping creation.")
                    return request.make_response(
                        json.dumps({'success': True, 'message': 'Timesheet entry already exists'}),
                        headers=[('Content-Type', 'application/json')]
                    )
            except Exception as e:
                _logger.warning(f"[{request_id}] Error checking for duplicates: {str(e)}")

            # Create timesheet entry
            _logger.info(f"[{request_id}] Calling portal_save_timesheet for task {task_id} with {hours} hours")
            result = task.portal_save_timesheet(float(hours), description, request.env.user)
            
            if result:
                request.env.cr.commit()
                
                # Check timesheet entries after creation
                entries_after = request.env['account.analytic.line'].sudo().search_count([
                    ('task_id', '=', task.id),
                    ('date', '=', fields.Date.today()),
                    ('name', '=', description or 'Timer session')
                ])
                _logger.info(f"[{request_id}] Timesheet entries after creation: {entries_after} (was {existing_entries})")
                _logger.info(f"[{request_id}] Timesheet entry created successfully for task {task_id}")
                
                return request.make_response(
                    json.dumps({'success': True}),
                    headers=[('Content-Type', 'application/json')]
                )
            else:
                _logger.warning(f"[{request_id}] Failed to create timesheet entry for task {task_id}")
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Failed to create timesheet entry'}),
                    headers=[('Content-Type', 'application/json')]
                )
        except Exception as e:
            _logger.error(f"[{request_id}] Error saving timesheet: {str(e)}", exc_info=True)
            return request.make_response(
                json.dumps({'success': False, 'error': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )