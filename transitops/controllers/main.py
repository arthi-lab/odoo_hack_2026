# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.addons.web.controllers.home import Home
from odoo.http import request
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)

class TransitopsHome(Home):

    @http.route('/web/login', type='http', auth='none', readonly=False)
    def web_login(self, redirect=None, **kw):
        role_rbac = request.params.get('role_rbac')
        
        # Call super to authenticate standard credentials
        response = super(TransitopsHome, self).web_login(redirect=redirect, **kw)

        # If login was successful (session has uid)
        if request.httprequest.method == 'POST' and request.session.uid:
            user = request.env['res.users'].sudo().browse(request.session.uid)
            
            # System administrators (admin or superuser) bypass role checks to prevent lockout
            if user.id == 1 or user.has_group('base.group_system'):
                return request.redirect('/transitops/dashboard/admin')

            ROLE_GROUPS = {
                'fleet_manager': 'transitops.group_transitops_fleet_manager',
                'dispatcher': 'transitops.group_transitops_dispatcher',
                'safety_officer': 'transitops.group_transitops_safety_officer',
                'financial_analyst': 'transitops.group_transitops_financial_analyst',
            }

            if role_rbac in ROLE_GROUPS:
                group_xml_id = ROLE_GROUPS[role_rbac]
                if not user.has_group(group_xml_id):
                    # User authenticated but lacks the selected role
                    request.session.logout()
                    
                    values = {k: v for k, v in request.params.items() if k in ['login', 'redirect', 'db']}
                    values['error'] = _("Access Denied: You do not have the %s role.") % dict(self._get_roles_list()).get(role_rbac, role_rbac)
                    values['roles'] = self._get_roles_list()
                    values['role_rbac'] = role_rbac
                    
                    response = request.render('web.login', values)
                    response.headers['Cache-Control'] = 'no-cache'
                    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
                    return response
                else:
                    return request.redirect(f'/transitops/dashboard/{role_rbac}')
            else:
                # No valid role selected for a non-admin user
                request.session.logout()
                values = {k: v for k, v in request.params.items() if k in ['login', 'redirect', 'db']}
                values['error'] = _("Access Denied: Please select a valid role.")
                values['roles'] = self._get_roles_list()
                
                response = request.render('web.login', values)
                response.headers['Cache-Control'] = 'no-cache'
                response.headers['X-Frame-Options'] = 'SAMEORIGIN'
                return response

        # Inject roles list into context for web.login template
        if isinstance(response, http.Response) and response.qcontext:
            response.qcontext['roles'] = self._get_roles_list()
            if 'role_rbac' in request.params:
                response.qcontext['role_rbac'] = request.params.get('role_rbac')
        return response

    @http.route(['/transitops/dashboard', '/transitops/dashboard/<string:role>'], type='http', auth='user', readonly=False)
    def transitops_dashboard_portal(self, role=None, **kw):
        user = request.env.user
        
        # Determine role if not specified
        if not role:
            if user.has_group('transitops.group_transitops_fleet_manager'):
                role = 'fleet_manager'
            elif user.has_group('transitops.group_transitops_dispatcher'):
                role = 'dispatcher'
            elif user.has_group('transitops.group_transitops_safety_officer'):
                role = 'safety_officer'
            elif user.has_group('transitops.group_transitops_financial_analyst'):
                role = 'financial_analyst'
            else:
                role = 'admin'
                
        # Gather live data from DB
        vehicles = request.env['transitops.vehicle'].sudo().search([])
        trips = request.env['transitops.trip'].sudo().search([])
        drivers = request.env['transitops.driver'].sudo().search([])
        maintenances = request.env['transitops.maintenance'].sudo().search([])
        expenses = request.env['transitops.expense'].sudo().search([])
        fuel_logs = request.env['transitops.fuel_log'].sudo().search([])
        
        active_v = len(vehicles.filtered(lambda v: v.status == 'on_trip'))
        available_v = len(vehicles.filtered(lambda v: v.status == 'available'))
        maint_v = len(vehicles.filtered(lambda v: v.status == 'in_shop'))
        active_t = len(trips.filtered(lambda t: t.status == 'dispatched'))
        pending_t = len(trips.filtered(lambda t: t.status == 'draft'))
        drivers_duty = len(drivers.filtered(lambda d: d.status == 'on_trip'))
        
        total_active_available = active_v + available_v
        utilization = int((active_v / total_active_available * 100.0) if total_active_available > 0 else 0.0)
        
        available_count = len(vehicles.filtered(lambda v: v.status == 'available'))
        on_trip_count = len(vehicles.filtered(lambda v: v.status == 'on_trip'))
        in_shop_count = len(vehicles.filtered(lambda v: v.status == 'in_shop'))
        retired_count = len(vehicles.filtered(lambda v: v.status == 'retired'))
        
        total_vehicles = len(vehicles) or 1
        available_pct = int((available_count / total_vehicles) * 100.0)
        on_trip_pct = int((on_trip_count / total_vehicles) * 100.0)
        in_shop_pct = int((in_shop_count / total_vehicles) * 100.0)
        retired_pct = int((retired_count / total_vehicles) * 100.0)
        
        total_fuel_cost = sum(fuel_logs.mapped('fuel_cost'))
        total_maint_cost = sum(maintenances.mapped('cost'))
        total_op_cost = total_fuel_cost + total_maint_cost
        total_liters = sum(fuel_logs.mapped('liters'))
        total_distance = sum(trips.mapped('planned_distance'))
        fuel_eff = round(total_distance / total_liters, 1) if total_liters > 0 else 8.4
        total_acq = sum(vehicles.mapped('acquisition_cost'))
        total_rev = total_distance * 25.0
        veh_roi = round(((total_rev - total_op_cost) / total_acq) * 100.0, 1) if total_acq > 0 else 14.2

        role_tabs = {
            'fleet_manager': ['dashboard', 'fleet', 'maintenance', 'settings'],
            'dispatcher': ['dashboard', 'fleet', 'drivers', 'trips', 'settings'],
            'safety_officer': ['dashboard', 'drivers', 'maintenance', 'settings'],
            'financial_analyst': ['dashboard', 'fuel_expenses', 'analytics', 'settings'],
            'admin': ['dashboard', 'fleet', 'drivers', 'trips', 'maintenance', 'fuel_expenses', 'analytics', 'settings']
        }
        allowed_tabs = role_tabs.get(role, role_tabs['admin'])
        recent_trips = trips.sudo().search([], limit=10, order='id desc')

        values = {
            'user': user,
            'role': role,
            'allowed_tabs': allowed_tabs,
            'role_label': dict(self._get_roles_list()).get(role, 'Administrator'),
            'active_vehicles': active_v,
            'available_vehicles': available_v,
            'maintenance_vehicles': maint_v,
            'active_trips': active_t,
            'pending_trips': pending_t,
            'drivers_on_duty': drivers_duty,
            'fleet_utilization': utilization,
            'available_count': available_count,
            'on_trip_count': on_trip_count,
            'in_shop_count': in_shop_count,
            'retired_count': retired_count,
            'available_pct': available_pct,
            'on_trip_pct': on_trip_pct,
            'in_shop_pct': in_shop_pct,
            'retired_pct': retired_pct,
            'recent_trips': recent_trips,
            'vehicles_list': vehicles,
            'drivers_list': drivers,
            'trips_list': trips,
            'maintenances_list': maintenances,
            'expenses_list': expenses,
            'fuel_logs_list': fuel_logs,
            'total_operational_cost': total_op_cost,
            'fuel_efficiency': fuel_eff,
            'vehicle_roi': veh_roi,
        }
        
        return request.render('transitops.portal_dashboard_template', values)

    def _get_roles_list(self):
        return [
            ('fleet_manager', _('Fleet Manager')),
            ('dispatcher', _('Dispatcher')),
            ('safety_officer', _('Safety Officer')),
            ('financial_analyst', _('Financial Analyst')),
        ]

    @http.route('/transitops/vehicle/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_vehicle_create(self, **kw):
        role = kw.get('role', 'admin')
        try:
            request.env['transitops.vehicle'].sudo().create({
                'registration_no': kw.get('registration_no'),
                'name': kw.get('name'),
                'type': kw.get('type'),
                'capacity_kg': int(kw.get('capacity_kg') or 0),
                'odometer': int(kw.get('odometer') or 0),
                'acquisition_cost': float(kw.get('acquisition_cost') or 0.0),
                'status': 'available',
            })
        except Exception as e:
            _logger.error("Failed to create vehicle: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#fleet')

    @http.route('/transitops/driver/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_driver_create(self, **kw):
        role = kw.get('role', 'admin')
        try:
            request.env['transitops.driver'].sudo().create({
                'name': kw.get('name'),
                'license_no': kw.get('license_no'),
                'category': kw.get('category'),
                'license_expiry': kw.get('license_expiry'),
                'contact': kw.get('contact'),
                'safety_status': kw.get('safety_status', 'available'),
                'status': 'available',
            })
        except Exception as e:
            _logger.error("Failed to create driver: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#drivers')

    @http.route('/transitops/trip/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_trip_create(self, **kw):
        role = kw.get('role', 'admin')
        try:
            request.env['transitops.trip'].sudo().create({
                'source': kw.get('source'),
                'destination': kw.get('destination'),
                'vehicle_id': int(kw.get('vehicle_id')),
                'driver_id': int(kw.get('driver_id')),
                'cargo_weight': int(kw.get('cargo_weight') or 0),
                'planned_distance': float(kw.get('planned_distance') or 0.0),
                'status': 'draft',
            })
        except Exception as e:
            _logger.error("Failed to create trip: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#trips')

    @http.route('/transitops/trip/<int:trip_id>/dispatch', type='http', auth='user', methods=['GET'], csrf=False)
    def transitops_trip_dispatch(self, trip_id, **kw):
        role = kw.get('role', 'admin')
        trip = request.env['transitops.trip'].sudo().browse(trip_id)
        if trip.exists():
            try:
                trip.action_dispatch()
            except Exception as e:
                _logger.error("Failed to dispatch trip: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#trips')

    @http.route('/transitops/trip/<int:trip_id>/complete', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_trip_complete(self, trip_id, **kw):
        role = kw.get('role', 'admin')
        trip = request.env['transitops.trip'].sudo().browse(trip_id)
        if trip.exists():
            try:
                final_odo = int(kw.get('final_odometer') or 0)
                trip.write({
                    'final_odometer': final_odo,
                    'status': 'completed'
                })
            except Exception as e:
                _logger.error("Failed to complete trip: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#trips')

    @http.route('/transitops/trip/<int:trip_id>/cancel', type='http', auth='user', methods=['GET'], csrf=False)
    def transitops_trip_cancel(self, trip_id, **kw):
        role = kw.get('role', 'admin')
        trip = request.env['transitops.trip'].sudo().browse(trip_id)
        if trip.exists():
            try:
                trip.action_cancel()
            except Exception as e:
                _logger.error("Failed to cancel trip: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#trips')

    @http.route('/transitops/maintenance/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_maintenance_create(self, **kw):
        role = kw.get('role', 'admin')
        try:
            request.env['transitops.maintenance'].sudo().create({
                'vehicle_id': int(kw.get('vehicle_id')),
                'service_type': kw.get('service_type'),
                'cost': float(kw.get('cost') or 0.0),
                'date': kw.get('date'),
                'status': kw.get('status', 'active'),
            })
        except Exception as e:
            _logger.error("Failed to create maintenance record: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#maintenance')

    @http.route('/transitops/maintenance/<int:maint_id>/complete', type='http', auth='user', methods=['GET'], csrf=False)
    def transitops_maintenance_complete(self, maint_id, **kw):
        role = kw.get('role', 'admin')
        maint = request.env['transitops.maintenance'].sudo().browse(maint_id)
        if maint.exists():
            try:
                maint.write({'status': 'completed'})
            except Exception as e:
                _logger.error("Failed to complete maintenance: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#maintenance')

    @http.route('/transitops/fuel/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_fuel_create(self, **kw):
        role = kw.get('role', 'admin')
        try:
            request.env['transitops.fuel_log'].sudo().create({
                'vehicle_id': int(kw.get('vehicle_id')),
                'date': kw.get('date'),
                'liters': float(kw.get('liters') or 0.0),
                'fuel_cost': float(kw.get('fuel_cost') or 0.0),
            })
        except Exception as e:
            _logger.error("Failed to log fuel: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#fuel_expenses')

    @http.route('/transitops/expense/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_expense_create(self, **kw):
        role = kw.get('role', 'admin')
        try:
            request.env['transitops.expense'].sudo().create({
                'trip_id': int(kw.get('trip_id')),
                'toll_cost': float(kw.get('toll_cost') or 0.0),
                'other_cost': float(kw.get('other_cost') or 0.0),
            })
        except Exception as e:
            _logger.error("Failed to log expense: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#fuel_expenses')

    @http.route('/transitops/settings/save', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_settings_save(self, **kw):
        role = kw.get('role', 'admin')
        try:
            sudo_config = request.env['ir.config_parameter'].sudo()
            if 'depot_name' in kw:
                sudo_config.set_param('transitops.depot_name', kw.get('depot_name'))
            if 'distance_unit' in kw:
                sudo_config.set_param('transitops.distance_unit', kw.get('distance_unit'))
        except Exception as e:
            _logger.error("Failed to save settings: %s", e)
        return request.redirect(f'/transitops/dashboard/{role}#settings')
