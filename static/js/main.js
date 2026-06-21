/* ═══════════════════════════════════════════════════════════
   Smart Code Plagiarism Detector — Main JS
   ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Theme Toggle ──────────────────────────────────────────
  const html       = document.documentElement;
  const themeToggle = document.getElementById('themeToggle');
  const themeIcon   = document.getElementById('themeIcon');

  const savedTheme = localStorage.getItem('theme') || 'light';
  html.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const current = html.getAttribute('data-theme');
      const next    = current === 'light' ? 'dark' : 'light';
      html.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      updateThemeIcon(next);
    });
  }

  function updateThemeIcon(theme) {
    if (!themeIcon) return;
    themeIcon.className = theme === 'light' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
  }

  // ── Sidebar Toggle ────────────────────────────────────────
  const sidebar        = document.getElementById('sidebar');
  const sidebarToggle  = document.getElementById('sidebarToggle');
  const sidebarClose   = document.getElementById('sidebarClose');
  const sidebarOverlay = document.getElementById('sidebarOverlay');

  function openSidebar() {
    sidebar?.classList.add('open');
    sidebarOverlay?.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    sidebar?.classList.remove('open');
    sidebarOverlay?.classList.remove('active');
    document.body.style.overflow = '';
  }

  sidebarToggle?.addEventListener('click', openSidebar);
  sidebarClose?.addEventListener('click', closeSidebar);
  sidebarOverlay?.addEventListener('click', closeSidebar);

  // ── Auto-dismiss alerts ───────────────────────────────────
  document.querySelectorAll('.alert.fade.show').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert?.close();
    }, 5000);
  });

  // ── Upload drag-and-drop zone ─────────────────────────────
  const zone     = document.getElementById('uploadZone');
  const fileInput = document.getElementById('fileInput');

  if (zone && fileInput) {
    zone.addEventListener('click', () => fileInput.click());

    zone.addEventListener('dragover', e => {
      e.preventDefault();
      zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('dragover');
      const dt = new DataTransfer();
      Array.from(e.dataTransfer.files).forEach(f => dt.items.add(f));
      fileInput.files = dt.files;
      updateFileList(fileInput.files);
    });

    fileInput.addEventListener('change', () => updateFileList(fileInput.files));
  }

  function updateFileList(files) {
    const container = document.getElementById('fileList');
    if (!container) return;
    container.innerHTML = '';
    Array.from(files).forEach(file => {
      const ext  = file.name.split('.').pop().toLowerCase();
      const icon = { py: '🐍', java: '☕', c: '⚙️', cpp: '⚙️' }[ext] || '📄';
      const size = (file.size / 1024).toFixed(1) + ' KB';
      const item = document.createElement('div');
      item.className = 'file-item d-flex align-items-center gap-2 p-2 rounded border mb-2';
      item.style.background = 'var(--surface-2)';
      item.innerHTML = `
        <span style="font-size:20px">${icon}</span>
        <div class="flex-1">
          <div class="fw-500" style="font-size:13px">${file.name}</div>
          <div class="text-muted" style="font-size:11px">${size}</div>
        </div>
        <span class="badge bg-primary text-uppercase" style="font-size:10px">${ext}</span>
      `;
      container.appendChild(item);
    });

    const zoneSub = document.getElementById('zoneSub');
    if (zoneSub) zoneSub.textContent = `${files.length} file(s) selected`;
  }

  // ── Animated counter on dashboard ─────────────────────────
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseFloat(el.getAttribute('data-count'));
    const isFloat = el.getAttribute('data-count').includes('.');
    const duration = 1000;
    const start = performance.now();

    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased    = 1 - Math.pow(1 - progress, 3);
      const current  = target * eased;
      el.textContent = isFloat ? current.toFixed(1) : Math.round(current);
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });

  // ── Progress bars animate on load ─────────────────────────
  document.querySelectorAll('.progress-bar[data-width]').forEach(bar => {
    const w = bar.getAttribute('data-width');
    setTimeout(() => { bar.style.width = w + '%'; }, 200);
  });

  // ── Gauge chart (compare result page) ────────────────────
  const gaugeCanvas = document.getElementById('gaugeChart');
  if (gaugeCanvas) {
    const score = parseFloat(gaugeCanvas.getAttribute('data-score') || '0');
    let color = '#2ec4b6';
    if (score > 60) color = '#e63946';
    else if (score > 30) color = '#ff9f1c';

    new Chart(gaugeCanvas, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [score, 100 - score],
          backgroundColor: [color, 'rgba(0,0,0,.08)'],
          borderWidth: 0,
          circumference: 240,
          rotation: -120,
        }]
      },
      options: {
        cutout: '80%',
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        animation: { duration: 1200, easing: 'easeOutQuart' }
      }
    });
  }

  // ── Similarity distribution pie chart ────────────────────
  const distCanvas = document.getElementById('distChart');
  if (distCanvas) {
    const low    = parseInt(distCanvas.getAttribute('data-low')    || '0');
    const medium = parseInt(distCanvas.getAttribute('data-medium') || '0');
    const high   = parseInt(distCanvas.getAttribute('data-high')   || '0');

    new Chart(distCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Low (0–30%)', 'Medium (31–60%)', 'High (61–100%)'],
        datasets: [{
          data: [low, medium, high],
          backgroundColor: ['#2ec4b6', '#ff9f1c', '#e63946'],
          borderWidth: 0,
          hoverOffset: 6,
        }]
      },
      options: {
        plugins: {
          legend: { position: 'bottom', labels: { padding: 16, font: { size: 12 } } },
          tooltip: { callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.raw} cases`
          }}
        },
        cutout: '65%',
        animation: { duration: 900 }
      }
    });
  }

  // ── Monthly trend bar chart ───────────────────────────────
  const trendCanvas = document.getElementById('trendChart');
  if (trendCanvas) {
    let labels = [], values = [];
    try {
      labels = JSON.parse(trendCanvas.getAttribute('data-labels') || '[]');
      values = JSON.parse(trendCanvas.getAttribute('data-values') || '[]');
    } catch (e) {}

    new Chart(trendCanvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Comparisons',
          data: values,
          backgroundColor: 'rgba(67,97,238,.7)',
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,.06)' }, ticks: { stepSize: 1 } },
          x: { grid: { display: false } }
        },
        animation: { duration: 900 }
      }
    });
  }

  // ── Algorithm breakdown bar chart (compare result) ────────
  const algoCanvas = document.getElementById('algoChart');
  if (algoCanvas) {
    const token  = parseFloat(algoCanvas.getAttribute('data-token')     || '0');
    const ast    = parseFloat(algoCanvas.getAttribute('data-ast')       || '0');
    const struct = parseFloat(algoCanvas.getAttribute('data-structure') || '0');
    const logic  = parseFloat(algoCanvas.getAttribute('data-logic')     || '0');

    new Chart(algoCanvas, {
      type: 'bar',
      data: {
        labels: ['Token Match', 'AST Analysis', 'Structure', 'Logic'],
        datasets: [{
          data: [token, ast, struct, logic],
          backgroundColor: ['#4361ee','#7209b7','#f72585','#ff9f1c'],
          borderRadius: 8,
          borderSkipped: false,
        }]
      },
      options: {
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { min: 0, max: 100, grid: { color: 'rgba(0,0,0,.06)' },
               ticks: { callback: v => v + '%' } },
          y: { grid: { display: false } }
        },
        animation: { duration: 900 }
      }
    });
  }

  // ── Batch select all ──────────────────────────────────────
  const selectAll = document.getElementById('selectAll');
  if (selectAll) {
    selectAll.addEventListener('change', () => {
      document.querySelectorAll('.file-checkbox').forEach(cb => {
        cb.checked = selectAll.checked;
      });
    });
  }

  // ── Confirm delete ────────────────────────────────────────
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      if (!confirm(el.getAttribute('data-confirm'))) e.preventDefault();
    });
  });

  // ── Fade-in elements on scroll ────────────────────────────
  const observer = new IntersectionObserver(entries => {
    entries.forEach(en => {
      if (en.isIntersecting) en.target.classList.add('visible');
    });
  }, { threshold: 0.1 });
  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));
});
