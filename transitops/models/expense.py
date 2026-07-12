# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TransitopsExpense(models.Model):
    _name = 'transitops.expense'
    _description = 'TransitOps Expense'
    _order = 'id desc'

    trip_id = fields.Many2one('transitops.trip', string='Trip', required=True)
    vehicle_id = fields.Many2one(
        'transitops.vehicle', 
        string='Vehicle', 
        related='trip_id.vehicle_id', 
        store=True, 
        readonly=True
    )
    toll_cost = fields.Float(string='Toll Cost', default=0.0)
    other_cost = fields.Float(string='Other Cost', default=0.0)
    
    maint_cost = fields.Float(
        string='Maintenance (Linked)', 
        compute='_compute_maint_cost', 
        store=True
    )
    total_cost = fields.Float(
        string='Total Cost', 
        compute='_compute_total_cost', 
        store=True
    )

    @api.depends('trip_id')
    def _compute_maint_cost(self):
        for expense in self:
            if expense.trip_id:
                maintenances = self.env['transitops.maintenance'].search([
                    ('trip_id', '=', expense.trip_id.id),
                    ('status', '=', 'completed')
                ])
                expense.maint_cost = sum(maintenances.mapped('cost'))
            else:
                expense.maint_cost = 0.0

    @api.depends('toll_cost', 'other_cost', 'maint_cost')
    def _compute_total_cost(self):
        for expense in self:
            expense.total_cost = expense.toll_cost + expense.other_cost + expense.maint_cost
