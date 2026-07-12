# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TransitopsTrip(models.Model):
    _name = 'transitops.trip'
    _description = 'TransitOps Trip'
    _order = 'id desc'

    name = fields.Char(
        string='Trip ID', 
        required=True, 
        copy=False, 
        readonly=True, 
        default=lambda self: '/'
    )
    source = fields.Char(string='Source', required=True)
    destination = fields.Char(string='Destination', required=True)
    
    vehicle_id = fields.Many2one(
        'transitops.vehicle', 
        string='Vehicle', 
        required=True,
        domain="[('status', '=', 'available')]"
    )
    driver_id = fields.Many2one(
        'transitops.driver', 
        string='Driver', 
        required=True,
        domain="[('status', '=', 'available')]"
    )
    
    cargo_weight = fields.Integer(string='Cargo Weight (kg)', required=True)
    planned_distance = fields.Float(string='Planned Distance (km)', required=True)
    eta = fields.Char(string='ETA', default='Awaiting vehicle')
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('dispatched', 'Dispatched'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', required=True, default='draft')

    final_odometer = fields.Integer(string='Final Odometer (km)')
    notes = fields.Text(string='Notes/Remarks')
    scheduled_date = fields.Date(string='Scheduled Date', default=fields.Date.today)
    actual_start = fields.Datetime(string='Actual Start')
    actual_end = fields.Datetime(string='Actual End')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('transitops.trip') or '/'
        return super(TransitopsTrip, self).create(vals_list)

    @api.constrains('vehicle_id', 'cargo_weight', 'driver_id', 'status', 'final_odometer')
    def _check_trip_rules(self):
        for trip in self:
            if trip.status == 'dispatched':
                if trip.cargo_weight > trip.vehicle_id.capacity_kg:
                    raise ValidationError(_(
                        "Vehicle Capacity: %s kg, Cargo Weight: %s kg. "
                        "Capacity exceeded by %s kg - dispatch blocked."
                    ) % (trip.vehicle_id.capacity_kg, trip.cargo_weight, trip.cargo_weight - trip.vehicle_id.capacity_kg))
                
                if trip.driver_id.is_expired:
                    raise ValidationError(_("Dispatch blocked: Selected driver's license is expired."))
                
                if trip.driver_id.safety_status == 'suspended' or trip.driver_id.status == 'suspended':
                    raise ValidationError(_("Dispatch blocked: Selected driver is suspended."))

            if trip.status == 'completed':
                if not trip.final_odometer:
                    raise ValidationError(_("Please specify the Final Odometer reading to complete the trip."))
                if trip.final_odometer < trip.vehicle_id.odometer:
                    raise ValidationError(_(
                        "Final odometer (%s km) cannot be less than the starting odometer (%s km)."
                    ) % (trip.final_odometer, trip.vehicle_id.odometer))

    def write(self, vals):
        # Track status changes to manage vehicle and driver availability
        for trip in self:
            old_status = trip.status
            new_status = vals.get('status', old_status)

            if old_status != new_status:
                if new_status == 'dispatched':
                    # Ensure vehicle and driver are currently available before taking them
                    if trip.vehicle_id.status != 'available':
                        raise ValidationError(_("Vehicle %s is not available (Status: %s)") % (trip.vehicle_id.registration_no, trip.vehicle_id.status))
                    if trip.driver_id.status != 'available':
                        raise ValidationError(_("Driver %s is not available (Status: %s)") % (trip.driver_id.name, trip.driver_id.status))
                    
                    trip.vehicle_id.status = 'on_trip'
                    trip.driver_id.status = 'on_trip'
                    vals['actual_start'] = fields.Datetime.now()
                
                elif new_status == 'completed':
                    # Update vehicle odometer
                    final_odo = vals.get('final_odometer', trip.final_odometer)
                    if not final_odo:
                        raise ValidationError(_("Please specify the Final Odometer reading to complete the trip."))
                    if final_odo < trip.vehicle_id.odometer:
                        raise ValidationError(_(
                            "Final odometer (%s km) cannot be less than the starting odometer (%s km)."
                        ) % (final_odo, trip.vehicle_id.odometer))
                    trip.vehicle_id.odometer = final_odo
                    
                    # Reset vehicle and driver to available
                    trip.vehicle_id.status = 'available'
                    trip.driver_id.status = 'available'
                    vals['actual_end'] = fields.Datetime.now()
                    
                    # Recompute driver trip completion rate
                    # Trigger rate recomputation
                    self.env.cr.execute(
                        "UPDATE transitops_driver SET status='available' WHERE id = %s",
                        [trip.driver_id.id]
                    )
                
                elif new_status == 'cancelled':
                    # Release vehicle and driver
                    trip.vehicle_id.status = 'available'
                    trip.driver_id.status = 'available'

        res = super(TransitopsTrip, self).write(vals)
        
        # Trigger trip completion rate updates if any trips were marked completed
        if 'status' in vals:
            for trip in self:
                trip.driver_id._compute_trip_completion_rate()
                
        return res

    def action_dispatch(self):
        self.write({'status': 'dispatched', 'eta': '45 min'})

    def action_complete(self):
        # This will be called from a wizard or simple form button after filling final_odometer
        if not self.final_odometer:
            # Let's set a default final_odometer just in case
            self.final_odometer = self.vehicle_id.odometer + int(self.planned_distance)
        self.write({'status': 'completed'})

    def action_cancel(self):
        self.write({'status': 'cancelled'})
