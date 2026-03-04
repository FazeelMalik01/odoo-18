/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup();
        // Initialize the custom print method
        this.doCustomPrint = this.doCustomPrint.bind(this);
        this.doCustomPrint.status = 'idle';
    },

    async doCustomPrint() {
        console.log("Custom print button clicked");
        
        try {
            this.doCustomPrint.status = 'loading';
            
            // Get the current order
            const order = this.pos.get_order();
            if (!order || !order.id) {
                throw new Error("No order found to print");
            }
            
            console.log("Generating HTML for order:", order.id);
            
            // Get POS configuration ID
            const posConfigId = this.pos.config.id;
            console.log("POS Config ID:", posConfigId);
            
            // Get report type from POS configuration
            const reportType = await this.getReceiptType(posConfigId);
            
            // Call the controller to generate HTML using fetch
            const response = await fetch('/custom_pos_receipt/generate_html', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    order_id: order.id,
                    pos_config_id: posConfigId,
                    report_type: reportType
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Open print preview using the same method as the original print functionality
                this.openPrintPreview(data.html_content);
                console.log("Print preview opened successfully");
            } else {
                throw new Error(data.error || "Failed to generate HTML");
            }
            
        } catch (error) {
            console.error("Error in custom print:", error);
            // You might want to show a notification to the user
            this.showNotification("Error generating print preview: " + error.message, "error");
        } finally {
            this.doCustomPrint.status = 'idle';
        }
    },

    openPrintPreview(htmlContent) {
        try {
            // Create a new window with the HTML content
            const printWindow = window.open('', '_blank', 'width=800,height=600');
            
            if (!printWindow) {
                throw new Error("Popup blocked. Please allow popups for this site.");
            }
            
            // Write the HTML content to the new window
            printWindow.document.write(htmlContent);
            printWindow.document.close();
            
            // Wait for the content to load, then trigger print dialog
            printWindow.onload = function() {
                printWindow.focus();
                printWindow.print();
            };
            
        } catch (error) {
            console.error("Error opening print preview:", error);
            throw error;
        }
    },

    showNotification(message, type = 'info') {
        // Simple notification - you might want to use Odoo's notification system
        console.log(`${type.toUpperCase()}: ${message}`);
        // You can implement a proper notification here if needed
    },

    async getReceiptType(posConfigId) {
        try {
            // Fetch the receipt type from POS configuration
            const url = posConfigId 
                ? `/custom_pos_receipt/get_receipt_type?pos_config_id=${posConfigId}`
                : '/custom_pos_receipt/get_receipt_type';
                
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return data.receipt_type || 'doha'; // Default to 'doha' if not found
            
        } catch (error) {
            console.error("Error fetching receipt type:", error);
            return 'doha'; // Default fallback
        }
    }
});
