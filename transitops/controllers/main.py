# -*- coding: utf-8 -*-
import logging
from odoo import http, _, fields
from odoo.addons.web.controllers.home import Home
from odoo.http import request
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class TransitopsHome(Home):

    def _set_flash(self, message, message_type='success'):
        request.session['transitops_flash'] = {
            'message': message,
            'type': message_type
        }

    def _get_flash(self):
        return request.session.pop('transitops_flash', None)

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
                if role_rbac:
                    request.session['transitops_role'] = role_rbac
                else:
                    request.session['transitops_role'] = 'admin'
                return request.redirect('/transitops/dashboard')

            ROLE_GROUPS = {
                'fleet_manager': 'transitops.group_transitops_fleet_manager',
                'dispatcher': 'transitops.group_transitops_dispatcher',
                'safety_officer': 'transitops.group_transitops_safety_officer',
                'financial_analyst': 'transitops.group_transitops_financial_analyst',
                'admin': 'base.group_system',
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
                    request.session['transitops_role'] = role_rbac
                    return request.redirect('/transitops/dashboard')
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

    @http.route(['/transitops/dashboard', '/transitops/dashboard/<string:old_role_url>'], type='http', auth='user', readonly=False)
    def transitops_dashboard_portal(self, old_role_url=None, **kw):
        user = request.env.user
        
        # If accessing the old URL schema, redirect to the clean single route
        if old_role_url:
            if old_role_url in ['fleet_manager', 'dispatcher', 'safety_officer', 'financial_analyst', 'admin']:
                request.session['transitops_role'] = old_role_url
            return request.redirect('/transitops/dashboard')

        # Resolve role from session or groups
        role = request.session.get('transitops_role')
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

        # Read and clear flash message
        flash = self._get_flash()

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
            'flash_message': flash.get('message') if flash else None,
            'flash_type': flash.get('type') if flash else None,
            'today': fields.Date.today().strftime('%Y-%m-%d'),
        }
        
        return request.render('transitops.portal_dashboard_template', values)

    def _get_roles_list(self):
        return [
            ('admin', _('Administrator')),
            ('fleet_manager', _('Fleet Manager')),
            ('dispatcher', _('Dispatcher')),
            ('safety_officer', _('Safety Officer')),
            ('financial_analyst', _('Financial Analyst')),
        ]

    @http.route('/transitops/vehicle/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_vehicle_create(self, **kw):
        try:
            reg_no = kw.get('registration_no')
            if not reg_no or not reg_no.strip():
                raise ValidationError(_("Registration number is required."))
            name = kw.get('name')
            if not name or not name.strip():
                raise ValidationError(_("Vehicle Name is required."))
            capacity_kg = int(kw.get('capacity_kg') or 0)
            if capacity_kg <= 0:
                raise ValidationError(_("Capacity must be greater than 0 kg."))
            
            # Check duplicate registration
            existing = request.env['transitops.vehicle'].sudo().search([('registration_no', '=', reg_no.strip())], limit=1)
            if existing:
                raise ValidationError(_("A vehicle with Registration No %s already exists.") % reg_no)
                
            request.env['transitops.vehicle'].sudo().create({
                'registration_no': reg_no.strip(),
                'name': name.strip(),
                'type': kw.get('type'),
                'capacity_kg': capacity_kg,
                'odometer': int(kw.get('odometer') or 0),
                'acquisition_cost': float(kw.get('acquisition_cost') or 0.0),
                'status': 'available',
            })
            self._set_flash(_("Vehicle created successfully."), 'success')
        except (ValidationError, UserError) as e:
            self._set_flash(str(e), 'error')
        except Exception as e:
            self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#fleet')

    @http.route('/transitops/driver/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_driver_create(self, **kw):
        try:
            name = kw.get('name')
            if not name or not name.strip():
                raise ValidationError(_("Driver Name is required."))
            license_no = kw.get('license_no')
            if not license_no or not license_no.strip():
                raise ValidationError(_("License Number is required."))
            
            # Duplicate license check
            existing = request.env['transitops.driver'].sudo().search([('license_no', '=', license_no.strip())], limit=1)
            if existing:
                raise ValidationError(_("A driver with License No %s already exists.") % license_no)
            
            request.env['transitops.driver'].sudo().create({
                'name': name.strip(),
                'license_no': license_no.strip(),
                'category': kw.get('category'),
                'license_expiry': kw.get('license_expiry'),
                'contact': kw.get('contact'),
                'safety_status': kw.get('safety_status', 'available'),
                'status': 'available',
            })
            self._set_flash(_("Driver created successfully."), 'success')
        except (ValidationError, UserError) as e:
            self._set_flash(str(e), 'error')
        except Exception as e:
            self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#drivers')

    @http.route('/transitops/trip/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_trip_create(self, **kw):
        try:
            source = kw.get('source')
            dest = kw.get('destination')
            if not source or not source.strip():
                raise ValidationError(_("Source location is required."))
            if not dest or not dest.strip():
                raise ValidationError(_("Destination location is required."))
            
            vehicle_id = int(kw.get('vehicle_id') or 0)
            driver_id = int(kw.get('driver_id') or 0)
            if not vehicle_id:
                raise ValidationError(_("Please select a vehicle."))
            if not driver_id:
                raise ValidationError(_("Please select a driver."))
                
            cargo_weight = int(kw.get('cargo_weight') or 0)
            if cargo_weight <= 0:
                raise ValidationError(_("Cargo weight must be greater than 0 kg."))
                
            planned_distance = float(kw.get('planned_distance') or 0.0)
            if planned_distance <= 0.0:
                raise ValidationError(_("Planned distance must be greater than 0 km."))

            vehicle = request.env['transitops.vehicle'].sudo().browse(vehicle_id)
            if not vehicle.exists():
                raise ValidationError(_("Selected vehicle does not exist."))
            driver = request.env['transitops.driver'].sudo().browse(driver_id)
            if not driver.exists():
                raise ValidationError(_("Selected driver does not exist."))

            # Business validation: pre-flight check cargo weight vs vehicle capacity
            if cargo_weight > vehicle.capacity_kg:
                raise ValidationError(_("Cargo weight (%s kg) exceeds vehicle capacity (%s kg).") % (cargo_weight, vehicle.capacity_kg))

            # Driver validation: check license expiry
            if driver.is_expired:
                raise ValidationError(_("Selected driver's license is expired."))
            if driver.safety_status == 'suspended' or driver.status == 'suspended':
                raise ValidationError(_("Selected driver is suspended or unavailable."))

            request.env['transitops.trip'].sudo().create({
                'source': source.strip(),
                'destination': dest.strip(),
                'vehicle_id': vehicle_id,
                'driver_id': driver_id,
                'cargo_weight': cargo_weight,
                'planned_distance': planned_distance,
                'notes': kw.get('notes'),
                'scheduled_date': kw.get('scheduled_date') or fields.Date.today(),
                'status': 'draft',
            })
            self._set_flash(_("Trip created successfully in Draft status."), 'success')
        except (ValidationError, UserError) as e:
            self._set_flash(str(e), 'error')
        except Exception as e:
            self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#trips')

    @http.route('/transitops/trip/<int:trip_id>/dispatch', type='http', auth='user', methods=['POST', 'GET'], csrf=False)
    def transitops_trip_dispatch(self, trip_id, **kw):
        trip = request.env['transitops.trip'].sudo().browse(trip_id)
        if trip.exists():
            try:
                trip.action_dispatch()
                self._set_flash(_("Trip %s dispatched successfully.") % trip.name, 'success')
            except (ValidationError, UserError) as e:
                self._set_flash(str(e), 'error')
            except Exception as e:
                self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#trips')

    @http.route('/transitops/trip/<int:trip_id>/complete', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_trip_complete(self, trip_id, **kw):
        trip = request.env['transitops.trip'].sudo().browse(trip_id)
        if trip.exists():
            try:
                final_odo = int(kw.get('final_odometer') or 0)
                if final_odo <= 0:
                    raise ValidationError(_("Please enter a valid final odometer reading."))
                trip.write({
                    'final_odometer': final_odo,
                    'status': 'completed'
                })
                self._set_flash(_("Trip %s marked as Completed.") % trip.name, 'success')
            except (ValidationError, UserError) as e:
                self._set_flash(str(e), 'error')
            except Exception as e:
                self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#trips')

    @http.route('/transitops/trip/<int:trip_id>/cancel', type='http', auth='user', methods=['POST', 'GET'], csrf=False)
    def transitops_trip_cancel(self, trip_id, **kw):
        trip = request.env['transitops.trip'].sudo().browse(trip_id)
        if trip.exists():
            try:
                trip.action_cancel()
                self._set_flash(_("Trip %s cancelled.") % trip.name, 'success')
            except (ValidationError, UserError) as e:
                self._set_flash(str(e), 'error')
            except Exception as e:
                self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#trips')

    @http.route('/transitops/maintenance/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_maintenance_create(self, **kw):
        try:
            vehicle_id = int(kw.get('vehicle_id') or 0)
            if not vehicle_id:
                raise ValidationError(_("Please select a vehicle."))
            vehicle = request.env['transitops.vehicle'].sudo().browse(vehicle_id)
            if vehicle.status == 'on_trip':
                raise ValidationError(_("Vehicle %s is currently on a trip. Cannot log maintenance.") % vehicle.registration_no)
                
            cost = float(kw.get('cost') or 0.0)
            if cost < 0.0:
                raise ValidationError(_("Maintenance cost cannot be negative."))
                
            request.env['transitops.maintenance'].sudo().create({
                'vehicle_id': vehicle_id,
                'service_type': kw.get('service_type'),
                'cost': cost,
                'date': kw.get('date'),
                'status': kw.get('status', 'active'),
            })
            self._set_flash(_("Maintenance record created successfully."), 'success')
        except (ValidationError, UserError) as e:
            self._set_flash(str(e), 'error')
        except Exception as e:
            self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#maintenance')

    @http.route('/transitops/maintenance/<int:maint_id>/complete', type='http', auth='user', methods=['GET'], csrf=False)
    def transitops_maintenance_complete(self, maint_id, **kw):
        maint = request.env['transitops.maintenance'].sudo().browse(maint_id)
        if maint.exists():
            try:
                maint.write({'status': 'completed'})
                self._set_flash(_("Maintenance log completed successfully."), 'success')
            except (ValidationError, UserError) as e:
                self._set_flash(str(e), 'error')
            except Exception as e:
                self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#maintenance')

    @http.route('/transitops/fuel/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_fuel_create(self, **kw):
        try:
            vehicle_id = int(kw.get('vehicle_id') or 0)
            if not vehicle_id:
                raise ValidationError(_("Please select a vehicle."))
            liters = float(kw.get('liters') or 0.0)
            if liters <= 0:
                raise ValidationError(_("Fuel liters must be greater than 0."))
            fuel_cost = float(kw.get('fuel_cost') or 0.0)
            if fuel_cost <= 0:
                raise ValidationError(_("Fuel cost must be greater than 0."))
                
            request.env['transitops.fuel_log'].sudo().create({
                'vehicle_id': vehicle_id,
                'date': kw.get('date'),
                'liters': liters,
                'fuel_cost': fuel_cost,
            })
            self._set_flash(_("Fuel log added successfully."), 'success')
        except (ValidationError, UserError) as e:
            self._set_flash(str(e), 'error')
        except Exception as e:
            self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#fuel_expenses')

    @http.route('/transitops/expense/create', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_expense_create(self, **kw):
        try:
            trip_id = int(kw.get('trip_id') or 0)
            if not trip_id:
                raise ValidationError(_("Please select a trip."))
            toll_cost = float(kw.get('toll_cost') or 0.0)
            other_cost = float(kw.get('other_cost') or 0.0)
            if toll_cost < 0 or other_cost < 0:
                raise ValidationError(_("Costs cannot be negative."))
                
            request.env['transitops.expense'].sudo().create({
                'trip_id': trip_id,
                'toll_cost': toll_cost,
                'other_cost': other_cost,
            })
            self._set_flash(_("Expense logged successfully."), 'success')
        except (ValidationError, UserError) as e:
            self._set_flash(str(e), 'error')
        except Exception as e:
            self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#fuel_expenses')

    @http.route('/transitops/settings/save', type='http', auth='user', methods=['POST'], csrf=True)
    def transitops_settings_save(self, **kw):
        try:
            depot_name = kw.get('depot_name')
            if not depot_name or not depot_name.strip():
                raise ValidationError(_("Depot Name cannot be blank."))
            sudo_config = request.env['ir.config_parameter'].sudo()
            sudo_config.set_param('transitops.depot_name', depot_name.strip())
            if 'distance_unit' in kw:
                sudo_config.set_param('transitops.distance_unit', kw.get('distance_unit'))
            self._set_flash(_("Settings saved successfully."), 'success')
        except (ValidationError, UserError) as e:
            self._set_flash(str(e), 'error')
        except Exception as e:
            self._set_flash(str(e), 'error')
        return request.redirect('/transitops/dashboard#settings')
