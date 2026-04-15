# -*- coding: utf-8 -*-


def post_init_hook(env):
    env['payment.provider']._ipos_ensure_module_link_all()
    # Ensure journals exist for ipos_pay so account.payment can be created on done tx.
    env['payment.provider']._ipos_ensure_journal()
