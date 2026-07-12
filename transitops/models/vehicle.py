# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TransitopsVehicle(models.Model):
    _name = 'transitops.vehicle'
    _description = 'TransitOps Vehicle'
    _rec_name = 'registration_no'

    registration_no = fields.Char(string='Registration No.', required=True, copy=False)
    name = fields.Char(string='Model/Name', required=True)
    type = fields.Selection([
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('mini', 'Mini')
    ], string='Type', required=True, default='van')
    capacity_kg = fields.Integer(string='Capacity (kg)', required=True, default=0)
    odometer = fields.Integer(string='Odometer (km)', required=True, default=0)
    acquisition_cost = fields.Float(string='Acquisition Cost', required=True, default=0.0)
    status = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('in_shop', 'In Shop'),
        ('retired', 'Retired')
    ], string='Status', required=True, default='available')

    _sql_constraints = [
        ('registration_no_unique', 'unique(registration_no)', 'The registration number must be unique!')
    ]
