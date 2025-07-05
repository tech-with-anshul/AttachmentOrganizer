// Dashboard JavaScript functionality

let recognitionSystem = {
    isRunning: false,
    statusCheckInterval: null
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    // Start periodic status checks
    startStatusChecking();
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

function startStatusChecking() {
    // Check status immediately
    checkRecognitionStatus();
    
    // Set up periodic checking
    recognitionSystem.statusCheckInterval = setInterval(checkRecognitionStatus, 30000); // Every 30 seconds
}

function stopStatusChecking() {
    if (recognitionSystem.statusCheckInterval) {
        clearInterval(recognitionSystem.statusCheckInterval);
        recognitionSystem.statusCheckInterval = null;
    }
}

function checkRecognitionStatus() {
    fetch('/api/recognition/status')
        .then(response => response.json())
        .then(data => {
            updateRecognitionStatus(data.is_running);
        })
        .catch(error => {
            console.error('Error checking recognition status:', error);
            updateRecognitionStatus(false);
        });
}

function updateRecognitionStatus(isRunning) {
    recognitionSystem.isRunning = isRunning;
    
    const toggleButton = document.getElementById('recognition-toggle');
    const statusSpan = document.getElementById('recognition-status');
    const statusCard = document.getElementById('recognition-status-card');
    
    if (toggleButton && statusSpan) {
        if (isRunning) {
            toggleButton.className = 'btn btn-outline-danger';
            toggleButton.innerHTML = '<i data-feather="stop-circle" class="me-1"></i><span id="recognition-status">Stop Recognition</span>';
            statusSpan.textContent = 'Stop Recognition';
        } else {
            toggleButton.className = 'btn btn-outline-success';
            toggleButton.innerHTML = '<i data-feather="play" class="me-1"></i><span id="recognition-status">Start Recognition</span>';
            statusSpan.textContent = 'Start Recognition';
        }
        
        // Refresh feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
    
    if (statusCard) {
        statusCard.textContent = isRunning ? 'Running' : 'Stopped';
        statusCard.className = isRunning ? 'mb-0 text-success' : 'mb-0 text-danger';
    }
}

function toggleRecognitionSystem() {
    const isRunning = recognitionSystem.isRunning;
    const endpoint = isRunning ? '/api/recognition/stop' : '/api/recognition/start';
    
    // Disable button during request
    const toggleButton = document.getElementById('recognition-toggle');
    if (toggleButton) {
        toggleButton.disabled = true;
        toggleButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
    }
    
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert('Error: ' + data.error, 'danger');
        } else {
            showAlert(data.message, 'success');
            // Check status after a short delay
            setTimeout(checkRecognitionStatus, 1000);
        }
    })
    .catch(error => {
        console.error('Error toggling recognition system:', error);
        showAlert('Failed to toggle recognition system', 'danger');
    })
    .finally(() => {
        // Re-enable button
        if (toggleButton) {
            toggleButton.disabled = false;
            checkRecognitionStatus(); // This will update the button text
        }
    });
}

function showAlert(message, type = 'info') {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type} alert-dismissible fade show`;
    alertContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of the main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.insertBefore(alertContainer, mainContent.firstChild);
    }
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertContainer.parentNode) {
            alertContainer.remove();
        }
    }, 5000);
}

function refreshDashboard() {
    // Show loading indicator
    const refreshButton = document.querySelector('[onclick="refreshDashboard()"]');
    if (refreshButton) {
        const originalContent = refreshButton.innerHTML;
        refreshButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Refreshing...';
        refreshButton.disabled = true;
        
        // Reload page after short delay
        setTimeout(() => {
            window.location.reload();
        }, 500);
    } else {
        window.location.reload();
    }
}

function exportAttendance() {
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;
    const employeeId = document.getElementById('employee-filter')?.value;
    
    let url = '/api/attendance/export?';
    const params = new URLSearchParams();
    
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (employeeId) params.append('employee_id', employeeId);
    
    url += params.toString();
    
    // Create temporary link to trigger download
    const link = document.createElement('a');
    link.href = url;
    link.download = `attendance_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showAlert('Attendance export started', 'success');
}

function applyFilters() {
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;
    const employeeId = document.getElementById('employee-filter')?.value;
    
    // Build query parameters
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (employeeId) params.append('employee_id', employeeId);
    
    // Reload page with filters
    const newUrl = window.location.pathname + '?' + params.toString();
    window.location.href = newUrl;
}

function resetFilters() {
    const today = new Date().toISOString().split('T')[0];
    
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const employeeFilter = document.getElementById('employee-filter');
    
    if (startDateInput) startDateInput.value = today;
    if (endDateInput) endDateInput.value = today;
    if (employeeFilter) employeeFilter.value = '';
    
    // Reload page without filters
    window.location.href = window.location.pathname;
}

function viewEmployeeHistory(employeeId) {
    const modal = new bootstrap.Modal(document.getElementById('employeeHistoryModal'));
    modal.show();
    
    // Load employee history
    loadEmployeeHistory(employeeId);
}

function loadEmployeeHistory(employeeId) {
    const contentDiv = document.getElementById('employee-history-content');
    contentDiv.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    fetch(`/api/attendance?employee_id=${employeeId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                contentDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            } else {
                displayEmployeeHistory(data);
            }
        })
        .catch(error => {
            console.error('Error loading employee history:', error);
            contentDiv.innerHTML = '<div class="alert alert-danger">Failed to load employee history</div>';
        });
}

function displayEmployeeHistory(attendanceData) {
    const contentDiv = document.getElementById('employee-history-content');
    
    if (attendanceData.length === 0) {
        contentDiv.innerHTML = '<div class="text-center text-muted">No attendance records found</div>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-striped"><thead><tr><th>Date</th><th>Time</th><th>Status</th></tr></thead><tbody>';
    
    attendanceData.forEach(record => {
        const date = new Date(record.timestamp);
        const dateStr = date.toLocaleDateString();
        const timeStr = date.toLocaleTimeString();
        const isLate = date.getHours() > 9 || (date.getHours() === 9 && date.getMinutes() > 0);
        const status = isLate ? 'Late' : 'On Time';
        const statusClass = isLate ? 'text-warning' : 'text-success';
        
        html += `
            <tr>
                <td>${dateStr}</td>
                <td>${timeStr}</td>
                <td><span class="${statusClass}">${status}</span></td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    contentDiv.innerHTML = html;
}

function viewAttendanceImage(imagePath) {
    const modal = new bootstrap.Modal(document.getElementById('attendanceImageModal'));
    const img = document.getElementById('attendance-image');
    
    if (img) {
        img.src = imagePath;
        img.onerror = function() {
            img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDIwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0xMDAgMTAwTDEwMCAxMDAiIHN0cm9rZT0iIzk5OTk5OSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPHRleHQgeD0iMTAwIiB5PSIxMTAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiM5OTk5OTkiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxMiI+SW1hZ2UgTm90IEZvdW5kPC90ZXh0Pgo8L3N2Zz4K';
        };
    }
    
    modal.show();
}

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Handle page visibility change
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopStatusChecking();
    } else {
        startStatusChecking();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    stopStatusChecking();
});
