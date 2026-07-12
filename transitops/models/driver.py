# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class TransitopsDriver(models.Model):
    _name = 'transitops.driver'
    _description = 'TransitOps Driver'

    name = fields.Char(string='Driver Name', required=True)
    license_no = fields.Char(string='License No.', required=True)
    category = fields.Selection([
        ('lmv', 'LMV'),
        ('hmv', 'HMV')
    ], string='Category', required=True, default='lmv')
    license_expiry = fields.Date(string='License Expiry', required=True)
    contact = fields.Char(string='Contact No.', required=True)
    
    trip_completion_rate = fields.Float(
        string='Trip Completion Rate (%)', 
        compute='_compute_trip_completion_rate', 
        store=True, 
        default=100.0
    )
    
    safety_status = fields.Selection([
        ('available', 'Available'),
        ('suspended', 'Suspended')
    ], string='Safety Rating', required=True, default='available')
    
    status = fields.Selection([
        ('available', 'Available'),
        ('suspended', 'Suspended'),
        ('on_trip', 'On Trip'),
        ('off_duty', 'Off Duty')
    ], string='Status', required=True, default='available')
    
    is_expired = fields.Boolean(
        string='License Expired', 
        compute='_compute_is_expired', 
        store=True
    )

    @api.depends('license_expiry')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for driver in self:
            if driver.license_expiry:
                driver.is_expired = driver.license_expiry < today
            else:
                driver.is_expired = False

    @api.onchange('safety_status')
    def _onchange_safety_status(self):
        for driver in self:
            if driver.safety_status == 'suspended':
                driver.status = 'suspended'
            elif driver.status == 'suspended':
                driver.status = 'available'

    @api.depends('name') # In Odoo, depends can trigger on a dummy field or we update it when completing trips
    def _compute_trip_completion_rate(self):
        for driver in self:
            trips = self.env['transitops.trip'].search([('driver_id', '=', driver.id)])
            total_trips = len(trips)
            if total_trips == 0:
                driver.trip_completion_rate = 100.0
            else:
                completed = len(trips.filtered(lambda t: t.status == 'completed'))
                driver.trip_completion_rate = (completed / total_trips) * 100.0
