import json
from maintainerops.models.report import ScanReport


def render_html(report: ScanReport) -> str:
    """Renders a self-contained, interactive single-file HTML dashboard with zero external dependencies."""
    report_dict = report.model_dump(mode="python")
    report_json_str = json.dumps(report_dict, indent=2, default=str)

    # Safe escaping for embedding JSON inside script tag
    safe_json = report_json_str.replace("</script>", "<\\/script>")

    score = report.metrics.health_score
    grade = report.metrics.health_grade
    grade_color = "#10b981" if score >= 85 else ("#f59e0b" if score >= 70 else "#ef4444")

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MaintainerOps Triage Dashboard - {report.repository}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --critical: #dc2626;
      --font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-family);
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 1.5rem;
    }}
    .container {{ max-width: 1280px; margin: 0 auto; }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--border);
      margin-bottom: 2rem;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .shield-icon {{
      font-size: 2rem;
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    h1 {{ font-size: 1.6rem; font-weight: 700; }}
    .repo-pill {{
      background: #1e293b;
      border: 1px solid var(--border);
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.875rem;
      font-family: monospace;
      color: #38bdf8;
    }}
    .meta-time {{ font-size: 0.85rem; color: var(--text-muted); }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      transition: transform 0.15s ease, border-color 0.15s ease;
    }}
    .kpi-card:hover {{
      transform: translateY(-2px);
      border-color: #475569;
    }}
    .kpi-title {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 600; }}
    .kpi-value {{ font-size: 1.85rem; font-weight: 700; color: #fff; }}
    .kpi-subtext {{ font-size: 0.75rem; color: var(--text-muted); }}

    .health-kpi {{
      border: 2px solid {grade_color};
      background: linear-gradient(180deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.9));
    }}
    .health-badge {{
      display: inline-block;
      padding: 0.15rem 0.5rem;
      border-radius: 0.375rem;
      background: {grade_color};
      color: #0f172a;
      font-weight: 800;
      font-size: 0.9rem;
      margin-left: 0.5rem;
    }}

    /* Controls bar */
    .controls {{
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }}
    .search-box {{
      flex: 1;
      min-width: 250px;
      position: relative;
    }}
    .search-input {{
      width: 100%;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      padding: 0.65rem 1rem;
      color: var(--text);
      font-size: 0.9rem;
      outline: none;
    }}
    .search-input:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }}
    .filter-tabs {{
      display: flex;
      gap: 0.5rem;
      overflow-x: auto;
      padding-bottom: 0.25rem;
    }}
    .filter-btn {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 0.5rem 0.85rem;
      border-radius: 0.5rem;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
    }}
    .filter-btn:hover, .filter-btn.active {{
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }}

    /* Finding Cards */
    .findings-list {{
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .finding-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      transition: border-color 0.2s ease;
    }}
    .finding-card:hover {{ border-color: #475569; }}
    .finding-card.sev-critical {{ border-left: 4px solid var(--critical); }}
    .finding-card.sev-high {{ border-left: 4px solid var(--warning); }}
    .finding-card.sev-medium {{ border-left: 4px solid #38bdf8; }}
    .finding-card.sev-low {{ border-left: 4px solid #64748b; }}

    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1rem;
      flex-wrap: wrap;
    }}
    .card-title-group {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-wrap: wrap;
    }}
    .item-link {{
      font-size: 1.05rem;
      font-weight: 600;
      color: #f1f5f9;
      text-decoration: none;
    }}
    .item-link:hover {{ color: var(--accent); text-decoration: underline; }}
    .type-pill {{
      padding: 0.2rem 0.5rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .pill-incomplete_issue {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
    .pill-ci_failure {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
    .pill-merge_conflict {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
    .pill-possible_duplicate {{ background: rgba(147, 51, 234, 0.15); color: #c084fc; border: 1px solid rgba(147, 51, 234, 0.3); }}
    .pill-stale_pr, .pill-stale_issue, .pill-stale_review {{ background: rgba(100, 116, 139, 0.15); color: #94a3b8; border: 1px solid rgba(100, 116, 139, 0.3); }}
    .pill-good_first_issue {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .pill-community_sentiment {{ background: rgba(220, 38, 38, 0.2); color: #fca5a5; border: 1px solid rgba(220, 38, 38, 0.4); }}
    .pill-high_priority_actionable {{ background: rgba(234, 88, 12, 0.15); color: #fb923c; border: 1px solid rgba(234, 88, 12, 0.3); }}

    .summary-text {{ font-size: 0.95rem; color: #cbd5e1; }}

    /* Evidence Box */
    .evidence-box {{
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      padding: 0.75rem;
      font-size: 0.85rem;
    }}
    .evidence-item {{ margin-bottom: 0.25rem; display: flex; gap: 0.5rem; }}
    .evidence-name {{ color: #38bdf8; font-weight: 600; min-width: 140px; }}
    .evidence-val {{ color: var(--text-muted); }}

    /* Draft box */
    .draft-box {{
      background: rgba(59, 130, 246, 0.05);
      border: 1px dashed rgba(59, 130, 246, 0.3);
      border-radius: 0.5rem;
      padding: 0.85rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}
    .draft-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.8rem;
      font-weight: 600;
      color: #60a5fa;
    }}
    .draft-content {{
      font-style: italic;
      color: #e2e8f0;
      font-size: 0.9rem;
      background: transparent;
      border: none;
      width: 100%;
      resize: vertical;
      font-family: inherit;
    }}
    .action-btn {{
      align-self: flex-start;
      background: #2563eb;
      color: #fff;
      border: none;
      padding: 0.35rem 0.75rem;
      border-radius: 0.375rem;
      font-size: 0.8rem;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: background 0.15s ease;
    }}
    .action-btn:hover {{ background: #1d4ed8; }}

    /* Toast */
    #toast {{
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: #10b981;
      color: #0f172a;
      font-weight: 600;
      padding: 0.75rem 1.25rem;
      border-radius: 0.5rem;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
      opacity: 0;
      transform: translateY(1rem);
      transition: all 0.25s ease;
      pointer-events: none;
      z-index: 999;
    }}
    #toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}

    .empty-state {{
      text-align: center;
      padding: 3rem 1rem;
      background: var(--card-bg);
      border: 1px dashed var(--border);
      border-radius: 0.75rem;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <span class="shield-icon">🛡️</span>
        <div>
          <h1>MaintainerOps Triage Dashboard</h1>
          <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.25rem;">
            <span class="repo-pill">{report.repository}</span>
            <span class="meta-time">v{report.tool_version} • Generated {report.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
          </div>
        </div>
      </div>
      <div>
        <button class="action-btn" onclick="window.print()">🖨️ Export / Print</button>
      </div>
    </header>

    <!-- KPI Grid -->
    <div class="kpi-grid">
      <div class="kpi-card health-kpi">
        <div class="kpi-title">Repo Health Index</div>
        <div class="kpi-value">{report.metrics.health_score}<span style="font-size: 1rem; color: var(--text-muted);">/100</span><span class="health-badge">{report.metrics.health_grade}</span></div>
        <div class="kpi-subtext">Explainable multi-factor score</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Open PR Blockers</div>
        <div class="kpi-value" style="color: {('#f87171' if report.metrics.blocked_prs_count > 0 else '#fff')};">{report.metrics.blocked_prs_count}</div>
        <div class="kpi-subtext">CI failures & merge conflicts</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Incomplete Issues</div>
        <div class="kpi-value" style="color: {('#fbbf24' if report.metrics.incomplete_issues_count > 0 else '#fff')};">{report.metrics.incomplete_issues_count}</div>
        <div class="kpi-subtext">Missing repro or environment</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Likely Duplicates</div>
        <div class="kpi-value">{report.metrics.potential_duplicates_count}</div>
        <div class="kpi-subtext">Cosine similarity matched</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Stale / Dormant</div>
        <div class="kpi-value">{report.metrics.stale_items_count}</div>
        <div class="kpi-subtext">Inactive &gt; 14 days</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Good First Issues</div>
        <div class="kpi-value" style="color: #34d399;">{report.metrics.good_first_issues_count}</div>
        <div class="kpi-subtext">Mentorship candidates</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Urgent / Sentiment</div>
        <div class="kpi-value" style="color: {('#fca5a5' if report.metrics.sentiment_alerts_count > 0 else '#fff')};">{report.metrics.sentiment_alerts_count}</div>
        <div class="kpi-subtext">High urgency alerts</div>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls">
      <div class="search-box">
        <input type="text" id="searchInput" class="search-input" placeholder="Search by title, number (#101), author, or keyword..." oninput="filterFindings()">
      </div>
      <div class="filter-tabs">
        <button class="filter-btn active" data-filter="all" onclick="setFilter('all', this)">All Findings ({len(report.findings)})</button>
        <button class="filter-btn" data-filter="blocked_pr" onclick="setFilter('blocked_pr', this)">PR Blockers</button>
        <button class="filter-btn" data-filter="incomplete" onclick="setFilter('incomplete', this)">Incomplete</button>
        <button class="filter-btn" data-filter="duplicate" onclick="setFilter('duplicate', this)">Duplicates</button>
        <button class="filter-btn" data-filter="stale" onclick="setFilter('stale', this)">Stale Items</button>
        <button class="filter-btn" data-filter="good_first" onclick="setFilter('good_first', this)">Good First Issues</button>
        <button class="filter-btn" data-filter="sentiment" onclick="setFilter('sentiment', this)">Sentiment</button>
      </div>
    </div>

    <!-- Findings Container -->
    <div id="findingsContainer" class="findings-list">
      <!-- Populated via client-side script for instant responsiveness -->
    </div>

    <div id="emptyState" class="empty-state" style="display: none;">
      <h3>🎉 No findings match the current criteria</h3>
      <p style="margin-top: 0.5rem;">All inspected items pass this health gate or match your query.</p>
    </div>
  </div>

  <div id="toast">Copied draft to clipboard! 📋</div>

  <script id="report-data" type="application/json">
{safe_json}
  </script>

  <script>
    const reportData = JSON.parse(document.getElementById('report-data').textContent);
    let activeFilter = 'all';

    function showToast(msg) {{
      const t = document.getElementById('toast');
      t.textContent = msg || 'Copied to clipboard!';
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2200);
    }}

    function copyToClipboard(text) {{
      navigator.clipboard.writeText(text).then(() => {{
        showToast('Draft response copied to clipboard! 📋');
      }}).catch(err => {{
        showToast('Copied text!');
      }});
    }}

    function setFilter(filterName, btn) {{
      activeFilter = filterName;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filterFindings();
    }}

    function renderFindings(findings) {{
      const container = document.getElementById('findingsContainer');
      const empty = document.getElementById('emptyState');
      container.innerHTML = '';

      if (findings.length === 0) {{
        empty.style.display = 'block';
        return;
      }}
      empty.style.display = 'none';

      findings.forEach(f => {{
        const card = document.createElement('div');
        card.className = `finding-card sev-${{f.severity}}`;

        let evidenceHtml = '';
        if (f.evidence && f.evidence.length > 0) {{
          evidenceHtml = `
            <div class="evidence-box">
              <div style="font-weight: 600; margin-bottom: 0.35rem; color: #94a3b8; font-size: 0.75rem; text-transform: uppercase;">Explainability Evidence</div>
              ${{f.evidence.map(ev => `
                <div class="evidence-item">
                  <span class="evidence-name">${{escapeHtml(ev.metric_name)}}:</span>
                  <span class="evidence-val">${{escapeHtml(ev.details)}}</span>
                </div>
              `).join('')}}
            </div>
          `;
        }}

        let draftHtml = '';
        if (f.draft_response) {{
          const cleanDraft = f.draft_response.replace(/"/g, '&quot;');
          draftHtml = `
            <div class="draft-box">
              <div class="draft-header">
                <span>💬 Polite Contributor Follow-Up Draft</span>
                <button class="action-btn" onclick="copyToClipboard(\\`${{escapeJs(f.draft_response)}}\\`)">Copy Draft</button>
              </div>
              <textarea class="draft-content" rows="2" readonly>${{escapeHtml(f.draft_response)}}</textarea>
            </div>
          `;
        }}

        const itemTypeUpper = f.item_type === 'pull_request' ? 'PR' : 'Issue';

        card.innerHTML = `
          <div class="card-header">
            <div class="card-title-group">
              <span class="type-pill pill-${{f.finding_type}}">${{f.finding_type.replace('_', ' ')}}</span>
              <a href="${{f.item_url}}" target="_blank" class="item-link">${{itemTypeUpper}} #${{f.item_number}}: ${{escapeHtml(f.item_title)}}</a>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center; font-size: 0.8rem; color: #94a3b8;">
              <span>Confidence: <strong>${{Math.round(f.confidence * 100)}}%</strong></span>
              <span>•</span>
              <span style="text-transform: capitalize;">Severity: <strong>${{f.severity}}</strong></span>
            </div>
          </div>
          <div class="summary-text">${{escapeHtml(f.summary)}}</div>
          <div style="font-size: 0.85rem; color: #38bdf8;"><strong>Suggested Action:</strong> ${{escapeHtml(f.suggested_action)}}</div>
          ${{evidenceHtml}}
          ${{draftHtml}}
        `;

        container.appendChild(card);
      }});
    }}

    function filterFindings() {{
      const query = document.getElementById('searchInput').value.toLowerCase().trim();
      const filtered = (reportData.findings || []).filter(f => {{
        // Filter by category
        if (activeFilter === 'blocked_pr') {{
          if (f.finding_type !== 'ci_failure' && f.finding_type !== 'merge_conflict') return false;
        }} else if (activeFilter === 'incomplete') {{
          if (f.finding_type !== 'incomplete_issue') return false;
        }} else if (activeFilter === 'duplicate') {{
          if (f.finding_type !== 'possible_duplicate') return false;
        }} else if (activeFilter === 'stale') {{
          if (!['stale_pr', 'stale_issue', 'stale_review'].includes(f.finding_type)) return false;
        }} else if (activeFilter === 'good_first') {{
          if (f.finding_type !== 'good_first_issue') return false;
        }} else if (activeFilter === 'sentiment') {{
          if (f.finding_type !== 'community_sentiment') return false;
        }}

        // Filter by text search
        if (query) {{
          const matchTitle = (f.item_title || '').toLowerCase().includes(query);
          const matchNum = String(f.item_number).includes(query.replace('#', ''));
          const matchSummary = (f.summary || '').toLowerCase().includes(query);
          const matchType = (f.finding_type || '').toLowerCase().includes(query);
          return matchTitle || matchNum || matchSummary || matchType;
        }}
        return true;
      }});

      renderFindings(filtered);
    }}

    function escapeHtml(str) {{
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }}

    function escapeJs(str) {{
      if (!str) return '';
      return String(str)
        .replace(/\\\\/g, '\\\\\\\\')
        .replace(/`/g, '\\\\`')
        .replace(/\\$/g, '\\\\$');
    }}

    // Initial render
    renderFindings(reportData.findings || []);
  </script>
</body>
</html>
"""
    return html_template
