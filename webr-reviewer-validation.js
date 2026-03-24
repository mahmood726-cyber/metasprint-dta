(() => {
  const config = window.__webrValidationConfig;
  if (!config || window.__webrValidationMounted) {
    return;
  }
  window.__webrValidationMounted = true;

  const helpers = {
    parseNumber(value) {
      if (value == null) {
        return NaN;
      }
      const cleaned = String(value).replace(/,/g, "").replace(/[^0-9.+-]/g, "");
      return cleaned ? Number(cleaned) : NaN;
    },
    text(selector, root = document) {
      return root.querySelector(selector)?.textContent?.trim() ?? "";
    },
    html(selector, root = document) {
      return root.querySelector(selector)?.innerHTML ?? "";
    },
    rows(selector, root = document) {
      return Array.from(root.querySelectorAll(selector));
    },
    sleep(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    },
    async waitFor(predicate, timeoutMs = 10000, intervalMs = 100) {
      const start = Date.now();
      while (Date.now() - start < timeoutMs) {
        try {
          if (await predicate()) {
            return true;
          }
        } catch (error) {
          // Ignore transient DOM states while polling.
        }
        await helpers.sleep(intervalMs);
      }
      throw new Error(`Timed out after ${timeoutMs}ms waiting for validation preconditions.`);
    },
    rString(value) {
      return `"${String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r/g, "\\r").replace(/\n/g, "\\n")}"`;
    },
    rVector(values) {
      return `c(${values.map((value) => {
        if (typeof value === "string") {
          return helpers.rString(value);
        }
        if (typeof value === "boolean") {
          return value ? "TRUE" : "FALSE";
        }
        if (value == null || Number.isNaN(value)) {
          return "NA";
        }
        return String(value);
      }).join(", ")})`;
    },
  };

  const root = document.createElement("section");
  root.setAttribute("aria-label", "WebR validation");
  root.innerHTML = `
    <style>
      .webr-validation-panel {
        position: fixed;
        right: 16px;
        bottom: 16px;
        width: min(420px, calc(100vw - 32px));
        max-height: min(70vh, 720px);
        overflow: hidden;
        z-index: 2147483000;
        border-radius: 16px;
        border: 1px solid rgba(15, 23, 42, 0.18);
        box-shadow: 0 24px 60px rgba(15, 23, 42, 0.22);
        background: rgba(255, 255, 255, 0.96);
        color: #0f172a;
        font: 13px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        backdrop-filter: blur(10px);
      }
      .webr-validation-panel * {
        box-sizing: border-box;
      }
      .webr-validation-panel[data-collapsed="true"] .webr-validation-body {
        display: none;
      }
      .webr-validation-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        border-bottom: 1px solid rgba(15, 23, 42, 0.08);
        background: linear-gradient(135deg, #0f172a, #1e293b);
        color: #f8fafc;
      }
      .webr-validation-badge {
        flex: 0 0 auto;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 999px;
        background: linear-gradient(135deg, #0ea5e9, #0284c7);
        font-weight: 700;
      }
      .webr-validation-title {
        flex: 1 1 auto;
        min-width: 0;
      }
      .webr-validation-title strong {
        display: block;
        font-size: 13px;
      }
      .webr-validation-title span {
        display: block;
        font-size: 11px;
        color: rgba(248, 250, 252, 0.75);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .webr-validation-actions {
        display: flex;
        gap: 8px;
      }
      .webr-validation-button {
        appearance: none;
        border: 0;
        border-radius: 10px;
        padding: 8px 10px;
        cursor: pointer;
        font: inherit;
        font-weight: 600;
        color: #0f172a;
        background: #e2e8f0;
      }
      .webr-validation-button-primary {
        background: #38bdf8;
      }
      .webr-validation-body {
        padding: 12px 14px 14px;
        overflow: auto;
        max-height: calc(min(70vh, 720px) - 58px);
      }
      .webr-validation-summary {
        margin-bottom: 12px;
        padding: 10px 12px;
        border-radius: 12px;
        background: #f8fafc;
        border: 1px solid rgba(15, 23, 42, 0.08);
      }
      .webr-validation-summary p {
        margin: 0;
      }
      .webr-validation-summary p + p {
        margin-top: 6px;
      }
      .webr-validation-status {
        font-weight: 700;
      }
      .webr-validation-status-pass {
        color: #166534;
      }
      .webr-validation-status-fail {
        color: #991b1b;
      }
      .webr-validation-status-run {
        color: #0f172a;
      }
      .webr-validation-list {
        display: grid;
        gap: 10px;
      }
      .webr-validation-item {
        border-radius: 12px;
        border: 1px solid rgba(15, 23, 42, 0.08);
        background: #fff;
        padding: 10px 12px;
      }
      .webr-validation-item[data-state="pass"] {
        border-color: rgba(22, 101, 52, 0.25);
        background: rgba(240, 253, 244, 0.95);
      }
      .webr-validation-item[data-state="fail"] {
        border-color: rgba(153, 27, 27, 0.22);
        background: rgba(254, 242, 242, 0.95);
      }
      .webr-validation-item-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 6px;
      }
      .webr-validation-item-header strong {
        font-size: 13px;
      }
      .webr-validation-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 56px;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
      }
      .webr-validation-pill-pass {
        color: #166534;
        background: rgba(34, 197, 94, 0.14);
      }
      .webr-validation-pill-fail {
        color: #991b1b;
        background: rgba(239, 68, 68, 0.14);
      }
      .webr-validation-pill-run {
        color: #075985;
        background: rgba(56, 189, 248, 0.14);
      }
      .webr-validation-note {
        margin: 0;
        color: #334155;
      }
      .webr-validation-time {
        margin-top: 8px;
        font-size: 11px;
        color: #64748b;
      }
      @media (prefers-color-scheme: dark) {
        .webr-validation-panel {
          background: rgba(15, 23, 42, 0.96);
          color: #e2e8f0;
          border-color: rgba(148, 163, 184, 0.2);
        }
        .webr-validation-body {
          background: rgba(15, 23, 42, 0.96);
        }
        .webr-validation-summary,
        .webr-validation-item {
          background: rgba(15, 23, 42, 0.78);
          border-color: rgba(148, 163, 184, 0.16);
        }
        .webr-validation-item[data-state="pass"] {
          background: rgba(20, 83, 45, 0.35);
        }
        .webr-validation-item[data-state="fail"] {
          background: rgba(127, 29, 29, 0.28);
        }
        .webr-validation-button {
          color: #0f172a;
        }
        .webr-validation-note,
        .webr-validation-time {
          color: #cbd5e1;
        }
      }
    </style>
    <div class="webr-validation-panel" data-collapsed="false">
      <div class="webr-validation-header">
        <div class="webr-validation-badge">R</div>
        <div class="webr-validation-title">
          <strong>WebR Validation</strong>
          <span>${config.appName || document.title || "Dashboard checks"}</span>
        </div>
        <div class="webr-validation-actions">
          <button type="button" class="webr-validation-button webr-validation-button-primary" data-action="run">Run</button>
          <button type="button" class="webr-validation-button" data-action="toggle">Hide</button>
        </div>
      </div>
      <div class="webr-validation-body">
        <div class="webr-validation-summary">
          <p class="webr-validation-status webr-validation-status-run" data-role="status">Idle</p>
          <p data-role="intro">${config.intro || "Runs reproducibility checks in WebR against the live page state."}</p>
          <p class="webr-validation-time" data-role="time">Not run yet.</p>
        </div>
        <div class="webr-validation-list" data-role="results"></div>
      </div>
    </div>
  `;

  document.body.appendChild(root);

  const panel = root.querySelector(".webr-validation-panel");
  const runButton = root.querySelector('[data-action="run"]');
  const toggleButton = root.querySelector('[data-action="toggle"]');
  const statusEl = root.querySelector('[data-role="status"]');
  const timeEl = root.querySelector('[data-role="time"]');
  const resultsEl = root.querySelector('[data-role="results"]');

  let webRPromise = null;
  let runInFlight = false;
  const debugState = {
    appName: config.appName || document.title || "Dashboard checks",
    phase: "idle",
    updatedAt: new Date().toISOString(),
    attempt: 0,
  };
  window.__webrValidationState = debugState;

  function setPhase(phase, extra = {}) {
    debugState.phase = phase;
    debugState.updatedAt = new Date().toISOString();
    Object.assign(debugState, extra);
  }

  function setStatus(kind, message) {
    statusEl.textContent = message;
    statusEl.className = `webr-validation-status ${
      kind === "pass"
        ? "webr-validation-status-pass"
        : kind === "fail"
          ? "webr-validation-status-fail"
          : "webr-validation-status-run"
    }`;
  }

  function setRunState(running) {
    runInFlight = running;
    runButton.disabled = running;
    runButton.textContent = running ? "Running..." : "Run";
  }

  function makeItem(title, state, detail) {
    const item = document.createElement("article");
    item.className = "webr-validation-item";
    item.dataset.state = state;
    item.innerHTML = `
      <div class="webr-validation-item-header">
        <strong>${title}</strong>
        <span class="webr-validation-pill ${
          state === "pass"
            ? "webr-validation-pill-pass"
            : state === "fail"
              ? "webr-validation-pill-fail"
              : "webr-validation-pill-run"
        }">${state}</span>
      </div>
      <p class="webr-validation-note">${detail}</p>
    `;
    return item;
  }

  function timeoutAfter(label, timeoutMs) {
    return new Promise((_, reject) => {
      window.setTimeout(() => {
        reject(new Error(`${label} timed out after ${timeoutMs}ms.`));
      }, timeoutMs);
    });
  }

  async function withTimeout(label, factory, timeoutMs) {
    return Promise.race([factory(), timeoutAfter(label, timeoutMs)]);
  }

  async function ensureWebR() {
    if (!webRPromise) {
      webRPromise = (async () => {
        const timeoutMs = Number(config.webRTimeoutMs) > 0 ? Number(config.webRTimeoutMs) : 90000;
        const maxAttempts = Number(config.webRAttempts) > 0 ? Number(config.webRAttempts) : 1;
        let lastError = null;

        for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
          setPhase("loading-webr", { attempt });
          try {
            const { WebR } = await withTimeout(
              "WebR module import",
              () => import("https://webr.r-wasm.org/latest/webr.mjs"),
              timeoutMs
            );
            const instance = new WebR();
            await withTimeout("WebR initialization", () => instance.init(), timeoutMs);
            setPhase("webr-ready", { attempt });
            return instance;
          } catch (error) {
            lastError = error;
            setPhase("webr-retry", {
              attempt,
              lastError: error instanceof Error ? error.message : String(error),
            });
            if (attempt < maxAttempts) {
              await helpers.sleep(250);
            }
          }
        }

        throw lastError || new Error("WebR initialization failed.");
      })().catch((error) => {
        webRPromise = null;
        throw error;
      });
    }
    return webRPromise;
  }

  async function runAll() {
    if (runInFlight) {
      return;
    }

    setRunState(true);
    resultsEl.innerHTML = "";
      setPhase("starting", { lastError: null, currentTest: null, passCount: 0, failCount: 0 });
      setStatus("run", "Loading WebR and preparing validation inputs...");
      timeEl.textContent = `Started at ${new Date().toLocaleString()}`;

    try {
      setPhase("preparing");
      if (typeof config.prepare === "function") {
        await config.prepare(helpers);
      }

      setPhase("waiting-ready");
      if (typeof config.ready === "function") {
        await config.ready(helpers);
      }

      const webR = await ensureWebR();
      const tests = Array.isArray(config.tests) ? config.tests : [];

      if (!tests.length) {
        throw new Error("No validation tests were configured for this page.");
      }

      let passCount = 0;
      let failCount = 0;

      for (const test of tests) {
        setPhase("running-test", { currentTest: test.name || "Unnamed check" });
        const payload = typeof test.collect === "function" ? await test.collect(helpers) : {};
        const rCode = await test.r(payload, helpers);
          const result = await webR.evalRString(rCode);
          const raw = String(result ?? "").trim();
          const [stateToken, ...rest] = raw.split("|");
          const normalized = stateToken === "PASS" ? "pass" : "fail";
          const detail = rest.join("|") || raw;

        if (normalized === "pass") {
          passCount += 1;
        } else {
          failCount += 1;
        }

        resultsEl.appendChild(makeItem(test.name || "Unnamed check", normalized, detail));
      }

      const overall = failCount === 0 ? "pass" : "fail";
        setPhase("completed", { passCount, failCount, currentTest: null, lastError: null });
      setStatus(
        overall,
        failCount === 0
          ? `All ${passCount} WebR checks passed.`
          : `${failCount} of ${passCount + failCount} WebR checks failed.`
      );
      timeEl.textContent = `Last run at ${new Date().toLocaleString()}`;
    } catch (error) {
      setPhase("failed", { lastError: error instanceof Error ? error.message : String(error) });
      setStatus("fail", "Validation could not complete.");
      timeEl.textContent = `Failed at ${new Date().toLocaleString()}`;
      resultsEl.appendChild(
        makeItem(
          "Runtime error",
          "fail",
          error instanceof Error ? error.message : String(error)
        )
      );
    } finally {
      setRunState(false);
    }
  }

  toggleButton.addEventListener("click", () => {
    const collapsed = panel.dataset.collapsed === "true";
    panel.dataset.collapsed = collapsed ? "false" : "true";
    toggleButton.textContent = collapsed ? "Hide" : "Show";
  });

  runButton.addEventListener("click", () => {
    runAll();
  });

  const autoRun = config.autoRun !== false;
  if (autoRun) {
    queueMicrotask(() => {
      runAll();
    });
  }
})();
