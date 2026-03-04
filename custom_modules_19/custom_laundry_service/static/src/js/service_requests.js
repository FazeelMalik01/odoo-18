(function() {
    'use strict';

    function initStatusSelects() {
        const statusSelects = document.querySelectorAll('.status-select');
        
        statusSelects.forEach(function(select) {
            const appointmentId = select.getAttribute('data-appointment-id');
            const currentStatus = select.getAttribute('data-current-status');
            
            // Store original value
            select.setAttribute('data-original-status', currentStatus);
            
            // Handle change event
            select.addEventListener('change', function() {
                const newStatus = this.value;
                const originalStatus = this.getAttribute('data-original-status');
                
                // If status didn't actually change, do nothing
                if (newStatus === originalStatus) {
                    return;
                }
                
                // Disable select while updating
                this.disabled = true;
                const originalValue = this.value;
                
                // Show loading state
                const originalHTML = this.innerHTML;
                this.innerHTML = '<option>Updating...</option>';
                
                // Prepare JSON-RPC request
                const jsonRpcRequest = {
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        appointment_id: parseInt(appointmentId),
                        status: newStatus
                    },
                    id: Math.floor(Math.random() * 1000000000)
                };
                
                // Send update request
                fetch('/my/service-requests/update_status', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(jsonRpcRequest)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok: ' + response.status);
                    }
                    return response.json();
                })
                .then(data => {
                    // Handle JSON-RPC response format
                    if (data.error) {
                        console.error('Error updating status:', data.error);
                        const errorMsg = data.error.message || data.error.data?.message || 'Unknown error';
                        alert('Error updating status: ' + errorMsg);
                        // Revert to original value
                        this.value = originalStatus;
                        this.innerHTML = originalHTML;
                        // Find and select the original option
                        const options = this.querySelectorAll('option');
                        options.forEach(opt => {
                            if (opt.value === originalStatus) {
                                opt.selected = true;
                            }
                        });
                    } else if (data.result) {
                        const result = data.result;
                        if (result.success) {
                            // Success - update the original status
                            this.setAttribute('data-original-status', newStatus);
                            this.setAttribute('data-current-status', newStatus);
                            // Reload page to show updated status with correct styling
                            window.location.reload();
                        } else {
                            alert('Error updating status. Please try again.');
                            this.value = originalStatus;
                            this.innerHTML = originalHTML;
                            const options = this.querySelectorAll('option');
                            options.forEach(opt => {
                                if (opt.value === originalStatus) {
                                    opt.selected = true;
                                }
                            });
                        }
                    } else {
                        throw new Error('Unexpected response format');
                    }
                })
                .catch(error => {
                    console.error('Error updating status:', error);
                    alert('Error updating status. Please try again.');
                    // Revert to original value
                    this.value = originalStatus;
                    this.innerHTML = originalHTML;
                    const options = this.querySelectorAll('option');
                    options.forEach(opt => {
                        if (opt.value === originalStatus) {
                            opt.selected = true;
                        }
                    });
                })
                .finally(() => {
                    this.disabled = false;
                });
            });
        });
    }

    function initImageUploads() {
        // Handle image upload button clicks
        const uploadButtons = document.querySelectorAll('.upload-images-btn');
        uploadButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                const appointmentId = this.getAttribute('data-appointment-id');
                const container = this.closest('.completion-images-container');
                const fileInput = container.querySelector('.completion-image-input');
                const files = fileInput.files;
                
                if (!files || files.length === 0) {
                    alert('Please select at least one image to upload.');
                    return;
                }
                
                // Disable button during upload
                this.disabled = true;
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i>Uploading...';
                
                // Create FormData
                const formData = new FormData();
                formData.append('appointment_id', appointmentId);
                
                for (let i = 0; i < files.length; i++) {
                    formData.append('images[]', files[i]);
                }
                
                // Upload images
                fetch('/my/service-requests/upload_images', {
                    method: 'POST',
                    credentials: 'same-origin',
                    body: formData
                })
                .then(response => {
                    // Get content type to check if it's JSON
                    const contentType = response.headers.get('content-type') || '';
                    const isJson = contentType.includes('application/json');
                    
                    // Check if response is ok
                    if (!response.ok) {
                        if (isJson) {
                            return response.json().then(data => {
                                throw new Error(data.error || `HTTP error! status: ${response.status}`);
                            });
                        } else {
                            // If HTML error page, return generic error
                            return response.text().then(html => {
                                console.error('Server returned HTML error page:', html.substring(0, 200));
                                throw new Error(`Server error (${response.status}). Please check the server logs.`);
                            });
                        }
                    }
                    
                    if (isJson) {
                        return response.json();
                    } else {
                        // Try to parse as JSON anyway
                        return response.text().then(text => {
                            try {
                                return JSON.parse(text);
                            } catch (e) {
                                throw new Error('Invalid response format from server');
                            }
                        });
                    }
                })
                .then(data => {
                    if (data.success) {
                        // Clear file input
                        fileInput.value = '';
                        // Reload page to show uploaded images
                        window.location.reload();
                    } else {
                        alert('Error uploading images: ' + (data.error || 'Unknown error'));
                        this.disabled = false;
                        this.innerHTML = originalText;
                    }
                })
                .catch(error => {
                    console.error('Error uploading images:', error);
                    let errorMessage = 'Error uploading images. Please try again.';
                    if (error.message) {
                        errorMessage += '\n' + error.message;
                    }
                    alert(errorMessage);
                    this.disabled = false;
                    this.innerHTML = originalText;
                });
            });
        });
        
        // Handle view images button clicks
        const viewButtons = document.querySelectorAll('.view-images-btn');
        viewButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                const imagesData = this.getAttribute('data-images');
                if (!imagesData) {
                    alert('No images to display.');
                    return;
                }
                
                try {
                    const images = JSON.parse(imagesData);
                    console.log('Parsed images:', images);
                    if (!images || images.length === 0) {
                        alert('No images to display.');
                        return;
                    }
                    
                    // Get or create modal
                    let modal = document.getElementById('completionImagesModal');
                    if (!modal) {
                        // Create modal if it doesn't exist
                        modal = document.createElement('div');
                        modal.className = 'modal fade';
                        modal.id = 'completionImagesModal';
                        modal.setAttribute('tabindex', '-1');
                        modal.setAttribute('aria-labelledby', 'completionImagesModalLabel');
                        modal.setAttribute('aria-hidden', 'true');
                        modal.innerHTML = `
                            <div class="modal-dialog modal-lg modal-dialog-centered">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title" id="completionImagesModalLabel">Completion Images</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                    </div>
                                    <div class="modal-body">
                                        <div id="modal-images-container" class="row g-3"></div>
                                    </div>
                                    <div class="modal-footer">
                                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                    </div>
                                </div>
                            </div>
                        `;
                        document.body.appendChild(modal);
                    }
                    
                    // Clear and populate images container
                    const container = modal.querySelector('#modal-images-container');
                    container.innerHTML = '';
                    
                    images.forEach(function(image) {
                        console.log('Processing image:', image);
                        const col = document.createElement('div');
                        col.className = 'col-md-6 col-lg-4';
                        
                        // Create image element - use the custom route URL
                        const img = document.createElement('img');
                        const imageUrl = image.url || `/my/service-requests/image/${image.id}`;
                        img.alt = image.name || 'Image';
                        img.className = 'card-img-top';
                        img.style.cssText = 'height: 200px; object-fit: cover; cursor: pointer; width: 100%; background-color: #f0f0f0; display: block;';
                        img.onclick = function() {
                            window.open(imageUrl, '_blank');
                        };
                        img.onload = function() {
                            console.log('Image loaded successfully:', imageUrl, 'Dimensions:', this.naturalWidth, 'x', this.naturalHeight);
                        };
                        img.onerror = function() {
                            console.error('Failed to load image:', imageUrl);
                            // Show placeholder on error
                            this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2RkZCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5JbWFnZSBub3QgYXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg==';
                            this.style.cursor = 'default';
                        };
                        // Set the image source
                        img.src = imageUrl;
                        
                        const cardBody = document.createElement('div');
                        cardBody.className = 'card-body p-2';
                        
                        const fileName = document.createElement('p');
                        fileName.className = 'card-text small text-truncate mb-0';
                        fileName.title = image.name || 'Image';
                        fileName.textContent = image.name || 'Image';
                        
                        const deleteBtn = document.createElement('button');
                        deleteBtn.type = 'button';
                        deleteBtn.className = 'btn btn-sm btn-danger mt-1 delete-image-btn-modal';
                        deleteBtn.setAttribute('data-image-id', image.id);
                        deleteBtn.setAttribute('data-appointment-id', button.getAttribute('data-appointment-id'));
                        deleteBtn.innerHTML = '<i class="fa fa-trash me-1"></i>Delete';
                        
                        cardBody.appendChild(fileName);
                        cardBody.appendChild(deleteBtn);
                        
                        const card = document.createElement('div');
                        card.className = 'card';
                        card.appendChild(img);
                        card.appendChild(cardBody);
                        
                        col.appendChild(card);
                        container.appendChild(col);
                    });
                    
                    // Initialize Bootstrap modal and show it
                    // Check if Bootstrap 5 is available
                    if (typeof bootstrap !== 'undefined') {
                        const bsModal = new bootstrap.Modal(modal);
                        bsModal.show();
                    } else if (typeof jQuery !== 'undefined' && jQuery.fn.modal) {
                        // Fallback to jQuery/bootstrap 4
                        jQuery(modal).modal('show');
                    } else {
                        // Fallback: show modal manually
                        modal.style.display = 'block';
                        modal.classList.add('show');
                        document.body.classList.add('modal-open');
                        const backdrop = document.createElement('div');
                        backdrop.className = 'modal-backdrop fade show';
                        backdrop.id = 'modal-backdrop';
                        document.body.appendChild(backdrop);
                        
                        // Handle close button
                        modal.querySelector('.btn-close, [data-bs-dismiss="modal"], .btn-secondary').addEventListener('click', function() {
                            modal.style.display = 'none';
                            modal.classList.remove('show');
                            document.body.classList.remove('modal-open');
                            const backdrop = document.getElementById('modal-backdrop');
                            if (backdrop) {
                                backdrop.remove();
                            }
                        });
                    }
                } catch (error) {
                    console.error('Error parsing images data:', error);
                    alert('Error loading images. Please try again.');
                }
            });
        });
        
        // Handle image deletion from modal
        document.addEventListener('click', function(e) {
            if (e.target.closest('.delete-image-btn-modal')) {
                const button = e.target.closest('.delete-image-btn-modal');
                if (!confirm('Are you sure you want to delete this image?')) {
                    return;
                }
                
                const imageId = button.getAttribute('data-image-id');
                const appointmentId = button.getAttribute('data-appointment-id');
                
                // Disable button
                button.disabled = true;
                
                // Delete image
                const jsonRpcRequest = {
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        image_id: parseInt(imageId)
                    },
                    id: Math.floor(Math.random() * 1000000000)
                };
                
                fetch('/my/service-requests/delete_image', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(jsonRpcRequest)
                })
                .then(response => response.json())
                .then(data => {
                    // Handle JSON-RPC response format
                    const result = data.result || data;
                    if (result.success) {
                        // Reload page to update image list
                        window.location.reload();
                    } else {
                        alert('Error deleting image: ' + (result.error || 'Unknown error'));
                        button.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('Error deleting image:', error);
                    alert('Error deleting image. Please try again.');
                    button.disabled = false;
                });
            }
        });
        
        // Handle image deletion
        const deleteButtons = document.querySelectorAll('.delete-image-btn');
        deleteButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                if (!confirm('Are you sure you want to delete this image?')) {
                    return;
                }
                
                const imageId = this.getAttribute('data-image-id');
                const appointmentId = this.getAttribute('data-appointment-id');
                
                // Disable button
                this.disabled = true;
                
                // Delete image
                const jsonRpcRequest = {
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        image_id: parseInt(imageId)
                    },
                    id: Math.floor(Math.random() * 1000000000)
                };
                
                fetch('/my/service-requests/delete_image', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(jsonRpcRequest)
                })
                .then(response => response.json())
                .then(data => {
                    // Handle JSON-RPC response format
                    const result = data.result || data;
                    if (result.success) {
                        // Reload page to update image list
                        window.location.reload();
                    } else {
                        alert('Error deleting image: ' + (result.error || 'Unknown error'));
                        this.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('Error deleting image:', error);
                    alert('Error deleting image. Please try again.');
                    this.disabled = false;
                });
            });
        });
    }

    function initCustomerImageViewer() {
        // Handle customer view images button clicks
        const viewButtons = document.querySelectorAll('.view-images-btn-customer');
        viewButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                const imagesData = this.getAttribute('data-images');
                if (!imagesData) {
                    alert('No images to display.');
                    return;
                }
                
                try {
                    const images = JSON.parse(imagesData);
                    console.log('Parsed images:', images);
                    if (!images || images.length === 0) {
                        alert('No images to display.');
                        return;
                    }
                    
                    // Get or create modal
                    let modal = document.getElementById('customerCompletionImagesModal');
                    if (!modal) {
                        // Create modal if it doesn't exist
                        modal = document.createElement('div');
                        modal.className = 'modal fade';
                        modal.id = 'customerCompletionImagesModal';
                        modal.setAttribute('tabindex', '-1');
                        modal.setAttribute('aria-labelledby', 'customerCompletionImagesModalLabel');
                        modal.setAttribute('aria-hidden', 'true');
                        modal.innerHTML = `
                            <div class="modal-dialog modal-lg modal-dialog-centered">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title" id="customerCompletionImagesModalLabel">Completion Images</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                    </div>
                                    <div class="modal-body">
                                        <div id="customer-modal-images-container" class="row g-3"></div>
                                    </div>
                                    <div class="modal-footer">
                                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                    </div>
                                </div>
                            </div>
                        `;
                        document.body.appendChild(modal);
                    }
                    
                    // Clear and populate images container
                    const container = modal.querySelector('#customer-modal-images-container');
                    container.innerHTML = '';
                    
                    images.forEach(function(image) {
                        console.log('Processing image:', image);
                        const col = document.createElement('div');
                        col.className = 'col-md-6 col-lg-4';
                        
                        // Create image element - use the custom route URL
                        const img = document.createElement('img');
                        const imageUrl = image.url || `/my/service-requests/image/${image.id}`;
                        img.alt = image.name || 'Image';
                        img.className = 'card-img-top';
                        img.style.cssText = 'height: 200px; object-fit: cover; cursor: pointer; width: 100%; background-color: #f0f0f0; display: block;';
                        img.onclick = function() {
                            window.open(imageUrl, '_blank');
                        };
                        img.onload = function() {
                            console.log('Image loaded successfully:', imageUrl, 'Dimensions:', this.naturalWidth, 'x', this.naturalHeight);
                        };
                        img.onerror = function() {
                            console.error('Failed to load image:', imageUrl);
                            // Show placeholder on error
                            this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2RkZCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5JbWFnZSBub3QgYXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg==';
                            this.style.cursor = 'default';
                        };
                        // Set the image source
                        img.src = imageUrl;
                        
                        const cardBody = document.createElement('div');
                        cardBody.className = 'card-body p-2';
                        
                        const fileName = document.createElement('p');
                        fileName.className = 'card-text small text-truncate mb-0';
                        fileName.title = image.name || 'Image';
                        fileName.textContent = image.name || 'Image';
                        
                        cardBody.appendChild(fileName);
                        
                        const card = document.createElement('div');
                        card.className = 'card';
                        card.appendChild(img);
                        card.appendChild(cardBody);
                        
                        col.appendChild(card);
                        container.appendChild(col);
                    });
                    
                    // Initialize Bootstrap modal and show it
                    // Check if Bootstrap 5 is available
                    if (typeof bootstrap !== 'undefined') {
                        const bsModal = new bootstrap.Modal(modal);
                        bsModal.show();
                    } else if (typeof jQuery !== 'undefined' && jQuery.fn.modal) {
                        // Bootstrap 4 with jQuery
                        jQuery(modal).modal('show');
                    } else {
                        // Fallback: manually show modal
                        modal.style.display = 'block';
                        modal.classList.add('show');
                        document.body.classList.add('modal-open');
                        
                        // Create backdrop
                        const backdrop = document.createElement('div');
                        backdrop.className = 'modal-backdrop fade show';
                        backdrop.id = 'customer-modal-backdrop';
                        document.body.appendChild(backdrop);
                        
                        // Handle close button
                        modal.querySelector('.btn-close, [data-bs-dismiss="modal"], .btn-secondary').addEventListener('click', function() {
                            modal.style.display = 'none';
                            modal.classList.remove('show');
                            document.body.classList.remove('modal-open');
                            const backdrop = document.getElementById('customer-modal-backdrop');
                            if (backdrop) {
                                backdrop.remove();
                            }
                        });
                    }
                } catch (error) {
                    console.error('Error parsing images data:', error);
                    alert('Error loading images. Please try again.');
                }
            });
        });
    }

    function initServiceRequestDetailLinks() {
        // Handle service request detail link clicks
        const detailLinks = document.querySelectorAll('.service-request-detail-link');
        detailLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const appointmentId = this.getAttribute('data-appointment-id');
                if (!appointmentId) {
                    alert('Invalid service request ID.');
                    return;
                }
                
                // Get or create modal
                let modal = document.getElementById('serviceRequestDetailModal');
                if (!modal) {
                    alert('Modal not found. Please refresh the page.');
                    return;
                }
                
                // Show loading state
                const contentDiv = modal.querySelector('#service-request-detail-content');
                contentDiv.innerHTML = `
                    <div class="text-center">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2">Loading details...</p>
                    </div>
                `;
                
                // Show modal
                if (typeof bootstrap !== 'undefined') {
                    const bsModal = new bootstrap.Modal(modal);
                    bsModal.show();
                } else if (typeof jQuery !== 'undefined' && jQuery.fn.modal) {
                    jQuery(modal).modal('show');
                } else {
                    modal.style.display = 'block';
                    modal.classList.add('show');
                    document.body.classList.add('modal-open');
                }
                
                // Fetch service request details
                const jsonRpcRequest = {
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        appointment_id: parseInt(appointmentId)
                    },
                    id: Math.floor(Math.random() * 1000000000)
                };
                
                fetch('/my/service-requests/get_details', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(jsonRpcRequest)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok: ' + response.status);
                    }
                    return response.json();
                })
                .then(data => {
                    // Handle JSON-RPC response format
                    if (data.error) {
                        console.error('Error loading details:', data.error);
                        const errorMsg = data.error.message || data.error.data?.message || 'Unknown error';
                        contentDiv.innerHTML = `
                            <div class="alert alert-danger" role="alert">
                                <strong>Error:</strong> ${errorMsg}
                            </div>
                        `;
                        return;
                    }
                    
                    const details = data.result || {};
                    
                    // Format the details in a nice layout
                    contentDiv.innerHTML = `
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Request Number</h6>
                                <p class="mb-0"><strong>${details.name || 'N/A'}</strong></p>
                            </div>
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Status</h6>
                                <p class="mb-0">
                                    <span class="badge bg-${details.status_value === 'pending' ? 'warning' : details.status_value === 'completed' ? 'success' : details.status_value === 'cancelled' ? 'danger' : 'info'}">
                                        ${details.status || 'N/A'}
                                    </span>
                                </p>
                            </div>
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Date</h6>
                                <p class="mb-0">${details.date || 'N/A'}</p>
                            </div>
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Time</h6>
                                <p class="mb-0">${details.time || 'N/A'}</p>
                            </div>
                            <div class="col-12 mb-3">
                                <h6 class="text-muted mb-1">Service Types</h6>
                                <p class="mb-0">${details.service_types || 'N/A'}</p>
                            </div>
                            <div class="col-12 mb-3">
                                <hr/>
                                <h6 class="text-muted mb-2">Customer Information</h6>
                            </div>
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Customer Name</h6>
                                <p class="mb-0">${details.customer_name || 'N/A'}</p>
                            </div>
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Phone</h6>
                                <p class="mb-0">${details.phone || 'N/A'}</p>
                            </div>
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Email</h6>
                                <p class="mb-0">${details.email || 'N/A'}</p>
                            </div>
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Zip Code</h6>
                                <p class="mb-0">${details.zip_code || 'N/A'}</p>
                            </div>
                            <div class="col-12 mb-3">
                                <hr/>
                                <h6 class="text-muted mb-2">Address Information</h6>
                            </div>
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Pickup Address</h6>
                                <p class="mb-0" style="white-space: pre-wrap;">${details.pickup_address || 'N/A'}</p>
                            </div>
                            <div class="col-md-6 mb-3">
                                <h6 class="text-muted mb-1">Delivery Address</h6>
                                <p class="mb-0" style="white-space: pre-wrap;">${details.delivery_address || 'N/A'}</p>
                            </div>
                            <div class="col-12 mb-3">
                                <hr/>
                                <h6 class="text-muted mb-2">Notes / Special Instructions</h6>
                                <p class="mb-0" style="white-space: pre-wrap;">${details.notes || 'N/A'}</p>
                            </div>
                        </div>
                    `;
                })
                .catch(error => {
                    console.error('Error loading service request details:', error);
                    contentDiv.innerHTML = `
                        <div class="alert alert-danger" role="alert">
                            <strong>Error:</strong> Failed to load service request details. Please try again.
                        </div>
                    `;
                });
            });
        });
    }

    function toggleApprovalStatusColumns() {
        // Check if any row has status confirmed or has_responded
        const rows = document.querySelectorAll('tbody tr');
        let hasConfirmedOrResponded = false;
        
        rows.forEach(function(row) {
            const statusColumn = row.querySelector('.status-column');
            if (statusColumn && statusColumn.style.display !== 'none') {
                hasConfirmedOrResponded = true;
            }
        });
        
        // Toggle header columns
        const approvalHeader = document.querySelector('.approval-column-header');
        const statusHeader = document.querySelector('.status-column-header');
        
        if (hasConfirmedOrResponded) {
            if (approvalHeader) approvalHeader.style.display = 'none';
            if (statusHeader) statusHeader.style.display = 'table-cell';
        } else {
            if (approvalHeader) approvalHeader.style.display = 'table-cell';
            if (statusHeader) statusHeader.style.display = 'none';
        }
    }

    function initApprovalButtons() {
        // Handle Accept button clicks
        const acceptButtons = document.querySelectorAll('.accept-request-btn');
        acceptButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                const appointmentId = this.getAttribute('data-appointment-id');
                if (!appointmentId) {
                    alert('Invalid appointment ID.');
                    return;
                }
                
                if (!confirm('Are you sure you want to accept this service request?')) {
                    return;
                }
                
                // Disable button
                this.disabled = true;
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i>Accepting...';
                
                // Prepare JSON-RPC request
                const jsonRpcRequest = {
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        appointment_id: parseInt(appointmentId)
                    },
                    id: Math.floor(Math.random() * 1000000000)
                };
                
                // Send approve request
                fetch('/my/service-requests/approve_request', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(jsonRpcRequest)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok: ' + response.status);
                    }
                    return response.json();
                })
                .then(data => {
                    // Handle JSON-RPC response format
                    if (data.error) {
                        console.error('Error approving request:', data.error);
                        const errorMsg = data.error.message || data.error.data?.message || 'Unknown error';
                        alert('Error approving request: ' + errorMsg);
                        this.disabled = false;
                        this.innerHTML = originalText;
                    } else if (data.result) {
                        const result = data.result;
                        if (result.success) {
                            // Success - reload page to show updated status
                            window.location.reload();
                        } else {
                            alert('Error approving request. Please try again.');
                            this.disabled = false;
                            this.innerHTML = originalText;
                        }
                    } else {
                        throw new Error('Unexpected response format');
                    }
                })
                .catch(error => {
                    console.error('Error approving request:', error);
                    alert('Error approving request. Please try again.');
                    this.disabled = false;
                    this.innerHTML = originalText;
                });
            });
        });
        
        // Handle Reject button clicks
        const rejectButtons = document.querySelectorAll('.reject-request-btn');
        rejectButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                const appointmentId = this.getAttribute('data-appointment-id');
                if (!appointmentId) {
                    alert('Invalid appointment ID.');
                    return;
                }
                
                if (!confirm('Are you sure you want to reject this service request? It will be hidden from your list.')) {
                    return;
                }
                
                // Disable button
                this.disabled = true;
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i>Rejecting...';
                
                // Prepare JSON-RPC request
                const jsonRpcRequest = {
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        appointment_id: parseInt(appointmentId)
                    },
                    id: Math.floor(Math.random() * 1000000000)
                };
                
                // Send reject request
                fetch('/my/service-requests/reject_request', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(jsonRpcRequest)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok: ' + response.status);
                    }
                    return response.json();
                })
                .then(data => {
                    // Handle JSON-RPC response format
                    if (data.error) {
                        console.error('Error rejecting request:', data.error);
                        const errorMsg = data.error.message || data.error.data?.message || 'Unknown error';
                        alert('Error rejecting request: ' + errorMsg);
                        this.disabled = false;
                        this.innerHTML = originalText;
                    } else if (data.result) {
                        const result = data.result;
                        if (result.success) {
                            // Success - reload page to hide rejected request
                            window.location.reload();
                        } else {
                            alert('Error rejecting request. Please try again.');
                            this.disabled = false;
                            this.innerHTML = originalText;
                        }
                    } else {
                        throw new Error('Unexpected response format');
                    }
                })
                .catch(error => {
                    console.error('Error rejecting request:', error);
                    alert('Error rejecting request. Please try again.');
                    this.disabled = false;
                    this.innerHTML = originalText;
                });
            });
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initStatusSelects();
            initImageUploads();
            initCustomerImageViewer();
            initServiceRequestDetailLinks();
            initApprovalButtons();
            toggleApprovalStatusColumns();
        });
    } else {
        initStatusSelects();
        initImageUploads();
        initCustomerImageViewer();
        initServiceRequestDetailLinks();
        initApprovalButtons();
        toggleApprovalStatusColumns();
    }
})();

