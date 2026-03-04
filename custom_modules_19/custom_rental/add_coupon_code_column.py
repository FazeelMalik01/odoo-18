#!/usr/bin/env python3
"""
One-time script to add coupon_code column to sale_order.
Run with Odoo shell: python odoo-bin shell -d YOUR_DATABASE < add_coupon_code_column.py
Or run the SQL below directly in PostgreSQL (psql or pgAdmin).
"""
# If using Odoo shell, uncomment and run:
# env.cr.execute("ALTER TABLE sale_order ADD COLUMN IF NOT EXISTS coupon_code VARCHAR")
# env.cr.commit()
# print("Column coupon_code added to sale_order.")

# --- OR run this SQL in your database (psql, pgAdmin, etc.): ---
# ALTER TABLE sale_order ADD COLUMN IF NOT EXISTS coupon_code VARCHAR;
