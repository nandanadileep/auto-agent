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
    get_last_dream,
    get_last_tick,
    get_recent_actions,
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
  --bg-2:      #0f1a11;
  --bg-3:      #132016;
  --bg-hover:  #172619;
  --border:    #1c3020;
  --border-2:  #27412c;
  --text:      #b89aaa;
  --text-2:    #d4bec8;
  --text-3:    #ede0e8;
  --text-dim:  #8a3a58;
  --green:     #a8e6be;
  --green-dim: #5aaa80;
  --green-bg:  #0a2014;
  --amber:     #f7c8a0;
  --amber-bg:  #201508;
  --red:       #f7aac8;
  --red-bg:    #210f18;
  --blue:      #a8d4f7;
  --blue-bg:   #0a1620;
  --purple:    #a8e6be;
  --mono:      'Berkeley Mono', 'TX-02', 'Fira Code', 'Cascadia Code', 'JetBrains Mono', ui-monospace, monospace;
}

[data-theme="light"] {
  --bg:        #f2f8f4;
  --bg-1:      #e8f2eb;
  --bg-2:      #ddeae0;
  --bg-3:      #d2e2d6;
  --bg-hover:  #c8dace;
  --border:    #a8ccb4;
  --border-2:  #88b098;
  --text:      #3a6048;
  --text-2:    #1e4030;
  --text-3:    #102818;
  --text-dim:  #b02460;
  --green:     #18763c;
  --green-dim: #106030;
  --green-bg:  #ccecd8;
  --amber:     #9a5e1a;
  --amber-bg:  #f4e8d0;
  --red:       #c0226a;
  --red-bg:    #fcdee8;
  --blue:      #1a5aac;
  --blue-bg:   #d0e8fc;
  --purple:    #18763c;
}

[data-theme="light"] .pulse-dot {
  animation: livepulse-light 2.4s ease-out infinite;
}
@keyframes livepulse-light {
  0%   { box-shadow: 0 0 0 0   rgba(24, 118, 60, 0.4); }
  60%  { box-shadow: 0 0 0 6px rgba(24, 118, 60, 0); }
  100% { box-shadow: 0 0 0 0   rgba(24, 118, 60, 0); }
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  background: var(--bg);
  color: var(--text-2);
  font-family: var(--mono);
  font-size: 14px;
  line-height: 1.5;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--red); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── STATUSBAR ─────────────────────────────────────────────── */
.statusbar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 20px;
  height: 44px;
  padding: 0 20px;
  background: var(--bg-1);
  border-bottom: 1px solid var(--border);
}

.product-name {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: var(--red);
  text-transform: lowercase;
}

.daemon-status {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  color: var(--text-dim);
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 0 rgba(168, 230, 190, 0.5);
  animation: livepulse 2.4s ease-out infinite;
}
@keyframes livepulse {
  0%   { box-shadow: 0 0 0 0   rgba(168, 230, 190, 0.5); }
  60%  { box-shadow: 0 0 0 6px rgba(168, 230, 190, 0); }
  100% { box-shadow: 0 0 0 0   rgba(168, 230, 190, 0); }
}

.tick-stamp {
  font-size: 11px;
  color: var(--text-dim);
  padding-left: 4px;
}

.sb-spacer { flex: 1; }

.sb-actions { display: flex; align-items: center; gap: 8px; }

.theme-toggle {
  background: transparent;
  border: 1px solid var(--border-2);
  color: var(--text-dim);
  width: 30px;
  height: 28px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 14px;
  font-family: var(--mono);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.15s, color 0.15s;
}
.theme-toggle:hover { border-color: var(--red); color: var(--red); }

/* ── CLI BUTTONS ───────────────────────────────────────────── */
.cli-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: transparent;
  border: 1px solid var(--border-2);
  color: var(--text);
  padding: 4px 11px;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.02em;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
  white-space: nowrap;
}
.cli-btn::before { content: '$'; color: var(--text-dim); margin-right: 2px; }
.cli-btn:hover { border-color: var(--red); color: var(--red); background: var(--red-bg); }
.cli-btn:active { opacity: 0.7; }
.cli-btn:disabled { opacity: 0.35; cursor: not-allowed; pointer-events: none; }

.cli-btn.dream-btn { border-color: var(--green); color: var(--green); }
.cli-btn.dream-btn::before { color: var(--green); opacity: 0.5; }
.cli-btn.dream-btn:hover { background: var(--green-bg); border-color: var(--green); }

.approve-btn {
  display: inline-flex;
  align-items: center;
  background: var(--green-bg);
  border: 1px solid rgba(34,212,122,0.25);
  color: var(--green);
  padding: 3px 9px;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--mono);
  font-size: 11px;
  transition: border-color 0.15s, background 0.15s;
}
.approve-btn:hover { border-color: var(--green); background: #0d2e1c; }
.approve-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.ghost-btn {
  display: inline-flex;
  align-items: center;
  background: transparent;
  border: 1px solid var(--border-2);
  color: var(--text);
  padding: 3px 9px;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--mono);
  font-size: 11px;
  text-decoration: none;
  transition: border-color 0.15s, color 0.15s;
}
.ghost-btn:hover { border-color: var(--text); color: var(--text-3); text-decoration: none; }

/* ── LAYOUT ────────────────────────────────────────────────── */
.workspace {
  display: grid;
  grid-template-columns: 1fr 340px;
  grid-template-rows: auto 1fr;
  gap: 0;
  height: calc(100vh - 44px);
  overflow: hidden;
}

.col-main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border);
}

.col-side {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── STAT ROW ──────────────────────────────────────────────── */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.stat-cell {
  padding: 14px 16px;
  border-right: 1px solid var(--border);
}
.stat-cell:last-child { border-right: none; }

.stat-label {
  font-size: 9.5px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-dim);
  margin-bottom: 5px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-3);
  line-height: 1;
}

.stat-value.low    { color: var(--green); }
.stat-value.medium { color: var(--amber); }
.stat-value.high   { color: var(--red); }

/* ── PANEL CHROME ──────────────────────────────────────────── */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 14px;
  background: var(--bg-1);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.panel-title {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--text-dim);
}

.panel-meta {
  font-size: 11px;
  color: var(--text-dim);
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ── ACTIONS FEED ──────────────────────────────────────────── */
.actions-feed {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border-2) transparent;
}

.action-line {
  display: flex;
  align-items: flex-start;
  gap: 0;
  border-bottom: 1px solid var(--border);
  border-left: 2px solid transparent;
  transition: border-left-color 0.15s, background 0.15s;
}
.action-line:last-child { border-bottom: none; }
.action-line:hover {
  border-left-color: var(--red);
  background: var(--bg-hover);
}

.action-prompt {
  flex-shrink: 0;
  width: 14px;
  padding: 8px 0 8px 12px;
  color: var(--text-dim);
  font-size: 11px;
  user-select: none;
}

.action-ts {
  flex-shrink: 0;
  width: 175px;
  padding: 8px 12px;
  font-size: 11.5px;
  color: var(--text-dim);
  white-space: nowrap;
  border-right: 1px solid var(--border);
}

.action-body {
  padding: 8px 14px;
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.5;
  word-break: break-word;
}

.feed-empty {
  padding: 20px 14px;
  color: var(--text-dim);
  font-size: 11px;
}

/* ── SIDE PANELS (scroll independently) ───────────────────── */
.side-scroll {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border-2) transparent;
}

/* ── PR CARDS ──────────────────────────────────────────────── */
.pr-item {
  padding: 11px 14px;
  border-bottom: 1px solid var(--border);
}
.pr-item:last-child { border-bottom: none; }

.pr-header {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin-bottom: 5px;
}

.pr-num {
  font-size: 11px;
  color: var(--text-dim);
  flex-shrink: 0;
}

.pr-title {
  font-size: 12px;
  color: var(--text-3);
  line-height: 1.4;
  word-break: break-word;
}

.pr-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 8px;
}

.tag {
  font-size: 9.5px;
  padding: 1px 6px;
  border-radius: 2px;
  border: 1px solid var(--border-2);
  color: var(--text-dim);
  letter-spacing: 0.03em;
}
.tag.t-stale   { border-color: rgba(247,170,200,0.4); color: var(--red);   background: var(--red-bg); }
.tag.t-ok      { border-color: rgba(168,230,190,0.4); color: var(--green); background: var(--green-bg); }
.tag.t-pending { border-color: rgba(247,200,160,0.4); color: var(--amber); background: var(--amber-bg); }

.pr-btns { display: flex; gap: 6px; }

/* ── MEMORY SECTION ────────────────────────────────────────── */
.memory-wrap {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-top: 1px solid var(--border);
  flex: 1;
  min-height: 0;
}

.dream-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 14px;
  background: var(--bg-1);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  font-size: 11px;
}

.dream-bar-label { color: var(--text-dim); }

#countdown-val {
  font-weight: 700;
  transition: color 0.5s;
}
.countdown-ok     { color: var(--text-2); }
.countdown-warn   { color: var(--amber); }
.countdown-urgent { color: var(--red); animation: livepulse-text 1.5s ease-in-out infinite; }

@keyframes livepulse-text {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
}

.dreaming-indicator {
  display: none;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--green);
}
.dreaming-indicator.active { display: flex; }
.dream-spin {
  width: 8px; height: 8px;
  border: 1px solid var(--green);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.memory-body {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border-2) transparent;
}

/* ── TOPIC ACCORDION ───────────────────────────────────────── */
.topic-row {
  border-bottom: 1px solid var(--border);
}
.topic-row:last-child { border-bottom: none; }

.topic-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  cursor: pointer;
  user-select: none;
  background: transparent;
  transition: background 0.12s;
}
.topic-trigger:hover { background: var(--bg-hover); }

.topic-arrow {
  font-size: 9px;
  color: var(--text-dim);
  width: 10px;
  flex-shrink: 0;
  transition: transform 0.18s;
}
.topic-trigger.open .topic-arrow { transform: rotate(90deg); }

.topic-filename {
  font-size: 12px;
  color: var(--green);
}

.topic-body {
  display: none;
  padding: 10px 14px 12px 32px;
  background: var(--bg);
  border-top: 1px solid var(--border);
  white-space: pre-wrap;
  font-size: 11.5px;
  color: var(--text-2);
  line-height: 1.65;
  max-height: 260px;
  overflow-y: auto;
}
.topic-body.open { display: block; }

/* ── LOG VIEWER ────────────────────────────────────────────── */
.log-viewer {
  font-size: 11.5px;
  line-height: 1.55;
}

.log-line {
  display: flex;
  align-items: baseline;
  gap: 0;
}
.log-line:nth-child(even) { background: var(--bg-2); }

.log-ln {
  flex-shrink: 0;
  width: 36px;
  padding: 3px 8px 3px 14px;
  text-align: right;
  color: var(--text-dim);
  font-size: 10px;
  user-select: none;
  border-right: 1px solid var(--border);
}

.log-text {
  padding: 3px 12px;
  color: var(--text-2);
  word-break: break-word;
}

/* ── TOAST ─────────────────────────────────────────────────── */
.toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 9px 14px;
  background: var(--bg-2);
  border: 1px solid var(--border-2);
  border-left: 3px solid var(--green);
  color: var(--text-2);
  font-size: 11.5px;
  border-radius: 3px;
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 0.2s, transform 0.2s;
  pointer-events: none;
  max-width: 320px;
  z-index: 999;
}
.toast.show { opacity: 1; transform: translateY(0); }
.toast.err  { border-left-color: var(--red); }


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
  <span class="tick-stamp" id="last-tick">no tick yet</span>
  <div class="sb-spacer"></div>
  <div class="sb-actions">
    <button class="theme-toggle" id="theme-btn" onclick="toggleTheme()" title="Toggle theme">◑</button>
    <button class="cli-btn" onclick="triggerTick(this)">tick</button>
    <button class="cli-btn dream-btn" onclick="triggerDream(this)">dream --now</button>
  </div>
</div>

<!-- WORKSPACE GRID -->
<div class="workspace">

  <!-- LEFT COLUMN -->
  <div class="col-main">

    <!-- STAT ROW -->
    <div class="stat-row">
      <div class="stat-cell">
        <div class="stat-label">autonomy</div>
        <div class="stat-value" id="stat-autonomy">—</div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">actions today</div>
        <div class="stat-value" id="stat-actions">—</div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">topics</div>
        <div class="stat-value" id="stat-topics">—</div>
      </div>
      <div class="stat-cell" style="border-right:none">
        <div class="stat-label">prs open</div>
        <div class="stat-value" id="stat-prs">—</div>
      </div>
    </div>

    <!-- ACTIONS FEED -->
    <div class="panel-header">
      <span class="panel-title">action log</span>
      <span class="panel-meta" id="actions-meta"></span>
    </div>
    <div class="actions-feed" id="actions-feed">
      <div class="feed-empty">loading...</div>
    </div>

    <!-- LOG VIEWER -->
    <div class="panel-header" style="border-top:1px solid var(--border)">
      <span class="panel-title">today's log</span>
      <span class="panel-meta" id="log-meta"></span>
    </div>
    <div class="actions-feed" id="log-viewer" style="flex:0 0 200px;border-top:none">
      <div class="feed-empty">loading...</div>
    </div>

  </div>

  <!-- RIGHT COLUMN -->
  <div class="col-side">

    <!-- OPEN PRS -->
    <div class="panel-header">
      <span class="panel-title">open pull requests</span>
    </div>
    <div class="side-scroll" style="flex:0 0 auto;max-height:45%">
      <div id="pr-list"><div class="feed-empty">loading...</div></div>
    </div>

    <!-- MEMORY / TOPICS -->
    <div class="memory-wrap">
      <div class="dream-bar">
        <span class="dream-bar-label">next dream</span>
        <span id="countdown-val" class="countdown-ok">—</span>
        <div style="flex:1"></div>
        <div class="dreaming-indicator" id="dreaming-ind">
          <div class="dream-spin"></div>
          <span>dreaming</span>
        </div>
        <span class="dream-bar-label">last:</span>
        <span id="last-dream" style="color:var(--text-2)">—</span>
      </div>
      <div class="panel-header" style="border-top:none">
        <span class="panel-title">memory topics</span>
        <span class="panel-meta" id="topics-meta"></span>
      </div>
      <div class="memory-body" id="topic-list">
        <div class="feed-empty">loading...</div>
      </div>
    </div>

  </div>
</div>

<div class="toast" id="toast"></div>

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

function fmtTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
}

function fmtShort(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString([], {month:'short',day:'numeric'})
       + ' ' + d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
}

function fmtFull(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'});
}

// returns null to skip the row, or a display string
function fmtAction(raw) {
  // bare dedup key with no message — skip entirely
  if (/^comment:pr#[0-9]+$/.test(raw)) return null;
  // comment:pr#N:message → "PR #N — message"
  const prMatch = raw.match(/^comment:pr#([0-9]+):(.+)$/);
  if (prMatch) return `PR #${prMatch[1]} — ${prMatch[2].trim()}`;
  return raw;
}

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

    const feed = document.getElementById('actions-feed');
    const meta = document.getElementById('actions-meta');
    if (!d.recent_actions || d.recent_actions.length === 0) {
      feed.innerHTML = '<div class="feed-empty">no actions yet</div>';
      meta.textContent = '';
    } else {
      const rows = d.recent_actions
        .map(a => ({ ts: a.timestamp, text: fmtAction(a.action) }))
        .filter(a => a.text !== null);
      meta.textContent = rows.length + ' shown';
      feed.innerHTML = rows.map(a =>
        `<div class="action-line">
          <span class="action-prompt">&gt;</span>
          <span class="action-ts">${esc(fmtFull(a.ts))}</span>
          <span class="action-body">${esc(a.text)}</span>
        </div>`
      ).join('') || '<div class="feed-empty">no actions yet</div>';
    }
  } catch(e) { console.error(e); }
}

async function loadPRs() {
  try {
    const r = await fetch('/api/prs');
    const prs = await r.json();
    document.getElementById('stat-prs').textContent = prs.length;

    const list = document.getElementById('pr-list');
    if (!prs.length) {
      list.innerHTML = '<div class="feed-empty">no open prs</div>';
      return;
    }
    list.innerHTML = prs.map(pr => {
      const reviewCls = pr.review_status === 'approved' ? 't-ok'
                      : pr.review_status === 'changes_requested' ? 't-stale'
                      : pr.review_status === 'pending' ? 't-pending' : '';
      const reviewLbl = pr.review_status === 'approved' ? 'approved'
                      : pr.review_status === 'changes_requested' ? 'changes requested'
                      : pr.review_status === 'pending' ? 'pending review' : 'no review';
      const stale = pr.is_stale ? `<span class="tag t-stale">stale</span>` : '';
      return `<div class="pr-item">
        <div class="pr-header">
          <span class="pr-num">#${pr.number}</span>
          <span class="pr-title">${esc(pr.title)}</span>
        </div>
        <div class="pr-tags">
          <span class="tag">${pr.days_open}d open</span>
          <span class="tag ${reviewCls}">${reviewLbl}</span>
          ${stale}
        </div>
        <div class="pr-btns">
          <button class="approve-btn" onclick="approvePR(${pr.number},this)">approve</button>
          <a class="ghost-btn" href="${esc(pr.url)}" target="_blank">github ↗</a>
        </div>
      </div>`;
    }).join('');
  } catch(e) { console.error(e); }
}

async function loadMemory() {
  try {
    const r = await fetch('/api/memory');
    const d = await r.json();

    // countdown coloring
    const cv = document.getElementById('countdown-val');
    cv.textContent = d.next_dream || '—';
    const hrs = parseInt((d.next_dream || '99h').split('h')[0], 10);
    cv.className = hrs < 2 ? 'countdown-urgent' : hrs < 6 ? 'countdown-warn' : 'countdown-ok';

    document.getElementById('last-dream').textContent =
      d.last_dream ? fmtShort(d.last_dream) : 'never';

    // topics
    const topics = d.topic_files || [];
    document.getElementById('stat-topics').textContent = topics.length;
    document.getElementById('topics-meta').textContent = topics.length + ' files';

    const tlist = document.getElementById('topic-list');
    if (!topics.length) {
      tlist.innerHTML = '<div class="feed-empty">no topics yet</div>';
    } else {
      tlist.innerHTML = topics.map((t, i) =>
        `<div class="topic-row">
          <div class="topic-trigger" id="tt-${i}" onclick="toggleTopic(${i})">
            <span class="topic-arrow">▶</span>
            <span class="topic-filename">${esc(t.name)}.md</span>
          </div>
          <div class="topic-body" id="tb-${i}">${esc(t.content)}</div>
        </div>`
      ).join('');
    }

    // log viewer
    const logEl = document.getElementById('log-viewer');
    const logMeta = document.getElementById('log-meta');
    const raw = (d.todays_log || '').trim();
    if (!raw) {
      logEl.innerHTML = '<div class="feed-empty">no log entries yet</div>';
      logMeta.textContent = '';
    } else {
      const lines = raw.split('\\n').filter(l => l.trim());
      logMeta.textContent = lines.length + ' entries';
      logEl.innerHTML = '<div class="log-viewer">' +
        lines.map((l, i) =>
          `<div class="log-line">
            <span class="log-ln">${i + 1}</span>
            <span class="log-text">${esc(l.replace(/^- /, ''))}</span>
          </div>`
        ).join('') +
      '</div>';
      logEl.scrollTop = logEl.scrollHeight;
    }
  } catch(e) { console.error(e); }
}

function toggleTopic(i) {
  const trigger = document.getElementById('tt-' + i);
  const body = document.getElementById('tb-' + i);
  trigger.classList.toggle('open');
  body.classList.toggle('open');
}

async function approvePR(num, btn) {
  btn.disabled = true;
  btn.textContent = 'posting...';
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
  btn.disabled = true;
  showToast('running tick...');
  try {
    await fetch('/api/tick', {method:'POST'});
    showToast('tick complete');
    await loadStatus();
  } catch(e) {
    showToast('tick failed', true);
  } finally {
    btn.disabled = false;
  }
}

async function triggerDream(btn) {
  btn.disabled = true;
  const ind = document.getElementById('dreaming-ind');
  ind.classList.add('active');
  showToast('dream started...');
  try {
    await fetch('/api/dream', {method:'POST'});
    setTimeout(async () => {
      ind.classList.remove('active');
      btn.disabled = false;
      await loadMemory();
      showToast('dream complete');
    }, 8000);
  } catch(e) {
    ind.classList.remove('active');
    btn.disabled = false;
    showToast('dream failed', true);
  }
}

function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next);
  localStorage.setItem('adTheme', next);
  document.getElementById('theme-btn').textContent = next === 'light' ? '●' : '◑';
}

function refresh() { loadStatus(); loadPRs(); loadMemory(); }

// sync toggle icon to saved theme
document.getElementById('theme-btn').textContent =
  (localStorage.getItem('adTheme') || 'dark') === 'light' ? '●' : '◑';

refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD_HTML


@app.get("/api/status")
async def status():
    memory_path = ROOT / config.MEMORY_MD_PATH
    memory_lines = []
    if memory_path.exists():
        memory_lines = memory_path.read_text().splitlines()[:20]

    recent = get_recent_actions(10)
    today_count = get_actions_today_count()
    last_action = recent[0]["action"] if recent else ""

    return {
        "last_tick": get_last_tick(),
        "autonomy": get_autonomy_level(),
        "last_action": last_action,
        "actions_today": today_count,
        "memory_summary": memory_lines,
        "recent_actions": recent,
    }


@app.get("/api/prs")
async def prs():
    pr_list = await get_open_prs()
    for pr in pr_list:
        pr["url"] = f"https://github.com/{config.GITHUB_REPO}/pull/{pr['number']}"
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


@app.post("/api/approve/{pr_number}")
async def approve(pr_number: int):
    gh = Github(config.GITHUB_TOKEN)
    repo = gh.get_repo(config.GITHUB_REPO)
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
