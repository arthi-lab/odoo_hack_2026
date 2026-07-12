# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    transitops_depot_name = fields.Char(
        string='Depot Name', 
        config_parameter='transitops.depot_name', 
        default='Gandhinagar Depot'
    )
    transitops_currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        config_parameter='transitops.currency_id'
    )
    transitops_distance_unit = fields.Selection([
        ('miles', 'Miles'),
        ('kilometers', 'Kilometers')
    ], string='Distance Unit', config_parameter='transitops.distance_unit', default='kilometers')
