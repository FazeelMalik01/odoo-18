import re
import json
from odoo import http
from odoo.http import request
from odoo.osv import expression
import uuid
import base64

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class PortalProgressReport(ProjectCustomerPortal):

    @http.route(['/my/progress_reports'], type='http', auth='user', website=True)
    def portal_my_progress_reports(self, **kw):
        Progress = request.env['custom.progress.report'].sudo()
        # Allow specific users to see all reports, others see only their own
        if request.env.user.email in ['saleh.hassouna@gmail.com', 'saleh@abuhayan.com']:
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
        planned_quantities = request.httprequest.form.getlist('planned_quantities[]')
        done_quantities = request.httprequest.form.getlist('done_quantities[]')  # ✅ new
        units = request.httprequest.form.getlist('units[]')
        task_descriptions = request.httprequest.form.getlist('task_descriptions[]')
        # We'll fetch files per row index: task_images_0, task_images_1, ...

        date = post.get('date')
        user_id = request.env.user.id

        batch_id = str(uuid.uuid4())

        for i, task_id in enumerate(task_ids):
            if not task_id:
                continue

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
                'task_name': int(task_id),
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

        return request.redirect('/my/progress_reports')

    @http.route(['/my/progress_reports/delete/<string:batch_id>'], type='json', auth='user', website=True, methods=['POST'])
    def delete_progress_report(self, batch_id, **kw):
        """Delete all progress reports with the given batch_id. Admin user can delete any user's reports."""
        try:
            # Only allow deletion for specific user emails
            if request.env.user.email not in ['saleh.hassouna@gmail.com', 'saleh@abuhayan.com']:
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

