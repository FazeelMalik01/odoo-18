odoo.define('custom_owner_approval.owner_approval_pagination', [], function () {
    'use strict';

    function initPagination() {
        const tbody = document.getElementById('owner_approval_tbody');
        const paginationEl = document.getElementById('owner_approval_pagination');
        const rowsPerPage = 10;

        if (!tbody || !paginationEl) return;

        let currentPage = 1;

        function showPage(page) {
            const rows = Array.from(tbody.querySelectorAll('tr.approval-row'));
            const noResultsRow = document.getElementById('owner_approval_no_results');

            // Filter visible rows based on data-filtered attribute (set by filters)
            const visibleRows = rows.filter(r => r.dataset.filtered === 'true');
            const totalPages = Math.ceil(visibleRows.length / rowsPerPage) || 1;

            // Clamp page
            if (page < 1) page = 1;
            if (page > totalPages) page = totalPages;
            currentPage = page;

            // Hide all rows first
            rows.forEach(r => r.classList.add('d-none'));

            // Show current page rows
            const start = (currentPage - 1) * rowsPerPage;
            const end = start + rowsPerPage;
            visibleRows.slice(start, end).forEach(r => r.classList.remove('d-none'));

            // Show "No results" if nothing visible
            if (visibleRows.length === 0) {
                noResultsRow?.classList.remove('d-none');
            } else {
                noResultsRow?.classList.add('d-none');
            }

            // Render pagination buttons
            renderPagination(totalPages);
        }

        function renderPagination(totalPages) {
            paginationEl.innerHTML = '';

            for (let i = 1; i <= totalPages; i++) {
                const li = document.createElement('li');
                li.className = 'page-item' + (i === currentPage ? ' active' : '');
                li.innerHTML = `<a href="#" class="page-link">${i}</a>`;
                li.addEventListener('click', function (e) {
                    e.preventDefault();
                    showPage(i);
                });
                paginationEl.appendChild(li);
            }
        }

        // Hook into filtering
        function updatePaginationAfterFilter() {
            const rows = Array.from(tbody.querySelectorAll('tr.approval-row'));
            rows.forEach(r => {
                // Mark rows as filtered or not based on d-none (set by filterTable)
                r.dataset.filtered = r.classList.contains('d-none') ? 'false' : 'true';
            });

            currentPage = 1;
            showPage(currentPage);
        }

        // Listen for custom event "filters-updated" from your filter JS
        document.addEventListener('filters-updated', updatePaginationAfterFilter);

        // Initial display: mark all rows as filtered
        const rows = Array.from(tbody.querySelectorAll('tr.approval-row'));
        rows.forEach(r => r.dataset.filtered = 'true');
        showPage(currentPage);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPagination);
    } else {
        initPagination();
    }
});
