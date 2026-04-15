# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DietPlan(models.Model):
    """Gym Diet Plan"""
    _name = 'diet.plan'
    _description = __doc__
    _rec_name = 'member_id'

    name = fields.Char(string='Title')
    member_id = fields.Many2one('res.partner')
    diet_plan_template_id = fields.Many2one('diet.plan.template', string='Diet Template')
    date = fields.Date()
    diet_meal_ids = fields.One2many('diet.meal', 'diet_plan_id', string='Diet Meals')
    charges = fields.Monetary()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company,
                                 ondelete='cascade', readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    invoice_id = fields.Many2one('account.move', copy=False)
    invoice_status = fields.Selection(related="invoice_id.status_in_payment")

    dietitian_id = fields.Many2one('res.users')

    diet_category_id = fields.Many2one('diet.category')
    diet_type_id = fields.Many2one('diet.type')
    total_calories = fields.Float(compute="_compute_calories_plan")

    @api.ondelete(at_uninstall=False)
    def _prevent_delete_invoiced_records(self):
        """ Prevent delete invoiced records """
        for rec in self:
            if rec.invoice_id:
                raise ValidationError(_('You cannot delete invoiced records.'))

    @api.onchange('diet_plan_template_id')
    def _onchange_template(self):
        """onchange template"""
        self.charges = self.diet_plan_template_id.charges

    @api.depends('diet_meal_ids')
    def _compute_calories_plan(self):
        """compute calories plan"""
        for rec in self:
            total = 0.0
            for data in rec.diet_meal_ids:
                total += data.total_calories
            rec.total_calories = total

    def clear_template_data(self):
        """clear template data"""
        for rec in self:
            if rec.diet_plan_template_id:
                rec.diet_plan_template_id = False
                for data in rec.diet_meal_ids:
                    data.unlink()

    def compute_diet_meal(self):
        """compute diet meal"""
        for record in self:
            if record.diet_plan_template_id:
                for rec in record.diet_plan_template_id.diet_meal_template_ids:
                    data = {
                        'name': rec.name,
                        'day': rec.day,
                        'diet_plan_id': record.id
                    }
                    diet_meal_id = self.env['diet.meal'].create(data)
                    for data in rec.breakfast_ids:
                        data_breakfast = {
                            'meal_type': data.meal_type,
                            'food_item_id': data.food_item_id.id,
                            'unit': data.unit,
                            'meal_time': data.meal_time,
                            'qty': data.qty,
                            'diet_meal_id': diet_meal_id.id,
                        }
                        self.env['meal.type'].create(data_breakfast)
                    for data in rec.morning_snack_ids:
                        data_morning_snack = {
                            'meal_type': data.meal_type,
                            'food_item_id': data.food_item_id.id,
                            'unit': data.unit,
                            'meal_time': data.meal_time,
                            'qty': data.qty,
                            'diet_meal_id': diet_meal_id.id,
                        }
                        self.env['meal.type'].create(data_morning_snack)
                    for data in rec.lunch_ids:
                        data_lunch = {
                            'meal_type': data.meal_type,
                            'food_item_id': data.food_item_id.id,
                            'meal_time': data.meal_time,
                            'unit': data.unit,
                            'qty': data.qty,
                            'diet_meal_id': diet_meal_id.id,
                        }
                        self.env['meal.type'].create(data_lunch)
                    for data in rec.evening_snack_ids:
                        data_evening_snack = {
                            'meal_type': data.meal_type,
                            'food_item_id': data.food_item_id.id,
                            'meal_time': data.meal_time,
                            'unit': data.unit,
                            'qty': data.qty,
                            'diet_meal_id': diet_meal_id.id,
                        }
                        self.env['meal.type'].create(data_evening_snack)
                    for data in rec.dinner_ids:
                        data_dinner = {
                            'meal_type': data.meal_type,
                            'food_item_id': data.food_item_id.id,
                            'meal_time': data.meal_time,
                            'unit': data.unit,
                            'qty': data.qty,
                            'diet_meal_id': diet_meal_id.id,
                        }
                        self.env['meal.type'].create(data_dinner)
                    for data in rec.diet_nutrient_ids:
                        data_nutrient = {
                            'nutrient_id': data.nutrient_id.id,
                            'value': data.value,
                            'unit': data.unit,
                            'diet_meal_id': diet_meal_id.id,
                        }
                        self.env['diet.nutrient'].create(data_nutrient)

    def action_invoice(self):
        """action invoice"""
        data = {
            'product_id': self.env.ref('tk_gym_management.gym_diet_nutrients').id,
            'name': self.name,
            'quantity': 1,
            'price_unit': self.charges
        }
        invoice_line = [(0, 0, data)]
        record = {
            'partner_id': self.member_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_line,
            'move_type': 'out_invoice',
            'diet_plan_id': self.id,

        }
        invoice_id = self.env['account.move'].sudo().create(record)
        self.invoice_id = invoice_id.id
        return {
            'type': "ir.actions.act_window",
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice_id.id,
            'view_mode': 'form',
            'target': 'current'
        }


class DietMeal(models.Model):
    """Gym Diet Meal"""
    _name = 'diet.meal'
    _description = __doc__

    name = fields.Char(string='Title')
    day = fields.Selection([('sunday', 'Sunday'), ('monday', 'Monday'), ('tuesday', 'Tuesday'),
                            ('wednesday', 'Wednesday'), ('thursday', 'Thursday'),
                            ('friday', 'Friday'),
                            ('saturday', 'Saturday')])
    diet_plan_id = fields.Many2one('diet.plan', ondelete='cascade')
    breakfast_ids = fields.One2many('meal.type', 'diet_meal_id',
                                    domain=[('meal_type', '=', 'breakfast')])
    morning_snack_ids = fields.One2many('meal.type', 'diet_meal_id',
                                        domain=[('meal_type', '=', 'midmorningsnacks')])
    lunch_ids = fields.One2many('meal.type', 'diet_meal_id',
                                domain=[('meal_type', '=', 'lunch')])
    evening_snack_ids = fields.One2many('meal.type', 'diet_meal_id',
                                        domain=[('meal_type', '=', 'evening-snacks')])
    dinner_ids = fields.One2many('meal.type', 'diet_meal_id',
                                 domain=[('meal_type', '=', 'dinner')])
    diet_nutrient_ids = fields.One2many('diet.nutrient', 'diet_meal_id', string='Nutrients')

    breakfast_calories = fields.Float(compute="_compute_breakfast_calories")
    morning_snack_calories = fields.Float(compute="_compute_morning_snack_calories")
    lunch_calories = fields.Float(compute="_compute_lunch_calories")
    evening_snack_calories = fields.Float(compute="_compute_evening_snack_calories")
    dinner_calories = fields.Float(compute="_compute_dinner_calories")

    total_calories = fields.Float(compute='_compute_total_calories', string='Calories per Day')

    @api.depends('dinner_ids')
    def _compute_dinner_calories(self):
        """compute dinner calories"""
        for rec in self:
            calories = 0.0
            for data in rec.dinner_ids:
                calories += data.total_calories
            rec.dinner_calories = calories

    @api.depends('evening_snack_ids')
    def _compute_evening_snack_calories(self):
        """compute evening snack calories"""
        for rec in self:
            calories = 0.0
            for data in rec.evening_snack_ids:
                calories += data.total_calories
            rec.evening_snack_calories = calories

    @api.depends('breakfast_ids')
    def _compute_breakfast_calories(self):
        """compute breakfast calories"""
        for rec in self:
            calories = 0.0
            for data in rec.breakfast_ids:
                calories += data.total_calories
            rec.breakfast_calories = calories

    @api.depends('morning_snack_ids')
    def _compute_morning_snack_calories(self):
        """compute morning snack calories"""
        for rec in self:
            calories = 0.0
            for data in rec.morning_snack_ids:
                calories += data.total_calories
            rec.morning_snack_calories = calories

    @api.depends('lunch_ids')
    def _compute_lunch_calories(self):
        """compute lunch calories"""
        for rec in self:
            calories = 0.0
            for data in rec.lunch_ids:
                calories += data.total_calories
            rec.lunch_calories = calories

    @api.depends('breakfast_calories', 'morning_snack_calories', 'lunch_calories',
                 'evening_snack_calories',
                 'dinner_calories')
    def _compute_total_calories(self):
        """compute total calories"""
        for rec in self:
            rec.total_calories = (rec.breakfast_calories
                                  + rec.morning_snack_calories
                                  + rec.lunch_calories
                                  + rec.evening_snack_calories
                                  + rec.dinner_calories)


class DietMealTemplate(models.Model):
    """Diet Meal Template"""
    _name = 'diet.meal.template'
    _description = __doc__

    name = fields.Char(string='Title')
    day = fields.Selection([('sunday', 'Sunday'), ('monday', 'Monday'), ('tuesday', 'Tuesday'),
                            ('wednesday', 'Wednesday'), ('thursday', 'Thursday'),
                            ('friday', 'Friday'),
                            ('saturday', 'Saturday')])
    breakfast_ids = fields.One2many('meal.type.template', 'diet_meal_template_id',
                                    domain=[('meal_type', '=', 'breakfast')])
    morning_snack_ids = fields.One2many('meal.type.template', 'diet_meal_template_id',
                                        domain=[('meal_type', '=', 'midmorningsnacks')])
    lunch_ids = fields.One2many('meal.type.template', 'diet_meal_template_id',
                                domain=[('meal_type', '=', 'lunch')])
    evening_snack_ids = fields.One2many('meal.type.template', 'diet_meal_template_id',
                                        domain=[('meal_type', '=', 'evening-snacks')])
    dinner_ids = fields.One2many('meal.type.template', 'diet_meal_template_id',
                                 domain=[('meal_type', '=', 'dinner')])
    diet_nutrient_ids = fields.One2many('diet.nutrient.template', 'diet_meal_template_id',
                                        string='Nutrients')
    diet_plan_template_id = fields.Many2one('diet.plan.template')

    breakfast_calories = fields.Float(compute="_compute_t_breakfast_calories")
    morning_snack_calories = fields.Float(compute="_compute_t_morning_snack_calories")
    lunch_calories = fields.Float(compute="_compute_t_lunch_calories")
    evening_snack_calories = fields.Float(compute="_compute_t_evening_snack_calories")
    dinner_calories = fields.Float(compute="_compute_t_dinner_calories")

    total_calories = fields.Float(compute='_compute_t_total_calories', string='Calories per Day')

    @api.depends('dinner_ids')
    def _compute_t_dinner_calories(self):
        """compute dinner calories"""
        for rec in self:
            calories = 0.0
            for data in rec.dinner_ids:
                calories += data.total_calories
            rec.dinner_calories = calories

    @api.depends('evening_snack_ids')
    def _compute_t_evening_snack_calories(self):
        """compute evening snack calories"""
        for rec in self:
            calories = 0.0
            for data in rec.evening_snack_ids:
                calories += data.total_calories
            rec.evening_snack_calories = calories

    @api.depends('breakfast_ids')
    def _compute_t_breakfast_calories(self):
        """compute breakfast calories"""
        for rec in self:
            calories = 0.0
            for data in rec.breakfast_ids:
                calories += data.total_calories
            rec.breakfast_calories = calories

    @api.depends('morning_snack_ids')
    def _compute_t_morning_snack_calories(self):
        """compute morning snack calories"""
        for rec in self:
            calories = 0.0
            for data in rec.morning_snack_ids:
                calories += data.total_calories
            rec.morning_snack_calories = calories

    @api.depends('lunch_ids')
    def _compute_t_lunch_calories(self):
        """compute lunch calories"""
        for rec in self:
            calories = 0.0
            for data in rec.lunch_ids:
                calories += data.total_calories
            rec.lunch_calories = calories

    @api.depends('breakfast_calories', 'morning_snack_calories', 'lunch_calories',
                 'evening_snack_calories',
                 'dinner_calories')
    def _compute_t_total_calories(self):
        """compute total calories"""
        for rec in self:
            rec.total_calories = (rec.breakfast_calories
                                  + rec.morning_snack_calories
                                  + rec.lunch_calories
                                  + rec.evening_snack_calories
                                  + rec.dinner_calories)


class DietPlanTemplate(models.Model):
    """Templates For Diet Plans"""
    _name = 'diet.plan.template'
    _description = __doc__

    name = fields.Char(string="Template Name")
    diet_meal_template_ids = fields.One2many('diet.meal.template', 'diet_plan_template_id')
    charges = fields.Monetary()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company,
                                 ondelete='cascade', readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    diet_category_id = fields.Many2one('diet.category')
    diet_type_id = fields.Many2one('diet.type')
    total_calories = fields.Float(compute="_compute_calories_template")

    @api.depends('diet_meal_template_ids')
    def _compute_calories_template(self):
        """compute calories template"""
        for rec in self:
            total = 0.0
            for data in rec.diet_meal_template_ids:
                total += data.total_calories
            rec.total_calories = total


class DietNutrients(models.Model):
    """Gym Diet Nutrient"""
    _name = 'diet.nutrient'
    _description = __doc__
    _rec_name = 'nutrient_id'

    nutrient_id = fields.Many2one('nutrient.type')
    value = fields.Float()
    unit = fields.Selection([('gm', 'gm'), ('mg', 'mg')])
    diet_meal_id = fields.Many2one('diet.meal', ondelete='cascade')


class DietNutrientsTemplate(models.Model):
    """Diet Nutrients Template"""
    _name = 'diet.nutrient.template'
    _description = __doc__
    _rec_name = 'nutrient_id'

    nutrient_id = fields.Many2one('nutrient.type')
    value = fields.Float()
    unit = fields.Selection([('gm', 'gm'), ('mg', 'mg')])
    diet_meal_template_id = fields.Many2one('diet.meal.template')


class MealType(models.Model):
    """Gym Meal Type"""
    _name = 'meal.type'
    _description = __doc__
    _rec_name = 'meal_type'

    meal_type = fields.Selection(
        [('breakfast', 'Breakfast'), ('midmorningsnacks', 'Mid Morning Snacks'),
         ('lunch', 'Lunch'), ('evening-snacks', 'Evening Snacks'), ('dinner', 'Dinner')])

    food_item_id = fields.Many2one('food.item')
    meal_time = fields.Float(string='Time')
    qty = fields.Float(string='Intake Qty')
    unit = fields.Selection([('unit', 'Unit'), ('gm', 'gm'), ('ml', 'ml'), ('ltr', 'ltr')],
                            string='Unit ')
    diet_meal_id = fields.Many2one('diet.meal', ondelete='cascade')
    intake_unit_id = fields.Many2one('uom.uom', related='food_item_id.unit_id',
                                     string='Intake Unit')
    food_unit_id = fields.Many2one('uom.uom', related='food_item_id.unit_id')
    calories = fields.Float(related='food_item_id.calories', string='Calories per Unit')
    total_calories = fields.Float(string='Calories', compute='_compute_calories')

    @api.depends('qty')
    def _compute_calories(self):
        """compute calories"""
        for rec in self:
            rec.total_calories = rec.calories * rec.qty

    @api.constrains('meal_time')
    def _check_meal_time(self):
        """check meal time"""
        for rec in self:
            if rec.meal_time <= 0 or rec.meal_time > 24:
                raise ValidationError(
                    _("For %s meal time must be between 1 to 24 hours.", rec.diet_meal_id.name))


class MealTypeTemplate(models.Model):
    """Meal Type Template"""
    _name = 'meal.type.template'
    _description = __doc__
    _rec_name = 'meal_type'

    meal_type = fields.Selection(
        [('breakfast', 'Breakfast'), ('midmorningsnacks', 'Mid Morning Snacks'),
         ('lunch', 'Lunch'), ('evening-snacks', 'Evening Snacks'), ('dinner', 'Dinner')])

    food_item_id = fields.Many2one('food.item')
    meal_time = fields.Float(string='Time')
    qty = fields.Float(string='Intake Qty')
    unit = fields.Selection([('unit', 'Unit'), ('gm', 'gm'), ('ml', 'ml'), ('ltr', 'ltr')],
                            string='Unit ')
    diet_meal_template_id = fields.Many2one('diet.meal.template')
    intake_unit_id = fields.Many2one('uom.uom', related='food_item_id.unit_id',
                                     string='Intake Unit')
    food_unit_id = fields.Many2one('uom.uom', related='food_item_id.unit_id')
    calories = fields.Float(related='food_item_id.calories', string='Calories per Unit')
    total_calories = fields.Float(string='Calories', compute='_compute_t_calories')

    @api.depends('qty')
    def _compute_t_calories(self):
        """compute calories"""
        for rec in self:
            rec.total_calories = rec.calories * rec.qty

    @api.constrains('meal_time')
    def _check_meal_time(self):
        """check meal time"""
        for rec in self:
            if rec.meal_time <= 0 or rec.meal_time > 24:
                raise ValidationError(
                    _("For %s meal time must be between 1 to 24 hours.",
                      rec.diet_meal_template_id.name))


class FoodItem(models.Model):
    """Gym Food Item"""
    _name = 'food.item'
    _description = __doc__
    _rec_name = 'name'

    name = fields.Char()
    food_type = fields.Selection([('vegetables', 'Vegetables'), ('fruits', 'Fruits'),
                                  ('cereals', 'Cereals'), ('tubers', 'Tubers'),
                                  ('legumes', 'Legumes'),
                                  ('Dairy', 'Dairy'), ('meat', 'Meat'), ('sweet', 'Sweet'),
                                  ('processed', 'Processed Food')])
    avatar = fields.Binary()
    unit_id = fields.Many2one('uom.uom')
    calories = fields.Float()


class NutrientType(models.Model):
    """Gym Nutrient Type"""
    _name = 'nutrient.type'
    _description = __doc__
    _rec_name = 'name'

    name = fields.Char()
    avatar = fields.Binary()
