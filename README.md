# MaintainerOps 🛡️

> **Spend less time sorting repository noise and more time building software.**

**MaintainerOps** is an open-source, human-first maintenance and explainable triage toolkit for GitHub repositories.

Rather than delegating maintenance decisions to opaque AI bots that spam contributors or automatically close valid bugs, MaintainerOps computes **transparent, evidence-backed recommendations**:
- 🖥️ **Interactive Web Dashboard:** Modern, glassmorphism maintainer dashboard with real-time health grading, live rule engine simulator, and 1-click polite draft responses.
- 📈 **Repository Health Index (0-100 & Letter Grades A+ to F):** Multi-factor health scoring across PR velocity, issue completeness, backlog freshness, and community urgency.
- 🔍 **Duplicate Issue Detection:** Powered by TF-IDF & Cosine Similarity with explicit matching keyword evidence.
- 📋 **Completeness Validation:** Detects missing reproduction steps, missing environment details, or missing stack traces.
- 🚦 **PR Blocker Analysis:** Aggregates failing CI check runs, merge conflicts, and stale review states.
- ⏳ **Stale Lifecycle Tracking:** Flags dormant issues and differentiates whether a PR is waiting on maintainer review or contributor updates.
- 🌱 **Good First Issue Detector:** Discovers newcomer-friendly issues ready for mentorship and onboarding.
- 🚨 **Community Sentiment & Outage Alerting:** Detects production-down urgency and high-friction threads for empathetic de-escalation.
- 💬 **Respectful Human-First Drafts:** Generates polite, contributor-friendly draft replies with 1-click clipboard copy.
- 🆓 **Zero Cost:** Operates 100% locally or inside GitHub Actions without requiring paid AI API tokens.

---

## ⚡ Quick Start

### Installation

```bash
pip install maintainerops
```

### 1. Launch the Interactive Web Dashboard

Launch the local web dashboard and REST API to interactively inspect repository health, simulate rule thresholds, and manage triage actions:

```bash
maintainerops dashboard
```
> Starts a threaded local web server at `http://127.0.0.1:8080` and automatically opens your browser.

### 2. View Terminal Health Scorecard

Generate an executive terminal health scorecard with gauges and primary bottlenecks:

```bash
maintainerops health fastapi/fastapi
# Or run offline with a fixture:
maintainerops health tests/fixtures/enterprise_repo.json
```

### 3. Scan a Public Repository or Offline Fixture

```bash
# Scan directly using GitHub API
maintainerops scan fastapi/fastapi

# Save report as interactive HTML, Markdown, or JSON
maintainerops scan fastapi/fastapi --format html --output report.html
maintainerops scan fastapi/fastapi --format markdown --output report.md
maintainerops scan fastapi/fastapi --format json --output report.json
```

### 4. Zero-Token Offline Testing (Mock Fixture)

You can run MaintainerOps against local JSON data without making any live network calls or consuming GitHub rate limits:

```bash
maintainerops scan tests/fixtures/enterprise_repo.json
maintainerops draft tests/fixtures/enterprise_repo.json 102
```

### 5. Export Standalone Self-Contained Dashboard

Generate a standalone, zero-dependency HTML dashboard for GitHub Pages, CI artifacts, or team sharing:

```bash
maintainerops export-dashboard tests/fixtures/enterprise_repo.json -o dashboard.html
```

---

## 🤖 GitHub Action Integration

Add `.github/workflows/triage.yml` to your repository:

```yaml
name: "MaintainerOps Triage"

on:
  workflow_dispatch:
  schedule:
    - cron: '0 8 * * 1' # Runs every Monday at 08:00 UTC

jobs:
  triage:
    runs-on: ubuntu-latest
    permissions:
      issues: read
      pull-requests: read
      checks: read
    steps:
      - uses: actions/checkout@v4
      - name: Run MaintainerOps
        uses: MaintainerOps/maintainerops@v0.2.0
        with:
          repository: ${{ github.repository }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          publish-summary: true
```

---

## 📐 Architecture & Philosophy

```
GitHub Repository / Offline Fixture
            │
    [ GitHub Adapter ] (Token Auth / ETag Caching / Rate Limit Guard)
            │
    [ Central Rule Engine ]
       ├─ Completeness Check (Repro steps, environment, code blocks)
       ├─ Duplicate Matching (TF-IDF + Cosine distance + Token overlap)
       ├─ PR Health & CI Diagnostics (Check runs, mergeable state)
       ├─ Stale Lifecycle (Review state: waiting on maintainer vs author)
       ├─ Good First Issue Discovery (Mentorship candidates)
       ├─ Community Urgency & Sentiment (Outage alerts & friction)
       └─ Repository Health Calculator (0-100 Score & A+ to F Grade)
            │
    [ Multi-Channel Presenters ]
       ├─ 🖥️ Interactive Web Dashboard & REST API (`maintainerops dashboard`)
       ├─ 🌐 Standalone Single-File HTML Dashboard (`--format html`)
       ├─ 📊 Executive Terminal Scorecard (`maintainerops health`)
       ├─ 💬 Polite Draft Inspector (`maintainerops draft`)
       └─ 📄 GitHub Action Step Summaries & JSON Exporters
```

MaintainerOps adheres to **safe operating modes**:
- `report`: Read repository data and output a structured report (Default).
- `suggest`: Draft labels and replies without publishing them.
- `review`: Present findings for maintainer verification.

No destructive write operations or blind automated issue closures occur.

---

## 📄 License

MaintainerOps is open source under the [MIT License](LICENSE).
