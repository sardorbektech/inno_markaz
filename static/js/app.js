/**
 * Inno Markaz - Frontend Application
 * Interacts with FastAPI backend through REST endpoints.
 * Supports multi-turn session memory, beautiful Markdown rendering, and stage timing.
 */

document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chatForm');
  const questionInput = document.getElementById('questionInput');
  const messagesList = document.getElementById('messagesList');
  const chatContainer = document.getElementById('chatContainer');
  const chipsContainer = document.getElementById('chipsContainer');
  const systemStatus = document.getElementById('systemStatus');
  const modelInfo = document.getElementById('modelInfo');
  const statusIndicator = document.getElementById('statusIndicator');
  const clearChatBtn = document.getElementById('clearChatBtn');
  const openSidebarBtn = document.getElementById('openSidebarBtn');
  const closeSidebarBtn = document.getElementById('closeSidebarBtn');
  const sidebar = document.getElementById('sidebar');
  const tableList = document.getElementById('tableList');
  const selectedTableName = document.getElementById('selectedTableName');
  const columnsList = document.getElementById('columnsList');

  let schemaData = {};

  // Session Memory: Generate or retrieve persistent session ID
  let currentSessionId = localStorage.getItem('inno_session_id');
  if (!currentSessionId) {
    currentSessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8);
    localStorage.setItem('inno_session_id', currentSessionId);
  }

  // 1. Fetch System Health & Configuration
  async function loadSystemInfo() {
    try {
      const [healthRes, configRes, schemaRes] = await Promise.all([
        fetch('/api/health'),
        fetch('/api/config'),
        fetch('/api/schema'),
      ]);

      if (healthRes.ok) {
        const health = await healthRes.json();
        statusIndicator.className = 'status-indicator online';
        systemStatus.textContent = `Tizim: ${health.database ? "PostgreSQL Faol" : "Bazaga ulanishda xato"}`;
      }

      if (configRes.ok) {
        const cfg = await configRes.json();
        modelInfo.textContent = `Provayder: ${cfg.provider} | ${cfg.model}`;
      }

      if (schemaRes.ok) {
        schemaData = await schemaRes.json();
        renderTableColumns('departments');
      }
    } catch (err) {
      console.warn('System status check failed:', err);
      statusIndicator.className = 'status-indicator';
      systemStatus.textContent = 'Server bilan aloqa yo\'q';
      modelInfo.textContent = 'Qayta urinilmoqda...';
    }
  }

  // 2. Render Schema Explorer Columns
  function renderTableColumns(tableName) {
    selectedTableName.textContent = tableName;
    columnsList.innerHTML = '';

    const tbl = schemaData[tableName];
    if (!tbl || !tbl.columns) {
      columnsList.innerHTML = '<div class="col-item">Ma\'lumot topilmadi</div>';
      return;
    }

    Object.entries(tbl.columns).forEach(([colName, colType]) => {
      const row = document.createElement('div');
      row.className = 'col-item';
      row.innerHTML = `
        <span class="col-name">${colName}</span>
        <span class="col-type">${colType}</span>
      `;
      columnsList.appendChild(row);
    });
  }

  // 3. Table list click events
  tableList.addEventListener('click', (e) => {
    if (e.target.classList.contains('table-item')) {
      document.querySelectorAll('.table-item').forEach(el => el.classList.remove('active'));
      e.target.classList.add('active');
      const tblName = e.target.dataset.table;
      renderTableColumns(tblName);
    }
  });

  // 4. Handle Chat Submission
  async function submitQuestion(questionText) {
    const text = questionText.trim();
    if (!text) return;

    // Append User Message
    appendUserMessage(text);
    questionInput.value = '';

    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Loading indicator
    const loadingElem = appendLoadingMessage();
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          user_role: 'viewer',
          session_id: currentSessionId,
        }),
      });

      const data = await resp.json();
      loadingElem.remove();

      if (data.session_id) {
        currentSessionId = data.session_id;
        localStorage.setItem('inno_session_id', currentSessionId);
      }

      appendAssistantMessage(data);
    } catch (err) {
      loadingElem.remove();
      appendAssistantMessage({
        success: false,
        answer: 'Server bilan bog\'lanishda xatolik yuz berdi.',
        error: err.message,
        stages: [{ stage: 'ERROR', status: 'failed', detail: err.message, duration: '0.00 s' }],
      });
    }

    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  // 5. Append User Message
  function appendUserMessage(text) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper user';
    wrapper.innerHTML = `<div class="user-bubble">${escapeHtml(text)}</div>`;
    messagesList.appendChild(wrapper);
  }

  // 6. Append Loading Indicator
  function appendLoadingMessage() {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper assistant';
    wrapper.innerHTML = `
      <div class="assistant-card">
        <div class="assistant-body">
          <div class="typing-indicator">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
            <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 0.5rem;">
              So'rov tahlil qilinmoqda (MCP xavfsizlik tekshiruvi va SQL bajarilmoqda)...
            </span>
          </div>
        </div>
      </div>
    `;
    messagesList.appendChild(wrapper);
    return wrapper;
  }

  // 7. Append Assistant Response with Pipeline Visibility & Timing
  function appendAssistantMessage(res) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper assistant';

    const stages = res.stages || [];
    const sql = res.sql || '';
    const results = res.results || [];
    const executionTime = res.execution_time_ms ? `${(res.execution_time_ms / 1000).toFixed(2)} s` : '';

    let stagesBadgesHtml = stages.map(s => {
      const isPassed = s.status === 'approved' || s.status === 'passed' || s.status === 'synthesized' || s.status === 'executed' || s.status === 'sanitized' || s.status === 'ready' || s.status === 'completed' || s.status === 'allowed';
      const isRejected = s.status === 'rejected' || s.status === 'denied' || s.status === 'failed';
      const badgeCls = isPassed ? 'passed' : isRejected ? 'rejected' : '';
      const durText = s.duration ? `<span class="stage-time" style="margin-left: 0.35rem; color: #93c5fd; font-weight: 600;">(${s.duration})</span>` : '';
      return `<span class="stage-badge ${badgeCls}">[${s.stage}] ${s.status}${durText}</span>`;
    }).join('');

    let resultsTableHtml = '';
    if (results.length > 0) {
      const keys = Object.keys(results[0]);
      resultsTableHtml = `
        <div class="data-table-container">
          <table class="data-table">
            <thead>
              <tr>${keys.map(k => `<th>${escapeHtml(k)}</th>`).join('')}</tr>
            </thead>
            <tbody>
              ${results.slice(0, 15).map(r => `
                <tr>${keys.map(k => `<td>${escapeHtml(String(r[k] !== undefined && r[k] !== null ? r[k] : 'NULL'))}</td>`).join('')}</tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    const html = `
      <div class="assistant-card">
        <div class="assistant-body markdown-body">
          ${renderMarkdown(res.answer)}
        </div>

        <div class="inspector-accordion">
          <div class="inspector-header">
            <span>🛡️ Jarayon tafsilotlari (MCP & SQL Visibility)</span>
            <span>${executionTime ? `Jami: ${executionTime} ` : ''}▾</span>
          </div>
          <div class="inspector-content">
            <div class="stages-flow">
              ${stagesBadgesHtml}
            </div>

            ${sql ? `
              <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Xavfsiz Parametrlangan SQL:</div>
              <div class="sql-view-container">${escapeHtml(sql)}</div>
            ` : ''}

            ${resultsTableHtml ? `
              <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Qaytarilgan ma'lumotlar (${results.length} ta satr):</div>
              ${resultsTableHtml}
            ` : ''}
          </div>
        </div>
      </div>
    `;

    wrapper.innerHTML = html;

    // Toggle accordion
    const header = wrapper.querySelector('.inspector-header');
    const content = wrapper.querySelector('.inspector-content');
    header.addEventListener('click', () => {
      content.classList.toggle('open');
      const arrow = content.classList.contains('open') ? '▴' : '▾';
      header.querySelector('span:last-child').textContent = `${executionTime ? `Jami: ${executionTime} ` : ''}${arrow}`;
    });

    messagesList.appendChild(wrapper);
  }

  // 8. Event Listeners
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    submitQuestion(questionInput.value);
  });

  chipsContainer.addEventListener('click', (e) => {
    if (e.target.classList.contains('chip')) {
      submitQuestion(e.target.textContent);
    }
  });

  clearChatBtn.addEventListener('click', () => {
    messagesList.innerHTML = '';
    // Reset session memory ID on chat clear
    currentSessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8);
    localStorage.setItem('inno_session_id', currentSessionId);
  });

  openSidebarBtn.addEventListener('click', () => {
    sidebar.classList.add('open');
  });

  closeSidebarBtn.addEventListener('click', () => {
    sidebar.classList.remove('open');
  });

  // Helpers
  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Beautiful Markdown rendering (using marked if available, fallback with table support)
  function renderMarkdown(text) {
    if (!text) return '';
    if (typeof marked !== 'undefined' && marked.parse) {
      try {
        return marked.parse(text);
      } catch (e) {
        console.warn('Marked parse error, using fallback:', e);
      }
    }

    // High-fidelity fallback Markdown renderer supporting tables, headings, and bold
    let html = escapeHtml(text);

    // Markdown tables: | col | col |
    const tableRegex = /((?:\|[^\n]+\|\r?\n)+)/g;
    html = html.replace(tableRegex, (match) => {
      const rows = match.trim().split(/\r?\n/).map(r => r.trim()).filter(Boolean);
      if (rows.length < 2) return match;

      let tableHtml = '<div class="data-table-container"><table class="data-table">';
      rows.forEach((row, idx) => {
        if (row.includes('---')) return; // separator row
        const cells = row.split('|').map(c => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1);
        if (idx === 0) {
          tableHtml += '<thead><tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
        } else {
          tableHtml += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
        }
      });
      tableHtml += '</tbody></table></div>';
      return tableHtml;
    });

    // Headings
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');

    // Bold text
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Bullet points
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');

    // Paragraphs
    html = html.replace(/\n\n/g, '<br><br>');

    return html;
  }

  // Initial load
  loadSystemInfo();
});
