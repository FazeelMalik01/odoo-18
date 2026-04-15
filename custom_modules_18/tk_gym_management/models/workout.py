# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api

# from odoo.addons.website.tools import get_video_embed_code
from odoo.addons.web_editor.tools import get_video_embed_code


class GymWorkout(models.Model):
    """Workout"""

    _name = "gym.workout"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = __doc__
    _rec_name = "name"

    avatar = fields.Binary()
    name = fields.Char()
    trainer_id = fields.Many2one(
        "hr.employee", string="Support Trainer", domain=[("is_trainer", "=", True)]
    )
    workout_day_ids = fields.Many2many("workout.days", string="Workout Days")
    calories_burn = fields.Integer()
    number_of_days = fields.Integer(string="No. of Days")
    workout_exercise_ids = fields.One2many(
        "workout.exercise", "gym_workout_id", string="Workout Exercises"
    )
    color = fields.Integer()


class WorkoutExercise(models.Model):
    """Workout Exercise"""

    _name = "workout.exercise"
    _description = __doc__
    _rec_name = "exercise_id"

    exercise_id = fields.Many2one("gym.exercise", string="Exercise")
    exercise_for_id = fields.Many2many("exercise.for")
    equipment_ids = fields.Many2many("gym.equipment", string="Equipments")
    exercise_sets = fields.Integer(string="Sets")
    sets_repeat = fields.Integer(string="Repeat")
    weight = fields.Float()
    gym_workout_id = fields.Many2one("gym.workout", ondelete="cascade")
    color = fields.Integer()

    @api.onchange("exercise_id")
    def _onchange_exercise(self):
        """onchange exercise"""
        self.exercise_for_id = self.exercise_id.exercise_for_id
        self.equipment_ids = self.exercise_id.equipment_ids


class WorkoutDays(models.Model):
    """Workout Days"""

    _name = "workout.days"
    _description = __doc__
    _rec_name = "day"

    color = fields.Integer(default=1)
    day = fields.Char()


class GymExerciseFor(models.Model):
    """Gym Exercise For"""

    _name = "exercise.for"
    _description = __doc__
    _rec_name = "name"

    color = fields.Integer(default=1)
    name = fields.Char(string="Exercise For")


class GymExercise(models.Model):
    """Gym Exercise"""

    _name = "gym.exercise"
    _description = __doc__
    _inherit = ["mail.thread", "mail.activity.mixin", "image.mixin"]

    avatar = fields.Binary()
    name = fields.Char(string="Exercise Name")
    exercise_for_id = fields.Many2many("exercise.for")
    available_equipment_ids = fields.Many2many(
        "gym.equipment",
        compute="_compute_available_equipment_ids",
        column1="gym_exercise",
        column2="gym_equipment",
        relation="exercise_equipment_rel",
    )
    equipment_ids = fields.Many2many(
        "gym.equipment", string="Equipments", domain="[('id', 'in', available_equipment_ids)]"
    )
    instruction = fields.Html(string="Instructions")
    exercise_step_ids = fields.One2many(
        "gym.exercise.step", "gym_exercise_id", string="Exercise Steps"
    )
    benefits = fields.Html()
    approx_time = fields.Char(string="Average time of Exercise")
    calories_burn_per_hour = fields.Integer(string="Calories Burn")
    color = fields.Integer()
    note_benefit = fields.Html()
    note_step = fields.Html()
    exercise_video = fields.Html(compute="_compute_get_video_preview", sanitize=False)
    video_url = fields.Char("Video URL", help="URL of a video for showcasing your product.")
    image = fields.Binary(" Image ", help="This field holds the image")

    @api.depends("exercise_for_id")
    def _compute_available_equipment_ids(self):
        """Compute Available Equipments"""
        for rec in self:
            if rec.exercise_for_id:
                equipment_ids = (
                    self.env["gym.equipment"]
                    .sudo()
                    .search([("exercise_for", "in", rec.exercise_for_id.ids)])
                    .ids
                )
            else:
                equipment_ids = []

            rec.available_equipment_ids = [(6, 0, equipment_ids)]

    @api.depends("video_url")
    def _compute_get_video_preview(self):
        """to get video field"""
        for image in self:
            image.exercise_video = get_video_embed_code(image.video_url) or False

    @api.onchange("exercise_for_id")
    def _onchange_exercise_for_id(self):
        """onchange exercise for id set empty equipment ids"""
        for rec in self:
            rec.equipment_ids = False


class GymExerciseStep(models.Model):
    """Gym Exercise Steps"""

    _name = "gym.exercise.step"
    _description = __doc__
    _rec_name = "name"

    name = fields.Char(string="Title")
    step_image = fields.Binary(string="Image")
    gym_exercise_id = fields.Many2one("gym.exercise")
    color = fields.Integer()
