# -*- coding: utf-8 -*-
{
    'name': 'TransitOps - Smart Transport Operations Platform',
    'version': '1.0',
    'summary': 'Centralized platform for vehicles, drivers, dispatch, maintenance, fuel logs, and expense analytics.',
    'description': """
TransitOps: Smart Transport Operations Platform
================================================
A comprehensive Odoo module to manage the complete lifecycle of transport operations.

Key Features:
-------------
1. **Dashboard & KPIs**:
   * Active, Available, and In-Maintenance vehicle counts.
   * Active and Pending trip metrics, and Drivers On Duty.
   * Fleet Utilization (%) computation.
   * Filters by type, status, and region.

2. **Vehicle Registry**:
   * Unique Registration Number, Model, Type, Load Capacity, Odometer, and Acquisition Cost.
   * Status lifecycles: Available, On Trip, In Shop, Retired.

3. **Driver Management**:
   * Profiles with License details, Expiry Dates, Safety Scores, and Status.
   * Safety checks to block expired or suspended drivers.

4. **Trip Management & Dispatch**:
   * Validation of vehicle load capacity.
   * Verification of driver license validity and availability.
   * Automatic status transitions on dispatch, completion, or cancellation.

5. **Maintenance Logging**:
   * Auto-transition of vehicle status to "In Shop" when log is active.
   * Reversion to "Available" (or previous valid status) upon closing maintenance.

6. **Fuel & Expense Tracking**:
   * Fuel logs and other operational expenses (tolls, maintenance costs).
   * Automatic computation of total operational cost per vehicle.

7. **Reports & Analytics**:
   * Fuel Efficiency (Distance / Fuel).
   * Vehicle Return on Investment (ROI).
   * Dashboard charts and analytics.
    """,
    'author': 'Odoo-Hackthon',
    'category': 'Operations/Logistics',
    'depends': ['base', 'mail'],
    'data': [],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
