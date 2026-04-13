import asyncio
import hashlib
import hmac
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from github import Github

import config
from daemon.tick import tick
from memory.daily_log import get_todays_log
from memory.dream import run_autodream
from memory.memory_md import list_topics, read_memory_md, read_topic
from presence import get_autonomy_level
from state import (
    get_actions_today_count,
    get_active_project,
    get_last_dream,
    get_last_tick,
    get_recent_actions,
    list_projects,
    set_active_project,
)
from watchers.github import get_open_prs

app = FastAPI()

ROOT = Path(__file__).parent.parent

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>auto dream</title>
<script>(function(){var t=localStorage.getItem('adTheme')||'dark';document.documentElement.setAttribute('data-theme',t);})();</script>
<style>
:root {
  --bg:        #070f09;
  --bg-1:      #0b140d;
  --bg-card:   #0f1a11;
  --bg-card-2: #132016;
  --bg-hover:  #172619;
  --border:    #1c3020;
  --border-2:  #27412c;
  --text:      #b89aaa;
  --text-2:    #d4bec8;
  --text-3:    #ede0e8;
  --text-dim:  #6b4a5a;
  --green:     #a8e6be;
  --green-dim: #3a8a60;
  --green-bg:  #0a2014;
  --amber:     #f7c8a0;
  --amber-bg:  #201508;
  --red:       #f7aac8;
  --red-bg:    #210f18;
  --mono:      'Berkeley Mono', 'JetBrains Mono', ui-monospace, monospace;
}

[data-theme="light"] {
  --bg:        #f4f8f5;
  --bg-1:      #eaf2ec;
  --bg-card:   #ffffff;
  --bg-card-2: #f0f7f2;
  --bg-hover:  #e2efe5;
  --border:    #c8dece;
  --border-2:  #a8c8b4;
  --text:      #4a6858;
  --text-2:    #2a4838;
  --text-3:    #142818;
  --text-dim:  #a03060;
  --green:     #1a7040;
  --green-dim: #3a9060;
  --green-bg:  #d4eed8;
  --amber:     #9a5e1a;
  --amber-bg:  #f4e8d0;
  --red:       #c0226a;
  --red-bg:    #fcdee8;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  background: var(--bg);
  color: var(--text-2);
  font-family: var(--mono);
  font-size: 13px;
  line-height: 1.5;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--red); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── STATUSBAR ─────────────────────────────────────────────── */
.statusbar {
  position: sticky; top: 0; z-index: 100;
  display: flex; align-items: center; gap: 16px;
  height: 48px; padding: 0 24px;
  background: var(--bg-1);
  border-bottom: 1px solid var(--border);
}

.product-name {
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.18em; color: var(--red); text-transform: lowercase;
}

.daemon-status {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--text-dim);
}

.pulse-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--green);
  animation: livepulse 2.4s ease-out infinite;
}
@keyframes livepulse {
  0%   { box-shadow: 0 0 0 0   rgba(168,230,190,0.5); }
  60%  { box-shadow: 0 0 0 6px rgba(168,230,190,0); }
  100% { box-shadow: 0 0 0 0   rgba(168,230,190,0); }
}
[data-theme="light"] .pulse-dot { animation: livepulse-lt 2.4s ease-out infinite; }
@keyframes livepulse-lt {
  0%   { box-shadow: 0 0 0 0   rgba(26,112,64,0.4); }
  60%  { box-shadow: 0 0 0 6px rgba(26,112,64,0); }
  100% { box-shadow: 0 0 0 0   rgba(26,112,64,0); }
}

.tick-stamp { font-size: 11px; color: var(--text-dim); }
.sb-spacer  { flex: 1; }
.sb-actions { display: flex; align-items: center; gap: 8px; }

/* Project selector */
.project-selector { position: relative; }
.project-btn {
  display: inline-flex; align-items: center; gap: 5px;
  background: transparent; border: 1px solid var(--border-2);
  color: var(--green); padding: 4px 10px; border-radius: 4px;
  cursor: pointer; font-family: var(--mono); font-size: 11px;
  transition: border-color 0.15s;
}
.project-btn:hover { border-color: var(--green); }
.proj-arrow { font-size: 9px; color: var(--text-dim); }
.project-dropdown {
  display: none; position: absolute; top: calc(100% + 4px); right: 0;
  min-width: 220px; background: var(--bg-card);
  border: 1px solid var(--border-2); border-radius: 6px;
  z-index: 200; overflow: hidden;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.project-dropdown.open { display: block; }
.proj-item {
  display: flex; align-items: center; gap: 8px; padding: 10px 14px;
  cursor: pointer; font-size: 11px; color: var(--text-2);
  transition: background 0.1s; border-bottom: 1px solid var(--border);
}
.proj-item:hover { background: var(--bg-hover); }
.proj-item.active { color: var(--green); }
.proj-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--border-2); flex-shrink: 0; }
.proj-item.active .proj-dot { background: var(--green); }
.proj-name { flex: 1; }
.proj-repo { font-size: 10px; color: var(--text-dim); }
.proj-remove { font-size: 13px; color: var(--text-dim); cursor: pointer; padding: 0 2px; opacity: 0; transition: opacity 0.1s, color 0.1s; }
.proj-item:hover .proj-remove { opacity: 1; }
.proj-remove:hover { color: var(--red); }
.proj-add-btn {
  display: flex; align-items: center; gap: 6px; width: 100%;
  padding: 10px 14px; background: transparent; border: none;
  color: var(--text-dim); font-family: var(--mono); font-size: 11px;
  cursor: pointer; text-align: left; transition: color 0.1s, background 0.1s;
}
.proj-add-btn:hover { color: var(--green); background: var(--bg-hover); }

/* Buttons */
.theme-toggle {
  position: fixed;
  bottom: 20px;
  right: 24px;
  z-index: 200;
  background: var(--bg-card);
  border: 1px solid var(--border-2);
  color: var(--text-dim);
  padding: 5px 13px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  font-family: var(--mono);
  transition: border-color 0.15s, color 0.15s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.theme-toggle:hover { border-color: var(--text-dim); color: var(--text-2); }

.cli-btn {
  display: inline-flex; align-items: center; gap: 5px;
  background: transparent; border: 1px solid var(--border-2);
  color: var(--text); padding: 4px 12px; border-radius: 4px;
  cursor: pointer; font-family: var(--mono); font-size: 11px;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
  white-space: nowrap;
}
.cli-btn::before { content: '$'; color: var(--text-dim); margin-right: 3px; }
.cli-btn:hover { border-color: var(--red); color: var(--red); background: var(--red-bg); }
.cli-btn:disabled { opacity: 0.35; cursor: not-allowed; pointer-events: none; }
.cli-btn.dream-btn { border-color: var(--green); color: var(--green); }
.cli-btn.dream-btn::before { color: var(--green); opacity: 0.5; }
.cli-btn.dream-btn:hover { background: var(--green-bg); }

/* ── PAGE ──────────────────────────────────────────────────── */
.page {
  max-width: 860px;
  margin: 0 auto;
  padding: 28px 24px 56px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── ATTENTION STRIP ───────────────────────────────────────── */
.attention-strip {
  display: none;
  flex-direction: column;
  gap: 8px;
  background: var(--red-bg);
  border: 1px solid rgba(247,170,200,0.18);
  border-left: 3px solid var(--red);
  border-radius: 6px;
  padding: 14px 18px;
}
.attention-strip.visible { display: flex; }
.attention-header {
  font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--red); font-weight: 600; margin-bottom: 2px;
}
.attention-item {
  display: flex; align-items: center; gap: 10px;
  font-size: 12px; color: var(--text-2);
}
.attn-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--red); flex-shrink: 0; }
.attn-text { flex: 1; }
.attn-age { color: var(--text-dim); font-size: 11px; white-space: nowrap; }
.attn-action {
  font-size: 10px; color: var(--red);
  border: 1px solid rgba(247,170,200,0.3); background: transparent;
  padding: 2px 8px; border-radius: 3px; cursor: pointer;
  font-family: var(--mono); text-decoration: none; transition: background 0.15s;
}
.attn-action:hover { background: rgba(247,170,200,0.1); text-decoration: none; }

/* ── STAT CARDS ────────────────────────────────────────────── */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px 20px 16px;
}
.stat-label {
  font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--text-dim); margin-bottom: 8px;
}
.stat-value {
  font-size: 28px; font-weight: 700; color: var(--text-3); line-height: 1;
}
.stat-value.low    { color: var(--red); }
.stat-value.medium { color: var(--amber); }
.stat-value.high   { color: var(--green); }

/* ── TABS ──────────────────────────────────────────────────── */
.tab-bar {
  display: flex; gap: 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}
.tab-btn {
  padding: 10px 18px; background: transparent; border: none;
  border-bottom: 2px solid transparent; color: var(--text-dim);
  font-family: var(--mono); font-size: 11px; cursor: pointer;
  letter-spacing: 0.05em; transition: color 0.15s, border-color 0.15s;
  margin-bottom: -1px;
}
.tab-btn:hover { color: var(--text-2); }
.tab-btn.active { color: var(--green); border-bottom-color: var(--green); }

.tab-panel { display: none; }
.tab-panel.active { display: block; }

/* ── ACTIVITY ──────────────────────────────────────────────── */
.activity-list { display: flex; flex-direction: column; }
.activity-item {
  display: flex; align-items: baseline; gap: 12px;
  padding: 11px 0; border-bottom: 1px solid var(--border);
}
.activity-item:last-child { border-bottom: none; }
.activity-bullet { color: var(--text-dim); font-size: 11px; flex-shrink: 0; }
.activity-text { flex: 1; font-size: 12px; color: var(--text-2); }
.activity-age { font-size: 11px; color: var(--text-dim); white-space: nowrap; flex-shrink: 0; }
.feed-empty { padding: 36px 0; text-align: center; color: var(--text-dim); font-size: 12px; }

/* ── PRS ───────────────────────────────────────────────────── */
.pr-list { display: flex; flex-direction: column; gap: 10px; }
.pr-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-left: 3px solid var(--border);
  border-radius: 8px; padding: 16px 18px;
  display: flex; align-items: center; gap: 14px;
}
.pr-card.stale   { border-left-color: var(--red); }
.pr-card.pending { border-left-color: var(--amber); }
.pr-card.approved { border-left-color: var(--green); }
.pr-num { font-size: 11px; color: var(--text-dim); flex-shrink: 0; width: 32px; }
.pr-info { flex: 1; min-width: 0; }
.pr-title {
  font-size: 13px; color: var(--text-3);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 5px;
}
.pr-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.pr-tag {
  font-size: 10px; padding: 2px 7px; border-radius: 3px; font-weight: 500;
  background: var(--bg-card-2); border: 1px solid var(--border); color: var(--text-dim);
}
.pr-tag.stale   { color: var(--red);   border-color: rgba(247,170,200,0.3); background: var(--red-bg); }
.pr-tag.pending { color: var(--amber); border-color: rgba(247,200,160,0.3); background: var(--amber-bg); }
.pr-tag.ok      { color: var(--green); border-color: rgba(168,230,190,0.3); background: var(--green-bg); }
.pr-btns { display: flex; gap: 6px; flex-shrink: 0; }
.pr-approve-btn {
  font-family: var(--mono); font-size: 11px; padding: 5px 12px;
  background: var(--green-bg); border: 1px solid rgba(168,230,190,0.3);
  color: var(--green); border-radius: 4px; cursor: pointer; transition: border-color 0.15s;
}
.pr-approve-btn:hover { border-color: var(--green); }
.pr-approve-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.pr-link {
  font-family: var(--mono); font-size: 11px; padding: 5px 12px;
  background: transparent; border: 1px solid var(--border-2);
  color: var(--text); border-radius: 4px; text-decoration: none;
  transition: border-color 0.15s; display: inline-flex; align-items: center;
}
.pr-link:hover { border-color: var(--text); color: var(--text-3); text-decoration: none; }

/* ── MEMORY ────────────────────────────────────────────────── */
.dream-card {
  display: flex; align-items: center; gap: 20px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 18px 20px; margin-bottom: 14px;
}
.dream-block { }
.dream-lbl { font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 4px; }
.dream-num { font-size: 22px; font-weight: 700; line-height: 1; }
.dream-num.ok     { color: var(--green); }
.dream-num.warn   { color: var(--amber); }
.dream-num.urgent { color: var(--red); }
.dream-sub { font-size: 11px; color: var(--text-dim); margin-top: 4px; }
.dream-div { width: 1px; height: 36px; background: var(--border); }
.dream-spacer { flex: 1; }
.dreaming-ind {
  display: none; align-items: center; gap: 6px; font-size: 11px; color: var(--green);
}
.dreaming-ind.active { display: flex; }
.dream-spin {
  width: 10px; height: 10px; border-radius: 50%;
  border: 1.5px solid transparent; border-top-color: var(--green);
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.topic-list { display: flex; flex-direction: column; gap: 3px; }
.topic-row { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.topic-trigger {
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  cursor: pointer; font-size: 12px; color: var(--text-2);
  background: var(--bg-card); transition: background 0.1s; user-select: none;
}
.topic-trigger:hover { background: var(--bg-hover); }
.topic-trigger.open { color: var(--green); }
.topic-arrow { font-size: 9px; color: var(--text-dim); transition: transform 0.2s; flex-shrink: 0; }
.topic-trigger.open .topic-arrow { transform: rotate(90deg); }
.topic-body {
  display: none; padding: 14px 16px; font-size: 11px; line-height: 1.7;
  color: var(--text); white-space: pre-wrap;
  background: var(--bg-card-2); border-top: 1px solid var(--border);
  max-height: 220px; overflow-y: auto;
}
.topic-body.open { display: block; }

/* ── LOGS ──────────────────────────────────────────────────── */
.log-list { display: flex; flex-direction: column; }
.log-date-header {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted); padding: 0 0 12px 0; margin-bottom: 4px;
  border-bottom: 1px solid var(--border);
}
.log-item {
  display: flex; align-items: baseline; gap: 12px;
  padding: 9px 0; border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.log-item:last-child { border-bottom: none; }
.log-time { font-size: 10px; color: var(--text-dim); flex-shrink: 0; min-width: 38px; }
.log-text { color: var(--text-2); flex: 1; }

/* ── TOAST ─────────────────────────────────────────────────── */
.toast {
  position: fixed; bottom: 24px; right: 24px;
  background: var(--bg-card); border: 1px solid var(--border-2);
  border-left: 3px solid var(--green); color: var(--text-2);
  padding: 10px 16px; font-size: 11.5px; border-radius: 5px;
  opacity: 0; transform: translateY(6px);
  transition: opacity 0.2s, transform 0.2s;
  pointer-events: none; max-width: 300px; z-index: 999;
}
.toast.show { opacity: 1; transform: translateY(0); }
.toast.err  { border-left-color: var(--red); }

/* ── MODAL ─────────────────────────────────────────────────── */
.modal-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.6); z-index: 500;
  align-items: center; justify-content: center;
}
.modal-overlay.open { display: flex; }
.modal {
  background: var(--bg-card); border: 1px solid var(--border-2);
  border-radius: 8px; padding: 28px; width: 400px; max-width: 95vw;
}
.modal-title {
  font-size: 11px; font-weight: 700; color: var(--green);
  letter-spacing: 0.12em; margin-bottom: 20px; text-transform: uppercase;
}
.modal-field { margin-bottom: 16px; }
.modal-label {
  display: block; font-size: 10px; color: var(--text-dim);
  letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 6px;
}
.modal-input {
  width: 100%; background: var(--bg-1); border: 1px solid var(--border-2);
  color: var(--text-3); padding: 8px 12px; border-radius: 4px;
  font-family: var(--mono); font-size: 12px; outline: none;
  transition: border-color 0.15s;
}
.modal-input:focus { border-color: var(--green); }
.modal-hint { font-size: 10px; color: var(--text-dim); margin-top: 4px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 24px; }
.modal-cancel {
  background: transparent; border: 1px solid var(--border-2); color: var(--text);
  padding: 6px 16px; border-radius: 4px; font-family: var(--mono);
  font-size: 11px; cursor: pointer; transition: border-color 0.15s;
}
.modal-cancel:hover { border-color: var(--text); }
.modal-submit {
  background: var(--green-bg); border: 1px solid var(--green);
  color: var(--green); padding: 6px 16px; border-radius: 4px;
  font-family: var(--mono); font-size: 11px; cursor: pointer;
}
.modal-submit:hover { background: #0d2e1c; }
.modal-submit:disabled { opacity: 0.4; cursor: not-allowed; }

@media (max-width: 640px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .page { padding: 16px 14px 40px; }
}
</style>
</head>
<body>

<!-- STATUSBAR -->
<div class="statusbar">
  <span class="product-name">auto dream</span>
  <div class="daemon-status">
    <div class="pulse-dot"></div>
    <span>daemon running</span>
  </div>
  <span class="tick-stamp" id="last-tick"></span>
  <div class="sb-spacer"></div>
  <div class="sb-actions">
    <div class="project-selector" id="proj-selector">
      <button class="project-btn" id="proj-btn" onclick="toggleProjDropdown()">
        <span id="proj-active-name">project</span>
        <span class="proj-arrow">▼</span>
      </button>
      <div class="project-dropdown" id="proj-dropdown">
        <div class="proj-item" style="color:var(--text-dim);cursor:default">loading...</div>
      </div>
    </div>
    <button class="cli-btn" onclick="triggerTick(this)">tick</button>
    <button class="cli-btn dream-btn" onclick="triggerDream(this)">dream --now</button>
  </div>
</div>

<!-- PAGE -->
<div class="page">

  <!-- NEEDS ATTENTION -->
  <div class="attention-strip" id="attention-strip">
    <div class="attention-header">needs attention</div>
    <div id="attention-items"></div>
  </div>

  <!-- STAT CARDS -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-label">autonomy</div>
      <div class="stat-value" id="stat-autonomy">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">actions today</div>
      <div class="stat-value" id="stat-actions">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">memory topics</div>
      <div class="stat-value" id="stat-topics">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">open prs</div>
      <div class="stat-value" id="stat-prs">—</div>
    </div>
  </div>

  <!-- TABS -->
  <div>
    <div class="tab-bar">
      <button class="tab-btn active" id="tab-btn-activity" onclick="switchTab('activity')">activity</button>
      <button class="tab-btn" id="tab-btn-prs" onclick="switchTab('prs')">pull requests</button>
      <button class="tab-btn" id="tab-btn-memory" onclick="switchTab('memory')">memory</button>
      <button class="tab-btn" id="tab-btn-logs" onclick="switchTab('logs')">logs</button>
    </div>

    <div class="tab-panel active" id="tab-activity">
      <div class="activity-list" id="activity-list">
        <div class="feed-empty">loading...</div>
      </div>
    </div>

    <div class="tab-panel" id="tab-prs">
      <div class="pr-list" id="pr-list">
        <div class="feed-empty">loading...</div>
      </div>
    </div>

    <div class="tab-panel" id="tab-memory">
      <div class="dream-card">
        <div class="dream-block">
          <div class="dream-lbl">next dream</div>
          <div class="dream-num ok" id="countdown-val">—</div>
        </div>
        <div class="dream-div"></div>
        <div class="dream-block">
          <div class="dream-lbl">last dream</div>
          <div class="dream-sub" id="last-dream" style="font-size:13px;color:var(--text-2)">—</div>
        </div>
        <div class="dream-spacer"></div>
        <div class="dreaming-ind" id="dreaming-ind">
          <div class="dream-spin"></div>
          <span>dreaming</span>
        </div>
      </div>
      <div class="topic-list" id="topic-list">
        <div class="feed-empty">no topics yet</div>
      </div>
    </div>

    <div class="tab-panel" id="tab-logs">
      <div class="log-list" id="log-list">
        <div class="feed-empty">loading...</div>
      </div>
    </div>
  </div>

</div>

<div class="toast" id="toast"></div>
<button class="theme-toggle" id="theme-btn" onclick="toggleTheme()">light</button>

<!-- ADD PROJECT MODAL -->
<div class="modal-overlay" id="proj-modal-overlay" onclick="closeAddProject(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-title">add project</div>
    <div class="modal-field">
      <label class="modal-label" for="mp-name">project name</label>
      <input class="modal-input" id="mp-name" type="text" placeholder="my-project" autocomplete="off" />
    </div>
    <div class="modal-field">
      <label class="modal-label" for="mp-repo">github repo</label>
      <input class="modal-input" id="mp-repo" type="text" placeholder="username/repo" autocomplete="off" />
      <div class="modal-hint">format: username/reponame</div>
    </div>
    <div class="modal-field">
      <label class="modal-label" for="mp-path">local repo path</label>
      <input class="modal-input" id="mp-path" type="text" placeholder="/Users/you/projects/repo" autocomplete="off" />
      <div class="modal-hint">absolute path on disk</div>
    </div>
    <div class="modal-actions">
      <button class="modal-cancel" onclick="closeAddProject()">cancel</button>
      <button class="modal-submit" id="mp-submit" onclick="submitAddProject()">add project</button>
    </div>
  </div>
</div>

<script>
let _toastTimer = null;

function showToast(msg, err) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (err ? ' err' : '');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => t.classList.remove('show'), 3200);
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function timeAgo(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);
  if (d > 0) return d + 'd ago';
  if (h > 0) return h + 'h ago';
  if (m > 0) return m + 'm ago';
  return 'just now';
}

function fmtTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
}

function fmtShort(iso) {
  if (!iso) return 'never';
  const d = new Date(iso);
  return d.toLocaleDateString([], {month:'short',day:'numeric'})
       + ' ' + d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
}

function fmtAction(raw) {
  if (/^comment:pr#[0-9]+$/.test(raw)) return null;
  const prMatch = raw.match(/^comment:pr#([0-9]+):(.+)$/);
  if (prMatch) return `PR #${prMatch[1]}: ${prMatch[2].trim()}`;
  return raw;
}

// ── TABS ──────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-btn-' + name).classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
}

// ── DATA LOADERS ──────────────────────────────────────────────
async function loadStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();

    const ts = d.last_tick ? 'tick ' + fmtTime(d.last_tick) : 'no tick yet';
    document.getElementById('last-tick').textContent = ts;

    const av = document.getElementById('stat-autonomy');
    av.textContent = d.autonomy || '—';
    av.className = 'stat-value ' + (d.autonomy || '');

    document.getElementById('stat-actions').textContent = d.actions_today ?? '—';

    const list = document.getElementById('activity-list');
    const rows = (d.recent_actions || [])
      .map(a => ({ ts: a.timestamp, text: fmtAction(a.action) }))
      .filter(a => a.text !== null);

    list.innerHTML = rows.length
      ? rows.map(a =>
          `<div class="activity-item">
            <span class="activity-bullet">›</span>
            <span class="activity-text">${esc(a.text)}</span>
            <span class="activity-age">${timeAgo(a.ts)}</span>
          </div>`
        ).join('')
      : '<div class="feed-empty">no actions yet</div>';
  } catch(e) { console.error(e); }
}

async function loadPRs() {
  try {
    const r = await fetch('/api/prs');
    const prs = await r.json();
    document.getElementById('stat-prs').textContent = prs.length;

    // needs attention strip
    const urgent = prs.filter(p => p.is_stale || p.review_status === 'changes_requested');
    const strip = document.getElementById('attention-strip');
    if (urgent.length) {
      strip.classList.add('visible');
      document.getElementById('attention-items').innerHTML = urgent.map(p => {
        const reason = p.review_status === 'changes_requested'
          ? 'changes requested'
          : `${p.days_open}d open, no review`;
        return `<div class="attention-item">
          <div class="attn-dot"></div>
          <span class="attn-text">PR #${p.number}: ${esc(p.title)}</span>
          <span class="attn-age">${reason}</span>
          <a class="attn-action" href="${esc(p.url)}" target="_blank">review</a>
        </div>`;
      }).join('');
    } else {
      strip.classList.remove('visible');
    }

    // pr tab
    const list = document.getElementById('pr-list');
    if (!prs.length) {
      list.innerHTML = '<div class="feed-empty">no open pull requests</div>';
      return;
    }
    list.innerHTML = prs.map(pr => {
      const cardCls = pr.is_stale ? 'stale'
                    : pr.review_status === 'approved' ? 'approved' : 'pending';
      const reviewLabel = pr.review_status === 'approved' ? 'approved'
                        : pr.review_status === 'changes_requested' ? 'changes requested'
                        : pr.review_status === 'pending' ? 'pending review' : 'no review';
      const reviewCls = pr.review_status === 'approved' ? 'ok'
                      : pr.review_status === 'changes_requested' ? 'stale' : 'pending';
      return `<div class="pr-card ${cardCls}">
        <span class="pr-num">#${pr.number}</span>
        <div class="pr-info">
          <div class="pr-title">${esc(pr.title)}</div>
          <div class="pr-meta">
            <span class="pr-tag">${pr.days_open}d open</span>
            <span class="pr-tag ${reviewCls}">${reviewLabel}</span>
            ${pr.is_stale ? '<span class="pr-tag stale">stale</span>' : ''}
          </div>
        </div>
        <div class="pr-btns">
          <button class="pr-approve-btn" onclick="approvePR(${pr.number},this)">approve</button>
          <a class="pr-link" href="${esc(pr.url)}" target="_blank">github ↗</a>
        </div>
      </div>`;
    }).join('');
  } catch(e) { console.error(e); }
}

async function loadMemory() {
  try {
    const r = await fetch('/api/memory');
    const d = await r.json();

    const cv = document.getElementById('countdown-val');
    cv.textContent = d.next_dream || '—';
    const hrs = parseInt((d.next_dream || '99h').split('h')[0], 10);
    cv.className = 'dream-num ' + (hrs < 2 ? 'urgent' : hrs < 6 ? 'warn' : 'ok');

    document.getElementById('last-dream').textContent = fmtShort(d.last_dream);

    const topics = d.topic_files || [];
    document.getElementById('stat-topics').textContent = topics.length;

    const tlist = document.getElementById('topic-list');
    tlist.innerHTML = topics.length
      ? topics.map((t, i) =>
          `<div class="topic-row">
            <div class="topic-trigger" id="tt-${i}" onclick="toggleTopic(${i})">
              <span class="topic-arrow">▶</span>
              <span>${esc(t.name)}.md</span>
            </div>
            <div class="topic-body" id="tb-${i}">${esc(t.content)}</div>
          </div>`
        ).join('')
      : '<div class="feed-empty">no topics yet</div>';

    // logs tab
    const raw = (d.todays_log || '').trim();
    const logList = document.getElementById('log-list');
    if (!raw) {
      logList.innerHTML = '<div class="feed-empty">no log entries yet</div>';
    } else {
      const today = new Date();
      const dateStr = today.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
      const lines = raw.split('\\n').filter(l => l.trim());
      const entries = lines.map(l => {
        const m = l.match(/^- ([0-9]{2}:[0-9]{2}) (.+)$/);
        return `<div class="log-item">
          <span class="log-time">${esc(m ? m[1] : '')}</span>
          <span class="log-text">${esc(m ? m[2] : l.replace(/^- /, ''))}</span>
        </div>`;
      }).join('');
      logList.innerHTML = `<div class="log-date-header">${esc(dateStr)}</div>` + entries;
    }
  } catch(e) { console.error(e); }
}

function toggleTopic(i) {
  document.getElementById('tt-' + i).classList.toggle('open');
  document.getElementById('tb-' + i).classList.toggle('open');
}

async function approvePR(num, btn) {
  btn.disabled = true; btn.textContent = 'posting...';
  try {
    await fetch('/api/approve/' + num, {method:'POST'});
    btn.textContent = 'approved ✓';
    showToast('commented on PR #' + num);
  } catch(e) {
    btn.textContent = 'error';
    showToast('failed to post comment', true);
  }
}

async function triggerTick(btn) {
  btn.disabled = true; showToast('running tick...');
  try {
    await fetch('/api/tick', {method:'POST'});
    showToast('tick complete'); await loadStatus();
  } catch(e) { showToast('tick failed', true); }
  finally { btn.disabled = false; }
}

async function triggerDream(btn) {
  btn.disabled = true;
  const ind = document.getElementById('dreaming-ind');
  ind.classList.add('active'); showToast('dream started...');
  try {
    await fetch('/api/dream', {method:'POST'});
    setTimeout(async () => {
      ind.classList.remove('active'); btn.disabled = false;
      await loadMemory(); showToast('dream complete');
    }, 8000);
  } catch(e) {
    ind.classList.remove('active'); btn.disabled = false;
    showToast('dream failed', true);
  }
}

function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next);
  localStorage.setItem('adTheme', next);
  document.getElementById('theme-btn').textContent = next === 'light' ? 'dark' : 'light';
}

// ── PROJECT SWITCHER ──────────────────────────────────────────
let _projOpen = false;

function toggleProjDropdown() {
  _projOpen = !_projOpen;
  document.getElementById('proj-dropdown').classList.toggle('open', _projOpen);
}

document.addEventListener('click', (e) => {
  if (!document.getElementById('proj-selector').contains(e.target)) {
    _projOpen = false;
    document.getElementById('proj-dropdown').classList.remove('open');
  }
});

async function loadProjects() {
  try {
    const r = await fetch('/api/projects');
    const d = await r.json();
    const active = d.active;
    document.getElementById('proj-active-name').textContent = active || 'project';
    const dropdown = document.getElementById('proj-dropdown');
    const items = (d.projects || []).map(p => {
      const safeName = esc(p.name).replace(/'/g, '&#39;');
      return `<div class="proj-item ${p.name === active ? 'active' : ''}" onclick="switchProject('${safeName}')">
        <div class="proj-dot"></div>
        <div style="flex:1;min-width:0">
          <div class="proj-name">${esc(p.name)}</div>
          <div class="proj-repo">${esc(p.github_repo)}</div>
        </div>
        <span class="proj-remove" title="remove" onclick="removeProject(event,'${safeName}')">×</span>
      </div>`;
    }).join('');
    dropdown.innerHTML = items +
      `<button class="proj-add-btn" onclick="openAddProject()">+ add project</button>`;
  } catch(e) { console.error(e); }
}

async function switchProject(name) {
  _projOpen = false;
  document.getElementById('proj-dropdown').classList.remove('open');
  try {
    const r = await fetch('/api/projects/switch', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name})
    });
    const d = await r.json();
    if (d.ok) { showToast('switched to ' + name); await loadProjects(); refresh(); }
    else { showToast('project not found', true); }
  } catch(e) { showToast('switch failed', true); }
}

function openAddProject() {
  _projOpen = false;
  document.getElementById('proj-dropdown').classList.remove('open');
  ['mp-name','mp-repo','mp-path'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('proj-modal-overlay').classList.add('open');
  setTimeout(() => document.getElementById('mp-name').focus(), 50);
}

function closeAddProject(e) {
  if (e && e.target !== document.getElementById('proj-modal-overlay')) return;
  document.getElementById('proj-modal-overlay').classList.remove('open');
}

async function submitAddProject() {
  const name = document.getElementById('mp-name').value.trim();
  const github_repo = document.getElementById('mp-repo').value.trim();
  const repo_path = document.getElementById('mp-path').value.trim();
  if (!name || !github_repo || !repo_path) { showToast('all fields required', true); return; }
  const btn = document.getElementById('mp-submit');
  btn.disabled = true; btn.textContent = 'adding...';
  try {
    const r = await fetch('/api/projects/add', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, github_repo, repo_path})
    });
    const d = await r.json();
    if (d.ok) {
      document.getElementById('proj-modal-overlay').classList.remove('open');
      showToast('project added: ' + name);
      await loadProjects();
    } else { showToast(d.error || 'failed to add project', true); }
  } catch(e) { showToast('error adding project', true); }
  finally { btn.disabled = false; btn.textContent = 'add project'; }
}

async function removeProject(e, name) {
  e.stopPropagation();
  try {
    const r = await fetch('/api/projects/remove', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name})
    });
    const d = await r.json();
    if (d.ok) { showToast('removed ' + name); await loadProjects(); }
    else { showToast(d.error || 'cannot remove', true); }
  } catch(e) { showToast('error removing project', true); }
}

document.querySelectorAll('.modal-input').forEach(inp => {
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') submitAddProject(); });
});

document.getElementById('theme-btn').textContent =
  (localStorage.getItem('adTheme') || 'dark') === 'light' ? '●' : '◑';

function refresh() { loadStatus(); loadPRs(); loadMemory(); }

loadProjects();
refresh();
setInterval(refresh, 30000);
setInterval(loadProjects, 60000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD_HTML


@app.get("/api/status")
async def status():
    recent = get_recent_actions(10)
    today_count = get_actions_today_count()
    last_action = recent[0]["action"] if recent else ""

    return {
        "last_tick": get_last_tick(),
        "autonomy": get_autonomy_level(),
        "last_action": last_action,
        "actions_today": today_count,
        "recent_actions": recent,
    }


@app.get("/api/prs")
async def prs():
    pr_list = await get_open_prs()
    active = get_active_project()
    github_repo = active.get("github_repo", config.GITHUB_REPO)
    for pr in pr_list:
        pr["url"] = f"https://github.com/{github_repo}/pull/{pr['number']}"
        pr.pop("diff", None)
    return pr_list


@app.get("/api/memory")
async def memory():
    now = datetime.now(timezone.utc)
    tomorrow_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    delta = tomorrow_midnight - now
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    topic_files = [
        {"name": name, "content": read_topic(name)}
        for name in sorted(list_topics())
    ]

    return {
        "memory_index": read_memory_md(),
        "topic_files": topic_files,
        "todays_log": get_todays_log(),
        "last_dream": get_last_dream(),
        "next_dream": f"{hours}h {minutes}m",
    }


@app.get("/api/projects")
async def projects():
    active = get_active_project()
    return {
        "projects": list_projects(),
        "active": active.get("name", ""),
    }


@app.post("/api/projects/switch")
async def switch_project(request: Request):
    body = await request.json()
    name = body.get("name", "")
    ok = set_active_project(name)
    return {"ok": ok}


@app.post("/api/projects/add")
async def add_project(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    github_repo = (body.get("github_repo") or "").strip()
    repo_path = (body.get("repo_path") or "").strip()
    if not name or not github_repo or not repo_path:
        return {"ok": False, "error": "name, github_repo, and repo_path are required"}
    from state import _load_projects, _PROJECTS_JSON
    projects = _load_projects()
    if any(p["name"] == name for p in projects):
        return {"ok": False, "error": f"project '{name}' already exists"}
    projects.append({"name": name, "repo_path": repo_path, "github_repo": github_repo})
    import json as _json
    _PROJECTS_JSON.write_text(_json.dumps(projects, indent=2))
    set_active_project(name)
    return {"ok": True}


@app.post("/api/projects/remove")
async def remove_project(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    from state import _load_projects, _PROJECTS_JSON, get_active_project as _gap
    projects = _load_projects()
    if len(projects) <= 1:
        return {"ok": False, "error": "cannot remove the only project"}
    active = _gap()
    filtered = [p for p in projects if p["name"] != name]
    if len(filtered) == len(projects):
        return {"ok": False, "error": "project not found"}
    import json as _json
    _PROJECTS_JSON.write_text(_json.dumps(filtered, indent=2))
    if active.get("name") == name:
        set_active_project(filtered[0]["name"])
    return {"ok": True}


@app.post("/api/approve/{pr_number}")
async def approve(pr_number: int):
    gh = Github(config.GITHUB_TOKEN)
    active = get_active_project()
    repo = gh.get_repo(active.get("github_repo", config.GITHUB_REPO))
    pr = repo.get_pull(pr_number)
    pr.create_issue_comment("auto dream: reviewed and approved by operator")
    return {"ok": True}


@app.post("/api/tick")
async def trigger_tick():
    await tick()
    return {"ok": True}


@app.post("/api/dream")
async def dream():
    def _run():
        asyncio.run(run_autodream())

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "dream started"}


# Events that should trigger an immediate tick
_PR_ACTIONS = {"opened", "synchronize", "reopened", "ready_for_review", "closed"}
_REVIEW_ACTIONS = {"submitted"}


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    body = await request.body()

    # verify HMAC signature when a secret is configured
    if config.GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="missing X-Hub-Signature-256")
        expected = "sha256=" + hmac.new(
            config.GITHUB_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="invalid signature")

    event = x_github_event or ""

    if event not in ("pull_request", "pull_request_review", "push"):
        return {"ok": True, "scheduled": False, "reason": "event not watched"}

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    action = payload.get("action", "")

    if event == "pull_request" and action not in _PR_ACTIONS:
        return {"ok": True, "scheduled": False, "reason": f"pr action '{action}' ignored"}

    if event == "pull_request_review" and action not in _REVIEW_ACTIONS:
        return {"ok": True, "scheduled": False, "reason": f"review action '{action}' ignored"}

    if event == "push":
        ref = payload.get("ref", "")
        default_branch = payload.get("repository", {}).get("default_branch", "main")
        if ref != f"refs/heads/{default_branch}":
            return {"ok": True, "scheduled": False, "reason": "push not to default branch"}

    background_tasks.add_task(tick)
    return {"ok": True, "scheduled": True, "event": event, "action": action}
