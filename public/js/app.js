/**
 * NegotiAgent AI - Frontend Application Controller
 * Handles SPA navigation, API requests, dynamic supplier registration,
 * autonomous auctions, replay, approvals, and PO printing.
 */

let currentLang = localStorage.getItem('negotiagent_lang') || 'en';
let cachedRfqs = [];
let cachedSuppliers = [];
let cachedOrders = [];
let currentReplayData = null;
let currentReplayRound = 1;
let activeModalRfqId = null;

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
  initTranslations();
  setupNavigation();
  setupRfqForm();
  setupSupplierModal();
  setupReplayControls();
  setupNotificationDrawer();

  // Load baseline data
  loadDashboardData();
  loadSuppliers();
  loadOrders();
  loadReports();
});

// --- TRANSLATIONS & LOCALIZATION ---
function initTranslations() {
  const selector = document.getElementById('languageSelector');
  if (selector) {
    selector.value = currentLang;
    selector.addEventListener('change', (e) => {
      currentLang = e.target.value;
      localStorage.setItem('negotiagent_lang', currentLang);
      applyTranslations();
      renderSuppliersGrid();
      renderRfqTable();
    });
  }
  applyTranslations();
}

function t(key, defaultVal = '') {
  if (window.translations && window.translations[currentLang] && window.translations[currentLang][key]) {
    return window.translations[currentLang][key];
  }
  if (window.translations && window.translations['en'] && window.translations['en'][key]) {
    return window.translations['en'][key];
  }
  return defaultVal || key;
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const translated = t(key);
    if (translated) {
      if (el.tagName === 'INPUT' && (el.type === 'button' || el.type === 'submit')) {
        el.value = translated;
      } else {
        el.textContent = translated;
      }
    }
  });
}

// --- SPA VIEW NAVIGATION ---
function setupNavigation() {
  const navLinks = {
    navLinkDashboard: 'viewDashboard',
    navLinkNewRfq: 'viewNewRfq',
    navLinkSuppliers: 'viewSuppliers',
    navLinkReplay: 'viewReplay',
    navLinkApprovals: 'viewApprovals',
    navLinkReports: 'viewReports'
  };

  Object.entries(navLinks).forEach(([linkId, viewId]) => {
    const link = document.getElementById(linkId);
    if (link) {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(viewId, link);
      });
    }
  });

  const btnOpenRfq = document.getElementById('btnOpenRfq');
  if (btnOpenRfq) {
    btnOpenRfq.addEventListener('click', () => {
      const newRfqLink = document.getElementById('navLinkNewRfq');
      switchView('viewNewRfq', newRfqLink);
    });
  }
}

function switchView(viewId, activeLinkEl) {
  document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(l => l.classList.remove('active'));

  const targetView = document.getElementById(viewId);
  if (targetView) targetView.classList.add('active');
  if (activeLinkEl) activeLinkEl.classList.add('active');

  // Trigger contextual data refresh
  if (viewId === 'viewDashboard') loadDashboardData();
  if (viewId === 'viewSuppliers') loadSuppliers();
  if (viewId === 'viewApprovals') loadOrders();
  if (viewId === 'viewReports') loadReports();
}

// --- DASHBOARD & RFQS ---
async function loadDashboardData() {
  try {
    const [rfqRes, reportRes] = await Promise.all([
      fetch('/api/rfqs'),
      fetch('/api/reports/summary')
    ]);

    if (rfqRes.ok) {
      cachedRfqs = await rfqRes.json();
      renderRfqTable();
      populateReplayDropdown();
    }

    if (reportRes.ok) {
      const report = await reportRes.json();
      document.getElementById('metricSavings').textContent = `₹${report.total_savings.toLocaleString('en-IN')}`;
      document.getElementById('metricCompleted').textContent = report.total_orders;
      document.getElementById('metricPending').textContent = (report.total_orders - report.paid_orders);
      document.getElementById('metricActive').textContent = cachedRfqs.filter(r => r.status.includes('Evaluating') || r.status.includes('Active')).length;
    }
  } catch (err) {
    console.error('Failed to load dashboard metrics:', err);
  }
}

function renderRfqTable() {
  const tbody = document.getElementById('rfqTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (cachedRfqs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:1.5rem; color:var(--text-muted);">No RFQs created yet. Click "+ Create New RFQ" to begin.</td></tr>`;
    return;
  }

  cachedRfqs.forEach(rfq => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <strong>${rfq.id}</strong><br>
        <span style="font-size:0.85rem; color:var(--text-muted);">${rfq.category} (${rfq.size})</span>
      </td>
      <td>${rfq.source_hub || 'Mudhal Titta Depot'}</td>
      <td>₹${rfq.budget_ceiling.toLocaleString('en-IN')} (${rfq.quantity} units)</td>
      <td><span class="status-badge ${getStatusBadgeClass(rfq.status)}">${rfq.status}</span></td>
      <td>
        <button class="btn-secondary btn-sm" onclick="triggerNegotiation('${rfq.id}')">Inspect & Run</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function getStatusBadgeClass(status) {
  if (status.includes('Approved') || status.includes('Completed') || status.includes('Awarded')) return 'badge-success';
  if (status.includes('Evaluating') || status.includes('Negotiating')) return 'badge-warning';
  return 'badge-info';
}

// --- RFQ CREATION & WEIGHT VALIDATION ---
function setupRfqForm() {
  const form = document.getElementById('rfqForm');
  const alertBox = document.getElementById('rfqAlert');
  const weightTotalTag = document.getElementById('weightTotalTag');
  const weightInputs = document.querySelectorAll('.weight-input');

  const updateWeightSum = () => {
    let sum = 0;
    weightInputs.forEach(input => sum += parseFloat(input.value) || 0);
    weightTotalTag.textContent = `${sum}%`;
    if (sum === 100) {
      weightTotalTag.className = 'total-weight-tag valid';
      return true;
    } else {
      weightTotalTag.className = 'total-weight-tag invalid';
      return false;
    }
  };

  weightInputs.forEach(input => input.addEventListener('input', updateWeightSum));

  const btnCancelRfq = document.getElementById('btnCancelRfq');
  if (btnCancelRfq) {
    btnCancelRfq.addEventListener('click', () => {
      form.reset();
      updateWeightSum();
      switchView('viewDashboard', document.getElementById('navLinkDashboard'));
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      alertBox.style.display = 'none';

      if (!updateWeightSum()) {
        alertBox.className = 'alert-box error';
        alertBox.textContent = 'Buyer priority weights must sum to exactly 100% before publishing.';
        alertBox.style.display = 'block';
        return;
      }

      const payload = {
        category: document.getElementById('tileCategory').value,
        size: document.getElementById('tileSize').value,
        quantity: parseInt(document.getElementById('boxQuantity').value, 10),
        budget_ceiling: parseFloat(document.getElementById('budgetCeiling').value),
        delivery_deadline: document.getElementById('deliveryDeadline').value || '2026-12-15',
        quality_grade: document.getElementById('qualityGrade').value,
        max_breakage: parseFloat(document.getElementById('maxBreakage').value),
        weights: {
          price: parseFloat(document.getElementById('weightPrice').value),
          quality: parseFloat(document.getElementById('weightQuality').value),
          delivery: parseFloat(document.getElementById('weightDelivery').value),
          warranty: parseFloat(document.getElementById('weightWarranty').value)
        }
      };

      try {
        const res = await fetch('/api/rfqs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Failed to create RFQ');
        }

        const created = await res.json();
        alertBox.className = 'alert-box success';
        alertBox.textContent = `RFQ ${created.id} created successfully! Initializing negotiation auction...`;
        alertBox.style.display = 'block';

        setTimeout(() => {
          form.reset();
          updateWeightSum();
          alertBox.style.display = 'none';
          switchView('viewDashboard', document.getElementById('navLinkDashboard'));
          triggerNegotiation(created.id);
        }, 1200);

      } catch (err) {
        alertBox.className = 'alert-box error';
        alertBox.textContent = err.message;
        alertBox.style.display = 'block';
      }
    });
  }
}

// --- DYNAMIC SUPPLIER REGISTRATION (MODAL) ---
function setupSupplierModal() {
  const modal = document.getElementById('addSupplierModal');
  const btnOpen = document.getElementById('btnOpenAddSupplierModal');
  const btnClose = document.getElementById('btnCloseSupplierModal');
  const btnCancel = document.getElementById('btnCancelSupplierModal');
  const form = document.getElementById('addSupplierForm');
  const alertBox = document.getElementById('supplierFormAlert');

  if (btnOpen) {
    btnOpen.addEventListener('click', () => {
      alertBox.style.display = 'none';
      form.reset();
      document.getElementById('newSupId').value = `SUP-DEPOT-${Math.floor(100 + Math.random() * 900)}`;
      modal.style.display = 'flex';
    });
  }

  const hideModal = () => { if (modal) modal.style.display = 'none'; };
  if (btnClose) btnClose.addEventListener('click', hideModal);
  if (btnCancel) btnCancel.addEventListener('click', hideModal);

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      alertBox.style.display = 'none';

      const basePrice = parseFloat(document.getElementById('newSupBasePrice').value);
      const walkaway = parseFloat(document.getElementById('newSupWalkaway').value);
      const standardLead = parseInt(document.getElementById('newSupLead').value, 10);
      const minLead = parseInt(document.getElementById('newSupMinLead').value, 10);

      if (walkaway > basePrice) {
        alertBox.className = 'alert-box error';
        alertBox.textContent = 'Minimum walkaway price cannot be higher than opening price!';
        alertBox.style.display = 'block';
        return;
      }

      if (minLead > standardLead) {
        alertBox.className = 'alert-box error';
        alertBox.textContent = 'Expedited lead days cannot exceed standard lead days!';
        alertBox.style.display = 'block';
        return;
      }

      const payload = {
        id: document.getElementById('newSupId').value.trim(),
        name: document.getElementById('newSupName').value.trim(),
        hub_location: document.getElementById('newSupHub').value.trim(),
        agent_strategy: document.getElementById('newSupStrategy').value,
        base_price_per_box: basePrice,
        min_walkaway_price: walkaway,
        standard_lead_days: standardLead,
        min_lead_days: minLead,
        offered_breakage_pct: parseFloat(document.getElementById('newSupBreakage').value),
        quality_score: parseFloat(document.getElementById('newSupQuality').value),
        reliability_score: parseFloat(document.getElementById('newSupReliability').value)
      };

      try {
        const res = await fetch('/api/suppliers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Failed to save supplier agent');
        }

        hideModal();
        await loadSuppliers();
        triggerInAppNotification(`New Supplier Agent "${payload.name}" registered and active in SQLite!`);
      } catch (err) {
        alertBox.className = 'alert-box error';
        alertBox.textContent = err.message;
        alertBox.style.display = 'block';
      }
    });
  }
}

async function loadSuppliers() {
  try {
    const res = await fetch('/api/suppliers');
    if (res.ok) {
      cachedSuppliers = await res.json();
      renderSuppliersGrid();
    }
  } catch (err) {
    console.error('Failed to load suppliers:', err);
  }
}

function renderSuppliersGrid() {
  const container = document.getElementById('suppliersContainer');
  if (!container) return;
  container.innerHTML = '';

  cachedSuppliers.forEach(s => {
    const card = document.createElement('article');
    card.className = 'supplier-card';
    card.innerHTML = `
      <div class="supplier-header">
        <div>
          <h3 style="font-size:1.05rem; font-weight:700; color:var(--primary-navy);">${t(s.id + '_name', s.name)}</h3>
          <div style="font-size:0.8rem; color:var(--text-muted);">${t(s.id + '_hub', s.hub_location)}</div>
        </div>
        <span class="badge-strategy ${s.agent_strategy}">${s.agent_strategy.toUpperCase()}</span>
      </div>
      <div class="supplier-stats-grid">
        <div class="stat-item">
          <div class="stat-label">Opening Quote</div>
          <div class="stat-val">₹${s.base_price_per_box}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Walkaway Floor</div>
          <div class="stat-val">₹${s.min_walkaway_price}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Standard Lead</div>
          <div class="stat-val">${s.standard_lead_days} Days</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Breakage Tol.</div>
          <div class="stat-val">≤ ${s.offered_breakage_pct}%</div>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

// --- NEGOTIATION SIMULATION EXECUTION ---
window.triggerNegotiation = async function(rfqId) {
  activeModalRfqId = rfqId;
  const modal = document.getElementById('negotiationModal');
  const body = document.getElementById('modalBody');
  const title = document.getElementById('modalTitle');

  title.textContent = `Autonomous Multi-Round Negotiation (${rfqId})`;
  body.innerHTML = `
    <div style="text-align:center; padding: 2rem;">
      <div class="spinner" style="margin: 0 auto 1rem;"></div>
      <p>Simulating 3-round concession protocol across supplier personas...</p>
    </div>
  `;
  modal.style.display = 'flex';

  try {
    const res = await fetch(`/api/negotiations/start/${rfqId}`, { method: 'POST' });
    if (!res.ok) throw new Error('Simulation failed to run');
    const outcome = await res.json();

    currentReplayData = outcome;

    body.innerHTML = `
      <div style="margin-bottom: 1.25rem;">
        <span class="badge-success" style="font-size:0.85rem; padding:0.3rem 0.6rem;">AUCTION CONCLUDED</span>
        <h4 style="margin: 0.6rem 0 0.2rem; font-size:1.15rem; color:var(--primary-navy);">
          Award Recommendation: ${outcome.winning_supplier.name}
        </h4>
        <div style="font-size:0.85rem; color:var(--text-muted);">${outcome.winning_supplier.hub_location}</div>
      </div>

      <div class="metrics-grid" style="grid-template-columns: 1fr 1fr; margin-bottom:1.25rem;">
        <div class="metric-card" style="padding:0.75rem;">
          <div class="metric-header">Simulated Savings</div>
          <div class="metric-value highlight" style="font-size:1.4rem;">₹${outcome.savings_amount.toLocaleString('en-IN')}</div>
          <div class="metric-desc">Under initial quote</div>
        </div>
        <div class="metric-card" style="padding:0.75rem;">
          <div class="metric-header">Final Agreed Cost</div>
          <div class="metric-value" style="font-size:1.4rem;">₹${outcome.final_total_cost.toLocaleString('en-IN')}</div>
          <div class="metric-desc">Taxable Subtotal</div>
        </div>
      </div>

      <div style="background:#f8fafc; border-left:4px solid var(--accent-gold); padding:0.75rem 1rem; border-radius:4px; font-size:0.88rem; line-height:1.45;">
        <strong>Executive Trade-Off Rationale:</strong><br>
        ${outcome.explanation}
      </div>
    `;

    loadDashboardData();
    populateReplayDropdown();
    triggerInAppNotification(`Negotiation completed for ${rfqId}. Recommended: ${outcome.winning_supplier.name}`);

  } catch (err) {
    body.innerHTML = `<div class="alert-box error">${err.message}</div>`;
  }
};

// Modal Actions
const btnCloseModal = document.getElementById('btnCloseModal');
if (btnCloseModal) {
  btnCloseModal.addEventListener('click', () => {
    document.getElementById('negotiationModal').style.display = 'none';
  });
}

const btnModalViewReplay = document.getElementById('btnModalViewReplay');
if (btnModalViewReplay) {
  btnModalViewReplay.addEventListener('click', () => {
    document.getElementById('negotiationModal').style.display = 'none';
    const select = document.getElementById('selectReplayRfq');
    if (select && activeModalRfqId) select.value = activeModalRfqId;
    switchView('viewReplay', document.getElementById('navLinkReplay'));
    loadReplay(activeModalRfqId);
  });
}

const btnModalApprove = document.getElementById('btnModalApprove');
if (btnModalApprove) {
  btnModalApprove.addEventListener('click', async () => {
    if (!activeModalRfqId) return;
    try {
      const res = await fetch(`/api/orders/approve/${activeModalRfqId}`, { method: 'POST' });
      if (!res.ok) throw new Error('Approval sign-off failed');
      const order = await res.json();
      document.getElementById('negotiationModal').style.display = 'none';
      switchView('viewApprovals', document.getElementById('navLinkApprovals'));
      triggerInAppNotification(`Purchase Order ${order.po_id} authorized for sign-off!`);
    } catch (err) {
      alert(err.message);
    }
  });
}

// --- REPLAY & AUDIT TRAIL CONTROLS ---
function setupReplayControls() {
  const steps = [
    { btn: 'btnStepRound1', round: 1 },
    { btn: 'btnStepRound2', round: 2 },
    { btn: 'btnStepRound3', round: 3 }
  ];

  steps.forEach(s => {
    const b = document.getElementById(s.btn);
    if (b) {
      b.addEventListener('click', () => {
        steps.forEach(x => document.getElementById(x.btn).classList.remove('active'));
        b.classList.add('active');
        currentReplayRound = s.round;
        renderReplayRound();
      });
    }
  });

  const select = document.getElementById('selectReplayRfq');
  if (select) {
    select.addEventListener('change', (e) => {
      loadReplay(e.target.value);
    });
  }
}

function populateReplayDropdown() {
  const select = document.getElementById('selectReplayRfq');
  if (!select) return;
  select.innerHTML = '<option value="">-- Choose an RFQ to inspect --</option>';
  cachedRfqs.forEach(r => {
    const opt = document.createElement('option');
    opt.value = r.id;
    opt.textContent = `${r.id} - ${r.category}`;
    select.appendChild(opt);
  });
}

async function loadReplay(rfqId) {
  if (!rfqId) return;
  try {
    const res = await fetch(`/api/negotiations/${rfqId}`);
    if (res.ok) {
      currentReplayData = await res.json();
      renderReplayRound();
    }
  } catch (err) {
    console.error('Failed to load replay:', err);
  }
}

function renderReplayRound() {
  const tbody = document.getElementById('replayTableBody');
  const rationaleText = document.getElementById('replayRationaleText');
  if (!tbody || !currentReplayData) return;
  tbody.innerHTML = '';

  const roundRounds = currentReplayData.rounds.filter(r => r.round_number === currentReplayRound);
  if (roundRounds.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem;">No data for Round ${currentReplayRound}</td></tr>`;
    return;
  }

  roundRounds.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${r.supplier_name || r.supplier_id}</strong></td>
      <td>₹${r.supplier_quote}</td>
      <td>₹${r.buyer_counter || 'N/A'}</td>
      <td>${r.lead_days_offered} Days</td>
      <td>${r.breakage_offered}%</td>
      <td><strong>${r.composite_score.toFixed(1)}</strong></td>
      <td><span class="status-badge ${r.decision === 'ACCEPTED' ? 'badge-success' : 'badge-info'}">${r.decision}</span></td>
    `;
    tbody.appendChild(tr);
  });

  if (rationaleText) {
    const r = roundRounds[0];
    rationaleText.textContent = r ? r.rationale : 'Multi-criteria concession analysis evaluated against buyer priority weights.';
  }
}

// --- HUMAN APPROVALS & PURCHASE ORDERS ---
async function loadOrders() {
  try {
    const res = await fetch('/api/orders');
    if (res.ok) {
      cachedOrders = await res.json();
      renderOrdersTable();
    }
  } catch (err) {
    console.error('Failed to load orders:', err);
  }
}

function renderOrdersTable() {
  const tbody = document.getElementById('ordersTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (cachedOrders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:var(--text-muted);">No Purchase Orders generated yet. Run a negotiation to award a consignment.</td></tr>`;
    return;
  }

  cachedOrders.forEach(po => {
    const isPaid = po.payment_status === 'PAID';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${po.id}</strong><br><span style="font-size:0.8rem; color:var(--text-muted);">${po.supplier_name}</span></td>
      <td>${po.item_description} (${po.quantity} units)</td>
      <td>₹${po.subtotal_amount.toLocaleString('en-IN')}</td>
      <td>₹${po.gst_amount.toLocaleString('en-IN')} (18%)</td>
      <td><strong>₹${po.total_amount.toLocaleString('en-IN')}</strong></td>
      <td>
        <span class="status-badge ${isPaid ? 'badge-success' : 'badge-warning'}">${po.payment_status}</span>
        ${!isPaid ? `<button class="btn-sm btn-primary" style="margin-left:0.4rem;" onclick="simulatePayment('${po.id}')">Pay OK</button>` : ''}
      </td>
      <td>
        <button class="btn-secondary btn-sm" onclick="openInvoiceModal('${po.id}')">Print Invoice / PO</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.simulatePayment = async function(poId) {
  try {
    const res = await fetch(`/api/orders/pay/${poId}?action=success`, { method: 'POST' });
    if (!res.ok) throw new Error('Payment simulation failed');
    triggerInAppNotification(`Payment simulated successfully for ${poId}! Status updated to PAID.`);
    loadOrders();
    loadDashboardData();
  } catch (err) {
    alert(err.message);
  }
};

window.openInvoiceModal = function(poId) {
  const po = cachedOrders.find(o => o.id === poId);
  if (!po) return;

  const area = document.getElementById('invoicePrintArea');
  const cgst = (po.gst_amount / 2).toFixed(2);
  const sgst = (po.gst_amount / 2).toFixed(2);

  area.innerHTML = `
    <div style="border-bottom: 2px solid var(--primary-navy); padding-bottom: 0.75rem; margin-bottom: 1rem; display:flex; justify-content:space-between;">
      <div>
        <h2 style="color:var(--primary-navy); margin:0 0 0.25rem;">Shree Mahalaxmi Marbel and Granite</h2>
        <div style="font-size:0.85rem; color:#475569;">Mudhal Titta, Aadamapur Road, Kolhapur, Maharashtra</div>
        <div style="font-size:0.85rem; color:#475569;">Proprietor: Mr. Vikram Gurav | GSTIN: 27AAGFG1234F1Z8</div>
      </div>
      <div style="text-align:right;">
        <h3 style="margin:0 0 0.25rem; color:#b45309;">GST PURCHASE ORDER</h3>
        <div style="font-size:0.9rem; font-weight:700;">PO #: ${po.id}</div>
        <div style="font-size:0.85rem; color:#64748b;">Date: ${new Date().toLocaleDateString('en-IN')}</div>
      </div>
    </div>

    <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1.5rem; font-size:0.9rem;">
      <div style="background:#f8fafc; padding:0.75rem; border-radius:4px;">
        <strong>Consignor / Supplier:</strong><br>
        ${po.supplier_name}<br>
        Depot Code: ${po.supplier_id}<br>
        Lead Time: ${po.lead_days} Days | Breakage Limit: ≤ ${po.breakage_allowance_pct}%
      </div>
      <div style="background:#f8fafc; padding:0.75rem; border-radius:4px;">
        <strong>Delivery Destination Depot:</strong><br>
        Shree Mahalaxmi Marbel and Granite Godown<br>
        Mudhal Titta, Kolhapur Junction 416208<br>
        Authorized Sign-off: ${po.approver_name || 'Mr. Vikram Gurav'}
      </div>
    </div>

    <table class="data-table" style="margin-bottom:1.5rem;">
      <thead>
        <tr>
          <th>Description of Consignment</th>
          <th>HSN Code</th>
          <th>Quantity</th>
          <th>Unit Rate</th>
          <th>Taxable Subtotal</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>${po.item_description}</td>
          <td>6907 / 6802</td>
          <td>${po.quantity} units</td>
          <td>₹${po.rate_per_box}</td>
          <td>₹${po.subtotal_amount.toLocaleString('en-IN')}</td>
        </tr>
      </tbody>
    </table>

    <div style="margin-left:auto; width:280px; font-size:0.9rem; line-height:1.6;">
      <div style="display:flex; justify-content:space-between;">
        <span>Taxable Subtotal:</span>
        <span>₹${po.subtotal_amount.toLocaleString('en-IN')}</span>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <span>CGST (9.0%):</span>
        <span>₹${cgst}</span>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <span>SGST (9.0%):</span>
        <span>₹${sgst}</span>
      </div>
      <div style="display:flex; justify-content:space-between; font-weight:700; border-top:1px solid #cbd5e1; padding-top:0.25rem;">
        <span>Total Order Amount:</span>
        <span style="color:var(--primary-navy);">₹${po.total_amount.toLocaleString('en-IN')}</span>
      </div>
    </div>
  `;

  document.getElementById('invoiceModal').style.display = 'flex';
};

const btnCloseInvoice = document.getElementById('btnCloseInvoice');
const btnDismissInvoice = document.getElementById('btnDismissInvoice');
if (btnCloseInvoice) btnCloseInvoice.addEventListener('click', () => document.getElementById('invoiceModal').style.display = 'none');
if (btnDismissInvoice) btnDismissInvoice.addEventListener('click', () => document.getElementById('invoiceModal').style.display = 'none');

const btnPrintInvoiceAction = document.getElementById('btnPrintInvoiceAction');
if (btnPrintInvoiceAction) {
  btnPrintInvoiceAction.addEventListener('click', () => {
    window.print();
  });
}

// --- REPORTS & ANALYTICS ---
async function loadReports() {
  try {
    const res = await fetch('/api/reports/summary');
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('reportAvgSavings').textContent = `${data.avg_savings_pct}%`;
    document.getElementById('reportTotalSpent').textContent = `₹${data.total_spent.toLocaleString('en-IN')}`;

    const winContainer = document.getElementById('supplierWinBars');
    if (winContainer && data.supplier_win_distribution) {
      winContainer.innerHTML = '';
      const totalWins = Object.values(data.supplier_win_distribution).reduce((a, b) => a + b, 0) || 1;

      Object.entries(data.supplier_win_distribution).forEach(([name, count]) => {
        const pct = Math.round((count / totalWins) * 100);
        const row = document.createElement('div');
        row.style.marginBottom = '0.75rem';
        row.innerHTML = `
          <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.25rem;">
            <span><strong>${name}</strong> (${count} wins)</span>
            <span>${pct}%</span>
          </div>
          <div style="background:#e2e8f0; height:8px; border-radius:4px; overflow:hidden;">
            <div style="background:var(--primary-navy); width:${pct}%; height:100%;"></div>
          </div>
        `;
        winContainer.appendChild(row);
      });
    }
  } catch (err) {
    console.error('Failed to load reports summary:', err);
  }
}

// --- NOTIFICATION DRAWER ---
function setupNotificationDrawer() {
  const btn = document.getElementById('btnNotifBell');
  const drawer = document.getElementById('notifDrawer');
  const btnClose = document.getElementById('btnCloseNotif');

  if (btn) {
    btn.addEventListener('click', () => {
      drawer.classList.toggle('open');
      const badge = document.getElementById('notifBadge');
      if (badge) badge.textContent = '0';
    });
  }
  if (btnClose) {
    btnClose.addEventListener('click', () => drawer.classList.remove('open'));
  }
}

function triggerInAppNotification(msg) {
  const list = document.getElementById('notifList');
  const badge = document.getElementById('notifBadge');
  if (!list) return;

  const li = document.createElement('li');
  li.className = 'notif-item';
  li.innerHTML = `
    <div style="font-weight:600; font-size:0.85rem; margin-bottom:0.15rem;">Procurement Update</div>
    <div style="font-size:0.8rem; color:#475569;">${msg}</div>
    <div style="font-size:0.75rem; color:#94a3b8; margin-top:0.25rem;">${new Date().toLocaleTimeString()}</div>
  `;
  list.prepend(li);

  if (badge) {
    let current = parseInt(badge.textContent, 10) || 0;
    badge.textContent = (current + 1).toString();
  }
}