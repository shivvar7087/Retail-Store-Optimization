
// Global Instant Navigation Listener for All KPI Cards & Buttons
document.addEventListener('click', function(e) {
    const el = e.target.closest('.kpi-card, [data-kpi], .btn-subpage, .nav-subpage-btn');
    if (el) {
        const kpi = el.getAttribute('data-kpi');
        const kpiMap = {
            'health': 'health.html',
            'critical': 'critical.html',
            'reorder': 'reorders.html',
            'budget': 'budget.html',
            'revenue': 'revenue.html'
        };
        const target = (kpi && kpiMap[kpi]) ? kpiMap[kpi] : el.getAttribute('href');
        if (target) {
            window.location.href = target;
        }
    }
});

const isLocalHttp = window.location.protocol.startsWith('http')
    && ['localhost', '127.0.0.1'].includes(window.location.hostname);
const API_BASE = isLocalHttp ? 'http://127.0.0.1:8000'
    : (window.location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:8000');

let storeProducts = [];
let optimizationResults = [];
let currentSortField = 'current_stock';
let currentSortAsc = true;
let demandChartInstance = null;
let healthChartInstance = null;
let pricingChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initEventListeners();
    checkApiConnection();
    loadCatalogAndOptimize();
    loadMarketBasket();
});

function initTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const targetId = tab.getAttribute('data-tab');
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) {
                targetPanel.classList.add('active');
            }

            if (targetId === 'catalog-tab' && demandChartInstance) {
                demandChartInstance.resize();
            }
            if (targetId === 'pricing-tab' && pricingChartInstance) {
                pricingChartInstance.resize();
            }
        });
    });
}

async function checkApiConnection() {
    const statusEl = document.getElementById('api-status');
    const textEl = document.getElementById('api-status-text');
    try {
        const res = await fetch(`${API_BASE}/api/store-kpis`);
        if (res.ok) {
            statusEl.className = 'api-status online';
            textEl.textContent = 'ML Backend Connected';
            const kpiData = await res.json();
            updateKpiCards(kpiData);
        } else {
            throw new Error('Non-200 status');
        }
    } catch (e) {
        statusEl.className = 'api-status offline';
        textEl.textContent = 'ML Backend Offline (Start FastAPI)';
    }
}

function updateKpiCards(kpi) {
    document.getElementById('kpi-health-score').textContent = `${kpi.health_score_pct}%`;
    document.getElementById('kpi-replenish-cost').textContent = `$${kpi.total_replenishment_budget.toLocaleString()}`;
    document.getElementById('kpi-revenue-protected').textContent = `$${kpi.potential_lost_sales_prevented.toLocaleString()}`;
}

async function loadCatalogAndOptimize() {
    const tbody = document.getElementById('catalog-tbody');
    try {
        const res = await fetch(`${API_BASE}/api/optimize-all`, { method: 'POST' });
        const data = await res.json();
        
        if (data.status === 'success') {
            optimizationResults = data.items;
            
            document.getElementById('kpi-critical-count').textContent = data.summary.critical_stockouts;
            document.getElementById('kpi-reorder-count').textContent = data.summary.reorders_needed;
            
            renderCatalogTable(optimizationResults);
            renderDemandChart(optimizationResults);
            renderHealthDonutChart(data.summary);
            populatePricingDropdown(optimizationResults);
        }
    } catch (err) {
        console.error('Failed to load store optimization data:', err);
        tbody.innerHTML = `<tr><td colspan="10" class="loading-cell text-red">⚠️ Unable to fetch from ML backend at ${API_BASE}. Make sure the FastAPI server is running.</td></tr>`;
    }
}

function renderCatalogTable(items) {
    const tbody = document.getElementById('catalog-tbody');
    const searchVal = document.getElementById('catalog-search').value.toLowerCase().trim();
    const catVal = document.getElementById('filter-category').value;
    const statusVal = document.getElementById('filter-status').value;

    const filtered = items.filter(item => {
        const matchesSearch = item.name.toLowerCase().includes(searchVal) || item.product_id.toLowerCase().includes(searchVal);
        const matchesCat = (catVal === 'ALL') || (item.category === catVal);
        const matchesStatus = (statusVal === 'ALL') || (item.status === statusVal);
        return matchesSearch && matchesCat && matchesStatus;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" class="loading-cell">No products match your filter criteria.</td></tr>`;
        return;
    }

    // Sort items by currentSortField in Increasing or Decreasing order
    filtered.sort((a, b) => {
        let valA = a[currentSortField];
        let valB = b[currentSortField];

        if (currentSortField === 'price') {
            valA = Number(a.price || 0);
            valB = Number(b.price || 0);
        } else if (currentSortField === 'current_stock') {
            valA = Number(a.current_stock ?? 0);
            valB = Number(b.current_stock ?? 0);
        } else if (currentSortField === 'predicted_weekly_demand') {
            valA = Number(a.predicted_weekly_demand || 0);
            valB = Number(b.predicted_weekly_demand || 0);
        } else if (currentSortField === 'reorder_point') {
            valA = Number(a.reorder_point || 0);
            valB = Number(b.reorder_point || 0);
        } else if (currentSortField === 'recommended_reorder') {
            valA = Number(a.recommended_reorder || 0);
            valB = Number(b.recommended_reorder || 0);
        } else if (currentSortField === 'stockout_probability_pct') {
            valA = Number(a.stockout_probability_pct || 0);
            valB = Number(b.stockout_probability_pct || 0);
        }

        if (typeof valA === 'number' && typeof valB === 'number') {
            return currentSortAsc ? valA - valB : valB - valA;
        }

        valA = (valA || '').toString().toLowerCase();
        valB = (valB || '').toString().toLowerCase();
        return currentSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    });

    updateSortUI();

    tbody.innerHTML = filtered.map(item => {
        let badgeClass = 'badge-optimal';
        if (item.status === 'CRITICAL_STOCKOUT') badgeClass = 'badge-critical';
        else if (item.status === 'REORDER_NEEDED') badgeClass = 'badge-reorder';
        else if (item.status === 'OVERSTOCKED') badgeClass = 'badge-overstocked';

        return `
            <tr>
                <td>
                    <strong>${item.name}</strong><br>
                    <small style="color:var(--text-muted); font-family:monospace;">${item.product_id}</small>
                </td>
                <td><span style="font-size:0.8rem; background:#f1f5f9; padding:2px 6px; border-radius:4px;">${item.category || 'Store SKU'}</span></td>
                <td><strong>${item.current_stock ?? '--'}</strong> <small style="color:var(--text-muted);">(${item.days_of_supply}d supply)</small></td>
                <td>$${Number(item.price || 0).toFixed(2)}</td>
                <td><strong class="text-blue">${item.predicted_weekly_demand}</strong> <small>units/wk</small></td>
                <td>${item.reorder_point} <small>(SS: ${item.safety_stock})</small></td>
                <td>
                    ${item.recommended_reorder > 0 
                        ? `<strong class="text-amber">+${item.recommended_reorder}</strong> <small>($${item.estimated_reorder_cost})</small>`
                        : `<span style="color:var(--text-muted);">0</span>`}
                </td>
                <td>
                    <span style="font-weight:700; color:${item.stockout_probability_pct > 50 ? 'var(--danger)' : (item.stockout_probability_pct > 20 ? 'var(--warning)' : 'var(--success)')};">
                        ${item.stockout_probability_pct}%
                    </span>
                </td>
                <td>
                    <span class="status-badge ${badgeClass}">${item.status_label}</span>
                </td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="showProductDetails('${item.product_id}')">
                        Inspect AI Plan
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function renderDemandChart(items) {
    const ctx = document.getElementById('inventoryDemandChart');
    if (!ctx) return;

    const sample = items.slice(0, 8);
    const labels = sample.map(i => i.name.length > 18 ? i.name.substring(0, 18) + '...' : i.name);
    const stockData = sample.map(i => i.current_stock || 20);
    const demandData = sample.map(i => i.predicted_weekly_demand);
    const ropData = sample.map(i => i.reorder_point);

    if (demandChartInstance) {
        demandChartInstance.destroy();
    }

    demandChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Current On-Hand Stock',
                    data: stockData,
                    backgroundColor: 'rgba(79, 70, 229, 0.75)',
                    borderColor: '#4f46e5',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'ML Predicted Weekly Demand',
                    data: demandData,
                    backgroundColor: 'rgba(14, 165, 233, 0.75)',
                    borderColor: '#0ea5e9',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    type: 'line',
                    label: 'Reorder Point (ROP)',
                    data: ropData,
                    borderColor: '#f59e0b',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointBackgroundColor: '#f59e0b',
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: { mode: 'index', intersect: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Units' }
                },
                x: {
                    ticks: { maxRotation: 25, minRotation: 20 }
                }
            }
        }
    });
}

function renderHealthDonutChart(summary) {
    const ctx = document.getElementById('healthDonutChart');
    if (!ctx) return;

    if (healthChartInstance) {
        healthChartInstance.destroy();
    }

    healthChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Critical Stockout', 'Reorder Needed', 'Optimal', 'Overstocked'],
            datasets: [{
                data: [
                    summary.critical_stockouts,
                    summary.reorders_needed,
                    summary.optimal_stock,
                    summary.overstocked
                ],
                backgroundColor: [
                    '#ef4444',
                    '#f59e0b',
                    '#10b981',
                    '#8b5cf6'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            },
            cutout: '68%'
        }
    });
}


function updateSortUI() {
    const sel = document.getElementById('sort-field');
    if (sel && sel.value !== currentSortField) {
        sel.value = currentSortField;
    }

    const orderIcon = document.getElementById('sort-order-icon');
    const orderText = document.getElementById('sort-order-text');
    if (orderIcon) orderIcon.textContent = currentSortAsc ? '▲' : '▼';
    if (orderText) orderText.textContent = currentSortAsc ? 'Increasing Order' : 'Decreasing Order';

    document.querySelectorAll('.sortable-th').forEach(th => {
        const field = th.getAttribute('data-sort');
        const iconSpan = th.querySelector('.sort-indicator');
        if (field === currentSortField) {
            th.classList.add('active-sort');
            if (iconSpan) iconSpan.textContent = currentSortAsc ? '▲' : '▼';
        } else {
            th.classList.remove('active-sort');
            if (iconSpan) iconSpan.textContent = '↕';
        }
    });
}

function initEventListeners() {
    document.getElementById('catalog-search')?.addEventListener('input', () => renderCatalogTable(optimizationResults));
    document.getElementById('filter-category')?.addEventListener('change', () => renderCatalogTable(optimizationResults));
    document.getElementById('filter-status')?.addEventListener('change', () => renderCatalogTable(optimizationResults));

    // Sort order toggle button (Increasing / Decreasing)
    document.getElementById('btn-sort-order')?.addEventListener('click', () => {
        currentSortAsc = !currentSortAsc;
        updateSortUI();
        renderCatalogTable(optimizationResults);
    });

    // Sort column dropdown
    document.getElementById('sort-field')?.addEventListener('change', (e) => {
        currentSortField = e.target.value;
        updateSortUI();
        renderCatalogTable(optimizationResults);
    });

    // Clickable table column headers
    document.querySelectorAll('.sortable-th').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.getAttribute('data-sort');
            if (currentSortField === field) {
                currentSortAsc = !currentSortAsc;
            } else {
                currentSortField = field;
                currentSortAsc = true;
            }
            updateSortUI();
            renderCatalogTable(optimizationResults);
        });
    });

    document.getElementById('btn-batch-optimize')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-batch-optimize');
        btn.disabled = true;
        btn.innerHTML = `<span class="btn-icon">⏳</span> Optimizing...`;
        await loadCatalogAndOptimize();
        await checkApiConnection();
        btn.disabled = false;
        btn.innerHTML = `<span class="btn-icon">⚡</span> Run Store Optimization`;
    });

    document.getElementById('calculator-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        await runSingleOptimization();
    });

    document.getElementById('btn-calc-sample')?.addEventListener('click', () => {
        document.getElementById('calc-product-name').value = 'Hydrating Facial Cleanser 200ml';
        document.getElementById('calc-category').value = 'Personal Care';
        document.getElementById('calc-current-stock').value = 14;
        document.getElementById('calc-last-week-sales').value = 62;
        document.getElementById('calc-price').value = 16.99;
        document.getElementById('calc-cost').value = 6.50;
        document.getElementById('calc-discount').value = 10;
        document.getElementById('calc-lead-time').value = 4;
        document.getElementById('calc-comp-price').value = 17.50;
        document.getElementById('calc-footfall').value = '1.2';
    });

    document.getElementById('btn-run-price-sim')?.addEventListener('click', runPriceSimulation);
    document.getElementById('price-select-product')?.addEventListener('change', onPricingProductChange);

    document.getElementById('modal-close')?.addEventListener('click', () => {
        document.getElementById('product-modal').classList.remove('open');
    });
}

async function runSingleOptimization() {
    const payload = {
        product_id: 'CUSTOM-SIM',
        name: document.getElementById('calc-product-name').value,
        current_stock: parseInt(document.getElementById('calc-current-stock').value),
        last_week_sales: parseInt(document.getElementById('calc-last-week-sales').value),
        price: parseFloat(document.getElementById('calc-price').value),
        cost: parseFloat(document.getElementById('calc-cost').value),
        discount_pct: parseFloat(document.getElementById('calc-discount').value),
        lead_time_days: parseInt(document.getElementById('calc-lead-time').value),
        competitor_price: parseFloat(document.getElementById('calc-comp-price').value),
        footfall_factor: parseFloat(document.getElementById('calc-footfall').value)
    };

    try {
        const res = await fetch(`${API_BASE}/api/optimize-single`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        displaySingleResult(data);
    } catch (err) {
        alert('Optimization request failed: ' + err.message);
    }
}

function displaySingleResult(data) {
    document.getElementById('res-weekly-demand').textContent = data.predicted_weekly_demand;
    document.getElementById('res-daily-demand').textContent = `${data.predicted_daily_demand} units / day`;
    document.getElementById('res-reorder-qty').textContent = data.recommended_reorder > 0 ? `+${data.recommended_reorder}` : '0';
    document.getElementById('res-reorder-cost').textContent = `Est. Cost: $${data.estimated_reorder_cost}`;
    document.getElementById('res-rop').textContent = data.reorder_point;
    document.getElementById('res-safety-stock').textContent = `Safety Buffer: ${data.safety_stock} units`;
    document.getElementById('res-stockout-risk').textContent = `${data.stockout_probability_pct}%`;
    document.getElementById('res-days-supply').textContent = `Supply: ${data.days_of_supply} days`;

    const badge = document.getElementById('calc-badge');
    badge.textContent = data.status_label;
    badge.className = 'status-badge';
    if (data.status === 'CRITICAL_STOCKOUT') badge.classList.add('badge-critical');
    else if (data.status === 'REORDER_NEEDED') badge.classList.add('badge-reorder');
    else if (data.status === 'OVERSTOCKED') badge.classList.add('badge-overstocked');
    else badge.classList.add('badge-optimal');

    document.getElementById('res-action-text').textContent = data.action_notes;
    document.getElementById('res-pricing-text').textContent = data.pricing_recommendation;
}

function populatePricingDropdown(items) {
    const sel = document.getElementById('price-select-product');
    if (!sel) return;
    sel.innerHTML = items.map(i => `<option value="${i.product_id}">${i.name} ($${Number(i.price).toFixed(2)})</option>`).join('');
    onPricingProductChange();
}

function onPricingProductChange() {
    const sel = document.getElementById('price-select-product');
    const selectedId = sel.value;
    const item = optimizationResults.find(i => i.product_id === selectedId);
    if (item) {
        document.getElementById('sim-base-price').value = item.price || 15.00;
        document.getElementById('sim-cost').value = item.cost || (item.price * 0.55).toFixed(2);
        document.getElementById('sim-base-demand').value = item.predicted_weekly_demand || 50;
        runPriceSimulation();
    }
}

async function runPriceSimulation() {
    const payload = {
        current_price: parseFloat(document.getElementById('sim-base-price').value),
        cost: parseFloat(document.getElementById('sim-cost').value),
        base_demand: parseFloat(document.getElementById('sim-base-demand').value)
    };

    try {
        const res = await fetch(`${API_BASE}/api/simulate-price`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        document.getElementById('opt-price-val').textContent = `$${Number(data.optimal_profit_price).toFixed(2)}`;
        document.getElementById('opt-profit-gain').textContent = `Max Estimated Weekly Profit: $${Number(data.max_estimated_profit).toLocaleString()}`;

        renderPricingChart(data.curve, data.current_price, data.optimal_profit_price);
    } catch (err) {
        console.error('Pricing simulation error:', err);
    }
}

function renderPricingChart(curve, currentPrice, optPrice) {
    const ctx = document.getElementById('priceElasticityChart');
    if (!ctx) return;

    const labels = curve.map(p => `$${p.price}`);
    const revenues = curve.map(p => p.simulated_revenue);
    const profits = curve.map(p => p.simulated_profit);

    if (pricingChartInstance) {
        pricingChartInstance.destroy();
    }

    pricingChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Simulated Revenue ($)',
                    data: revenues,
                    borderColor: '#0ea5e9',
                    backgroundColor: 'rgba(14, 165, 233, 0.1)',
                    tension: 0.3,
                    fill: false
                },
                {
                    label: 'Simulated Gross Profit ($)',
                    data: profits,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    tension: 0.3,
                    fill: true,
                    borderWidth: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: { mode: 'index', intersect: false }
            },
            scales: {
                y: {
                    title: { display: true, text: 'USD ($)' },
                    beginAtZero: true
                },
                x: {
                    title: { display: true, text: 'Price Point' }
                }
            }
        }
    });
}

async function loadMarketBasket() {
    const container = document.getElementById('bundles-container');
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE}/api/market-basket`);
        const data = await res.json();
        
        container.innerHTML = data.bundles.map(b => `
            <div class="bundle-card">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <h4 class="bundle-title">${b.name}</h4>
                        <span class="status-badge badge-optimal">${b.discount_suggestion}</span>
                    </div>
                    <ul class="bundle-items">
                        ${b.items.map(item => `<li>🔹 ${item}</li>`).join('')}
                    </ul>
                </div>
                <div class="bundle-metrics">
                    <span><strong>Lift:</strong> ${b.lift}x</span>
                    <span><strong>Confidence:</strong> ${(b.confidence * 100).toFixed(0)}%</span>
                    <span><strong>Synergy:</strong> <span style="color:var(--primary); font-weight:700;">${b.synergy_score}</span></span>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Error fetching market basket:', e);
    }
}

window.showProductDetails = function(productId) {
    const item = optimizationResults.find(i => i.product_id === productId);
    if (!item) return;

    const modal = document.getElementById('product-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');

    modalTitle.textContent = `${item.name} (${item.product_id})`;
    modalBody.innerHTML = `
        <div style="margin-bottom:1rem;">
            <span class="status-badge" style="background:${item.urgency_color}22; color:${item.urgency_color}; font-size:0.85rem; padding:4px 10px;">
                ${item.status_label}
            </span>
        </div>
        <p style="margin-bottom:1rem; font-size:0.95rem; color:var(--text-secondary);">
            ${item.action_notes}
        </p>

        <div class="metrics-summary-grid" style="margin-bottom:1rem;">
            <div class="metric-box">
                <span class="metric-label">Current On-Hand</span>
                <span class="metric-num">${item.current_stock}</span>
                <span class="metric-detail">${item.days_of_supply} days of supply</span>
            </div>
            <div class="metric-box">
                <span class="metric-label">ML Predicted Demand</span>
                <span class="metric-num text-blue">${item.predicted_weekly_demand}</span>
                <span class="metric-detail">${item.predicted_daily_demand} units / day</span>
            </div>
            <div class="metric-box">
                <span class="metric-label">Reorder Point (ROP)</span>
                <span class="metric-num">${item.reorder_point}</span>
                <span class="metric-detail">Safety Buffer: ${item.safety_stock} units</span>
            </div>
            <div class="metric-box">
                <span class="metric-label">Recommended Order</span>
                <span class="metric-num text-amber">+${item.recommended_reorder}</span>
                <span class="metric-detail">PO Cost: $${item.estimated_reorder_cost}</span>
            </div>
        </div>

        <div style="background:#f8fafc; padding:0.9rem; border-radius:8px; border:1px solid var(--border);">
            <strong>Dynamic Pricing Insight:</strong>
            <p style="font-size:0.88rem; color:var(--text-secondary); margin-top:0.25rem;">
                ${item.pricing_recommendation}
            </p>
        </div>
    `;

    modal.classList.add('open');
};
