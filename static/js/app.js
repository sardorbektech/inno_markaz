/**
 * Inno Markaz - Frontend Application
 * Interacts with FastAPI backend through REST endpoints.
 */

document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chatForm');
  const questionInput = document.getElementById('questionInput');
  const messagesList = document.getElementById('messagesList');
  const chatContainer = document.getElementById('chatContainer');
  const chipsContainer = document.getElementById('chipsContainer');
  const userRoleSelect = document.getElementById('userRoleSelect');
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

    const role = userRoleSelect.value || 'analyst';

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, user_role: role }),
      });

      const data = await resp.json();
      loadingElem.remove();

      appendAssistantMessage(data);
    } catch (err) {
      loadingElem.remove();
      appendAssistantMessage({
        success: false,
        answer: 'Server bilan bog\'lanishda xatolik yuz berdi.',
        error: err.message,
        stages: [{ stage: 'ERROR', status: 'failed', detail: err.message }],
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
              So'rov tahlil qilinmoqda (MCP tekshiruvi va SQL bajarilmoqda)...
            </span>
          </div>
        </div>
      </div>
    `;
    messagesList.appendChild(wrapper);
    return wrapper;
  }

  // 7. Append Assistant Response with Pipeline Visibility
  function appendAssistantMessage(res) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper assistant';

    const isSuccess = res.success !== false;
    const stages = res.stages || [];
    const sql = res.sql || '';
    const results = res.results || [];
    const executionTime = res.execution_time_ms ? `${res.execution_time_ms.toFixed(1)} ms` : '';

    let stagesBadgesHtml = stages.map(s => {
      const isPassed = s.status === 'approved' || s.status === 'passed' || s.status === 'synthesized' || s.status === 'executed' || s.status === 'sanitized';
      const isRejected = s.status === 'rejected' || s.status === 'denied' || s.status === 'failed';
      const badgeCls = isPassed ? 'passed' : isRejected ? 'rejected' : '';
      return `<span class="stage-badge ${badgeCls}">[${s.stage}] ${s.status}</span>`;
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
        <div class="assistant-body">
          ${formatAnswerMarkdown(res.answer)}
        </div>

        <div class="inspector-accordion">
          <div class="inspector-header">
            <span>🛡️ Jarayon tafsilotlari (MCP & SQL Visibility)</span>
            <span>${executionTime} ▾</span>
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
              <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Filtrlangan natijalar (${results.length} ta satr):</div>
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
      header.querySelector('span:last-child').textContent = content.classList.contains('open')
        ? `${executionTime} ▴`
        : `${executionTime} ▾`;
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

  function formatAnswerMarkdown(text) {
    if (!text) return '';
    // Basic Markdown format: line breaks, bold, bullet points
    let formatted = escapeHtml(text)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n- /g, '<br>• ')
      .replace(/\n/g, '<br>');
    return `<p>${formatted}</p>`;
  }

  // Initial load
  loadSystemInfo();
});
