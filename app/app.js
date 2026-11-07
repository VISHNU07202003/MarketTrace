// MarketTrace Dashboard Application Logic

let currentRunType = "damaged";
let selectedDeliveryId = null;
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, ch => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[ch]));

document.addEventListener("DOMContentLoaded", () => {
  initKeyboardNavigation();
  loadRunOverview("damaged");
  loadRecoveryComparison();
});

function initKeyboardNavigation() {
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    if (e.key === "1") switchView("overview");
    else if (e.key === "2") switchView("incident");
    else if (e.key === "3") switchView("recovery");
  });
}

function switchView(viewName) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".view-panel").forEach(panel => panel.classList.remove("active"));

  const targetTab = document.getElementById(`tab-${viewName}`);
  const targetPanel = document.getElementById(`view-${viewName}`);

  if (targetTab && targetPanel) {
    targetTab.classList.add("active");
    targetTab.setAttribute("aria-selected", "true");
    document.querySelectorAll(".tab-btn").forEach(btn => {
      if (btn !== targetTab) btn.setAttribute("aria-selected", "false");
    });
    targetPanel.classList.add("active");
  }
}

async function loadRunOverview(type) {
  currentRunType = type;
  try {
    const res = await fetch(`/api/run-overview?type=${type}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Overview unavailable");

    document.getElementById("badge-source").textContent = data.record_source;
    loadTimeline(type);

    const stateEl = document.getElementById("metric-state");
    stateEl.textContent = data.current_book_state;
    stateEl.className = "metric-value status-badge " + 
      (data.current_book_state === "VALID" ? "status-valid" : "status-incomplete");

    document.getElementById("metric-total").textContent = data.total_events;
    document.getElementById("metric-counts").textContent = `${data.accepted_count} / ${data.rejected_count}`;
    
    document.getElementById("metric-bid").textContent = data.current_book_state === "VALID" && data.best_bid_ticks !== null
      ? `$${(data.best_bid_ticks / 100).toLocaleString(undefined, {minimumFractionDigits: 2})}` 
      : "EMPTY";

    document.getElementById("metric-ask").textContent = data.current_book_state === "VALID" && data.best_ask_ticks !== null
      ? `$${(data.best_ask_ticks / 100).toLocaleString(undefined, {minimumFractionDigits: 2})}` 
      : "EMPTY";

    document.getElementById("metric-mid").textContent = data.current_book_state === "VALID" && data.midpoint_half_ticks !== null
      ? `$${(data.midpoint_half_ticks / 200).toLocaleString(undefined, {minimumFractionDigits: 3, maximumFractionDigits: 3})}`
      : "WITHHELD";

    document.getElementById("metric-spread").textContent = data.current_book_state === "VALID" && data.spread_ticks !== null
      ? `${data.spread_ticks} ticks ($${(data.spread_ticks / 100).toFixed(2)})` 
      : "WITHHELD";

  } catch (err) {
    console.error("Error loading run overview:", err);
  }
}

async function loadTimeline(type) {
  try {
    const res = await fetch(`/api/timeline?type=${type}`);
    const data = await res.json();
    const listEl = document.getElementById("timeline-list");
    listEl.innerHTML = "";

    data.timeline.forEach((item, idx) => {
      const div = document.createElement("button");
      div.type = "button";
      div.className = "timeline-item";
      
      const isFault = item.decision_code !== "ACCEPTED" || item.resulting_book_state === "INCOMPLETE";
      const isResync = item.message_kind === "SNAPSHOT" && idx > 10;

      if (isFault) div.classList.add("fault");
      if (isResync) div.classList.add("resync");

      let tagClass = "tag-accepted";
      if (item.decision_code === "DROPPED_DUPLICATE") tagClass = "tag-duplicate";
      else if (isFault) tagClass = "tag-rejected";

      div.innerHTML = `
        <div>
          <span class="item-id">${escapeHtml(item.delivery_id)}</span>
          <span style="color: var(--text-secondary); margin-left: 6px;">${escapeHtml(item.side)} ${escapeHtml(item.message_kind)}</span>
        </div>
        <div>
          <span class="item-tag ${tagClass}">${escapeHtml(item.decision_code)}</span>
        </div>
      `;

      div.onclick = () => {
        document.querySelectorAll(".timeline-item").forEach(el => el.classList.remove("selected"));
        div.classList.add("selected");
        inspectDelivery(item.delivery_id);
      };

      listEl.appendChild(div);
    });

    // Auto-select first fault or first item
    const faultItem = data.timeline.find(i => i.delivery_id === "inc_0061");
    if (faultItem) {
      const element = [...listEl.children].find(el => el.querySelector(".item-id")?.textContent === faultItem.delivery_id);
      element?.classList.add("selected");
      inspectDelivery(faultItem.delivery_id);
    } else if (data.timeline.length > 0) {
      inspectDelivery(data.timeline[0].delivery_id);
    }

  } catch (err) {
    console.error("Error loading timeline:", err);
  }
}

async function inspectDelivery(deliveryId) {
  selectedDeliveryId = deliveryId;
  const contentEl = document.getElementById("inspector-content");
  contentEl.innerHTML = "<p>Loading inspector data...</p>";

  try {
    const res = await fetch(`/api/incident-detail?type=${encodeURIComponent(currentRunType)}&delivery_id=${encodeURIComponent(deliveryId)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Incident unavailable");

    const ev = data.event || {};
    const dec = data.decision || {};
    const chain = data.depgraph_chain || [];
    const snap = data.nearest_snapshot;
    const classification = data.source_classification || "NORMAL_DELIVERY";
    const injected = data.injected_fault_info;

    let chainHtml = chain.map(node => `
      <div class="flow-node ${node.status === 'VALID' ? 'state-valid' : 'state-incomplete'}">
        <div>
          <div class="node-title">${escapeHtml(node.stage)} <span style="font-size: 0.75rem; color: var(--text-secondary); font-weight: normal;">[${escapeHtml(node.units)}]</span></div>
          <div class="node-desc">${escapeHtml(node.desc)}</div>
          <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 3px; font-family: var(--font-mono);">
            Window: [${node.time_window ? node.time_window[0] : 0}, ${node.time_window ? node.time_window[1] : 0}] ns
          </div>
        </div>
        <div>
          <span class="badge ${node.status === 'VALID' ? 'badge-parity' : 'badge-synthetic'}">${escapeHtml(node.status)}</span>
        </div>
      </div>
    `).join("");

    let snapshotNotice = snap ? `
      <div style="margin-top: 6px; padding: 6px 10px; background: rgba(56, 189, 248, 0.1); border-left: 3px solid #38bdf8; font-size: 0.8rem;">
        <strong>Nearest Known-Good Snapshot Anchor:</strong> ${escapeHtml(snap.delivery_id)} (Seq: ${escapeHtml(snap.provider_sequence ?? 'N/A')}, Time: ${escapeHtml(snap.receive_time_ns)} ns)
      </div>
    ` : "";

    let faultNotice = injected ? `
      <div style="margin-top: 6px; padding: 6px 10px; background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; font-size: 0.8rem;">
        <strong>Injected Fault Scenario:</strong> ${escapeHtml(injected.fault_type)} — <em>${escapeHtml(injected.comment)}</em>
      </div>
    ` : "";

    contentEl.innerHTML = `
      <div class="inspector-section">
        <h4>Delivery Identification & Provenance</h4>
        <div style="font-family: var(--font-mono); font-size: 0.9rem; margin-bottom: 8px;">
          <strong>ID:</strong> ${escapeHtml(data.delivery_id)} |
          <strong>Kind:</strong> ${escapeHtml(ev.message_kind)} |
          <strong>Sequence:</strong> ${escapeHtml(ev.provider_sequence ?? 'N/A')} |
          <span class="badge ${classification === 'SYNTHETIC_FAULT_INJECTION' ? 'badge-synthetic' : 'badge-engine'}">${escapeHtml(classification)}</span>
        </div>
        <div style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-secondary);">
          <div><strong>Source Receive Time:</strong> ${ev.receive_time_ns} ns</div>
          <div><strong>Engine Replay Time:</strong> ${ev.replay_time_ns} ns</div>
        </div>
        ${faultNotice}
        ${snapshotNotice}
      </div>

      <div class="inspector-section">
        <h4>${escapeHtml(data.record_source)} Decision & Quality State</h4>
        <pre class="code-block">${escapeHtml(JSON.stringify(dec, null, 2))}</pre>
      </div>

      <div class="inspector-section">
        <h4>Raw Event Envelope Payload</h4>
        <pre class="code-block">${escapeHtml(JSON.stringify(ev, null, 2))}</pre>
      </div>

      <div class="inspector-section">
        <h4>Local 11-sample volatility</h4>
        <p>${escapeHtml(data.volatility_result?.status ?? "NO UPDATE SAMPLE")}: ${data.volatility_result?.numeric_value == null ? "withheld" : Number(data.volatility_result.numeric_value).toExponential(5)}</p>
      </div>

      <div class="inspector-section">
        <h4>Typed DepGraph dependency path</h4>
        <div class="flow-chain">
          ${chainHtml}
        </div>
      </div>
    `;

  } catch (err) {
    contentEl.innerHTML = `<p style="color: var(--accent-red);">Error loading inspector details: ${escapeHtml(err.message)}</p>`;
  }
}

async function loadRecoveryComparison() {
  try {
    const res = await fetch("/api/recovery-comparison");
    const data = await res.json();
    const tbody = document.getElementById("comparison-tbody");
    tbody.innerHTML = "";

    data.comparison.forEach(row => {
      const tr = document.createElement("tr");

      const fmt = value => value === null ? "—" : value.toExponential(4);

      tr.innerHTML = `
        <td style="font-family: var(--font-mono); font-weight: 600;">${escapeHtml(row.delivery_id)}</td>
        <td><span class="item-tag tag-accepted">${row.clean_status}</span> ${fmt(row.clean_value)}</td>
        <td><span class="item-tag ${row.damaged_status === 'VALID' ? 'tag-accepted' : 'tag-rejected'}">${row.damaged_status}</span> ${fmt(row.damaged_value)}</td>
        <td><span class="item-tag tag-accepted">${row.recovered_status}</span> ${fmt(row.recovered_value)}</td>
        <td title="Synthetic event time">[${row.window_start_ns}, ${row.window_end_ns}]</td>
        <td>${row.is_affected ? '<span style="color: var(--accent-red); font-weight: 600;">YES (Recovered)</span>' : '<span style="color: var(--accent-green);">NO (Preserved)</span>'}</td>
        <td style="color: var(--text-secondary); font-size: 0.8rem;">${escapeHtml(row.explanation)}</td>
      `;

      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Error loading recovery comparison:", err);
  }
}
