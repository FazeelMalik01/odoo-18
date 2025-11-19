import re
import json
from odoo import http
from odoo.http import request
from odoo.osv import expression
import uuid
import base64
import logging

_logger = logging.getLogger(__name__)

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class PortalProgressReport(ProjectCustomerPortal):

    @http.route(['/my/progress_reports'], type='http', auth='user', website=True)
    def portal_my_progress_reports(self, **kw):
        Progress = request.env['custom.progress.report'].sudo()
        # Allow Daily Report Reviewer group and specific users to see all reports, others see only their own
        has_reviewer_access = request.env.user.has_group('custom_progress_report.group_daily_report_reviewer')
        if has_reviewer_access or request.env.user.email in ['saleh.hassouna@gmail.com', 'saleh@abuhayan.com']:
            domain = []
        else:
            domain = [('user_id', '=', request.env.user.id)]

        # Group by batch id (each submission)
        batches = Progress.read_group(
            domain,
            ['report_batch_id', 'date:max(date)'],
            ['report_batch_id']
        )

        grouped_list = []
        for batch in batches:
            label = batch.get('date', '') or batch.get('date:max(date)', '') or ''
            batch_domain = batch.get('__domain', [])
            records = Progress.search(batch_domain, order='id desc')
            grouped_list.append({
                'label': label,
                'records': records,
            })

        # 🧠 Sort newest first using date
        grouped_list.sort(key=lambda x: x['label'], reverse=True)

        return request.render('custom_progress_report.portal_my_progress_reports', {
            'grouped_reports': grouped_list,
        })

    @http.route(['/my/progress_reports/create'], type='http', auth='user', website=True, methods=['POST'])
    def create_progress_report(self, **post):
        task_ids = request.httprequest.form.getlist('task_ids[]')
        main_task_ids = request.httprequest.form.getlist('main_task_ids[]')
        planned_quantities = request.httprequest.form.getlist('planned_quantities[]')
        done_quantities = request.httprequest.form.getlist('done_quantities[]')  # ✅ new
        units = request.httprequest.form.getlist('units[]')
        task_descriptions = request.httprequest.form.getlist('task_descriptions[]')
        
        # Timesheet data
        timesheet_dates = request.httprequest.form.getlist('timesheet_dates[]')
        timesheet_employee_ids = request.httprequest.form.getlist('timesheet_employee_ids[]')
        timesheet_hours = request.httprequest.form.getlist('timesheet_hours[]')
        timesheet_workers = request.httprequest.form.getlist('timesheet_workers[]')
        timesheet_descriptions = request.httprequest.form.getlist('timesheet_descriptions[]')
        
        # We'll fetch files per row index: task_images_0, task_images_1, ...

        # Get single project_id and date (shared for all tasks)
        project_id = post.get('project_id')
        date = post.get('date')
        user_id = request.env.user.id

        batch_id = str(uuid.uuid4())
        
        # Get project for timesheet creation
        project = None
        if project_id:
            project = request.env['project.project'].sudo().browse(int(project_id))

        # Process all rows (handle both main tasks and subtasks)
        max_rows = max(len(task_ids), len(main_task_ids))
        
        for i in range(max_rows):
            # Get task_id (subtask) and main_task_id for this row
            task_id = task_ids[i] if i < len(task_ids) else None
            main_task_id = main_task_ids[i] if i < len(main_task_ids) else None
            
            # Determine which task to use for progress report and timesheet
            # If subtask is selected, use subtask; otherwise use main task
            report_task_id = task_id if task_id else main_task_id
            
            if not report_task_id:
                continue
            
            # Determine which task to use for timesheet
            # Logic: If subtask is selected, add timesheet to subtask; if only main task, add to main task
            timesheet_task_id = task_id if task_id else main_task_id

            # Handle multiple images (up to 10) for this task row
            image_records = []
            try:
                # Get all files for this row (format: task_images_{row_index}_0[])
                file_objects = request.httprequest.files.getlist(f'task_images_{i}_0[]')
                
                for file_idx, file_obj in enumerate(file_objects[:10]):  # Limit to 10 images
                    if file_obj is not None:
                        filename = getattr(file_obj, 'filename', '') or ''
                        if filename.strip():
                            file_bytes = file_obj.read() or b''
                            if file_bytes:
                                image_b64 = base64.b64encode(file_bytes).decode('utf-8')
                                image_mimetype = getattr(file_obj, 'mimetype', None) or getattr(file_obj, 'content_type', None) or 'image/jpeg'
                                
                                image_records.append({
                                    'image': image_b64,
                                    'image_mimetype': image_mimetype,
                                    'sequence': file_idx,
                                })
            except Exception as e:
                # If error occurs, continue without images
                pass

            # Get first image for backward compatibility (task_image field)
            first_image_b64 = False
            first_image_mimetype = False
            if image_records:
                first_image_b64 = image_records[0]['image']
                first_image_mimetype = image_records[0]['image_mimetype']

            progress_report = request.env['custom.progress.report'].sudo().create({
                'task_name': int(report_task_id),
                'task_description': task_descriptions[i] if i < len(task_descriptions) else '',
                'date': date,
                'done_quantity': done_quantities[i] if i < len(done_quantities) else 0.0,
                'planned_quantity': planned_quantities[i] if i < len(planned_quantities) else 0.0,
                'unit': units[i] if i < len(units) else '',
                'task_image': first_image_b64,  # Keep for backward compatibility
                'task_image_mimetype': first_image_mimetype,  # Keep for backward compatibility
                'user_id': user_id,
                'report_batch_id': batch_id,
            })

            # Create image records
            if image_records:
                for img_data in image_records:
                    request.env['custom.progress.report.image'].sudo().create({
                        'progress_report_id': progress_report.id,
                        'image': img_data['image'],
                        'image_mimetype': img_data['image_mimetype'],
                        'sequence': img_data['sequence'],
                    })
            
            # Create timesheet entry if timesheet data is provided
            if timesheet_task_id and i < len(timesheet_dates) and timesheet_dates[i]:
                timesheet_date = timesheet_dates[i]
                timesheet_employee_id = timesheet_employee_ids[i] if i < len(timesheet_employee_ids) else None
                timesheet_hour = timesheet_hours[i] if i < len(timesheet_hours) else None
                timesheet_worker = timesheet_workers[i] if i < len(timesheet_workers) else 1
                timesheet_desc = timesheet_descriptions[i] if i < len(timesheet_descriptions) else ''
                
                # Only create timesheet if required fields are present
                if timesheet_date and timesheet_employee_id and timesheet_hour and float(timesheet_hour) > 0:
                    try:
                        # Convert days to hours (1 day = 8 working hours)
                        timesheet_hours_value = float(timesheet_hour) * 8.0
                        
                        timesheet_vals = {
                            'task_id': int(timesheet_task_id),
                            'project_id': project.id if project else None,
                            'date': timesheet_date,
                            'employee_id': int(timesheet_employee_id),
                            'unit_amount': timesheet_hours_value,
                            'name': timesheet_desc or '',
                            'no_of_workers': int(timesheet_worker) if timesheet_worker else 1,
                        }
                        request.env['account.analytic.line'].sudo().create(timesheet_vals)
                    except Exception as e:
                        _logger.error("Error creating timesheet: %s", str(e))
                        # Continue even if timesheet creation fails

        return request.redirect('/my/progress_reports')

    @http.route(['/my/progress_reports/view/<string:batch_id>'], type='http', auth='user', website=True)
    def view_progress_report(self, batch_id, **kw):
        """View details of a specific progress report batch"""
        Progress = request.env['custom.progress.report'].sudo()
        
        # Allow Daily Report Reviewer group and specific users to see all reports, others see only their own
        has_reviewer_access = request.env.user.has_group('custom_progress_report.group_daily_report_reviewer')
        if has_reviewer_access or request.env.user.email in ['saleh.hassouna@gmail.com', 'saleh@abuhayan.com']:
            domain = [('report_batch_id', '=', batch_id)]
        else:
            domain = [('report_batch_id', '=', batch_id), ('user_id', '=', request.env.user.id)]
        
        records = Progress.search(domain, order='id')
        
        if not records:
            return request.redirect('/my/progress_reports')
        
        # Read records with image fields to ensure binary data is loaded
        records = records.read(['task_name', 'task_description', 'date', 'done_quantity', 
                                'planned_quantity', 'task_image', 'task_image_mimetype', 
                                'task_image_ids', 'report_batch_id'])
        
        # Prepare report data
        report_data = []
        for record_data in records:
            # Get the actual record object to access related fields
            record = Progress.browse(record_data['id'])
            task = record.task_name
            project_name = task.project_id.name if task and task.project_id else 'N/A'
            main_task_name = ''
            subtask_name = ''
            
            if task:
                if task.parent_id:
                    # It's a subtask
                    main_task_name = task.parent_id.name
                    subtask_name = task.name
                else:
                    # It's a main task
                    main_task_name = task.name
                    subtask_name = ''
            
            # Prepare images data - same approach as task_view.xml
            images_data = []
            # Access image records from the record object (not record_data)
            if record.task_image_ids:
                for img in record.task_image_ids:
                    # Read the image binary field to get base64 data
                    img_data = img.read(['image', 'image_mimetype'])[0]
                    image_data = img_data.get('image', '')
                    if image_data:
                        # Handle image data same way as in task_view.xml
                        # image_data from read() is already base64 encoded string
                        if isinstance(image_data, (bytes, bytearray)):
                            image_data = image_data.decode('utf-8')
                        images_data.append({
                            'image': image_data,
                            'mimetype': img_data.get('image_mimetype') or 'image/jpeg',
                        })
            elif record_data.get('task_image'):
                # Backward compatibility with old task_image field
                image_data = record_data.get('task_image', '')
                if image_data:
                    if isinstance(image_data, (bytes, bytearray)):
                        image_data = image_data.decode('utf-8')
                    images_data.append({
                        'image': image_data,
                        'mimetype': record_data.get('task_image_mimetype') or 'image/jpeg',
                    })
            
            # Convert date to string for JSON serialization
            date_value = record_data.get('date')
            date_str = date_value.strftime('%Y-%m-%d') if date_value else ''
            
            report_data.append({
                'id': record_data['id'],
                'index': len(report_data),  # Add index for JavaScript
                'project_name': project_name,
                'main_task_name': main_task_name,
                'subtask_name': subtask_name,
                'date': date_str,
                'done_quantity': record_data.get('done_quantity', 0),
                'planned_quantity': record_data.get('planned_quantity', 0),
                'description': record_data.get('task_description') or '',
                'images': images_data,
                'task_id': task.id if task else None,  # Add task_id for timesheet button
            })
        
        # Convert images data to JSON string for JavaScript
        images_json = json.dumps(report_data)
        
        # Get report date and submitted by email from first record
        report_date = ''
        submitted_by_email = ''
        first_record_obj = None
        if records:
            first_record_obj = Progress.browse(records[0]['id'])
            # Ensure access_token exists (portal.mixin generates it automatically on create, but ensure it's set for existing records)
            if not first_record_obj.access_token:
                first_record_obj.access_token = first_record_obj._portal_ensure_token()
            report_date = first_record_obj.date if first_record_obj.date else ''
            if first_record_obj.user_id:
                submitted_by_email = first_record_obj.user_id.email or first_record_obj.user_id.name or 'N/A'
        
        return request.render('custom_progress_report.portal_view_progress_report', {
            'report_data': report_data,
            'report_data_json': images_json,
            'batch_id': batch_id,
            'report_date': report_date,
            'submitted_by_email': submitted_by_email,
            'report_record': first_record_obj,  # Pass record object for chatter
            'object': first_record_obj,  # Also pass as 'object' for portal.message_thread template
            'token': first_record_obj.access_token if first_record_obj and first_record_obj.access_token else '',  # Pass token directly
        })
    
    @http.route(['/my/progress_reports/timesheets/<int:task_id>'], type='json', auth='user', website=True, methods=['POST'])
    def get_task_timesheets(self, task_id, **kw):
        """Fetch timesheet data for a specific task and its parent main task"""
        try:
            Task = request.env['project.task'].sudo()
            task = Task.browse(task_id)
            
            # Check access - user must have access to the task
            if not task.exists():
                return {'error': 'Task not found'}
            
            # Get parent task if this is a subtask
            parent_task = None
            if task.parent_id:
                parent_task = task.parent_id
            
            Timesheet = request.env['account.analytic.line'].sudo()
            
            # Check if UOM is days
            is_uom_day = False
            if hasattr(Timesheet, '_is_timesheet_encode_uom_day'):
                try:
                    is_uom_day = Timesheet._is_timesheet_encode_uom_day()
                except:
                    pass
            
            # Helper function to format time
            def format_time(hours, is_day=False):
                if is_day:
                    try:
                        # Convert hours to days format using model method
                        days = Timesheet._convert_hours_to_days(hours)
                        return f"{days:.2f}"
                    except:
                        # Fallback to hours if conversion fails
                        h = int(hours)
                        m = int((hours - h) * 60)
                        return f"{h:02d}:{m:02d}"
                else:
                    # Format as hours (HH:MM format)
                    h = int(hours)
                    m = int((hours - h) * 60)
                    return f"{h:02d}:{m:02d}"
            
            # Helper function to prepare timesheet data
            def prepare_timesheet_data(timesheets):
                timesheet_data = []
                for ts in timesheets:
                    # Format date using Odoo's date formatting
                    date_str = ''
                    if ts.date:
                        # Use Odoo's format_date for proper locale formatting
                        try:
                            date_str = request.env['ir.qweb.field.date'].value_to_html(ts.date, {})
                        except:
                            # Fallback to standard format
                            date_str = ts.date.strftime('%m/%d/%Y')
                    
                    # Format time spent
                    time_spent_formatted = format_time(ts.unit_amount or 0.0, is_uom_day)
                    
                    timesheet_data.append({
                        'date': date_str,
                        'date_raw': ts.date.strftime('%Y-%m-%d') if ts.date else '',  # Keep raw for sorting
                        'employee': ts.employee_id.name if ts.employee_id else '',
                        'description': ts.name or '',
                        'time_spent': ts.unit_amount or 0.0,
                        'time_spent_formatted': time_spent_formatted,
                        'no_of_workers': ts.no_of_workers if hasattr(ts, 'no_of_workers') else 1,
                    })
                return timesheet_data
            
            # Helper function to get task summary
            def get_task_summary(task_obj):
                total_time = task_obj.effective_hours if hasattr(task_obj, 'effective_hours') else 0.0
                allocated = task_obj.allocated_hours if hasattr(task_obj, 'allocated_hours') else 0.0
                remaining = task_obj.remaining_hours if hasattr(task_obj, 'remaining_hours') else 0.0
                
                # Calculate days spent (assuming 8 hours per day)
                eff_days = round(total_time / 8.0, 2) if total_time else 0.0
                alloc_days = round(allocated / 8.0, 2) if allocated > 0 else 0.0
                
                return {
                    'task_name': task_obj.name if task_obj else '',
                    'total_time_spent': total_time,
                    'total_time_spent_formatted': format_time(total_time, is_uom_day),
                    'allocated_hours': allocated,
                    'allocated_hours_formatted': format_time(allocated, is_uom_day) if allocated > 0 else '',
                    'remaining_hours': remaining,
                    'remaining_hours_formatted': format_time(remaining, is_uom_day) if allocated > 0 else '',
                    'is_uom_day': is_uom_day,
                    'eff_days': int(eff_days),
                    'alloc_days': int(alloc_days),
                }
            
            # Get timesheets for subtask
            subtask_timesheets = Timesheet.search([
                ('task_id', '=', task_id),
                ('project_id', '!=', False)
            ], order='date desc')
            
            subtask_data = prepare_timesheet_data(subtask_timesheets)
            subtask_summary = get_task_summary(task)
            
            # Get timesheets for main task if this is a subtask
            main_task_data = []
            main_task_summary = None
            if parent_task:
                main_task_timesheets = Timesheet.search([
                    ('task_id', '=', parent_task.id),
                    ('project_id', '!=', False)
                ], order='date desc')
                main_task_data = prepare_timesheet_data(main_task_timesheets)
                main_task_summary = get_task_summary(parent_task)
            
            return {
                'success': True,
                'subtask': {
                    'task_name': task.name,
                    'timesheets': subtask_data,
                    'summary': subtask_summary,
                },
                'main_task': {
                    'task_name': parent_task.name if parent_task else None,
                    'timesheets': main_task_data,
                    'summary': main_task_summary,
                } if parent_task else None,
            }
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Error fetching timesheets for task %s: %s", task_id, str(e))
            return {'error': str(e)}

    @http.route(['/my/progress_reports/delete/<string:batch_id>'], type='json', auth='user', website=True, methods=['POST'])
    def delete_progress_report(self, batch_id, **kw):
        """Delete all progress reports with the given batch_id. Only saleh@abuhayan.com can delete reports."""
        try:
            # Only allow deletion for specific user email
            if request.env.user.email != 'saleh@abuhayan.com':
                return {'success': False, 'error': 'You do not have permission to delete reports.'}
            
            Progress = request.env['custom.progress.report'].sudo()
            
            # Admin user can delete any user's reports, so don't filter by user_id
            reports = Progress.search([
                ('report_batch_id', '=', batch_id)
            ])
            
            if not reports:
                return {'success': False, 'error': 'Report not found or you do not have permission to delete it.'}
            
            # Delete all reports in the batch (cascade will handle related images)
            report_count = len(reports)
            reports.unlink()
            
            return {'success': True, 'message': f'Successfully deleted {report_count} report(s).'}
            
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Error deleting progress report batch %s: %s", batch_id, str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/get_task_details', type='http', auth='user', csrf=False)
    def get_task_details(self, **kwargs):
        try:
            task_id = int(kwargs.get('task_id', 0))
            if not task_id:
                return request.make_response(
                    json.dumps({'error': 'Missing task_id'}),
                    headers=[('Content-Type', 'application/json')]
                )

            task = request.env['project.task'].sudo().browse(task_id)
            if not task.exists():
                return request.make_response(
                    json.dumps({'error': 'Task not found'}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Strip HTML tags from description
            raw_description = task.description or ''
            clean_description = re.sub('<[^<]+?>', '', raw_description).strip()

            # Extract proper unit name
            unit_value = task.unit.name if task.unit else ''

            data = {
                'description': clean_description,
                'planned_quantity': task.planned_quantity or 0.0,
                'unit': unit_value,
            }

            return request.make_response(
                json.dumps(data),
                headers=[('Content-Type', 'application/json')]
            )
        
        except Exception as e:
            # Log error and return message
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )
        
    @http.route(['/my/tasks/<int:task_id>'], type='http', auth="public", website=True)
    def portal_my_task(self, task_id, report_type=None, access_token=None, project_sharing=False, **kw):
        """
        Override the core portal_my_task route to add custom progress report data.
        This extends the core functionality by replicating parent logic and adding custom data.
        """
        from odoo.exceptions import AccessError, MissingError
        
        try:
            # Replicate parent method's access check
            task_sudo = self._document_check_access('project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Handle report types (PDF, HTML, TEXT) - delegate to parent
        if report_type in ('pdf', 'html', 'text'):
            return super().portal_my_task(task_id, report_type=report_type, access_token=access_token, project_sharing=project_sharing, **kw)

        # Ensure attachment are accessible with access token inside template (from parent)
        for attachment in task_sudo.attachment_ids:
            attachment.generate_access_token()
        if project_sharing is True:
            # Then the user arrives to the stat button shown in form view of project.task and the portal user can see only 1 task
            # so the history should be reset.
            request.session['my_tasks_history'] = task_sudo.ids
        
        # Get base values from parent method (includes timesheets and all core functionality)
        values = self._task_get_page_view_values(task_sudo, access_token, **kw)
        
        # Now add our custom progress report data
        try:
            # Fetch all progress reports linked to this task AND its subtasks
            ProgressReport = request.env['custom.progress.report'].sudo()
            
            # Collect all task IDs: main task + all subtasks
            task_ids = [task_sudo.id]
            try:
                if task_sudo.child_ids:
                    child_ids = task_sudo.child_ids.ids
                    if child_ids:
                        task_ids.extend(child_ids)
            except Exception:
                # If we can't access child_ids, continue with just the main task
                pass
            
            # Search for reports of main task and all subtasks
            task_reports = ProgressReport.search([('task_name', 'in', task_ids)], order="date desc") if task_ids else []

            # Group reports by submission batch so same-day submissions render separately
            grouped_reports_by_batch = {}
            ordered_groups = []
            for line in task_reports:
                batch_key = line.report_batch_id or f"line-{line.id}"
                label = line.date.strftime('%Y-%m-%d') if line.date else 'No Date'

                if batch_key not in grouped_reports_by_batch:
                    grouped_reports_by_batch[batch_key] = {
                        'label': label,
                        'records': [],
                    }
                    ordered_groups.append(grouped_reports_by_batch[batch_key])

                grouped_reports_by_batch[batch_key]['records'].append(line)

            # Calculate summary data for Total Progress Summary section
            is_main_task = bool(task_sudo.child_ids)
            summary_data = {
                'task_name': task_sudo.name,
                'is_main_task': is_main_task,
            }

            if is_main_task:
                try:
                    # Main task: Calculate progress rate as average of subtask progress rates
                    subtask_totals = {}  # {subtask_id: {'planned': float, 'done': float, 'unit': str}}
                    
                    # Get child task IDs safely
                    child_ids = task_sudo.child_ids.ids if task_sudo.child_ids else []
                    
                    # Group reports by subtask and calculate totals
                    for line in task_reports:
                        if not line.task_name:
                            continue
                        subtask_id = line.task_name.id
                        # Only process subtasks, not the main task itself
                        if subtask_id in child_ids:
                            if subtask_id not in subtask_totals:
                                subtask_totals[subtask_id] = {
                                    'planned': float(line.planned_quantity or 0.0),
                                    'done': 0.0,
                                    'unit': line.unit or '',
                                }
                            subtask_totals[subtask_id]['done'] += float(line.done_quantity or 0.0)
                    
                    # Calculate progress rate as average of each subtask's progress rate
                    if subtask_totals:
                        subtask_progress_rates = []
                        for data in subtask_totals.values():
                            planned = float(data.get('planned', 0.0))
                            done = float(data.get('done', 0.0))
                            if planned > 0.0:
                                progress_rate = (done / planned * 100.0)
                            else:
                                progress_rate = 0.0
                            subtask_progress_rates.append(progress_rate)
                        
                        # Average of all subtask progress rates
                        avg_progress_rate = sum(subtask_progress_rates) / len(subtask_progress_rates) if subtask_progress_rates else 0.0
                        
                        summary_data.update({
                            'avg_planned': 0.0,  # Always 0 for main task
                            'avg_done': 0.0,  # Always 0 for main task
                            'unit': list(subtask_totals.values())[0].get('unit', '') if subtask_totals else '',
                            'progress_rate': avg_progress_rate,
                        })
                    else:
                        summary_data.update({
                            'avg_planned': 0.0,
                            'avg_done': 0.0,
                            'unit': '',
                            'progress_rate': 0.0,
                        })
                except Exception as e:
                    # Fallback if calculation fails
                    summary_data.update({
                        'avg_planned': 0.0,
                        'avg_done': 0.0,
                        'unit': '',
                        'progress_rate': 0.0,
                    })
            else:
                try:
                    # Subtask: Calculate totals for this subtask only
                    total_done = 0.0
                    planned_qty = 0.0
                    unit = ''
                    
                    for line in task_reports:
                        if not line.task_name:
                            continue
                        if line.task_name.id == task_sudo.id:
                            total_done += float(line.done_quantity or 0.0)
                            if planned_qty == 0.0:
                                planned_qty = float(line.planned_quantity or 0.0)
                                unit = line.unit or ''
                    
                    summary_data.update({
                        'planned_qty': planned_qty,
                        'total_done': total_done,
                        'unit': unit,
                        'progress_rate': (total_done / planned_qty * 100.0) if planned_qty > 0.0 else 0.0,
                    })
                except Exception:
                    # Fallback if calculation fails
                    summary_data.update({
                        'planned_qty': 0.0,
                        'total_done': 0.0,
                        'unit': '',
                        'progress_rate': 0.0,
                    })
            
            # Add our custom data to the values (preserving all parent values including timesheets)
            values.update({
                'grouped_reports': ordered_groups,
                'summary_data': summary_data,
            })
            
        except Exception as e:
            # Log the error for debugging but don't break the page
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Error adding progress report data to portal_my_task for task_id %s: %s", task_id, str(e))
            # Continue with empty custom data if there's an error
            values.update({
                'grouped_reports': [],
                'summary_data': None,
            })
        
        # Render with all values (core + custom)
        return request.render("project.portal_my_task", values)

    def _get_my_tasks_searchbar_filters(self, project_domain=None, task_domain=None):
        """
        Override to remove filter functionality - return empty dict so no filters are applied.
        This ensures all projects are shown by default.
        """
        return {}

    @http.route(['/my/tasks', '/my/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_tasks(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='name', groupby=None, **kw):
        """
        Override to remove filter functionality and show all projects by default.
        Always uses a domain that shows all tasks with projects (no filtering by specific project).
        """
        from odoo.addons.portal.controllers.portal import pager as portal_pager
        
        # Always use domain to show all tasks with projects (no filtering by specific project)
        # This matches the original 'all' filter behavior: show all tasks that belong to projects
        domain = [('project_id', '!=', False)]
        
        values = self._prepare_tasks_values(page, date_begin, date_end, sortby, search, search_in, groupby, domain=domain)

        # pager
        pager_vals = values['pager']
        # Don't include filterby in URL args since we're not using filters
        pager = portal_pager(**pager_vals)

        grouped_tasks = values['grouped_tasks'](pager['offset'])
        values.update({
            'grouped_tasks': grouped_tasks,
            'show_project': True,
            'pager': pager,
            'searchbar_filters': {},  # Empty filters dict
            'filterby': 'all',  # Set to 'all' but it won't be used
        })
        return request.render("project.portal_my_tasks", values)

    @http.route(['/all/task'], type='http', auth="user", website=True)
    def portal_all_task(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='name', groupby='project_id', project_id=None, **kw):
        """
        Route that displays all projects, tasks, and subtasks in accordion structure.
        Shows all tasks without filtering by project, unless project_id is provided.
        If project_id is provided, only shows that project's tasks and expands its accordion.
        """
        from odoo.osv.expression import AND
        from odoo.tools import groupby as groupbyelem
        from operator import itemgetter
        
        # Start with empty domain to get ALL tasks regardless of state or project
        domain = []
        
        # Filter by project_id if provided
        selected_project_id = None
        if project_id:
            try:
                selected_project_id = int(project_id)
                domain = AND([domain, [('project_id', '=', selected_project_id)]])
            except (ValueError, TypeError):
                selected_project_id = None
        
        # Get all tasks without pagination limit
        Task = request.env['project.task']
        Task_sudo = Task.sudo()
        Project = request.env['project.project']
        
        # Filter to only show tasks from projects with privacy_visibility='portal' 
        # (Invited portal users and all internal users - public visibility)
        if not selected_project_id:
            # Get all projects with portal visibility
            portal_projects = Project.sudo().search([('privacy_visibility', '=', 'portal')])
            if portal_projects:
                # Only include tasks from these projects
                domain = AND([domain, [('project_id', 'in', portal_projects.ids)]])
            else:
                # If no portal projects exist, return empty result
                domain = AND([domain, [('id', '=', False)]])
        else:
            # If a specific project is selected, verify it has portal visibility
            project = Project.sudo().browse(selected_project_id)
            if not project.exists() or project.privacy_visibility != 'portal':
                # Project doesn't exist or doesn't have portal visibility, return empty
                domain = AND([domain, [('id', '=', False)]])
        
        # Apply access rules only (necessary for security, but don't filter by project or state)
        if Task.has_access('read'):
            domain = AND([domain, request.env['ir.rule']._compute_domain(Task._name, 'read')])
        
        # Only apply date filters if explicitly provided
        if date_begin and date_end:
            domain = AND([domain, [('create_date', '>', date_begin), ('create_date', '<=', date_end)]])
        
        # Only apply search filters if explicitly provided
        if search and search_in:
            # Get milestone info for search domain
            milestone_domain = AND([domain, [('allow_milestones', '=', True)], [('milestone_id', '!=', False)]])
            milestones_allowed = Task_sudo.search_count(milestone_domain, limit=1) == 1
            domain = AND([domain, self._task_get_search_domain(search_in, search, milestones_allowed, False)])
        
        # Set order (same as _prepare_tasks_values)
        if groupby == 'none':
            group_field = None
        elif groupby == 'priority':
            group_field = 'priority desc'
        else:
            group_field = groupby
        
        # Build order string properly
        if group_field:
            order = '%s, %s' % (group_field, sortby) if sortby else group_field
        else:
            order = sortby or 'create_date desc'
        
        # Get all tasks (no limit)
        all_tasks = Task_sudo.search(domain, order=order)
        
        # Prepare tasks values to get other template variables (use empty domain to get all tasks)
        values = self._prepare_tasks_values(page, date_begin, date_end, sortby, search, search_in, groupby, url="/all/task", domain=[])
        
        # Group tasks by project_id
        if groupby != 'none':
            grouped_tasks = [Task_sudo.concat(*g) for k, g in groupbyelem(all_tasks, itemgetter(groupby))]
        else:
            grouped_tasks = [all_tasks] if all_tasks else []
        
        # Sort by state if needed
        task_states = dict(Task_sudo._fields['state']._description_selection(request.env))
        if sortby == 'state':
            if groupby == 'none' and grouped_tasks:
                grouped_tasks[0] = grouped_tasks[0].sorted(lambda tasks: task_states.get(tasks.state))
            else:
                grouped_tasks.sort(key=lambda tasks: task_states.get(tasks[0].state))
        
        values.update({
            'grouped_tasks': grouped_tasks,
            'show_project': True,
            'page_name': 'all_task',  # Set page_name for breadcrumb condition
            'selected_project_id': selected_project_id,  # Pass selected project ID to template
        })
        
        return request.render("custom_progress_report.portal_all_task", values)

    def _prepare_project_domain(self):
        """
        Override to only show projects with portal visibility (public visibility).
        This ensures only projects visible to all portal and internal users are shown.
        """
        from odoo.osv.expression import AND
        domain = super()._prepare_project_domain() if hasattr(super(), '_prepare_project_domain') else []
        # Only show projects with privacy_visibility='portal' (Invited portal users and all internal users)
        domain = AND([domain, [('privacy_visibility', '=', 'portal')]])
        return domain

