/* ============================================================
   NetScan — Frontend Logic
   ============================================================ */

const socket = io();

// ---------- DOM refs ----------
const startBtn     = document.getElementById('startBtn');
const exportBtn    = document.getElementById('exportBtn');
const btnSpinner   = document.getElementById('btnSpinner');
const btnLabel     = document.getElementById('btnLabel');
const targetEl     = document.getElementById('target');
const portsEl      = document.getElementById('ports');
const scanTypeEl   = document.getElementById('scanType');
const statusPill   = document.getElementById('statusPill');
const progressCard = document.getElementById('progressCard');
const progressLabel= document.getElementById('progressLabel');
const progressPct  = document.getElementById('progressPct');
const progressFill = document.getElementById('progressFill');
const resultsEl    = document.getElementById('results');
const resultsSub   = document.getElementById('resultsSub');
const filterInput  = document.getElementById('filterInput');
const statHosts    = document.getElementById('statHosts');
const statPorts    = document.getElementById('statPorts');
const statServices = document.getElementById('statServices');
const statTime     = document.getElementById('statTime');
const themeToggle  = document.getElementById('themeToggle');

let lastResults = null;
let allHosts = [];
let timerStart = null;
let timerHandle = null;

/* ============================================================
   THEME
   ============================================================ */
const savedTheme = localStorage.getItem('theme') || 'dark';
setTheme(savedTheme);

themeToggle.addEventListener('click', () => {
  setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
});

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem('theme', theme);
  themeToggle.querySelector('.theme-icon').textContent = theme === 'dark' ? '☀' : '☾';
  themeToggle.querySelector('.theme-label').textContent = theme === 'dark' ? 'Light mode' : 'Dark mode';
}

/* ============================================================
   TOASTS
   ============================================================ */
function showToast(message, type = 'info', duration = 3500) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  document.getElementById('toasts').appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(20px)';
    setTimeout(() => el.remove(), 300);
  }, duration);
}

/* ============================================================
   START SCAN
   ============================================================ */
startBtn.addEventListener('click', () => {
  const payload = {
    target: targetEl.value.trim(),
    ports: portsEl.value.trim(),
    scan_type: scanTypeEl.value,
  };

  if (!payload.target) {
    showToast('Please enter a target range.', 'error');
    return;
  }

  resetUI();
  socket.emit('start_scan', payload);
  showToast(`Scanning ${payload.target}…`, 'info');
});

/* ============================================================
   EXPORT
   ============================================================ */
exportBtn.addEventListener('click', () => {
  if (!lastResults) return;
  const blob = new Blob([JSON.stringify(lastResults, null, 2)], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url;
  a.download = `netscan_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Exported scan results.', 'success');
});

/* ============================================================
   FILTER
   ============================================================ */
filterInput.addEventListener('input', () => {
  applyFilter(filterInput.value.trim().toLowerCase());
});

function applyFilter(q) {
  const cards = document.querySelectorAll('.host-card');
  cards.forEach(card => {
    const text = card.dataset.search || '';
    card.style.display = !q || text.includes(q) ? '' : 'none';
  });
}

/* ============================================================
   SOCKET EVENTS
   ============================================================ */
socket.on('connect', () => {
  console.log('[NetScan] Connected');
});

socket.on('scan_status', d => {
  setStatus('running', d.message);
  progressCard.classList.remove('hidden');
});

socket.on('hosts_found', d => {
  statHosts.textContent = d.count;
  resultsSub.textContent = `${d.count} live host(s) found`;
  setStatus('running', `Found ${d.count} host(s). Scanning ports…`);
});

socket.on('scan_progress', d => {
  const pct = d.percent || Math.floor((d.current / d.total) * 100);
  progressFill.style.width = pct + '%';
  progressPct.textContent  = pct + '%';
  progressLabel.textContent = `Scanning ${d.current_host} (${d.current}/${d.total})`;
});

socket.on('host_result', host => {
  allHosts.push(host);
  appendHostCard(host);
  updateStats();
});

socket.on('scan_complete', d => {
  progressFill.style.width = '100%';
  progressPct.textContent  = '100%';
  progressLabel.textContent = `Done — ${d.summary.hosts} host(s), ${d.summary.open_ports} open port(s)`;
  setStatus('done', 'Scan complete');
  stopTimer();
  statTime.textContent = (d.elapsed || 0).toFixed(1) + 's';
  lastResults = d.hosts || allHosts;
  exportBtn.disabled = false;
  startBtn.disabled = false;
  btnSpinner.classList.add('hidden');
  btnLabel.textContent = 'Start Scan';
  showToast(`Scan complete in ${d.elapsed}s`, 'success');
});

socket.on('scan_error', d => {
  setStatus('error', d.message || 'Scan error');
  showToast(d.message || 'Scan error', 'error', 5000);
  startBtn.disabled = false;
  btnSpinner.classList.add('hidden');
  btnLabel.textContent = 'Start Scan';
  stopTimer();
});

/* ============================================================
   UI HELPERS
   ============================================================ */
function resetUI() {
  allHosts = [];
  lastResults = null;
  startBtn.disabled = true;
  exportBtn.disabled = true;
  btnSpinner.classList.remove('hidden');
  btnLabel.textContent = 'Scanning…';
  statusPill.className = 'status-pill running';
  statusPill.querySelector('.dot').nextSibling.textContent = ' Starting…';
  progressCard.classList.remove('hidden');
  progressFill.style.width = '0%';
  progressPct.textContent = '0%';
  progressLabel.textContent = 'Starting scan…';
  resultsEl.innerHTML = '';
  resultsSub.textContent = 'Scanning…';
  statHosts.textContent = '0';
  statPorts.textContent = '0';
  statServices.textContent = '0';
  statTime.textContent = '0.0s';
  startTimer();
}

function setStatus(state, text) {
  statusPill.className = 'status-pill ' + state;
  // dot is first child span, text is the raw text node after it
  const dot = statusPill.querySelector('.dot');
  statusPill.childNodes.forEach(n => {
    if (n.nodeType === 3) n.textContent = ' ' + text;
  });
}

function startTimer() {
  timerStart = Date.now();
  clearInterval(timerHandle);
  timerHandle = setInterval(() => {
    statTime.textContent = ((Date.now() - timerStart) / 1000).toFixed(1) + 's';
  }, 100);
}
function stopTimer() { clearInterval(timerHandle); }

function updateStats() {
  statHosts.textContent = allHosts.length;
  const totalPorts = allHosts.reduce((s, h) => s + h.open_ports.length, 0);
  statPorts.textContent = totalPorts;
  const services = new Set();
  allHosts.forEach(h => h.open_ports.forEach(p => {
    if (p.service && p.service !== 'unknown') services.add(p.service);
  }));
  statServices.textContent = services.size;
}

function appendHostCard(host) {
  const card = document.createElement('div');
  card.className = 'host-card';
  card.dataset.search = (
    host.ip + ' ' + host.mac + ' ' + host.vendor + ' ' +
    host.open_ports.map(p => p.port + ' ' + p.service).join(' ')
  ).toLowerCase();

  const portsHtml = host.open_ports.length
    ? host.open_ports.map(p => `
        <tr>
          <td>${p.port}</td>
          <td>${escapeHtml(p.service)}</td>
          <td><span class="state-open">${p.state}</span></td>
          <td class="banner-cell">${p.banner ? escapeHtml(p.banner) : '—'}</td>
        </tr>`).join('')
    : `<tr><td colspan="4" style="text-align:center;color:var(--text-dim)">No open ports detected</td></tr>`;

  card.innerHTML = `
    <div class="host-header">
      <span class="host-ip">${escapeHtml(host.ip)}</span>
      <span class="host-mac">${escapeHtml(host.mac)}</span>
      <span class="host-vendor">${escapeHtml(host.vendor)}</span>
      <span class="host-badge">${host.open_ports.length} open</span>
    </div>
    <table class="port-table">
      <thead>
        <tr><th>Port</th><th>Service</th><th>State</th><th>Banner</th></tr>
      </thead>
      <tbody>${portsHtml}</tbody>
    </table>`;

  resultsEl.appendChild(card);
}

function escapeHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}
