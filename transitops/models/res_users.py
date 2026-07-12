# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessDenied

class ResUsers(models.Model):
    _inherit = 'res.users'

    failed_login_attempts = fields.Integer(string='Failed Login Attempts', default=0, copy=False)

    @api.model
    def _login(self, credential, user_agent_env):
        login = credential.get('login')
        if login:
            # Check if the user is already locked
            user = self.sudo().search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
            if user and user.failed_login_attempts >= 5:
                raise AccessDenied(_("Account locked after 5 failed attempts. Please contact your administrator."))

        try:
            auth_info = super(ResUsers, self)._login(credential, user_agent_env)
            # On success, reset the failed attempt counter
            if login:
                user = self.sudo().search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
                if user and user.failed_login_attempts > 0:
                    self.env.cr.execute(
                        "UPDATE res_users SET failed_login_attempts = 0 WHERE id = %s",
                        [user.id]
                    )
                    self.env.cr.commit()
            return auth_info
        except AccessDenied:
            # On failure, increment the counter
            if login:
                user = self.sudo().search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
                if user:
                    self.env.cr.execute(
                        "UPDATE res_users SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1 WHERE id = %s",
                        [user.id]
                    )
                    self.env.cr.commit()
            raise
