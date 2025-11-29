// Foundamental LLM SEO - Frontend JavaScript

// =====================
// Utility Functions
// =====================

function formatDate(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// =====================
// Table Sorting
// =====================

function initSortableTables() {
    document.querySelectorAll('.data-table.sortable th[data-sort]').forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', () => {
            const table = th.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const column = th.dataset.sort;
            const colIndex = Array.from(th.parentNode.children).indexOf(th);
            
            // Toggle sort direction
            const currentDir = th.dataset.sortDir || 'asc';
            const newDir = currentDir === 'asc' ? 'desc' : 'asc';
            
            // Reset all headers
            table.querySelectorAll('th').forEach(h => {
                h.dataset.sortDir = '';
                h.classList.remove('sort-asc', 'sort-desc');
            });
            
            th.dataset.sortDir = newDir;
            th.classList.add(`sort-${newDir}`);
            
            // Sort rows
            rows.sort((a, b) => {
                const aVal = a.children[colIndex]?.textContent.trim() || '';
                const bVal = b.children[colIndex]?.textContent.trim() || '';
                
                // Try numeric comparison
                const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
                const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return newDir === 'asc' ? aNum - bNum : bNum - aNum;
                }
                
                // String comparison
                return newDir === 'asc' 
                    ? aVal.localeCompare(bVal) 
                    : bVal.localeCompare(aVal);
            });
            
            // Reorder DOM
            rows.forEach(row => tbody.appendChild(row));
        });
    });
}

// =====================
// API Helpers
// =====================

async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`/api${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        return null;
    }
}

// =====================
// Notifications
// =====================

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">×</button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// =====================
// Chart Helpers
// =====================

const chartColors = {
    blue: 'rgba(59, 130, 246, 0.8)',
    purple: 'rgba(139, 92, 246, 0.8)',
    green: 'rgba(34, 197, 94, 0.8)',
    yellow: 'rgba(234, 179, 8, 0.8)',
    red: 'rgba(239, 68, 68, 0.8)',
    pink: 'rgba(236, 72, 153, 0.8)',
    gray: 'rgba(107, 114, 128, 0.8)'
};

const chartColorArray = Object.values(chartColors);

function getChartDefaults() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: '#94a3b8',
                    font: {
                        family: 'Inter, sans-serif'
                    }
                }
            }
        },
        scales: {
            x: {
                ticks: { color: '#94a3b8' },
                grid: { color: 'rgba(51, 65, 85, 0.5)' }
            },
            y: {
                ticks: { color: '#94a3b8' },
                grid: { color: 'rgba(51, 65, 85, 0.5)' }
            }
        }
    };
}

// =====================
// Keyboard Shortcuts
// =====================

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.search-input');
        if (searchInput) searchInput.focus();
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.open').forEach(modal => {
            modal.classList.remove('open');
        });
    }
});

// =====================
// Initialize
// =====================

document.addEventListener('DOMContentLoaded', () => {
    initSortableTables();
    
    // Add smooth scroll behavior
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href'))?.scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
    
    console.log('🔍 Foundamental LLM SEO UI initialized');
});
