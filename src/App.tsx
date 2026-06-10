import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { openUrl, revealItemInDir } from "@tauri-apps/plugin-opener";
import "./App.css";

type ArchitectureItem = {
  title: string;
  description: string;
  details: string[];
};

type AppOverview = {
  appName: string;
  tagline: string;
  currentPhase: string;
  nextTarget: string;
  modules: ArchitectureItem[];
  workstreams: ArchitectureItem[];
  principles: string[];
};

type GenerateSummary = {
  totalJobs: number;
  writtenFiles: string[];
  skippedBlank: number;
};

type IntegrityFileReport = {
  path: string;
  status: string;
};

type IntegrityReport = {
  repo: string;
  defaultBranch: string;
  checkedFiles: number;
  matches: number;
  changed: number;
  missing: number;
  repaired: number;
  files: IntegrityFileReport[];
};

type GenerationEvent = {
  kind: string;
  message: string;
  done?: number | null;
  total?: number | null;
  outputId?: number | null;
  outputFile?: string | null;
};

type TabKey = "generator" | "blank";

type DiscordServer = {
  label: string;
  url: string;
};

const discordServers: DiscordServer[] = [
  { label: "Canary", url: "https://discord.gg/gvTj5sh9Mp" },
  { label: "TK Dev", url: "https://discord.gg/rj97H4JD3k" },
];

function deriveGenerateOutputDir(filePath: string) {
  const separator = filePath.includes("\\") ? "\\" : "/";
  const normalized = filePath.replace(/[\\/]+/g, separator);
  const lastSeparator = normalized.lastIndexOf(separator);
  if (lastSeparator === -1) {
    return `generate${separator}gifs`;
  }

  return `${normalized.slice(0, lastSeparator)}${separator}generate${separator}gifs`;
}

const fallbackOverview: AppOverview = {
  appName: "TK Dev Tools",
  tagline: "A Rust + React + Tauri foundation for the Python tool suite.",
  currentPhase: "Architecture scaffold",
  nextTarget: "Port the GIF Generator core into Rust.",
  modules: [
    {
      title: "Core",
      description: "Binary parsing, sprite decoding, frame assembly, integrity checks.",
      details: ["DAT parser", "SPR parser", "GIF renderer", "Integrity verifier"],
    },
    {
      title: "Shell",
      description: "Tauri commands and app state that connect the UI to Rust.",
      details: ["Typed commands", "Progress events", "File dialogs", "Open-folder actions"],
    },
    {
      title: "UI",
      description: "React workspace for the generator and future admin tools.",
      details: ["Hero dashboard", "Generator workspace", "Log panel", "Extensible tabs"],
    },
  ],
  workstreams: [
    {
      title: "Phase 1",
      description: "Recreate the current Python feature set with clear boundaries.",
      details: ["Project shell", "App identity", "Architecture map", "Command contract"],
    },
    {
      title: "Phase 2",
      description: "Move the GIF generator logic to Rust without changing the workflow.",
      details: ["File parsing", "Rendering pipeline", "Background jobs", "Progress reporting"],
    },
    {
      title: "Phase 3",
      description: "Add the remaining tools and polish the product for daily use.",
      details: ["More tabs", "Persistent settings", "Better packaging", "Release workflow"],
    },
  ],
  principles: [
    "Keep the current workflow recognizable for existing users.",
    "Move reusable logic into Rust and keep the UI declarative.",
    "Expose only the commands the front end needs.",
    "Design for future tools, not just the first generator.",
  ],
};

function App() {
  const [overview, setOverview] = useState<AppOverview>(fallbackOverview);
  const [status, setStatus] = useState("Loading architecture...");
  const [result, setResult] = useState<GenerateSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>("generator");
  const [showLog, setShowLog] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [showDiscordMenu, setShowDiscordMenu] = useState(false);

  const [clientVersion, setClientVersion] = useState("1100");
  const [sprPath, setSprPath] = useState("");
  const [datPath, setDatPath] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [onlyPickable, setOnlyPickable] = useState(false);
  const [useRange, setUseRange] = useState(false);
  const [startId, setStartId] = useState("100");
  const [endId, setEndId] = useState("1100");
  const [frameDelayMs, setFrameDelayMs] = useState("100");
  const [workers, setWorkers] = useState("4");
  const [progressDone, setProgressDone] = useState(0);
  const [progressTotal, setProgressTotal] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [integrityReport, setIntegrityReport] = useState<IntegrityReport | null>(null);

  const discordMenuRef = useRef<HTMLDivElement>(null);
  const generationUnlistenRef = useRef<(() => void) | null>(null);

  function appendLog(message: string) {
    setLogs((current) => {
      if (current[current.length - 1] === message) {
        return current;
      }

      return [...current, message];
    });
  }

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      try {
        const data = await invoke<AppOverview>("get_app_overview");
        if (active) {
          setOverview(data);
          setStatus("Architecture loaded from Rust.");
        }
      } catch {
        if (active) {
          setStatus("Using local fallback overview.");
        }
      }
    }

    void loadOverview();
    const unsubscribePromise = listen<GenerationEvent>("generation://event", (event) => {
      const payload = event.payload;
      if (payload.kind === "log") {
        appendLog(payload.message);
      }
      if (payload.kind === "progress") {
        setProgressDone(payload.done ?? 0);
        setProgressTotal(payload.total ?? 0);
        appendLog(payload.message);
      }
      if (payload.kind === "done") {
        setProgressDone(payload.done ?? 0);
        setProgressTotal(payload.total ?? 0);
        appendLog(payload.message);
        setStatus("Generation finished.");
      }
    });

    void unsubscribePromise.then((unlisten) => {
      if (!active) {
        unlisten();
        return;
      }

      generationUnlistenRef.current?.();
      generationUnlistenRef.current = unlisten;
    });

    return () => {
      active = false;
      generationUnlistenRef.current?.();
      generationUnlistenRef.current = null;
    };
  }, []);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!showDiscordMenu) {
        return;
      }
      if (discordMenuRef.current && !discordMenuRef.current.contains(event.target as Node)) {
        setShowDiscordMenu(false);
      }
    }

    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [showDiscordMenu]);

  async function browseSpr() {
    const path = await invoke<string | null>("select_spr_file");
    if (path) {
      setSprPath(path);
      setOutputDir(deriveGenerateOutputDir(path));
    }
  }

  async function browseDat() {
    const path = await invoke<string | null>("select_dat_file");
    if (path) {
      setDatPath(path);
      setOutputDir(deriveGenerateOutputDir(path));
    }
  }

  async function browseOutput() {
    const path = await invoke<string | null>("select_output_dir");
    if (path) {
      setOutputDir(path);
    }
  }

  async function openDiscord(url: string) {
    setShowDiscordMenu(false);
    await openUrl(url);
  }

  async function runGeneration() {
    setError(null);
    setResult(null);
    setBusy(true);
    setStatus("Generating GIFs...");
    setProgressDone(0);
    setProgressTotal(0);
    setLogs([]);

    try {
      const inferredSourcePath = datPath.trim() || sprPath.trim();
      const effectiveOutputDir = outputDir.trim()
        ? outputDir.trim()
        : inferredSourcePath
          ? deriveGenerateOutputDir(inferredSourcePath)
          : "";

      const summary = await invoke<GenerateSummary>("generate_gifs", {
        request: {
          clientVersion: Number(clientVersion),
          sprPath,
          datPath,
          outputDir: effectiveOutputDir,
          onlyPickable,
          useRange,
          startId: useRange ? Number(startId) : null,
          endId: useRange ? Number(endId) : null,
          frameDelayMs: Number(frameDelayMs),
          workers: Number(workers),
        },
      });

      setResult(summary);
      setStatus(`Generated ${summary.writtenFiles.length} file(s).`);
      if (effectiveOutputDir) {
        setOutputDir(effectiveOutputDir);
        await revealItemInDir(effectiveOutputDir);
      }
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      setError(message);
      setStatus("Generation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runIntegrityCheck() {
    setError(null);
    setIntegrityReport(null);
    setStatus("Checking integrity...");

    try {
      const report = await invoke<IntegrityReport>("check_integrity");
      setIntegrityReport(report);
      setStatus(
        `Integrity check complete: ${report.matches} match(es), ${report.repaired} repaired.`,
      );
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      setError(message);
      setStatus("Integrity check failed.");
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <img src="/icon.png" alt="" className="brand-icon" />
          </div>
          <div>
            <p className="brand-kicker">
              Created By LeoTK
            </p>
            <strong>{overview.appName}</strong>
          </div>
        </div>

        <div className="topbar-actions">
          <span className="topbar-status">{status}</span>

          <button type="button" className="ghost-button" onClick={runIntegrityCheck} disabled={busy}>
            Check integrity
          </button>

          <div className="discord-wrap" ref={discordMenuRef}>
            <button
              type="button"
              className="ghost-button"
              aria-haspopup="menu"
              aria-expanded={showDiscordMenu}
              onClick={() => setShowDiscordMenu((current) => !current)}
            >
              Discord
            </button>
            {showDiscordMenu ? (
              <div className="dropdown-menu" role="menu">
                {discordServers.map((server) => (
                  <button
                    key={server.label}
                    type="button"
                    className="dropdown-item"
                    onClick={() => void openDiscord(server.url)}
                  >
                    <span>{server.label}</span>
                    <small>{server.url}</small>
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <button type="button" className="ghost-button" onClick={() => setShowAbout(true)}>
            About
          </button>
          <button type="button" className="ghost-button" onClick={() => setShowLog((current) => !current)}>
            {showLog ? "Hide log" : "Show log"}
          </button>
        </div>
      </header>

      <section className="tab-shell">
        <div className="tab-strip" role="tablist" aria-label="Workspace tabs">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "generator"}
            className={activeTab === "generator" ? "tab-button active" : "tab-button"}
            onClick={() => setActiveTab("generator")}
          >
            GIF Generator
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "blank"}
            className={activeTab === "blank" ? "tab-button active" : "tab-button"}
            onClick={() => setActiveTab("blank")}
          >
            Blank
          </button>
        </div>

        {activeTab === "generator" ? (
          <article className="panel wide tab-panel">
            <div className={showLog ? "generator-layout log-open" : "generator-layout"}>
              <div className="generator-main">
                <div className="form-grid">
                  <label className="field">
                    <span>Client Version</span>
                    <input value={clientVersion} onChange={(event) => setClientVersion(event.target.value)} />
                  </label>

                  <label className="field">
                    <span>Workers</span>
                    <input
                      type="number"
                      min={1}
                      step={1}
                      value={workers}
                      onChange={(event) => setWorkers(event.target.value)}
                    />
                  </label>

                  <label className="field wide-field">
                    <span>SPR File</span>
                    <div className="input-row">
                      <input
                        value={sprPath}
                        onChange={(event) => setSprPath(event.target.value)}
                        placeholder="C:\\path\\to\\Tibia.spr"
                      />
                      <button type="button" className="ghost-button" onClick={browseSpr}>
                        Browse
                      </button>
                    </div>
                  </label>

                  <label className="field wide-field">
                    <span>DAT File</span>
                    <div className="input-row">
                      <input
                        value={datPath}
                        onChange={(event) => setDatPath(event.target.value)}
                        placeholder="C:\\path\\to\\Tibia.dat"
                      />
                      <button type="button" className="ghost-button" onClick={browseDat}>
                        Browse
                      </button>
                    </div>
                  </label>

                  <label className="field wide-field">
                    <span>Output Folder</span>
                    <div className="input-row">
                      <input
                        value={outputDir}
                        onChange={(event) => setOutputDir(event.target.value)}
                        placeholder="C:\\output\\folder"
                      />
                      <button type="button" className="ghost-button" onClick={browseOutput}>
                        Browse
                      </button>
                    </div>
                  </label>

                  <div className="options-grid wide-field">
                    <div className="options-group">
                      <label className="checkbox-field compact-checkbox">
                        <input
                          type="checkbox"
                          checked={onlyPickable}
                          onChange={(event) => setOnlyPickable(event.target.checked)}
                        />
                        <span>Only pickable items</span>
                      </label>
                      <label className="field compact-field compact-delay">
                        <span>Frame delay (ms)</span>
                        <input value={frameDelayMs} onChange={(event) => setFrameDelayMs(event.target.value)} />
                      </label>
                    </div>

                    <div className="options-group">
                      <label className="checkbox-field compact-checkbox compact-range-toggle">
                        <input type="checkbox" checked={useRange} onChange={(event) => setUseRange(event.target.checked)} />
                        <span>Use ID range</span>
                      </label>
                      <div className="range-row">
                        <label className="field compact-field">
                          <span>Start ID</span>
                          <input
                            value={startId}
                            onChange={(event) => setStartId(event.target.value)}
                            disabled={!useRange}
                          />
                        </label>

                        <label className="field compact-field">
                          <span>End ID</span>
                          <input
                            value={endId}
                            onChange={(event) => setEndId(event.target.value)}
                            disabled={!useRange}
                          />
                        </label>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="actions">
                  <button type="button" className="primary-action" onClick={runGeneration} disabled={busy}>
                    {busy ? "Generating..." : "Generate GIFs"}
                  </button>
                </div>

                <div className="progress-shell" aria-label="Generation progress">
                  <div className="progress-row">
                    <span>Progress</span>
                    <strong>{progressTotal > 0 ? `${progressDone}/${progressTotal}` : "Idle"}</strong>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width:
                          progressTotal > 0
                            ? `${Math.min(100, Math.round((progressDone / progressTotal) * 100))}%`
                            : "0%",
                      }}
                    />
                  </div>
                </div>

                {error ? <p className="error-box">{error}</p> : null}
                {result ? (
                  <div className="result-box">
                    <strong>Generation complete</strong>
                    <p>
                      {result.totalJobs} job(s) processed, {result.writtenFiles.length} file(s) written,{" "}
                      {result.skippedBlank} blank item(s) skipped.
                    </p>
                  </div>
                ) : null}

                {integrityReport ? (
                  <div className="result-box integrity-box">
                    <strong>Integrity report</strong>
                    <p>
                      {integrityReport.checkedFiles} file(s) checked on {integrityReport.repo} (
                      {integrityReport.defaultBranch}).
                    </p>
                    <p>
                      {integrityReport.matches} match(es), {integrityReport.changed} changed,{" "}
                      {integrityReport.missing} missing, {integrityReport.repaired} repaired.
                    </p>
                    <div className="integrity-list">
                      {integrityReport.files.map((file) => (
                        <div className={`integrity-entry status-${file.status.replace(/[^a-z]/gi, "-")}`} key={file.path}>
                          <span>{file.path}</span>
                          <strong>{file.status}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              <aside className={showLog ? "log-drawer open" : "log-drawer closed"} aria-hidden={!showLog}>
                <div className="panel-head compact">
                  <p className="eyebrow">Log</p>
                  <h2>Live events</h2>
                </div>
                <div className="log-list">
                  {logs.length === 0 ? <p className="log-empty">No events yet.</p> : null}
                  {logs.map((entry, index) => (
                    <div className="log-entry" key={`${index}-${entry}`}>
                      {entry}
                    </div>
                  ))}
                </div>
              </aside>
            </div>
          </article>
        ) : (
          <article className="panel wide tab-panel blank-panel">
            <div className="panel-head">
              <p className="eyebrow">Blank tab</p>
              <h2>Reserved space for the next tools</h2>
            </div>
            <p className="lede">
              This tab mirrors the empty page behavior from a `QTabWidget`, so the shell can grow
              without forcing every tool into the same workspace.
            </p>

            <div className="cards">
              {overview.modules.map((module) => (
                <div className="card" key={module.title}>
                  <h3>{module.title}</h3>
                  <p>{module.description}</p>
                  <ul>
                    {module.details.map((detail) => (
                      <li key={detail}>{detail}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            <div className="blank-grid">
              <div className="panel-inner">
                <div className="panel-head compact">
                  <p className="eyebrow">Roadmap</p>
                  <h2>Delivery phases</h2>
                </div>
                <div className="stack">
                  {overview.workstreams.map((phase) => (
                    <div className="timeline-item" key={phase.title}>
                      <div className="timeline-marker" />
                      <div>
                        <h3>{phase.title}</h3>
                        <p>{phase.description}</p>
                        <ul>
                          {phase.details.map((detail) => (
                            <li key={detail}>{detail}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel-inner">
                <div className="panel-head compact">
                  <p className="eyebrow">Guidelines</p>
                  <h2>Migration principles</h2>
                </div>
                <div className="principles">
                  {overview.principles.map((principle) => (
                    <div className="principle" key={principle}>
                      {principle}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </article>
        )}
      </section>

      {showAbout ? (
        <div className="modal-overlay" role="presentation" onClick={() => setShowAbout(false)}>
          <div className="modal-card" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <div className="modal-head">
              <div>
                <p className="eyebrow">About</p>
                <h2>{overview.appName}</h2>
              </div>
              <button type="button" className="ghost-button" onClick={() => setShowAbout(false)}>
                Close
              </button>
            </div>

            <p className="lede">
              A Rust + React + Tauri migration of the Python tooling suite, keeping the GIF generator
              workflow visible while we move the heavy work into native code.
            </p>

            <div className="modal-grid">
              <div className="modal-block">
                <span className="status-label">Current phase</span>
                <strong>{overview.currentPhase}</strong>
              </div>
              <div className="modal-block">
                <span className="status-label">Next target</span>
                <strong>{overview.nextTarget}</strong>
              </div>
              <div className="modal-block">
                <span className="status-label">Repo</span>
                <strong>LeoTKBR/tk-dev-tools</strong>
              </div>
              <div className="modal-block">
                <span className="status-label">Discord</span>
                <strong>{discordServers.map((server) => server.label).join(" / ")}</strong>
              </div>
            </div>

            <p className="copyright-note">
              Copyright © 2026 TK Dev Core. All rights reserved. Unauthorized use, reproduction, or
              distribution is strictly prohibited.
            </p>
          </div>
        </div>
      ) : null}
    </main>
  );
}

export default App;
