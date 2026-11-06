// MarketTrace Dashboard Application Logic

let currentRunType = "faulted";
let selectedDeliveryId = null;

document.addEventListener("DOMContentLoaded", () => {
  initKeyboardNavigation();
  loadRunOverview("faulted");
  loadTimeline("faulted");
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
    targetPanel.classList.add("active");
  }
}

async function loadRunOverview(type) {
  currentRunType = type;
  try {
    const res = await fetch(`/api/run-overview?type=${type}`);
    const data = await res.json();

    const stateEl = document.getElementById("metric-state");
    stateEl.textContent = data.current_book_state;
    stateEl.className = "metric-value status-badge " + 
      (data.current_book_state === "VALID" ? "status-valid" : "status-incomplete");

    document.getElementById("metric-total").textContent = data.total_events;
    document.getElementById("metric-counts").textContent = `${data.accepted_count} / ${data.rejected_count}`;
    
    document.getElementById("metric-bid").textContent = data.best_bid_ticks 
      ? `$${(data.best_bid_ticks / 100).toLocaleString(undefined, {minimumFractionDigits: 2})}` 
      : "EMPTY";

    document.getElementById("metric-ask").textContent = data.best_ask_ticks 
      ? `$${(data.best_ask_ticks / 100).toLocaleString(undefined, {minimumFractionDigits: 2})}` 
      : "EMPTY";

    document.getElementById("metric-mid").textContent = data.midpoint_ticks 
      ? `$${(data.midpoint_ticks / 100).toLocaleString(undefined, {minimumFractionDigits: 2})}` 
      : "EMPTY";

    document.getElementById("metric-spread").textContent = data.spread_ticks 
      ? `${data.spread_ticks} ticks ($${(data.spread_ticks / 100).toFixed(2)})` 
      : "EMPTY";

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
      const div = document.createElement("div");
      div.className = "timeline-item";
      
      const isFault = item.decision_code !== "ACCEPTED";
      const isResync = item.message_kind === "SNAPSHOT" && idx > 10;

      if (isFault) div.classList.add("fault");
      if (isResync) div.classList.add("resync");

      let tagClass = "tag-accepted";
      if (item.decision_code === "DROPPED_DUPLICATE") tagClass = "tag-duplicate";
      else if (isFault) tagClass = "tag-rejected";

      div.innerHTML = `
        <div>
          <span class="item-id">${item.delivery_id}</span>
          <span style="color: var(--text-secondary); margin-left: 6px;">${item.side} ${item.message_kind}</span>
        </div>
        <div>
          <span class="item-tag ${tagClass}">${item.decision_code}</span>
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
    const faultItem = data.timeline.find(i => i.decision_code === "REJECTED_OUT_OF_SEQUENCE");
    if (faultItem) {
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
    const res = await fetch(`/api/incident-detail?delivery_id=${deliveryId}`);
    const data = await res.json();

    const ev = data.event || {};
    const dec = data.decision || {};
    const chain = data.depgraph_chain || [];

    let chainHtml = chain.map(node => `
      <div class="flow-node ${node.status === 'VALID' ? 'state-valid' : 'state-incomplete'}">
        <div>
          <div class="node-title">${node.stage}</div>
          <div class="node-desc">${node.desc}</div>
        </div>
        <div>
          <span class="badge ${node.status === 'VALID' ? 'badge-parity' : 'badge-synthetic'}">${node.status}</span>
        </div>
      </div>
    `).join("");

    contentEl.innerHTML = `
      <div class="inspector-section">
        <h4>Delivery Identification</h4>
        <div style="font-family: var(--font-mono); font-size: 0.9rem; margin-bottom: 8px;">
          <strong>ID:</strong> ${data.delivery_id} | 
          <strong>Kind:</strong> ${ev.message_kind} | 
          <strong>Sequence:</strong> ${ev.provider_sequence ?? 'N/A'}
        </div>
      </div>

      <div class="inspector-section">
        <h4>C++ Engine Decision & Quality State</h4>
        <pre class="code-block">${JSON.stringify(dec, null, 2)}</pre>
      </div>

      <div class="inspector-section">
        <h4>Raw Event Envelope Payload</h4>
        <pre class="code-block">${JSON.stringify(ev, null, 2)}</pre>
      </div>

      <div class="inspector-section">
        <h4>DepGraph Invalidation Lineage</h4>
        <div class="flow-chain">
          ${chainHtml}
        </div>
      </div>
    `;

  } catch (err) {
    contentEl.innerHTML = `<p style="color: var(--accent-red);">Error loading inspector details: ${err.message}</p>`;
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

      const cleanMid = row.clean_midpoint ? `$${(row.clean_midpoint / 100).toFixed(2)}` : "--";
      const damMid = row.damaged_midpoint ? `$${(row.damaged_midpoint / 100).toFixed(2)}` : "--";
      const recMid = row.recovered_midpoint ? `$${(row.recovered_midpoint / 100).toFixed(2)}` : "--";

      tr.innerHTML = `
        <td style="font-family: var(--font-mono); font-weight: 600;">${row.delivery_id}</td>
        <td><span class="item-tag tag-accepted">${row.clean_status}</span> ${cleanMid}</td>
        <td><span class="item-tag ${row.damaged_status === 'VALID' ? 'tag-accepted' : 'tag-rejected'}">${row.damaged_status}</span> ${damMid}</td>
        <td><span class="item-tag tag-accepted">${row.recovered_status}</span> ${recMid}</td>
        <td><span class="badge-rev">Rev ${row.revision}</span></td>
        <td>${row.is_affected ? '<span style="color: var(--accent-red); font-weight: 600;">YES (Recovered)</span>' : '<span style="color: var(--accent-green);">NO (Preserved)</span>'}</td>
        <td style="color: var(--text-secondary); font-size: 0.8rem;">${row.explanation}</td>
      `;

      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Error loading recovery comparison:", err);
  }
}
