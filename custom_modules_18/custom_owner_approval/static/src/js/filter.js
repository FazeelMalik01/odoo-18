odoo.define('custom_owner_approval.owner_approval_search', [], function () {
    'use strict';

    function initFilters() {
        const searchEl = document.getElementById('owner_approval_search');
        const statusEl = document.getElementById('owner_status_filter');
        const typeEl = document.getElementById('owner_type_filter');
        const projectEl = document.getElementById('owner_project_filter');
        const taskEl = document.getElementById('owner_task_filter');
        const tbody = document.getElementById('owner_approval_tbody');
        const noResultsRow = document.getElementById('owner_approval_no_results');
        const clearEl = document.getElementById('owner_clear_filters');

        if (!tbody) return;

        function filterTable() {
            const q = (searchEl?.value || '').trim().toLowerCase();
            const selectedStatus = (statusEl?.value || '').toLowerCase();
            const selectedType = (typeEl?.value || '').toLowerCase();
            const selectedProject = projectEl?.value || '';
            const selectedTask = taskEl?.value || '';

            const rows = tbody.querySelectorAll('tr.approval-row');
            let visibleCount = 0;

            rows.forEach(row => {
                const name = (row.dataset.name || '').toLowerCase();
                const title = (row.dataset.title || '').toLowerCase();
                const type = (row.dataset.type || '').toLowerCase();
                const state = (row.dataset.state || '').toLowerCase();
                const project = row.dataset.project || '';
                const task = row.dataset.task || '';

                const matchSearch =
                    !q || name.includes(q) || title.includes(q) || type.includes(q);

                const matchStatus = !selectedStatus || state === selectedStatus;
                const matchType = !selectedType || type === selectedType;
                const matchProject = !selectedProject || project === selectedProject;
                const matchTask = !selectedTask || task === selectedTask;

                const show =
                    matchSearch &&
                    matchStatus &&
                    matchType &&
                    matchProject &&
                    matchTask;

                row.classList.toggle('d-none', !show);
                if (show) visibleCount++;
            });

            if (noResultsRow) {
                noResultsRow.classList.toggle(
                    'd-none',
                    !(visibleCount === 0 && rows.length > 0)
                );
            }
        }

        // Events
        searchEl?.addEventListener('input', filterTable);
        statusEl?.addEventListener('change', filterTable);
        typeEl?.addEventListener('change', filterTable);
        projectEl?.addEventListener('change', filterTable);
        taskEl?.addEventListener('change', filterTable);

        // Clear filters
        clearEl?.addEventListener('click', function (e) {
            e.preventDefault();

            if (searchEl) searchEl.value = '';
            if (statusEl) statusEl.value = '';
            if (typeEl) typeEl.value = '';
            if (projectEl) projectEl.value = '';
            if (taskEl) taskEl.value = '';

            filterTable();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFilters);
    } else {
        initFilters();
    }
});
