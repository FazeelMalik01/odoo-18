# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields,models,api, _
from ast import literal_eval
from odoo import SUPERUSER_ID
import base64

class LowStockNotification(models.Model):
	_name="low.stock.notification"
	_description="Low Stock Notification"

	company_id = fields.Many2one('res.company','Company')
	low_stock_products_ids = fields.One2many(related='company_id.low_stock_products_ids',string="Low Stock")
	
	def action_list_products_(self):

		products_list = []

		products_dlt = [(2, dlt.id, 0) for dlt in self.env.company.low_stock_products_ids]
		self.env.company.low_stock_products_ids = products_dlt

		if self.env.company.notification_base == 'on_hand':

			if self.env.company.notification_products == 'for_all':

				if self.env.company.notification_product_type == 'variant':
					result = self.env['product.product'].search([
						('qty_available', '<', self.env.company.min_quantity),
						('type', '=', 'consu')
					])
					for product in result:
						name_att = ' '
						for attribute in product.product_template_attribute_value_ids:
							name_att = name_att + attribute.name + '  '
						if product.product_template_attribute_value_ids:
							name_pro = product.name + ' - ' + name_att + '  '
						else:
							name_pro = product.name
						products_list.append([0, 0, {
							'name': name_pro,
							'limit_quantity': self.env.company.min_quantity,
							'stock_quantity': product.qty_available,
						}])

				else:
					result = self.env['product.template'].search([('type', '=', 'consu')])
					for product in result:
						if product.qty_available < self.env.company.min_quantity:
							products_list.append([0, 0, {
								'name': product.name,
								'limit_quantity': self.env.company.min_quantity,
								'stock_quantity': product.qty_available,
							}])

			if self.env.company.notification_products == 'fore_product':

				if self.env.company.notification_product_type == 'variant':
					result = self.env['product.product'].search([('type', '=', 'consu')])
					for product in result:
						if product.qty_available < product.min_quantity:
							name_att = ' '
							for attribute in product.product_template_attribute_value_ids:
								name_att = name_att + attribute.name + '  '
							if product.product_template_attribute_value_ids:
								name_pro = product.name + ' - ' + name_att + '  '
							else:
								name_pro = product.name
							products_list.append([0, 0, {
								'name': name_pro,
								'limit_quantity': product.min_quantity,
								'stock_quantity': product.qty_available,
							}])

				else:
					result = self.env['product.template'].search([('type', '=', 'consu')])
					for product in result:
						if product.qty_available < product.temp_min_quantity:
							products_list.append([0, 0, {
								'name': product.name,
								'limit_quantity': product.temp_min_quantity,
								'stock_quantity': product.qty_available,
							}])

			if self.env.company.notification_products == 'reorder':

				if self.env.company.notification_product_type == 'variant':
					result = self.env['product.product'].search([('type', '=', 'consu')])
					for product in result:
						if product.qty_available < product.qty_min:
							name_att = ' '
							for attribute in product.product_template_attribute_value_ids:
								name_att = name_att + attribute.name + '  '
							if product.product_template_attribute_value_ids:
								name_pro = product.name + ' - ' + name_att + '  '
							else:
								name_pro = product.name
							products_list.append([0, 0, {
								'name': name_pro,
								'limit_quantity': product.qty_min,
								'stock_quantity': product.qty_available,
							}])
				else:
					# on_hand + reorder + template
					orderpoints = self.env['stock.warehouse.orderpoint'].search([])
					seen_products = set()
					for op in orderpoints:
						product = op.product_id
						if not product or product.type != 'consu':
							continue
						tmpl = product.product_tmpl_id
						if tmpl.id in seen_products:
							continue
						virtual_available = tmpl.virtual_available  # FIXED: was qty_available
						if virtual_available < op.product_min_qty:
							seen_products.add(tmpl.id)
							products_list.append([0, 0, {
								'name': tmpl.name,
								'limit_quantity': op.product_min_qty,
								'stock_quantity': virtual_available,  # FIXED: was qty_available
							}])

		if self.env.company.notification_base == 'fore_cast':

			if self.env.company.notification_products == 'for_all':

				if self.env.company.notification_product_type == 'variant':
					result = self.env['product.product'].search([
						('virtual_available', '<', self.env.company.min_quantity),
						('type', '=', 'consu')
					])
					for product in result:
						name_att = ' '
						for attribute in product.product_template_attribute_value_ids:
							name_att = name_att + attribute.name + '  '
						if product.product_template_attribute_value_ids:
							name_pro = product.name + ' - ' + name_att + '  '
						else:
							name_pro = product.name
						products_list.append([0, 0, {
							'name': name_pro,
							'limit_quantity': self.env.company.min_quantity,
							'stock_quantity': product.virtual_available,
						}])

				else:
					result = self.env['product.template'].search([])
					for product in result:
						if product.virtual_available < self.env.company.min_quantity:
							products_list.append([0, 0, {
								'name': product.name,
								'limit_quantity': self.env.company.min_quantity,
								'stock_quantity': product.virtual_available,
							}])

			if self.env.company.notification_products == 'fore_product':

				if self.env.company.notification_product_type == 'variant':
					result = self.env['product.product'].search([('type', '=', 'consu')])
					for product in result:
						if product.virtual_available < product.min_quantity:
							name_att = ' '
							for attribute in product.product_template_attribute_value_ids:
								name_att = name_att + attribute.name + '  '
							if product.product_template_attribute_value_ids:
								name_pro = product.name + ' - ' + name_att + '  '
							else:
								name_pro = product.name
							products_list.append([0, 0, {
								'name': name_pro,
								'limit_quantity': product.min_quantity,
								'stock_quantity': product.virtual_available,
							}])

				else:
					result = self.env['product.template'].search([('type', '=', 'consu')])
					for product in result:
						if product.virtual_available < product.temp_min_quantity:
							products_list.append([0, 0, {
								'name': product.name,
								'limit_quantity': product.temp_min_quantity,
								'stock_quantity': product.virtual_available,
							}])

			if self.env.company.notification_products == 'reorder':

				if self.env.company.notification_product_type == 'variant':
					result = self.env['product.product'].search([('type', '=', 'consu')])
					for product in result:
						if product.virtual_available < product.qty_min:
							name_att = ' '
							for attribute in product.product_template_attribute_value_ids:
								name_att = name_att + attribute.name + '  '
							if product.product_template_attribute_value_ids:
								name_pro = product.name + ' - ' + name_att + '  '
							else:
								name_pro = product.name
							products_list.append([0, 0, {
								'name': name_pro,
								'limit_quantity': product.qty_min,
								'stock_quantity': product.virtual_available,
							}])

				else:
					# on_hand + reorder + template
					orderpoints = self.env['stock.warehouse.orderpoint'].search([])
					seen_products = set()
					for op in orderpoints:
						product = op.product_id
						if not product or product.type != 'consu':
							continue
						tmpl = product.product_tmpl_id
						if tmpl.id in seen_products:
							continue
						virtual_available = tmpl.virtual_available  # FIXED: was qty_available
						if virtual_available < op.product_min_qty:
							seen_products.add(tmpl.id)
							products_list.append([0, 0, {
								'name': tmpl.name,
								'limit_quantity': op.product_min_qty,
								'stock_quantity': virtual_available,  # FIXED: was qty_available
							}])

		self.env.company.low_stock_products_ids = products_list

		return
	# def action_low_stock_send(self):

	# 	context = self._context
	# 	current_uid = context.get('uid')
	# 	su_id = self.env['res.users'].browse(current_uid)
	# 	self.action_list_products_()
	# 	company = self.env['res.company'].search([('notify_low_stock','=',True)])
	# 	res = self.env['res.config.settings'].search([],order="id desc", limit=1)
	# 	if su_id :
	# 		current_user = su_id
	# 	else:
	# 		current_user = self.env.user
	# 	if self.env.company.low_stock_products_ids:
	# 		if company:
	# 			for company_is in company:
	# 				template_id = self.env['ir.model.data']._xmlid_lookup('bi_product_low_stock_notification.low_stock_email_template')[1]
	# 				email_template_obj = self.env['mail.template'].browse(template_id)
	# 				if template_id:
	# 					values = email_template_obj._generate_template([res.id], ('subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'))[res.id]
	# 					values['email_from'] = current_user.email
	# 					values['email_to'] = company_is.email
	# 					values['author_id'] = current_user.partner_id.id
	# 					values['res_id'] = False
	# 					pdf = self.env['ir.actions.report']._render_qweb_pdf("bi_product_low_stock_notification.action_low_stock_report", res.id)
	# 					values['attachment_ids'] = [(0,0,{
	# 						'name': 'Product Low Stock Report',
	# 						'datas': base64.b64encode(pdf[0]),
	# 						'res_model': self._name,
	# 						'res_id': self.id,
	# 						'mimetype': 'application/pdf',
	# 						'type': 'binary',
	# 						})]
	# 					mail_mail_obj = self.env['mail.mail']
	# 					msg_id = mail_mail_obj.create(values)
	# 					if msg_id:
	# 						msg_id.send()
	# 				if pdf:
	# 					channel = self.env['discuss.channel'].channel_get(
	# 						[current_user.partner_id.id])
	# 					channel_id = self.env['discuss.channel'].browse(channel["id"])

	# 					channel_id.message_post(
	# 						author_id=current_user.partner_id.id,
	# 						attachments=[('Product Low Stock Report.pdf', pdf[0])],
	# 						body="List of products which have less on-hand quantity than the minimum quantity are",

	# 						message_type='comment',
	# 						subtype_xmlid='mail.mt_comment',
	# 					)

	# 		for partner in self.env['res.users'].search([]):
	# 			if partner.notify_user:
	# 				template_id = self.env['ir.model.data']._xmlid_lookup('bi_product_low_stock_notification.low_stock_email_template')[1]
	# 				email_template_obj = self.env['mail.template'].browse(template_id)
	# 				if template_id:
	# 					values = email_template_obj._generate_template([res.id], ('subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'))[res.id]
	# 					values['email_from'] = current_user.email
	# 					values['email_to'] = partner.email
	# 					values['author_id'] = current_user.partner_id.id
	# 					values['res_id'] = False
	# 					pdf = self.env['ir.actions.report']._render_qweb_pdf("bi_product_low_stock_notification.action_low_stock_report", res.id)
	# 					values['attachment_ids'] = [(0,0,{
	# 						'name': 'Product Low Stock Report',
	# 						'datas': base64.b64encode(pdf[0]),
	# 						'res_model': self._name,
	# 						'res_id': self.id,
	# 						'mimetype': 'application/pdf',
	# 						'type': 'binary',
	# 						})]
	# 					mail_mail_obj = self.env['mail.mail']
	# 					msg_id = mail_mail_obj.create(values)
	# 					if msg_id:
	# 						msg_id.send()

	# 				if pdf:
	# 					channel = self.env['discuss.channel'].channel_get(
	# 						[partner.partner_id.id])
	# 					channel_id = self.env['discuss.channel'].browse(channel["id"])

	# 					channel_id.message_post(
	# 						author_id=current_user.partner_id.id,
	# 						attachments=[('Product Low Stock Report.pdf', pdf[0])],
	# 						body="List of products which have less on-hand quantity than the minimum quantity are",

	# 						message_type='comment',
	# 						subtype_xmlid='mail.mt_comment',
	# 					)

	# 	return True


	def action_low_stock_send(self):

		context = self._context
		current_uid = context.get('uid') or self.env.uid
		current_user = self.env['res.users'].browse(current_uid)
		if not current_user.exists():
			current_user = self.env.user

		self.action_list_products_()

		company = self.env['res.company'].search([('notify_low_stock', '=', True)])

		if not self.env.company.low_stock_products_ids:
			return True

		template_id = self.env['ir.model.data']._xmlid_lookup(
			'bi_product_low_stock_notification.low_stock_email_template'
		)[1]
		email_template_obj = self.env['mail.template'].browse(template_id)

		# Render PDF once using self.id
		pdf = self.env['ir.actions.report']._render_qweb_pdf(
			'bi_product_low_stock_notification.action_low_stock_report',
			self.id,
		)

		def build_attachment():
			return [(0, 0, {
				'name': 'Product Low Stock Report',
				'datas': base64.b64encode(pdf[0]),
				'res_model': self._name,
				'res_id': self.id,
				'mimetype': 'application/pdf',
				'type': 'binary',
			})]

		def send_email(email_to):
			if not email_to:
				return
			values = email_template_obj._generate_template(
				[self.id],
				('subject', 'body_html', 'email_from', 'email_to',
				'partner_to', 'email_cc', 'reply_to', 'scheduled_date'),
			)[self.id]

			# Get outgoing mail server (SMTP)
			mail_server = self.env['ir.mail_server'].search([], order='sequence asc', limit=1)

			values['email_from'] = mail_server.smtp_user if mail_server else current_user.email
			values['email_to'] = email_to
			values['author_id'] = current_user.partner_id.id
			values['res_id'] = False
			values['attachment_ids'] = build_attachment()

			# Link SMTP server if found
			if mail_server:
				values['mail_server_id'] = mail_server.id

			msg_id = self.env['mail.mail'].create(values)
			if msg_id:
				msg_id.send()

		def send_discuss_notification(partner_id):
			channel = self.env['discuss.channel'].channel_get([partner_id])
			channel_id = self.env['discuss.channel'].browse(channel['id'])
			channel_id.message_post(
				author_id=current_user.partner_id.id,
				attachments=[('Product Low Stock Report.pdf', pdf[0])],
				body='List of products which have less on-hand quantity than the minimum quantity are',
				message_type='comment',
				subtype_xmlid='mail.mt_comment',
			)

		# Collect all emails to send to avoid duplicates
		emails_sent = set()

		# 1. Send to logged-in user (via SMTP)
		if current_user.email and current_user.email not in emails_sent:
			send_email(current_user.email)
			emails_sent.add(current_user.email)
			send_discuss_notification(current_user.partner_id.id)

		# 2. Send to companies with notify_low_stock = True
		if company:
			for company_is in company:
				if template_id and company_is.email and company_is.email not in emails_sent:
					send_email(company_is.email)
					emails_sent.add(company_is.email)

		# 3. Send to users with notify_user = True
		for partner in self.env['res.users'].search([]):
			if partner.notify_user:
				if template_id and partner.email and partner.email not in emails_sent:
					send_email(partner.email)
					emails_sent.add(partner.email)
				if partner.id != current_user.id:
					send_discuss_notification(partner.partner_id.id)

		return True

class LowstockLine(models.Model):
    _name = 'low.stock.line'
    _description = "Low Stock Line"

    name = fields.Char(string='Product name')
    stock_quantity = fields.Float(string='Quantity')
    limit_quantity = fields.Float(string='Quantity limit')
    stock_product_id = fields.Many2one('low.stock.notification')
    new_product_id = fields.Many2one('res.company')

    orderpoint_min_qty = fields.Float(
        string='Minimum Quantity',
        compute='_compute_orderpoint_fields'
    )

    orderpoint_qty_to_order = fields.Float(
        string='Quantity to Order',
        compute='_compute_orderpoint_fields'
    )

    # ADD THESE
    orderpoint_qty_forecast = fields.Float(
        string='Forecast Quantity',
        compute='_compute_orderpoint_fields'
    )

    orderpoint_max_qty = fields.Float(
        string='Maximum Quantity',
        compute='_compute_orderpoint_fields'
    )

    def _compute_orderpoint_fields(self):
        for rec in self:
            orderpoint = self.env['stock.warehouse.orderpoint'].search(
                [('product_id.name', '=', rec.name)], limit=1
            )

            rec.orderpoint_min_qty = orderpoint.product_min_qty if orderpoint else 0.0
            rec.orderpoint_qty_to_order = orderpoint.qty_to_order if orderpoint else 0.0
            rec.orderpoint_qty_forecast = orderpoint.qty_forecast if orderpoint else 0.0
            rec.orderpoint_max_qty = orderpoint.product_max_qty if orderpoint else 0.0