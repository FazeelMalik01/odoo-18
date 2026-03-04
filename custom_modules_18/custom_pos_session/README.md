# Custom POS Session Module

This module extends the Odoo Point of Sale functionality with the following features:

## Features

1. **Store Name in Report Header**: Displays the POS store name (config_id) in the daily sales report header.

2. **Auto Download on Close Register**: Automatically downloads the daily sales report PDF when the "Close Register" button is clicked, in addition to the existing session closing functionality.

## Technical Implementation

### JavaScript Extension
- **File**: `static/src/js/closing_popup.js`
- **Functionality**: Patches the `ClosePosPopup.prototype.confirm()` method to automatically download the sales report before closing the session.
- **Error Handling**: Includes try-catch to ensure that download failures don't prevent session closing.

### Template Extension
- **File**: `views/views.xml`
- **Functionality**: Extends the `point_of_sale.pos_session_sales_details` template to show the POS store name in the report header.

## Installation

1. Place the module in your Odoo addons directory
2. Update the app list in Odoo
3. Install the "Custom POS Session Report" module

## Usage

1. Open a POS session
2. When ready to close the session, click "Close Register"
3. The system will automatically download the daily sales report PDF
4. The session will close normally with all existing functionality preserved

## Dependencies

- `point_of_sale` module (Odoo 18.0)

## Author

Your Company
