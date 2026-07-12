# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TransitopsDashboard(models.TransientModel):
    _name = 'transitops.dashboard'
    _description = 'TransitOps Dashboard'

    name = fields.Char(string='Name', default='TransitOps Dashboard')
    active_vehicles = fields.Integer(compute='_compute_metrics')
    available_vehicles = fields.Integer(compute='_compute_metrics')
    maintenance_vehicles = fields.Integer(compute='_compute_metrics')
    active_trips = fields.Integer(compute='_compute_metrics')
    pending_trips = fields.Integer(compute='_compute_metrics')
    drivers_on_duty = fields.Integer(compute='_compute_metrics')
    fleet_utilization = fields.Float(compute='_compute_metrics')

    # Progress bar percentages
    available_pct = fields.Float(compute='_compute_pct')
    on_trip_pct = fields.Float(compute='_compute_pct')
    in_shop_pct = fields.Float(compute='_compute_pct')
    retired_pct = fields.Float(compute='_compute_pct')

    # Counts for status display
    available_count = fields.Integer(compute='_compute_pct')
    on_trip_count = fields.Integer(compute='_compute_pct')
    in_shop_count = fields.Integer(compute='_compute_pct')
    retired_count = fields.Integer(compute='_compute_pct')

    recent_trip_ids = fields.Many2many('transitops.trip', compute='_compute_recent_trips')

    def _compute_metrics(self):
        for dashboard in self:
            vehicles = self.env['transitops.vehicle'].search([])
            active_v = len(vehicles.filtered(lambda v: v.status == 'on_trip'))
            available_v = len(vehicles.filtered(lambda v: v.status == 'available'))
            maint_v = len(vehicles.filtered(lambda v: v.status == 'in_shop'))

            trips = self.env['transitops.trip'].search([])
            active_t = len(trips.filtered(lambda t: t.status == 'dispatched'))
            pending_t = len(trips.filtered(lambda t: t.status == 'draft'))

            drivers = self.env['transitops.driver'].search([])
            drivers_duty = len(drivers.filtered(lambda d: d.status == 'on_trip'))

            total_active_available = active_v + available_v
            utilization = (active_v / total_active_available * 100.0) if total_active_available > 0 else 0.0

            dashboard.active_vehicles = active_v
            dashboard.available_vehicles = available_v
            dashboard.maintenance_vehicles = maint_v
            dashboard.active_trips = active_t
            dashboard.pending_trips = pending_t
            dashboard.drivers_on_duty = drivers_duty
            dashboard.fleet_utilization = utilization

    def _compute_pct(self):
        for dashboard in self:
            vehicles = self.env['transitops.vehicle'].search([])
            total = len(vehicles)
            if total == 0:
                dashboard.available_pct = 0
                dashboard.on_trip_pct = 0
                dashboard.in_shop_pct = 0
                dashboard.retired_pct = 0
                dashboard.available_count = 0
                dashboard.on_trip_count = 0
                dashboard.in_shop_count = 0
                dashboard.retired_count = 0
            else:
                c_avail = len(vehicles.filtered(lambda v: v.status == 'available'))
                c_trip = len(vehicles.filtered(lambda v: v.status == 'on_trip'))
                c_shop = len(vehicles.filtered(lambda v: v.status == 'in_shop'))
                c_retired = len(vehicles.filtered(lambda v: v.status == 'retired'))

                dashboard.available_pct = (c_avail / total) * 100.0
                dashboard.on_trip_pct = (c_trip / total) * 100.0
                dashboard.in_shop_pct = (c_shop / total) * 100.0
                dashboard.retired_pct = (c_retired / total) * 100.0

                dashboard.available_count = c_avail
                dashboard.on_trip_count = c_trip
                dashboard.in_shop_count = c_shop
                dashboard.retired_count = c_retired

    def _compute_recent_trips(self):
        for dashboard in self:
            dashboard.recent_trip_ids = self.env['transitops.trip'].search([], limit=5, order='id desc')

    def action_open_dashboard(self):
        record = self.create({})
        return {
            'name': 'TransitOps Dashboard',
            'type': 'ir.actions.act_window',
            'res_model': 'transitops.dashboard',
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
            'flags': {'initial_mode': 'view'},
        }
