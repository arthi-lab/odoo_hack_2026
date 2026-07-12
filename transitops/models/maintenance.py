# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TransitopsMaintenance(models.Model):
    _name = 'transitops.maintenance'
    _description = 'TransitOps Maintenance'
    _order = 'id desc'

    vehicle_id = fields.Many2one('transitops.vehicle', string='Vehicle', required=True)
    trip_id = fields.Many2one('transitops.trip', string='Linked Trip')
    service_type = fields.Char(string='Service Type', required=True)
    cost = fields.Float(string='Cost', required=True, default=0.0)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    status = fields.Selection([
        ('active', 'In Shop'),
        ('completed', 'Completed')
    ], string='Status', required=True, default='active')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(TransitopsMaintenance, self).create(vals_list)
        for record in records:
            if record.status == 'active':
                record.vehicle_id.status = 'in_shop'
            elif record.status == 'completed' and record.vehicle_id.status == 'in_shop':
                record.vehicle_id.status = 'available'
        return records

    def write(self, vals):
        for record in self:
            old_status = record.status
            new_status = vals.get('status', old_status)
            
            # Check if vehicle has changed
            old_vehicle = record.vehicle_id
            new_vehicle = self.env['transitops.vehicle'].browse(vals.get('vehicle_id', old_vehicle.id))
            
            if old_status != new_status or old_vehicle != new_vehicle:
                if new_status == 'active':
                    new_vehicle.status = 'in_shop'
                    if old_vehicle != new_vehicle and old_vehicle.status == 'in_shop':
                        old_vehicle.status = 'available'
                elif new_status == 'completed':
                    new_vehicle.status = 'available'
                    if old_vehicle != new_vehicle and old_vehicle.status == 'in_shop':
                        old_vehicle.status = 'available'
                        
        res = super(TransitopsMaintenance, self).write(vals)
        
        # Trigger recomputation of linked trip expenses
        for record in self:
            if record.trip_id:
                expenses = self.env['transitops.expense'].search([('trip_id', '=', record.trip_id.id)])
                for expense in expenses:
                    expense._compute_maint_cost()
                    
        return res
