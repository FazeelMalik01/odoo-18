# file: odoo_addons/autocad_timesheet/controllers/main.py

from odoo import http, fields
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)

class AutoCADController(http.Controller):

    @http.route('/api/autocad', type='http', auth='public', methods=['POST'], csrf=False)
    def autocad_timesheet(self, **post):
        _logger.info("========== AUTOCAD API CALLED ==========")

        try:
            # Parse JSON body
            raw_data = request.httprequest.data
            if not raw_data:
                _logger.error("Empty request body received")
                return request.make_response(
                    json.dumps({"error": "Empty request body"}),
                    status=400,
                    headers=[('Content-Type', 'application/json')]
                )

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                _logger.error(f"Invalid JSON received: {e}")
                return request.make_response(
                    json.dumps({"error": f"Invalid JSON: {str(e)}"}),
                    status=400,
                    headers=[('Content-Type', 'application/json')]
                )

            _logger.info(f"Incoming Data: {data}")

            # Extract fields
            action      = data.get('action')
            project_id  = data.get('project_id')
            task_id     = data.get('task_id')
            employee_id = data.get('employee_id')
            filename    = data.get('filename', 'Unknown')
            duration    = data.get('duration', 0)

            _logger.info(f"Action: {action} | File: {filename} | Duration: {duration} | "
                         f"Project: {project_id} | Task: {task_id} | Employee ID: {employee_id}")

            # ── Validate required fields ────────────────────────────────────────
            missing = []
            if not action:
                missing.append('action')
            if not project_id:
                missing.append('project_id')
            if not task_id:
                missing.append('task_id')
            if not employee_id:
                missing.append('employee_id')

            if missing:
                msg = f"Missing required fields: {', '.join(missing)}"
                _logger.error(msg)
                return request.make_response(
                    json.dumps({"error": msg}),
                    status=400,
                    headers=[('Content-Type', 'application/json')]
                )

            # ── Validate action value ───────────────────────────────────────────
            if action not in ('start', 'stop'):
                msg = f"Invalid action '{action}'. Must be 'start' or 'stop'."
                _logger.error(msg)
                return request.make_response(
                    json.dumps({"error": msg}),
                    status=400,
                    headers=[('Content-Type', 'application/json')]
                )

            # ── Look up Project ─────────────────────────────────────────────────
            project = request.env['project.project'].sudo().search(
                [('name', '=', project_id)], limit=1
            )
            if not project:
                msg = f"Project not found: '{project_id}'"
                _logger.error(msg)
                return request.make_response(
                    json.dumps({"error": msg}),
                    status=404,
                    headers=[('Content-Type', 'application/json')]
                )

            # ── Look up Task ────────────────────────────────────────────────────
            task = request.env['project.task'].sudo().search(
                [('name', '=', task_id), ('project_id', '=', project.id)], limit=1
            )
            if not task:
                msg = f"Task not found: '{task_id}' under project '{project_id}'"
                _logger.error(msg)
                return request.make_response(
                    json.dumps({"error": msg}),
                    status=404,
                    headers=[('Content-Type', 'application/json')]
                )

            # ── Look up Employee ────────────────────────────────────────────────
            try:
                emp_id_int = int(employee_id)
            except (ValueError, TypeError):
                msg = f"employee_id must be an integer, got: '{employee_id}'"
                _logger.error(msg)
                return request.make_response(
                    json.dumps({"error": msg}),
                    status=400,
                    headers=[('Content-Type', 'application/json')]
                )

            employee = request.env['hr.employee'].sudo().browse(emp_id_int)
            if not employee.exists():
                msg = f"Employee with ID {emp_id_int} not found"
                _logger.error(msg)
                return request.make_response(
                    json.dumps({"error": msg}),
                    status=404,
                    headers=[('Content-Type', 'application/json')]
                )

            _logger.info(f"Resolved — Project: [{project.id}] {project.name} | "
                         f"Task: [{task.id}] {task.name} | "
                         f"Employee: [{employee.id}] {employee.name}")

            # ── Handle 'start' action ───────────────────────────────────────────
            if action == 'start':
                _logger.info("Start event received — no timesheet entry created.")
                return request.make_response(
                    json.dumps({"status": "ok", "message": "Session started"}),
                    status=200,
                    headers=[('Content-Type', 'application/json')]
                )

            # ── Handle 'stop' action ────────────────────────────────────────────
            if action == 'stop':
                if duration <= 0:
                    msg = f"Stop received but duration is {duration} — skipping timesheet creation."
                    _logger.warning(msg)
                    return request.make_response(
                        json.dumps({"status": "skipped", "message": msg}),
                        status=200,
                        headers=[('Content-Type', 'application/json')]
                    )

                timesheet = request.env['account.analytic.line'].sudo().create({
                    'name': f"AutoCAD Work: {filename}",
                    'project_id': project.id,
                    'task_id': task.id,
                    'employee_id': employee.id,
                    'unit_amount': round(duration, 4),
                    'date': fields.Date.today(),
                })

                _logger.info(f"Timesheet CREATED — ID: {timesheet.id} | "
                             f"Duration: {timesheet.unit_amount}h | "
                             f"Date: {timesheet.date}")
                _logger.info("========== AUTOCAD API END ==========")

                return request.make_response(
                    json.dumps({
                        "status": "ok",
                        "message": "Timesheet created",
                        "timesheet_id": timesheet.id,
                        "duration_hours": timesheet.unit_amount,
                        "date": str(timesheet.date),
                        "project": project.name,
                        "task": task.name,
                        "employee": employee.name,
                    }),
                    status=200,
                    headers=[('Content-Type', 'application/json')]
                )

        except Exception as e:
            _logger.exception("AUTOCAD CONTROLLER UNHANDLED ERROR")
            return request.make_response(
                json.dumps({"error": str(e)}),
                status=500,
                headers=[('Content-Type', 'application/json')]
            )