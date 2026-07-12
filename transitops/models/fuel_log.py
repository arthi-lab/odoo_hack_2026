# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TransitopsFuelLog(models.Model):
    _name = 'transitops.fuel_log'
    _description = 'TransitOps Fuel Log'
    _order = 'date desc, id desc'

    vehicle_id = fields.Many2one('transitops.vehicle', string='Vehicle', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    liters = fields.Float(string='Liters', required=True, default=0.0)
    fuel_cost = fields.Float(string='Fuel Cost', required=True, default=0.0)
