/** @odoo-module **/
console.log("hehhee boi");

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillStart, useState } from "@odoo/owl";

async function attachVendorsToJournalItems(journalItems) {
    try {
        const saleOrders = await fetchSaleOrders();
        const vendorMap = {};

        // Build vendor map: saleOrderId → vendorName
        saleOrders.forEach(order => {
            if (order.vendor_id && order.vendor_id[1]) {
                vendorMap[order.id] = order.vendor_id[1];
            }
        });

        // Map journal item ref or name to vendor
        return journalItems.map(item => {
            const relatedOrder = saleOrders.find(order =>
                item.ref?.includes(order.name) || item.name?.includes(order.name)
            );
            if (relatedOrder && relatedOrder.vendor_id && relatedOrder.vendor_id[1]) {
                item.vendor_name = relatedOrder.vendor_id[1];
            } else {
                item.vendor_name = "—";
            }
            return item;
        });
    } catch (err) {
        console.error("Error attaching vendors:", err);
        return journalItems;
    }
}


// JSON-RPC fetch functions
async function fetchProjects() {
    try {
        const res = await fetch("/web/dataset/call_kw/project.project/search_read", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "project.project",
                    method: "search_read",
                    args: [[]],
                    kwargs: {
                        fields: ["id", "name"],
                    },
                },
                id: 1,
            }),
        });
        const data = await res.json();
        console.log("Projects:", data.result);
        return data.result || [];
    } catch (err) {
        console.error("Error fetching projects:", err);
        return [];
    }
}

async function fetchPartners() {
    try {
        const res = await fetch("/web/dataset/call_kw/res.partner/search_read", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "res.partner",
                    method: "search_read",
                    args: [[]],
                    kwargs: {},
                },
                id: 2,
            }),
        });
        const data = await res.json();
        console.log("Partners:", data.result);
        return data.result || [];
    } catch (err) {
        console.error("Error fetching partners:", err);
        return [];
    }
}

async function fetchSaleOrders() {
    try {
        const res = await fetch("/web/dataset/call_kw/sale.order/search_read", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "sale.order",
                    method: "search_read",
                    args: [[]],
                    kwargs: {
                      fields: ["id", "name", "vendor_id"],
                    },
                },
                id: 3,
            }),
        });
        const data = await res.json();
        console.log("Sale Orders:", data.result);
        return data.result || [];
    } catch (err) {
        console.error("Error fetching sale orders:", err);
        return [];
    }
}

async function fetchInvoices() {
    try {
        const res = await fetch("/web/dataset/call_kw/account.move/search_read", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "account.move",
                    method: "search_read",
                    args: [[["move_type", "=", "out_invoice"]]],
                    kwargs: {},
                },
                id: 4,
            }),
        });
        const data = await res.json();
        console.log("Invoices:", data.result);
        return data.result || [];
    } catch (err) {
        console.error("Error fetching invoices:", err);
        return [];
    }
}

async function fetchJournalItemsByPartner(partnerId) {
    try {
        // Step 1: Get all projects of this partner
        const projectRes = await fetch("/web/dataset/call_kw/project.project/search_read", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "project.project",
                    method: "search_read",
                    args: [[["partner_id", "=", partnerId]]],
                    kwargs: { fields: ["id", "name"] },
                },
                id: 10,
            }),
        });

        const projectData = await projectRes.json();
        const projects = projectData.result || [];
        const projectIds = projects.map(p => p.id);

        // Step 2: Build domain for both partner + its projects
        const domain = [["partner_id", "=", partnerId]];
        if (projectIds.length > 0) {
            domain.push("|");
            domain.push(["project_id", "in", projectIds]);
        }

        // Step 3: Fetch all journal lines matching domain
        const journalRes = await fetch("/web/dataset/call_kw/account.move.line/search_read", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "account.move.line",
                    method: "search_read",
                    args: [domain],
                    kwargs: {
                        fields: [
                            "id",
                            "date",
                            "move_name",
                            "partner_id",
                            "account_id",
                            "ref",
                            "name",
                            "debit",
                            "credit",
                            "balance",
                            "currency_id",
                            "amount_currency",
                            "project_id",
                        ],
                        order: "date desc",
                        limit: 100,
                    },
                },
                id: 11,
            }),
        });

        const data = await journalRes.json();
        console.log("Journal Items (Partner + Projects):", data.result);
        return data.result || [];

    } catch (err) {
        console.error("Error fetching journal items (partner + projects):", err);
        return [];
    }
}

async function fetchJournalItemsByProject(projectId) {
    try {
        const res = await fetch("/web/dataset/call_kw/account.move.line/search_read", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "account.move.line",
                    method: "search_read",
                    args: [[["project_id", "=", projectId]]],
                    kwargs: {
                        fields: [
                            "id", // Ensure we get the id field
                            "date",
                            "move_name",
                            "partner_id",
                            "account_id",
                            "ref",
                            "name",
                            "debit",
                            "credit",
                            "balance",
                            "currency_id",
                            "amount_currency",
                            "project_id",
                        ],
                        order: "date desc",
                        limit: 50,
                    },
                },
                id: 7,
            }),
        });
        const data = await res.json();
        console.log("Journal Items (by Project):", data.result);
        return data.result || [];
    } catch (err) {
        console.error("Error fetching journal items by project:", err);
        return [];
    }
}

async function fetchJournalItemsByDateRange(startDate, endDate, partnerId = null, projectId = null) {
    try {
        const domain = [
            ["date", ">=", startDate],
            ["date", "<=", endDate]
        ];

        if (partnerId) {
            domain.push(["partner_id", "=", partnerId]);
        }

        if (projectId) {
            domain.push(["project_id", "=", projectId]);
        }

        const res = await fetch("/web/dataset/call_kw/account.move.line/search_read", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "account.move.line",
                    method: "search_read",
                    args: [domain],
                    kwargs: {
                        fields: [
                            "id", // Ensure we get the id field
                            "date",
                            "move_name",
                            "account_id",
                            "partner_id",
                            "ref",
                            "name",
                            "debit",
                            "credit",
                            "balance",
                            "currency_id",
                            "amount_currency",
                            "project_id"
                        ],
                        order: "date desc",
                        limit: 50,
                    },
                },
                id: 8,
            }),
        });
        const data = await res.json();
        console.log("Journal Items (by Date Range):", data.result);
        return data.result || [];
    } catch (err) {
        console.error("Error fetching journal items by date range:", err);
        return [];
    }
}

// PDF Generation Function
function generatePDFFromTable(journalItems, dateText, filters = {}) {
    const pdfWindow = window.open('', '_blank');
    const currentDate = new Date().toLocaleDateString();

    let filterText = '';
    if (filters.partnerName) {
        filterText += `Partner: ${filters.partnerName} | `;
    }
    if (filters.projectName) {
        filterText += `Project: ${filters.projectName} | `;
    }
    if (filters.dateRange) {
        filterText += `Period: ${filters.dateRange}`;
    }

    const totalDebit = journalItems.reduce((sum, item) => sum + (item.debit || 0), 0);
    const totalCredit = journalItems.reduce((sum, item) => sum + (item.credit || 0), 0);
    const totalBalance = journalItems.reduce((sum, item) => sum + (item.balance !== undefined ? item.balance : (item.debit || 0) - (item.credit || 0)), 0);

    const pdfContent = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>General Ledger Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 10px; }
                .company-name { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
                .report-title { font-size: 18px; margin-bottom: 5px; }
                .report-date { font-size: 14px; color: #666; }
                .filters { margin: 15px 0; padding: 10px; background-color: #f5f5f5; border-radius: 5px; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; font-weight: bold; }
                .text-right { text-align: right; }
                .text-center { text-align: center; }
                .total-row { background-color: #e9ecef; font-weight: bold; }
                .footer { margin-top: 30px; text-align: center; font-size: 12px; color: #666; }
                .number { text-align: right; font-family: monospace; }
            </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">Falcon General Ledger</div>
                <div class="report-title">General Ledger Report</div>
                <div class="report-date">Generated on: ${currentDate}</div>
            </div>

            ${filterText ? `<div class="filters"><strong>Filters:</strong> ${filterText}</div>` : ''}

            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Communication</th>
                        <th>Partner</th>
                        <th>Project</th>
                        <th>Currency</th>
                        <th>Vendor</th>
                        <th class="text-right">Debit</th>
                        <th class="text-right">Credit</th>
                        <th class="text-right">Balance</th>
                    </tr>
                </thead>
                <tbody>
                    ${journalItems.length > 0 ?
                        journalItems.map(item => `
                            <tr>
                                <td>${item.date || ''}</td>
                                <td>${item.move_name || item.name || ''}</td>
                                <td>${item.partner_id ? item.partner_id[1] : '—'}</td>
                                <td>${item.project_id ? item.project_id[1] : '—'}</td>
                                <td>${item.vendor_name || '—'}</td>
                                <td>${item.currency_id ? item.currency_id[1] : ''}</td>
                                <td class="number">${(item.debit || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                <td class="number">${(item.credit || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                <td class="number">${((item.balance !== undefined ? item.balance : (item.debit || 0) - (item.credit || 0))).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            </tr>
                        `).join('')
                        :
                        `<tr><td colspan="9" class="text-center">No records found</td></tr>`
                    }
                </tbody>
                <tfoot>
                    <tr class="total-row">
                        <td colspan="5"><strong>Total</strong></td>
                        <td class="number"><strong>${totalDebit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
                        <td class="number"><strong>${totalCredit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
                        <td class="number"><strong>${totalBalance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
                    </tr>
                </tfoot>
            </table>

            <div class="footer">
                Page 1 of 1 | Generated by Falcon Accounting System
            </div>

            <script>
                setTimeout(() => {
                    window.print();
                    setTimeout(() => {
                        window.close();
                    }, 1000);
                }, 500);
            </script>
        </body>
        </html>
    `;

    pdfWindow.document.write(pdfContent);
    pdfWindow.document.close();
}

// Excel Generation Function
function generateExcelFromTable(journalItems, dateText, filters = {}) {
    try {
        // Check if SheetJS is available
        if (typeof XLSX === 'undefined') {
            alert('Excel export library not loaded. Please contact administrator.');
            return;
        }

        // Create workbook and worksheet
        const wb = XLSX.utils.book_new();
        const wsData = [];

        // Add header information
        wsData.push(['Falcon General Ledger Report']);
        wsData.push(['Generated on: ' + new Date().toLocaleDateString()]);
        wsData.push([]);
        wsData.push(['Report Period: ' + dateText]);

        // Add filter information
        if (filters.partnerName || filters.projectName) {
            wsData.push([]);
            wsData.push(['Filters:']);
            if (filters.partnerName) {
                wsData.push(['Partner: ' + filters.partnerName]);
            }
            if (filters.projectName) {
                wsData.push(['Project: ' + filters.projectName]);
            }
        }

        wsData.push([]);

        // Add column headers
        wsData.push(['Date', 'Communication', 'Partner', 'Project', 'Vendor', 'Currency', 'Debit', 'Credit', 'Balance']);

        // Add data rows
        journalItems.forEach(item => {
            wsData.push([
                item.date || '',
                item.move_name || item.name || '',
                item.partner_id ? item.partner_id[1] : '—',
                item.project_id ? item.project_id[1] : '—',
                item.vendor_name || '—',
                item.currency_id ? item.currency_id[1] : '',
                item.debit || 0,
                item.credit || 0,
                item.balance !== undefined ? item.balance : (item.debit || 0) - (item.credit || 0)
            ]);
        });

        // Add totals row
        const totalDebit = journalItems.reduce((sum, item) => sum + (item.debit || 0), 0);
        const totalCredit = journalItems.reduce((sum, item) => sum + (item.credit || 0), 0);
        const totalBalance = journalItems.reduce((sum, item) => sum + (item.balance !== undefined ? item.balance : (item.debit || 0) - (item.credit || 0)), 0);

        wsData.push([]);
        wsData.push(['TOTAL', '', '', '', '', totalDebit, totalCredit, totalBalance]);

        // Create worksheet
        const ws = XLSX.utils.aoa_to_sheet(wsData);

        // Set column widths
        if (!ws['!cols']) ws['!cols'] = [];
        const colWidths = [12, 25, 20, 20, 12, 12, 12, 12];
        colWidths.forEach((width, index) => {
            ws['!cols'][index] = { width: width };
        });

        // Apply basic styling to header row (row 9, since we have 8 header rows)
        const headerRow = 9;
        'ABCDEFGH'.split('').forEach(col => {
            const cellAddress = col + headerRow;
            if (ws[cellAddress]) {
                ws[cellAddress].s = {
                    font: { bold: true, color: { rgb: 'FFFFFF' } },
                    fill: { fgColor: { rgb: '4472C4' } },
                    alignment: { horizontal: 'center' }
                };
            }
        });

        // Apply number formatting to debit, credit, and balance columns
        journalItems.forEach((_, index) => {
            const row = headerRow + index + 1;
            ['F', 'G', 'H'].forEach(col => {
                const cellAddress = col + row;
                if (ws[cellAddress]) {
                    ws[cellAddress].z = '#,##0.00';
                }
            });
        });

        // Format total row
        const totalRow = headerRow + journalItems.length + 1;
        'ABCDEFGH'.split('').forEach(col => {
            const cellAddress = col + totalRow;
            if (ws[cellAddress]) {
                ws[cellAddress].s = {
                    font: { bold: true },
                    fill: { fgColor: { rgb: 'F2F2F2' } }
                };
                if (['F', 'G', 'H'].includes(col)) {
                    ws[cellAddress].z = '#,##0.00';
                }
            }
        });

        // Add worksheet to workbook
        XLSX.utils.book_append_sheet(wb, ws, 'General Ledger');

        // Generate filename
        const filename = `General_Ledger_${dateText.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().split('T')[0]}.xlsx`;

        // Save the file
        XLSX.writeFile(wb, filename);

    } catch (error) {
        console.error('Error generating Excel file:', error);
        alert('Error generating Excel file. Please try again.');
    }
}

// Component Definition
export class FalconGeneralLedger extends Component {
    setup() {
        this.state = useState({
            selectedDateRange: "month",
            startDate: this.getFirstDayOfMonth(),
            endDate: this.getLastDayOfMonth(),
            dateText: this.getCurrentMonthText(),
            showDatePicker: false,
            selectedPartner: null,
            selectedProject: null,
            currentJournalItems: [], // Store current journal items for export
            tableData: [], // For template rendering
            isLoading: true
        });

        onWillStart(async () => {
            await this.loadJournalItems();
        });

        onMounted(() => {
            this.setupEventListeners();
        });
    }

    setupEventListeners() {
        // Toggle extra columns
        const toggleBtn = document.getElementById("toggle-btn");
        const extraCols = document.querySelectorAll(".col-extra");
        const partnerRow = document.querySelector(".partner-row");
        let expanded = true;

        if (toggleBtn) {
            toggleBtn.addEventListener("click", () => {
                expanded = !expanded;

                extraCols.forEach((col) => {
                    col.style.display = expanded ? "" : "none";
                });

                if (partnerRow) {
                    partnerRow.style.display = expanded ? "none" : "";
                }

                toggleBtn.textContent = expanded ? "Show Less ▲" : "Show More ▼";
            });
        }

        // Projects and Partners buttons logic
        const projectsBtn = document.getElementById("projects-btn");
        const partnersBtn = document.getElementById("partners-btn");
        const projectsInput = document.getElementById("projects-input");
        const partnersInput = document.getElementById("partners-input");

        if (projectsBtn && partnersBtn && projectsInput && partnersInput) {
            // Projects
            projectsBtn.addEventListener("click", async () => {
                const isVisible = projectsInput.style.display === "block";
                projectsInput.style.display = isVisible ? "none" : "block";
                partnersInput.style.display = "none";

                if (!isVisible) {
                    projectsInput.innerHTML = '<option value="">Select Project</option>';
                    try {
                        const projects = await fetchProjects();
                        projects.forEach((proj) => {
                            const option = document.createElement("option");
                            option.value = proj.id;
                            option.textContent = proj.name;
                            projectsInput.appendChild(option);
                        });
                    } catch (error) {
                        console.error("Failed to fetch projects:", error);
                    }
                }
            });

            projectsInput.addEventListener("change", async (e) => {
                const projectId = parseInt(e.target.value);
                if (projectId) {
                    await this.handleProjectSelect(projectId);
                }
            });

            // Partners
            partnersBtn.addEventListener("click", async () => {
                const isVisible = partnersInput.style.display === "block";
                partnersInput.style.display = isVisible ? "none" : "block";
                projectsInput.style.display = "none";

                if (!isVisible) {
                    partnersInput.innerHTML = '<option value="">Select Partner</option>';
                    try {
                        const partners = await fetchPartners();
                        partners.forEach((partner) => {
                            const option = document.createElement("option");
                            option.value = partner.id;
                            option.textContent = partner.name;
                            partnersInput.appendChild(option);
                        });
                    } catch (error) {
                        console.error("Failed to fetch partners:", error);
                    }
                }
            });

            partnersInput.addEventListener("change", async (e) => {
                const partnerId = parseInt(e.target.value);
                if (partnerId) {
                    await this.handlePartnerSelect(partnerId);
                }
            });
        }
    }

    // Helper functions for date handling
    getFirstDayOfMonth() {
        const date = new Date();
        return new Date(date.getFullYear(), date.getMonth(), 1).toISOString().split('T')[0];
    }

    getLastDayOfMonth() {
        const date = new Date();
        return new Date(date.getFullYear(), date.getMonth() + 1, 0).toISOString().split('T')[0];
    }

    getCurrentMonthText() {
        const date = new Date();
        return date.toLocaleString('default', { month: 'long', year: 'numeric' });
    }

    formatDateForDisplay(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString();
    }

    // Date range selection handlers
    selectThisMonth() {
        this.state.startDate = this.getFirstDayOfMonth();
        this.state.endDate = this.getLastDayOfMonth();
        this.state.dateText = this.getCurrentMonthText();
        this.state.selectedDateRange = "month";
        this.state.showDatePicker = false;
        this.state.selectedPartner = null;
        this.state.selectedProject = null;
        this.loadJournalItems();
    }

    selectLastMonth() {
        const date = new Date();
        const firstDay = new Date(date.getFullYear(), date.getMonth() - 1, 1);
        const lastDay = new Date(date.getFullYear(), date.getMonth(), 0);

        this.state.startDate = firstDay.toISOString().split('T')[0];
        this.state.endDate = lastDay.toISOString().split('T')[0];
        this.state.dateText = firstDay.toLocaleString('default', { month: 'long', year: 'numeric' });
        this.state.selectedDateRange = "month";
        this.state.showDatePicker = false;
        this.state.selectedPartner = null;
        this.state.selectedProject = null;
        this.loadJournalItems();
    }

    selectThisQuarter() {
        const date = new Date();
        const quarter = Math.floor(date.getMonth() / 3);
        const firstDay = new Date(date.getFullYear(), quarter * 3, 1);
        const lastDay = new Date(date.getFullYear(), quarter * 3 + 3, 0);

        this.state.startDate = firstDay.toISOString().split('T')[0];
        this.state.endDate = lastDay.toISOString().split('T')[0];
        this.state.dateText = `Q${quarter + 1} ${date.getFullYear()}`;
        this.state.selectedDateRange = "quarter";
        this.state.showDatePicker = false;
        this.state.selectedPartner = null;
        this.state.selectedProject = null;
        this.loadJournalItems();
    }

    selectThisYear() {
        const date = new Date();
        const firstDay = new Date(date.getFullYear(), 0, 1);
        const lastDay = new Date(date.getFullYear(), 11, 31);

        this.state.startDate = firstDay.toISOString().split('T')[0];
        this.state.endDate = lastDay.toISOString().split('T')[0];
        this.state.dateText = date.getFullYear().toString();
        this.state.selectedDateRange = "year";
        this.state.showDatePicker = false;
        this.state.selectedPartner = null;
        this.state.selectedProject = null;
        this.loadJournalItems();
    }

    // Custom date selection
    handleCustomDateSelect() {
        const startInput = document.getElementById("custom-start-date");
        const endInput = document.getElementById("custom-end-date");

        if (startInput && endInput && startInput.value && endInput.value) {
            this.state.startDate = startInput.value;
            this.state.endDate = endInput.value;

            const start = new Date(startInput.value);
            const end = new Date(endInput.value);

            if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
                this.state.dateText = start.toLocaleString('default', { month: 'long', year: 'numeric' });
            } else {
                this.state.dateText = `${this.formatDateForDisplay(startInput.value)} - ${this.formatDateForDisplay(endInput.value)}`;
            }

            this.state.selectedDateRange = "custom";
            this.state.showDatePicker = false;
            this.state.selectedPartner = null;
            this.state.selectedProject = null;
            this.loadJournalItems();
        }
    }

    // Toggle date picker visibility
    toggleDatePicker() {
        this.state.showDatePicker = !this.state.showDatePicker;

        const projectsInput = document.getElementById("projects-input");
        const partnersInput = document.getElementById("partners-input");

        if (projectsInput) projectsInput.style.display = "none";
        if (partnersInput) partnersInput.style.display = "none";
    }

    // PDF Generation Method
    async generatePDF() {
        try {
            if (this.state.currentJournalItems.length === 0) {
                alert("No data available to generate PDF.");
                return;
            }

            // Get current filter information
            const filters = {
                dateRange: this.state.dateText
            };

            // Add partner/project filter info if applicable
            if (this.state.selectedPartner) {
                const partners = await fetchPartners();
                const currentPartner = partners.find(p => p.id === this.state.selectedPartner);
                filters.partnerName = currentPartner ? `${currentPartner.name} (incl. projects)` : 'Unknown Partner';
            }

            if (this.state.selectedProject) {
                const projects = await fetchProjects();
                const currentProject = projects.find(p => p.id === this.state.selectedProject);
                filters.projectName = currentProject ? currentProject.name : 'Unknown Project';
            }

            // Generate PDF
            generatePDFFromTable(this.state.currentJournalItems, this.state.dateText, filters);

        } catch (error) {
            console.error('Error generating PDF:', error);
            alert('Error generating PDF. Please try again.');
        }
    }

    // Excel Generation Method
    async generateExcel() {
        try {
            if (this.state.currentJournalItems.length === 0) {
                alert("No data available to generate Excel file.");
                return;
            }

            // Get current filter information
            const filters = {
                dateRange: this.state.dateText
            };

            // Add partner/project filter info if applicable
            if (this.state.selectedPartner) {
                const partners = await fetchPartners();
                const currentPartner = partners.find(p => p.id === this.state.selectedPartner);
                filters.partnerName = currentPartner ? currentPartner.name : 'Unknown Partner';
            }

            if (this.state.selectedProject) {
                const projects = await fetchProjects();
                const currentProject = projects.find(p => p.id === this.state.selectedProject);
                filters.projectName = currentProject ? currentProject.name : 'Unknown Project';
            }

            // Generate Excel file
            generateExcelFromTable(this.state.currentJournalItems, this.state.dateText, filters);

        } catch (error) {
            console.error('Error generating Excel file:', error);
            alert('Error generating Excel file. Please try again.');
        }
    }

    // Load journal items based on current filters
    async loadJournalItems() {
        this.state.isLoading = true;
        let journalItems = [];

        try {
            if (this.state.selectedPartner) {
                journalItems = await fetchJournalItemsByPartner(this.state.selectedPartner);
            } else if (this.state.selectedProject) {
                journalItems = await fetchJournalItemsByProject(this.state.selectedProject);
            } else {
                journalItems = await fetchJournalItemsByDateRange(
                    this.state.startDate,
                    this.state.endDate
                );
            }

            journalItems = await attachVendorsToJournalItems(journalItems);


            // Store current journal items for export generation
            this.state.currentJournalItems = journalItems;
            this.state.tableData = journalItems;

        } catch (error) {
            console.error('Error loading journal items:', error);
            this.state.tableData = [];
        } finally {
            this.state.isLoading = false;
        }
    }

    // Handle partner selection
    async handlePartnerSelect(partnerId) {
        this.state.selectedPartner = partnerId;
        this.state.selectedProject = null;
        this.state.isLoading = true;

        try {
            const journalItems = await fetchJournalItemsByPartner(partnerId);
            this.state.currentJournalItems = journalItems;
            this.state.tableData = journalItems;
        } catch (error) {
            console.error("Error loading partner + project journal items:", error);
            this.state.tableData = [];
        } finally {
            this.state.isLoading = false;
        }
        // Keep project input cleared
        const projectsInput = document.getElementById("projects-input");
        if (projectsInput) projectsInput.value = "";
    }


    // Handle project selection
    async handleProjectSelect(projectId) {
        this.state.selectedProject = projectId;
        this.state.selectedPartner = null;
        await this.loadJournalItems();

        // Show Project column again
        document.querySelectorAll("th.project-col, td.project-col").forEach(col => {
            col.style.visibility = "visible";
        });

        const partnersInput = document.getElementById("partners-input");
        if (partnersInput) partnersInput.value = "";
    }
}

FalconGeneralLedger.template = "custom_general_ledger.falcon_general_ledger_template";
registry.category("actions").add("falcon_general_ledger_tag", FalconGeneralLedger);
