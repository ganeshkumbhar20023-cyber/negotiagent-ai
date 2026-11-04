/**
 * NegotiAgent AI - Main Frontend Controller
 * Domain: Tiles, Marbles & Granite Procurement
 * Sponsor: Shree Mahalaxmi Marbel and Granite (Mudal Titta, Kolhapur)
 * Institution: DYPCET Kolhapur
 */

function formatINR(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(amount);
}

let currentLang = localStorage.getItem('negotiagent_lang') || 'en';
let activeReplayData = null;
let currentReplayRound = 1;
let activeModalRfqId = null;

function getTranslatedHub(sourceHub) {
  const dict = translations[currentLang] || translations.en;
  if (!sourceHub) return dict.hub_default;
  if (sourceHub.includes('Morbi Cluster')) return dict.hub_morbi;
  if (sourceHub.includes('Kolhapur Regional')) return dict.hub_kolhapur;
  if (sourceHub.includes('Pune Industrial')) return dict.hub_pune;
  return dict.hub_default;
}

function getTranslatedStatusBadge(statusText) {
  const dict = translations[currentLang] || translations.en;
  let pillClass = 'evaluating';
  let label = dict.statusEvaluating;

  if (statusText.includes('Round 2') || statusText.includes('फेरी २') || statusText.includes('दौर 2')) {
    pillClass = 'round2';
    label = dict.statusRound2;
  } else if (statusText.includes('Ready for Approval') || statusText.includes('समीक्षा') || statusText.includes('मंजुरी')) {
    pillClass = 'review';
    label = dict.statusPendingReview;
  } else if (statusText.includes('Order Simulated') || statusText.includes('आदेश')) {
    pillClass = 'completed';
    label = dict.statusCompleted;
  }

  return `<span class="status-pill ${pillClass}">${label}</span>`;
}

function setLanguage(lang) {
  if (!translations[lang]) return;
  currentLang = lang;
  localStorage.setItem('negotiagent_lang', lang);

  const selector = document.getElementById('languageSelector');
  if (selector && selector.value !== lang) {
    selector.value = lang;
  }

  document.querySelectorAll('[data-i18n]').forEach((element) => {
    const key = element.getAttribute('data-i18n');
    if (translations[lang][key]) {
      element.textContent = translations[lang][key];
    }
  });

  document.documentElement.lang = lang;
  updateWeightSumDisplay();

  loadSuppliersFromBackend();
  loadRfqsFromBackend();
  loadNotifications();
  loadOrdersFromBackend();
  loadReportsData();
  if (activeReplayData) renderReplayRound(currentReplayRound);
}

// 6-Way View Switcher
function navigateTo(viewId) {
  const views = {
    dashboard: document.getElementById('viewDashboard'),
    'new-rfq': document.getElementById('viewNewRfq'),
    suppliers: document.getElementById('viewSuppliers'),
    replay: document.getElementById('viewReplay'),
    approvals: document.getElementById('viewApprovals'),
    reports: document.getElementById('viewReports')
  };

  const navs = {
    dashboard: document.getElementById('navLinkDashboard'),
    'new-rfq': document.getElementById('navLinkNewRfq'),
    suppliers: document.getElementById('navLinkSuppliers'),
    replay: document.getElementById('navLinkReplay'),
    approvals: document.getElementById('navLinkApprovals'),
    reports: document.getElementById('navLinkReports')
  };

  Object.keys(views).forEach((key) => {
    if (views[key]) views[key].classList.remove('active');
    if (navs[key]) navs[key].classList.remove('active');
  });

  if (views[viewId]) {
    views[viewId].classList.add('active');
    if (navs[viewId]) navs[viewId].classList.add('active');
    window.location.hash = viewId;
  }
}

function updateWeightSumDisplay() {
  const p = Number(document.getElementById('weightPrice')?.value || 0);
  const q = Number(document.getElementById('weightQuality')?.value || 0);
  const d = Number(document.getElementById('weightDelivery')?.value || 0);
  const w = Number(document.getElementById('weightWarranty')?.value || 0);
  const total = p + q + d + w;

  const totalTag = document.getElementById('weightTotalTag');
  if (!totalTag) return total;

  totalTag.textContent = `${total}%`;
  totalTag.className = total === 100 ? 'total-weight-tag valid' : 'total-weight-tag invalid';
  return total;
}

// Notifications Drawer
async function loadNotifications() {
  const notifList = document.getElementById('notifList');
  const notifBadge = document.getElementById('notifBadge');
  if (!notifList) return;

  try {
    const res = await fetch('/api/notifications');
    if (!res.ok) return;
    const notifs = await res.json();

    if (notifBadge) notifBadge.textContent = notifs.length;
    notifList.innerHTML = '';

    if (notifs.length === 0) {
      notifList.innerHTML = `<li class="notif-item" style="color:var(--text-muted);">${translations[currentLang].notifEmpty}</li>`;
      return;
    }

    notifs.forEach((n) => {
      const li = document.createElement('li');
      li.className = 'notif-item';
      li.innerHTML = `
        <div class="notif-item-title">${n.title}</div>
        <div>${n.message}</div>
        <div class="notif-item-time">${n.created_at}</div>
      `;
      notifList.appendChild(li);
    });
  } catch (err) {
    console.error('Error loading notifications:', err);
  }
}

// Reports Analytics Loader
async function loadReportsData() {
  const avgSavingsElem = document.getElementById('reportAvgSavings');
  const totalSpentElem = document.getElementById('reportTotalSpent');
  const winBarsContainer = document.getElementById('supplierWinBars');

  try {
    const res = await fetch('/api/reports/summary');
    if (!res.ok) return;
    const data = await res.json();

    if (avgSavingsElem) avgSavingsElem.textContent = `${data.avg_savings_pct}%`;
    if (totalSpentElem) totalSpentElem.textContent = formatINR(data.total_spent);

    if (winBarsContainer) {
      winBarsContainer.innerHTML = '';
      const wins = data.supplier_win_distribution || {};
      const totalWins = Object.values(wins).reduce((a, b) => a + b, 0) || 1;

      Object.entries(wins).forEach(([name, count]) => {
        const pct = Math.round((count / totalWins) * 100);
        const barItem = document.createElement('div');
        barItem.className = 'dist-bar-item';
        barItem.innerHTML = `
          <div class="dist-bar-header">
            <span>${name}</span>
            <span>${count} deals (${pct}%)</span>
          </div>
          <div class="dist-bar-track">
            <div class="dist-bar-fill" style="width: ${pct}%;"></div>
          </div>
        `;
        winBarsContainer.appendChild(barItem);
      });
    }
  } catch (err) {
    console.error('Error loading reports:', err);
  }
}

// Trigger Live Negotiation
async function triggerNegotiation(rfqId) {
  activeModalRfqId = rfqId;
  const modal = document.getElementById('negotiationModal');
  const modalBody = document.getElementById('modalBody');
  const modalTitle = document.getElementById('modalTitle');

  modalTitle.textContent = `Autonomous Negotiation: ${rfqId}`;
  modalBody.innerHTML = `
    <div style="text-align: center; padding: 2rem;">
      <p>Simulating 3 rounds across candidate supplier agents...</p>
      <small style="color:var(--text-muted)">Evaluating Price, Quality, Lead Time, Breakage</small>
    </div>
  `;
  modal.style.display = 'flex';

  try {
    const res = await fetch(`/api/negotiations/start/${rfqId}`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run negotiation simulation');
    const data = await res.json();

    const w = data.winning_supplier;
    modalBody.innerHTML = `
      <div class="recommend-badge">RECOMMENDED SUPPLIER: ${w.name}</div>
      <p><strong>Hub Location:</strong> ${w.hub_location}</p>
      <p><strong>Final Negotiated Rate:</strong> ${formatINR(w.final_box_quote)} / unit</p>
      <p><strong>Consignment Total:</strong> ${formatINR(w.final_total_cost)} (Saved: ${formatINR(data.savings_amount)})</p>
      <p><strong>Dispatch Lead Time:</strong> ${w.lead_days} days | <strong>Breakage Guarantee:</strong> &le; ${w.breakage_pct}%</p>
      <p><strong>Composite Utility Score:</strong> ${w.composite_score} / 100 pts</p>

      <div class="explanation-card">
        <strong>Agent Reasoning & Trade-off Analysis:</strong><br>
        ${data.explanation}
      </div>
    `;

    document.getElementById('btnModalViewReplay').onclick = () => {
      modal.style.display = 'none';
      openReplayForRfq(rfqId);
    };

    document.getElementById('btnModalApprove').onclick = () => {
      modal.style.display = 'none';
      approveNegotiationRfq(rfqId);
    };

    loadRfqsFromBackend();
    loadNotifications();
    loadReportsData();
    const savingsElem = document.getElementById('metricSavings');
    if (savingsElem) {
      savingsElem.textContent = formatINR(142500 + data.savings_amount);
    }

  } catch (err) {
    modalBody.innerHTML = `<div class="alert-box danger" style="display:block">Error: ${err.message}</div>`;
  }
}

// Human Approver Sign-Off
async function approveNegotiationRfq(rfqId) {
  try {
    const res = await fetch(`/api/orders/approve/${rfqId}`, { method: 'POST' });
    if (!res.ok) throw new Error('Approval request failed');
    const result = await res.json();

    alert(`Human Sign-Off Confirmed!\nPurchase Order ${result.po_id} has been generated for ₹${result.total_amount?.toLocaleString('en-IN') || ''}`);
    navigateTo('approvals');
    loadOrdersFromBackend();
    loadRfqsFromBackend();
    loadNotifications();
    loadReportsData();
  } catch (err) {
    alert(`Approval Error: ${err.message}`);
  }
}

// Sandbox Payment Simulation
async function simulateSandboxPayment(poId, outcome) {
  try {
    const res = await fetch(`/api/orders/pay/${poId}?action=${outcome}`, { method: 'POST' });
    if (!res.ok) throw new Error('Payment processing failed');
    await res.json();

    loadOrdersFromBackend();
    loadNotifications();
    loadReportsData();
  } catch (err) {
    alert(`Sandbox Payment Error: ${err.message}`);
  }
}

// Load and Render Purchase Orders Table
async function loadOrdersFromBackend() {
  const tbody = document.getElementById('ordersTableBody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/orders');
    if (!res.ok) return;
    const orders = await res.json();

    tbody.innerHTML = '';
    const dict = translations[currentLang] || translations.en;

    if (orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:var(--text-muted)">${dict.noOrdersYet}</td></tr>`;
      return;
    }

    orders.forEach((po) => {
      let payClass = 'pending';
      let payLabel = dict.payStatusPending;
      if (po.payment_status === 'PAID') {
        payClass = 'paid';
        payLabel = dict.payStatusPaid;
      } else if (po.payment_status === 'FAILED') {
        payClass = 'failed';
        payLabel = dict.payStatusFailed;
      }

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${po.id}</strong><br><small style="color:var(--text-muted)">RFQ: ${po.rfq_id}</small></td>
        <td><strong>${po.supplier_name}</strong><br><small>${po.item_description} (Qty: ${po.quantity})</small></td>
        <td>${formatINR(po.subtotal_amount)}</td>
        <td>${formatINR(po.gst_amount)}</td>
        <td><strong>${formatINR(po.total_amount)}</strong></td>
        <td>
          <span class="pay-pill ${payClass}">${payLabel}</span>
          ${po.payment_status !== 'PAID' ? `
            <div style="margin-top:0.35rem; display:flex; gap:0.25rem;">
              <button class="btn-success-sm" style="font-size:0.7rem; padding:0.2rem 0.4rem;" onclick="simulateSandboxPayment('${po.id}', 'success')">Pay OK</button>
              <button class="btn-sm" style="background:#ef4444; font-size:0.7rem; padding:0.2rem 0.4rem;" onclick="simulateSandboxPayment('${po.id}', 'failed')">Fail</button>
            </div>
          ` : ''}
        </td>
        <td>
          <button class="btn-sm" onclick='renderInvoiceModal(${JSON.stringify(po)})'>${dict.btnPrintInvoice}</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    const pendingKpi = document.getElementById('metricPending');
    if (pendingKpi) {
      const pendingCount = orders.filter((o) => o.payment_status === 'PENDING').length;
      pendingKpi.textContent = pendingCount;
    }

    const completedKpi = document.getElementById('metricCompleted');
    if (completedKpi) {
      const paidCount = orders.filter((o) => o.payment_status === 'PAID').length;
      completedKpi.textContent = 14 + paidCount;
    }

  } catch (err) {
    console.error('Error loading orders:', err);
  }
}

// Generate Printable Tax Invoice / PO View for Shree Mahalaxmi Marbel and Granite
function renderInvoiceModal(po) {
  const modal = document.getElementById('invoiceModal');
  const printArea = document.getElementById('invoicePrintArea');

  const subtotal = Number(po.subtotal_amount ?? po.subtotal ?? (po.rate_per_box * po.quantity) ?? 0);
  const gstAmount = Number(po.gst_amount ?? (subtotal * 0.18) ?? 0);
  const totalAmount = Number(po.total_amount ?? (subtotal + gstAmount) ?? 0);
  const breakage = po.breakage_allowance_pct ?? po.breakage_pct ?? po.max_breakage ?? 1.5;
  const description = po.item_description || po.material || "PGVT Vitrified Floor Tiles (Premium Grade)";
  const approver = po.approver_name || "Ganesh G. Kumbhar (DYPCET Kolhapur)";
  const leadDays = po.lead_days || 4;
  const supplierName = po.supplier_name || "Kolhapur Regional Tiles & Granite Yard";

  printArea.innerHTML = `
    <div class="invoice-header">
      <div>
        <div class="invoice-company">SHREE MAHALAXMI MARBEL AND GRANITE</div>
        <div class="invoice-subtext">Proprietor: Mr. Vikram Gurav | Quality Tiles, Marbles & Granite Wholesale</div>
        <div class="invoice-subtext">📍 Mudhal Titta, Aadamapur Road, Kolhapur, Maharashtra</div>
        <div class="invoice-subtext">GSTIN: <strong>27SMMAG9876K1Z2</strong> | State Code: 27 (Maharashtra)</div>
      </div>
      <div style="text-align: right;">
        <div class="invoice-title">PURCHASE ORDER</div>
        <div class="invoice-subtext"><strong>PO Number:</strong> ${po.id || "PO-SMMG-2026"}</div>
        <div class="invoice-subtext"><strong>Date:</strong> ${po.created_at || new Date().toLocaleDateString('en-GB')}</div>
        <div class="invoice-subtext"><strong>Linked RFQ:</strong> ${po.rfq_id || "RFQ-TILE-101"}</div>
        <div class="invoice-subtext"><strong>Status:</strong> ${po.payment_status || "APPROVED"}</div>
      </div>
    </div>

    <div class="invoice-meta-grid">
      <div class="invoice-meta-box">
        <strong>SUPPLIER / CONSIGNOR:</strong><br>
        <strong>${supplierName}</strong><br>
        Direct Industrial Supply Route to Mudhal Titta Depot<br>
        Delivery Lead Commitment: <strong>${leadDays} Days</strong><br>
        Guaranteed Transit Breakage: <strong>&le; ${breakage}%</strong>
      </div>
      <div class="invoice-meta-box">
        <strong>CONSIGNEE / DELIVERY SITE:</strong><br>
        <strong>Shree Mahalaxmi Marbel and Granite Godown</strong><br>
        Mudhal Titta, Aadamapur Road, Kolhapur<br>
        Student Project Lead: <strong>Ganesh G. Kumbhar (Roll No. 147)</strong><br>
        Team: <strong>Rushikesh Powar, Rohit Mengane, Pawan Payghan (DYPCET)</strong>
      </div>
    </div>

    <table class="invoice-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Material Description & Specifications</th>
          <th>HSN Code</th>
          <th>Quantity</th>
          <th>Negotiated Rate / Unit</th>
          <th>Taxable Amount (₹)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>1</td>
          <td><strong>${description}</strong><br><small>Fully palletized consignment with transit breakage protection</small></td>
          <td>6907 / 6802</td>
          <td>${po.quantity || 850}</td>
          <td>${formatINR(po.rate_per_box || 520)}</td>
          <td>${formatINR(subtotal)}</td>
        </tr>
      </tbody>
    </table>

    <div class="invoice-totals">
      <table class="invoice-totals-table">
        <tr>
          <td>Taxable Subtotal:</td>
          <td style="text-align:right;"><strong>${formatINR(subtotal)}</strong></td>
        </tr>
        <tr>
          <td>CGST (9.0%):</td>
          <td style="text-align:right;">${formatINR(gstAmount / 2)}</td>
        </tr>
        <tr>
          <td>SGST (9.0%):</td>
          <td style="text-align:right;">${formatINR(gstAmount / 2)}</td>
        </tr>
        <tr class="invoice-grand-total">
          <td>Grand Total:</td>
          <td style="text-align:right;">${formatINR(totalAmount)}</td>
        </tr>
      </table>
    </div>

    <div class="invoice-terms">
      <strong>Terms & Conditions:</strong><br>
      1. All goods covered under transit breakage replacement warranty up to ${breakage}%.<br>
      2. Material dispatch must arrive at Mudhal Titta Depot within ${leadDays} calendar days from PO confirmation.<br>
      3. Valid academic demonstration contract generated via NegotiAgent AI for Shree Mahalaxmi Marbel and Granite.
    </div>

    <div class="invoice-signatures">
      <div>
        ____________________________<br>
        Mr. Vikram Gurav (Owner)<br>
        <strong>Shree Mahalaxmi Marbel and Granite</strong>
      </div>
      <div style="text-align:right;">
        ____________________________<br>
        Authorized Signatory & Seal<br>
        <strong>${supplierName}</strong>
      </div>
    </div>
  `;

  document.getElementById('btnPrintInvoiceAction').onclick = () => window.print();
  modal.style.display = 'flex';
}

// Replay Handling
async function openReplayForRfq(rfqId) {
  navigateTo('replay');
  const selectElem = document.getElementById('selectReplayRfq');
  if (selectElem) selectElem.value = rfqId;
  await loadReplayTranscript(rfqId);
}

async function loadReplayTranscript(rfqId) {
  try {
    const res = await fetch(`/api/negotiations/${rfqId}`);
    if (!res.ok) {
      document.getElementById('replayTableBody').innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:var(--text-muted)">No negotiation transcript found. Click 'Inspect' on the dashboard first to execute this negotiation.</td></tr>`;
      document.getElementById('replayRationaleText').textContent = 'No session transcript recorded yet.';
      return;
    }
    activeReplayData = await res.json();
    setReplayRound(1);
  } catch (err) {
    console.error('Error fetching replay data:', err);
  }
}

function setReplayRound(roundNum) {
  currentReplayRound = roundNum;
  document.querySelectorAll('.step-btn').forEach((btn, idx) => {
    btn.classList.toggle('active', idx + 1 === roundNum);
  });
  renderReplayRound(roundNum);
}

function renderReplayRound(roundNum) {
  const tableBody = document.getElementById('replayTableBody');
  const rationaleBox = document.getElementById('replayRationaleText');
  if (!activeReplayData || !tableBody) return;

  const roundRows = activeReplayData.rounds.filter((r) => r.round_number === roundNum);
  tableBody.innerHTML = '';

  const dict = translations[currentLang] || translations.en;

  roundRows.forEach((r) => {
    const supName = dict[`${r.supplier_id}_name`] || r.supplier_name;
    let decPillClass = 'evaluated';
    let decLabel = dict.decEvaluated;

    if (r.decision === 'accepted') {
      decPillClass = 'accepted';
      decLabel = dict.decAccepted;
    } else if (r.decision === 'rejected') {
      decPillClass = 'rejected';
      decLabel = dict.decRejected;
    } else if (r.decision === 'countered') {
      decPillClass = 'countered';
      decLabel = dict.decCountered;
    }

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${supName}</strong></td>
      <td><strong>${formatINR(r.quote_per_box)}</strong></td>
      <td>${r.buyer_counter ? formatINR(r.buyer_counter) : '—'}</td>
      <td>${r.lead_days} days</td>
      <td>&le; ${r.breakage_pct}%</td>
      <td><strong>${r.composite_score}</strong> / 100</td>
      <td><span class="decision-pill ${decPillClass}">${decLabel}</span></td>
    `;
    tableBody.appendChild(tr);
  });

  if (roundNum === 1) {
    rationaleBox.innerHTML = `<strong>Round 1 Opening Analysis:</strong> Supplier agents submitted initial quotes based on standard factory price lists. The buyer agent evaluated quotes against target ceiling rates and prepared counter-proposals.`;
  } else if (roundNum === 2) {
    rationaleBox.innerHTML = `<strong>Round 2 Strategy Concessions:</strong> Suppliers adjusted quotes according to programmed negotiation personalities (Aggressive: strict margin defense; Cooperative: accelerated delivery; Balanced: proportional concessions).`;
  } else {
    rationaleBox.innerHTML = `<strong>Round 3 Best & Final Offer:</strong> Suppliers submitted final walk-away limits. The buyer agent completed multi-criteria weighted scoring. <strong>Winning Supplier: ${activeReplayData.recommended_supplier_name}</strong> locking in a final total of ${formatINR(activeReplayData.final_price)}.`;
  }
}

// Fetch all RFQs from SQLite Backend API
async function loadRfqsFromBackend() {
  const tableBody = document.getElementById('rfqTableBody');
  const selectReplay = document.getElementById('selectReplayRfq');
  if (!tableBody) return;

  try {
    const res = await fetch('/api/rfqs');
    if (!res.ok) throw new Error('Failed to load RFQs');
    const rfqs = await res.json();

    tableBody.innerHTML = '';
    if (selectReplay) selectReplay.innerHTML = '';

    rfqs.forEach((rfq) => {
      const translatedHub = getTranslatedHub(rfq.source_hub);
      const statusBadgeHtml = getTranslatedStatusBadge(rfq.status);
      const btnInspectText = translations[currentLang].btnViewDetails;
      const btnReplayText = translations[currentLang].btnReplayRfq;
      const btnApproveText = translations[currentLang].btnApproveRfq;

      const isReadyForApproval = rfq.status.includes('Ready for Approval') || rfq.status.includes('समीक्षा') || rfq.status.includes('मंजुरी');

      const row = document.createElement('tr');
      row.innerHTML = `
        <td><strong>${rfq.id}</strong><br><small style="color:var(--text-muted)">${rfq.category} ${rfq.size} (Qty: ${rfq.quantity})</small></td>
        <td>${translatedHub}</td>
        <td>${formatINR(rfq.budget_ceiling)}</td>
        <td>${statusBadgeHtml}</td>
        <td style="white-space:nowrap;">
          <button class="btn-sm" onclick="triggerNegotiation('${rfq.id}')">${btnInspectText}</button>
          <button class="btn-outline-sm" onclick="openReplayForRfq('${rfq.id}')">${btnReplayText}</button>
          ${isReadyForApproval ? `<button class="btn-success-sm" onclick="approveNegotiationRfq('${rfq.id}')">${btnApproveText}</button>` : ''}
        </td>
      `;
      tableBody.appendChild(row);

      if (selectReplay) {
        const opt = document.createElement('option');
        opt.value = rfq.id;
        opt.textContent = `${rfq.id} - ${rfq.category} (${rfq.quantity})`;
        selectReplay.appendChild(opt);
      }
    });

    const activeKpi = document.getElementById('metricActive');
    if (activeKpi) activeKpi.textContent = rfqs.length;

  } catch (err) {
    console.error('Error fetching RFQs:', err);
  }
}

// Load Simulated Suppliers
async function loadSuppliersFromBackend() {
  const container = document.getElementById('suppliersContainer');
  if (!container) return;

  try {
    const res = await fetch('/api/suppliers');
    if (!res.ok) throw new Error('Failed to load suppliers');
    const suppliers = await res.json();

    container.innerHTML = '';
    suppliers.forEach((s) => {
      const langDict = translations[currentLang] || translations.en;
      const displayName = langDict[`${s.id}_name`] || s.name;
      const displayHub = langDict[`${s.id}_hub`] || s.hub_location;
      const strategyKey = `strat_${s.agent_strategy}`;
      const displayStrategy = langDict[strategyKey] || s.agent_strategy;

      const card = document.createElement('article');
      card.className = 'supplier-card';
      card.innerHTML = `
        <div>
          <div class="supplier-header">
            <span class="supplier-name">${displayName}</span>
            <span class="strategy-badge ${s.agent_strategy}">${displayStrategy}</span>
          </div>
          <div class="supplier-location">📍 ${displayHub}</div>
          <div class="supplier-specs">
            <div class="spec-item">
              <span class="spec-label">${langDict.supplierBasePrice}</span>
              <span class="spec-value">${formatINR(s.base_price_per_box)}</span>
            </div>
            <div class="spec-item">
              <span class="spec-label">${langDict.supplierWalkaway}</span>
              <span class="spec-value">${formatINR(s.min_walkaway_price)}</span>
            </div>
            <div class="spec-item">
              <span class="spec-label">${langDict.supplierLeadTime}</span>
              <span class="spec-value">${s.min_lead_days} - ${s.standard_lead_days} days</span>
            </div>
            <div class="spec-item">
              <span class="spec-label">${langDict.supplierBreakage}</span>
              <span class="spec-value">&le; ${s.offered_breakage_pct}%</span>
            </div>
            <div class="spec-item">
              <span class="spec-label">${langDict.supplierQuality}</span>
              <span class="spec-value">${s.quality_score}/100</span>
            </div>
            <div class="spec-item">
              <span class="spec-label">${langDict.supplierReliability}</span>
              <span class="spec-value">${s.reliability_score}/100</span>
            </div>
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error('Error fetching suppliers:', err);
  }
}

// Handle Form Submission (POST /api/rfqs)
async function handleRfqSubmit(e) {
  e.preventDefault();
  const alertBox = document.getElementById('rfqAlert');
  alertBox.className = 'alert-box';
  alertBox.textContent = '';

  const totalWeights = updateWeightSumDisplay();
  if (totalWeights !== 100) {
    alertBox.textContent = `${translations[currentLang].valErrTotalWeight} ${totalWeights}%`;
    alertBox.className = 'alert-box danger';
    return;
  }

  const deadlineInput = document.getElementById('deliveryDeadline').value;
  if (!deadlineInput) {
    alertBox.textContent = translations[currentLang].valErrFutureDate;
    alertBox.className = 'alert-box danger';
    return;
  }

  const payload = {
    category: document.getElementById('tileCategory').value,
    size: document.getElementById('tileSize').value,
    quantity: Number(document.getElementById('boxQuantity').value),
    budget_ceiling: Number(document.getElementById('budgetCeiling').value),
    delivery_deadline: deadlineInput,
    quality_grade: document.getElementById('qualityGrade').value,
    max_breakage: Number(document.getElementById('maxBreakage').value),
    weights: {
      price: Number(document.getElementById('weightPrice').value),
      quality: Number(document.getElementById('weightQuality').value),
      delivery: Number(document.getElementById('weightDelivery').value),
      warranty: Number(document.getElementById('weightWarranty').value)
    }
  };

  try {
    const res = await fetch('/api/rfqs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Could not save RFQ');
    }

    alertBox.textContent = translations[currentLang].valSuccessCreated;
    alertBox.className = 'alert-box success';

    setTimeout(async () => {
      await loadRfqsFromBackend();
      document.getElementById('rfqForm').reset();
      document.getElementById('deliveryDeadline').value = getDefaultDeadline();
      updateWeightSumDisplay();
      alertBox.className = 'alert-box';
      navigateTo('dashboard');
    }, 1000);

  } catch (err) {
    alertBox.textContent = `Error: ${err.message}`;
    alertBox.className = 'alert-box danger';
  }
}

function getDefaultDeadline() {
  const d = new Date();
  d.setDate(d.getDate() + 14);
  return d.toISOString().split('T')[0];
}

document.addEventListener('DOMContentLoaded', () => {
  const selector = document.getElementById('languageSelector');
  if (selector) {
    selector.value = currentLang;
    selector.addEventListener('change', (e) => setLanguage(e.target.value));
  }

  const deadlineElem = document.getElementById('deliveryDeadline');
  if (deadlineElem) {
    deadlineElem.value = getDefaultDeadline();
    deadlineElem.min = new Date().toISOString().split('T')[0];
  }

  document.querySelectorAll('.weight-input').forEach((input) => {
    input.addEventListener('input', updateWeightSumDisplay);
  });

  // Notification Drawer
  const bellBtn = document.getElementById('btnNotifBell');
  const notifDrawer = document.getElementById('notifDrawer');
  const btnCloseNotif = document.getElementById('btnCloseNotif');

  bellBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    notifDrawer.classList.toggle('open');
  });

  btnCloseNotif?.addEventListener('click', () => notifDrawer.classList.remove('open'));
  document.addEventListener('click', (e) => {
    if (!notifDrawer?.contains(e.target) && e.target !== bellBtn) {
      notifDrawer?.classList.remove('open');
    }
  });

  // Modal Closers
  const modal = document.getElementById('negotiationModal');
  document.getElementById('btnCloseModal')?.addEventListener('click', () => modal.style.display = 'none');

  const invoiceModal = document.getElementById('invoiceModal');
  document.getElementById('btnCloseInvoice')?.addEventListener('click', () => invoiceModal.style.display = 'none');
  document.getElementById('btnDismissInvoice')?.addEventListener('click', () => invoiceModal.style.display = 'none');

  // Replay Step Buttons
  document.getElementById('btnStepRound1')?.addEventListener('click', () => setReplayRound(1));
  document.getElementById('btnStepRound2')?.addEventListener('click', () => setReplayRound(2));
  document.getElementById('btnStepRound3')?.addEventListener('click', () => setReplayRound(3));

  document.getElementById('selectReplayRfq')?.addEventListener('change', (e) => {
    loadReplayTranscript(e.target.value);
  });

  // Navigation Links
  document.getElementById('navLinkDashboard')?.addEventListener('click', (e) => {
    e.preventDefault();
    navigateTo('dashboard');
  });

  document.getElementById('navLinkNewRfq')?.addEventListener('click', (e) => {
    e.preventDefault();
    navigateTo('new-rfq');
  });

  document.getElementById('navLinkSuppliers')?.addEventListener('click', (e) => {
    e.preventDefault();
    navigateTo('suppliers');
  });

  document.getElementById('navLinkReplay')?.addEventListener('click', (e) => {
    e.preventDefault();
    navigateTo('replay');
    const selectElem = document.getElementById('selectReplayRfq');
    if (selectElem && selectElem.value) loadReplayTranscript(selectElem.value);
  });

  document.getElementById('navLinkApprovals')?.addEventListener('click', (e) => {
    e.preventDefault();
    navigateTo('approvals');
    loadOrdersFromBackend();
  });

  document.getElementById('navLinkReports')?.addEventListener('click', (e) => {
    e.preventDefault();
    navigateTo('reports');
    loadReportsData();
  });

  document.getElementById('btnOpenRfq')?.addEventListener('click', () => {
    navigateTo('new-rfq');
  });

  document.getElementById('btnCancelRfq')?.addEventListener('click', () => {
    navigateTo('dashboard');
  });

  document.getElementById('rfqForm')?.addEventListener('submit', handleRfqSubmit);

  const savingsElem = document.getElementById('metricSavings');
  if (savingsElem) savingsElem.textContent = formatINR(142500);

  setLanguage(currentLang);
  updateWeightSumDisplay();
  loadRfqsFromBackend();
  loadSuppliersFromBackend();
  loadNotifications();
  loadOrdersFromBackend();
  loadReportsData();
});