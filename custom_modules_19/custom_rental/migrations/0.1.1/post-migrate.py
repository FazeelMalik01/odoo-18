# -*- coding: utf-8 -*-

def migrate(cr, version):
    cr.execute("""
        ALTER TABLE sale_order
        ADD COLUMN IF NOT EXISTS coupon_code VARCHAR
    """)
