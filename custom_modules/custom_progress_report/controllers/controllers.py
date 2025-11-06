import re
import json
from odoo import http
from odoo.http import request
import uuid
import base64

class PortalProgressReport(http.Controller):

    @http.route(['/my/progress_reports'], type='http', auth='user', website=True)
    def portal_my_progress_reports(self, **kw):
        Progress = request.env['custom.progress.report'].sudo()
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

            # Safely extract base64 image only if a real file was uploaded
            image_b64 = False
            image_mimetype = False
            try:
                file_obj = request.httprequest.files.get(f'task_images_{i}')
                if file_obj is not None:
                    filename = getattr(file_obj, 'filename', '') or ''
                    if filename.strip():
                        file_bytes = file_obj.read() or b''
                        if file_bytes:
                            image_b64 = base64.b64encode(file_bytes).decode('utf-8')
                            image_mimetype = getattr(file_obj, 'mimetype', None) or getattr(file_obj, 'content_type', None) or 'image/jpeg'
            except Exception:
                image_b64 = False
                image_mimetype = False

            request.env['custom.progress.report'].sudo().create({
                'task_name': int(task_id),
                'task_description': task_descriptions[i] if i < len(task_descriptions) else '',
                'date': date,
                'done_quantity': done_quantities[i] if i < len(done_quantities) else 0.0,  # ✅ per-row quantity
                'planned_quantity': planned_quantities[i] if i < len(planned_quantities) else 0.0,
                'unit': units[i] if i < len(units) else '',
                'task_image': image_b64,
                'task_image_mimetype': image_mimetype,
                'user_id': user_id,
                'report_batch_id': batch_id,
            })

        return request.redirect('/my/progress_reports')

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
        
    @http.route(['/my/tasks/<int:task_id>'], type='http', auth='user', website=True)
    def portal_task_detail(self, task_id, **kw):
        Task = request.env['project.task'].sudo()
        task = Task.browse(task_id)
        if not task.exists():
            return request.not_found()

        # Fetch all progress reports linked to this task
        ProgressReport = request.env['custom.progress.report'].sudo()
        task_reports = ProgressReport.search([('task_name', '=', task.id)], order="date desc")

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

        return request.render('project.portal_my_task', {
            'task': task,
            'object': task,  # ✅ required for portal.message_thread
            'grouped_reports': ordered_groups,
        })

