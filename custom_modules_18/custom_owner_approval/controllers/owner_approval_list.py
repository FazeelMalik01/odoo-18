from odoo import http
from odoo.http import request
from datetime import datetime
import base64

class OwnerApprovalPortal(http.Controller):

    @http.route(['/my/owner-approvals'], type='http', auth='user', website=True)
    def owner_approval_list(self, **kw):

        user = request.env.user
        partner = user.partner_id

        domain = [('state', '!=', 'draft')]

        # If NOT supervisor, restrict to own records
        if not user.has_group('custom_owner_approval.group_owner_approval_supervisor'):
            domain.append(('owner_partner_id', '=', partner.id))

        approvals = request.env['owner.approval'].sudo().search(
            domain,
            order='submission_date desc'
        )

        return request.render(
            'custom_owner_approval.owner_approval_list_template',
            {
                'page_name': 'Owner Approvals',
                'approvals': approvals,
            }
        )

    @http.route(['/my/owner-approval/<int:approval_id>'], type='http', auth='user', website=True)
    def owner_approval_detail(self, approval_id, **kw):
        user = request.env.user
        partner = user.partner_id

        domain = [('id', '=', approval_id)]

        # Restrict only if NOT supervisor
        if not user.has_group('custom_owner_approval.group_owner_approval_supervisor'):
            domain.append(('owner_partner_id', '=', partner.id))

        approval = request.env['owner.approval'].sudo().search(domain, limit=1)

        if not approval:
            return request.not_found()

        return request.render(
            'custom_owner_approval.owner_approval_detail_template',
            {
                'page_name': 'Owner Approval Detail',
                'approval': approval,
                'object': approval,

            }
        )
    
    @http.route(['/my/owner-approval/update/<int:approval_id>'], type='http', auth='user', website=True, methods=['POST'])
    def owner_approval_update(self, approval_id, **post):

        user = request.env.user
        partner = user.partner_id

        domain = [('id', '=', approval_id)]

        if not user.has_group('custom_owner_approval.group_owner_approval_supervisor'):
            domain.append(('owner_partner_id', '=', partner.id))

        approval = request.env['owner.approval'].sudo().search(domain, limit=1)
        if not approval:
            return request.not_found()

        vals = {}

        decision = post.get('decision')
        if decision:
            vals['decision'] = decision

            response_dt = datetime.now().replace(microsecond=0)
            vals['owner_response_date'] = response_dt

            # Determine correct state
            if decision == 'approved':
                if approval.due_date and response_dt > approval.due_date:
                    vals['state'] = 'late'
                else:
                    vals['state'] = 'approved'
            elif decision in ['rejected', 'revise']:
                vals['state'] = decision

            # Handle signatures only when actually approved (not late)
            if vals.get('state') in ['approved', 'late']:
                resp_user = approval.responsible_user_id
                if resp_user and hasattr(resp_user, 'sign_signature') and resp_user.sign_signature:
                    vals['responsible_signature'] = resp_user.sign_signature

                owner_partner = approval.owner_partner_id
                if owner_partner:
                    owner_user = owner_partner.user_ids[:1]
                    if owner_user and hasattr(owner_user, 'sign_signature') and owner_user.sign_signature:
                        vals['owner_signature'] = owner_user.sign_signature
            else:
                vals['responsible_signature'] = False
                vals['owner_signature'] = False

        if post.get('owner_comments') is not None:
            vals['owner_comments'] = post.get('owner_comments')

        if vals:
            approval.write(vals)

        return request.redirect(f'/my/owner-approval/{approval_id}')

    @http.route('/my/owner-approval/upload/<int:approval_id>', type='http', auth='user', website=True, methods=['POST'])
    def upload_attachment(self, approval_id, **post):
        user = request.env.user
        partner = user.partner_id

        domain = [('id', '=', approval_id)]

        if not user.has_group('custom_owner_approval.group_owner_approval_supervisor'):
            domain.append(('owner_partner_id', '=', partner.id))

        approval = request.env['owner.approval'].sudo().search(domain, limit=1)

        if not approval:
            return request.not_found()

        file = request.httprequest.files.get('attachment')

        if file and file.filename:

            attachment = request.env['ir.attachment'].sudo().create({
                'name': file.filename,
                'datas': base64.b64encode(file.read()),
                'res_model': 'owner.approval',
                'res_id': approval.id,
                'type': 'binary',
                'mimetype': file.mimetype,
            })

            # Force link into many2many field (extra safe)
            approval.write({
                'attachment_ids': [(4, attachment.id)]
            })

        return request.redirect(f'/my/owner-approval/{approval_id}')
