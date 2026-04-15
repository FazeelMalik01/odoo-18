from odoo import http, fields
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class TimesheetPortalController(ProjectCustomerPortal):
    """Extends the project portal to add timer + timesheet approval on task pages."""

    # ----------------------------------------------------------------
    # Inject extra context into the task page
    # ----------------------------------------------------------------
    def _task_get_page_view_values(self, task, access_token, **kwargs):
        values = super()._task_get_page_view_values(task, access_token, **kwargs)
        user = request.env.user
        if not user._is_public():
            Approval = request.env['portal.timesheet.approval'].sudo()
            running_timer = Approval.search([
                ('task_id',        '=', task.id),
                ('portal_user_id', '=', user.id),
                ('state',          '=', 'timing'),
            ], limit=1)
            approval_requests = Approval.search([
                ('task_id',        '=', task.id),
                ('portal_user_id', '=', user.id),
                ('state',          'in', ['pending', 'approved', 'rejected']),
            ])
            # Pass epoch milliseconds so JS can display in the user's local timezone
            timer_start_ms = 0
            if running_timer and running_timer.timer_start:
                import calendar
                timer_start_ms = int(
                    calendar.timegm(running_timer.timer_start.timetuple()) * 1000
                )
            values.update({
                'running_timer':          running_timer,
                'timer_start_ms':         timer_start_ms,
                'approval_requests':      approval_requests,
                'show_timesheet_section': True,
            })
        return values

    # ----------------------------------------------------------------
    # Timer: Start
    # ----------------------------------------------------------------
    @http.route(
        '/my/tasks/<int:task_id>/timer/start',
        type='jsonrpc', auth='user', methods=['POST'], website=True,
    )
    def portal_timer_start(self, task_id, **kw):
        try:
            self._document_check_access('project.task', task_id)
        except (AccessError, MissingError):
            return {'error': 'Access denied'}

        user = request.env.user
        Approval = request.env['portal.timesheet.approval'].sudo()

        existing = Approval.search([
            ('task_id',        '=', task_id),
            ('portal_user_id', '=', user.id),
            ('state',          '=', 'timing'),
        ], limit=1)
        if existing:
            import calendar
            return {
                'error': 'A timer is already running for this task.',
                'timer_start_ms': int(
                    calendar.timegm(existing.timer_start.timetuple()) * 1000
                ),
            }

        now = fields.Datetime.now()
        import calendar
        Approval.create({
            'name':           '/',
            'task_id':        task_id,
            'portal_user_id': user.id,
            'date':           fields.Date.today(),
            'timer_start':    now,
            'state':          'timing',
            'unit_amount':    0.0,
        })
        return {
            'success':        True,
            'timer_start_ms': int(calendar.timegm(now.timetuple()) * 1000),
        }

    # ----------------------------------------------------------------
    # Timer: Stop  →  creates pending approval record immediately
    # ----------------------------------------------------------------
    @http.route(
        '/my/tasks/<int:task_id>/timer/stop',
        type='jsonrpc', auth='user', methods=['POST'], website=True,
    )
    def portal_timer_stop(self, task_id, description='', **kw):
        try:
            self._document_check_access('project.task', task_id)
        except (AccessError, MissingError):
            return {'error': 'Access denied'}

        user = request.env.user
        Approval = request.env['portal.timesheet.approval'].sudo()

        running = Approval.search([
            ('task_id',        '=', task_id),
            ('portal_user_id', '=', user.id),
            ('state',          '=', 'timing'),
        ], limit=1)
        if not running:
            return {'error': 'No active timer found for this task.'}

        now = fields.Datetime.now()
        elapsed = (now - running.timer_start).total_seconds() / 3600.0
        name = description.strip() if description and description.strip() else '/'

        # Always create the record — set state='pending' directly
        running.write({
            'timer_stop':  now,
            'unit_amount': round(elapsed, 2),
            'name':        name,
            'state':       'pending',
        })

        # Notify manager only if configured — never blocks record creation
        running._notify_manager_best_effort()

        return {
            'success':     True,
            'hours':       round(elapsed, 2),
            'approval_id': running.id,
        }

    # ----------------------------------------------------------------
    # Manual timesheet entry  →  creates pending approval record
    # ----------------------------------------------------------------
    @http.route(
        '/my/tasks/<int:task_id>/timesheet/submit',
        type='jsonrpc', auth='user', methods=['POST'], website=True,
    )
    def portal_timesheet_submit(self, task_id, description, hours, date=None, **kw):
        try:
            self._document_check_access('project.task', task_id)
        except (AccessError, MissingError):
            return {'error': 'Access denied'}

        try:
            hours = float(hours)
        except (ValueError, TypeError):
            return {'error': 'Invalid hours value.'}

        if hours <= 0:
            return {'error': 'Hours must be greater than 0.'}

        if not description or not description.strip():
            return {'error': 'Description is required.'}

        user = request.env.user
        Approval = request.env['portal.timesheet.approval'].sudo()

        approval = Approval.create({
            'name':           description.strip(),
            'task_id':        task_id,
            'portal_user_id': user.id,
            'date':           date or fields.Date.today(),
            'unit_amount':    hours,
            'state':          'pending',
        })

        # Notify manager only if configured
        approval._notify_manager_best_effort()

        return {
            'success':     True,
            'approval_id': approval.id,
        }
