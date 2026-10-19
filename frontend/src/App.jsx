import { useEffect, useMemo, useRef, useState } from "react";
import {
  ShieldCheck,
  UploadCloud,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock3,
  Search,
  ChevronDown,
  RefreshCw,
  LockKeyhole,
  Activity,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Settings,
  Globe,
} from "lucide-react";

import "./index.css";


const normalizeApiUrl = (url) => {
  if (!url) return "";
  let clean = url.trim().replace(/\/+$/, "");
  if (clean && !clean.startsWith("http://") && !clean.startsWith("https://")) {
    clean = `https://${clean}`;
  }
  return clean;
};

const getInitialApiUrl = () => {
  const saved = localStorage.getItem("complyai_api_url");
  if (saved && saved.trim()) return normalizeApiUrl(saved);

  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && envUrl.trim()) {
    return normalizeApiUrl(envUrl);
  }

  if (import.meta.env.DEV) {
    return "http://127.0.0.1:8000";
  }

  return "https://complyai-backend.onrender.com";
};

const FRAMEWORKS = [
  "GDPR",
  "HIPAA",
  "SOC 2",
  "ISO 27001",
  "CCPA",
];


function App() {
  const inputRef = useRef(null);

  const [apiUrl, setApiUrl] = useState(getInitialApiUrl);
  const [showSettings, setShowSettings] = useState(false);
  const [tempApiUrl, setTempApiUrl] = useState(apiUrl);
  const [backendStatus, setBackendStatus] = useState("checking");

  const [file, setFile] = useState(null);
  const [framework, setFramework] = useState("GDPR");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setBackendStatus("checking");

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    fetch(`${apiUrl}/api/health`, { signal: controller.signal })
      .then((res) => {
        clearTimeout(timeoutId);
        if (isMounted) {
          if (res.ok) setBackendStatus("online");
          else setBackendStatus("error");
        }
      })
      .catch(() => {
        clearTimeout(timeoutId);
        if (isMounted) {
          setBackendStatus("sleeping");
        }
      });

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [apiUrl]);

  const saveApiUrl = (e) => {
    e.preventDefault();
    const clean = normalizeApiUrl(tempApiUrl);
    if (!clean) return;
    localStorage.setItem("complyai_api_url", clean);
    setApiUrl(clean);
    setShowSettings(false);
  };

  const resetApiUrl = () => {
    localStorage.removeItem("complyai_api_url");
    const defaultUrl = import.meta.env.DEV
      ? "http://127.0.0.1:8000"
      : normalizeApiUrl(import.meta.env.VITE_API_BASE_URL) || "https://complyai-backend.onrender.com";
    setApiUrl(defaultUrl);
    setTempApiUrl(defaultUrl);
    setShowSettings(false);
  };


  const stats = useMemo(() => {
    if (!report) {
      return {
        high: 0,
        critical: 0,
        compliant: 0,
      };
    }

    return {
      high: report.high_risk_count || 0,
      critical: report.critical_count || 0,
      compliant:
        report.findings?.filter(
          (item) => item.status === "compliant"
        ).length || 0,
    };
  }, [report]);


  const selectFile = (selectedFile) => {
    if (!selectedFile) return;

    const allowed = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
      "text/markdown",
    ];

    const extension = selectedFile.name
      .split(".")
      .pop()
      .toLowerCase();

    if (
      !allowed.includes(selectedFile.type) &&
      !["pdf", "docx", "txt", "md"].includes(extension)
    ) {
      setError("Please upload a PDF, DOCX, TXT or MD file.");
      return;
    }

    setFile(selectedFile);
    setError("");
    setReport(null);
  };


  const handleDrop = (event) => {
    event.preventDefault();

    const droppedFile = event.dataTransfer.files?.[0];

    if (droppedFile) {
      selectFile(droppedFile);
    }
  };


  const analyze = async () => {
    if (!file) {
      setError("Upload a document first.");
      return;
    }

    setLoading(true);
    setError("");
    setReport(null);

    try {
      const formData = new FormData();

      formData.append("file", file);
      formData.append("framework", framework);

      const response = await fetch(
        `${apiUrl}/api/analyze`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Compliance analysis failed."
        );
      }

      setReport(data);
    } catch (err) {
      const isNetworkError =
        err.name === "TypeError" ||
        err.message?.toLowerCase().includes("fetch") ||
        err.message?.toLowerCase().includes("failed to fetch") ||
        err.message?.toLowerCase().includes("networkerror");

      if (isNetworkError) {
        setError(
          `Unable to connect to backend (${apiUrl}). If using Render's free tier, the backend spins down when idle and takes ~45 seconds to wake up. Please wait 30 seconds and retry, or configure your Backend URL via the top button.`
        );
      } else {
        setError(
          err.message ||
            "Unable to connect to ComplyAI backend."
        );
      }
    } finally {
      setLoading(false);
    }
  };


  const statusClass = (status) => {
    if (status === "compliant") return "status-good";
    if (status === "non_compliant") return "status-bad";
    return "status-review";
  };


  const severityClass = (severity) => {
    return `severity-${severity.toLowerCase()}`;
  };


  return (
    <div className="app-shell">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={23} />
          </div>

          <div>
            <div className="brand-name">
              ComplyAI
            </div>

            <div className="brand-subtitle">
              Policy Intelligence
            </div>
          </div>
        </div>


        <div className="sidebar-section">
          <div className="sidebar-label">
            WORKSPACE
          </div>

          <div className="nav-item active">
            <Activity size={18} />
            Compliance Overview
          </div>

          <div className="nav-item">
            <FileText size={18} />
            Documents
          </div>

          <div className="nav-item">
            <ShieldAlert size={18} />
            Risk Findings
          </div>
        </div>


        <div className="sidebar-bottom">

          <div className="secure-card">
            <div className="secure-icon">
              <LockKeyhole size={16} />
            </div>

            <div>
              <strong>Secure Analysis</strong>
              <span>
                Documents processed by your AI workflow.
              </span>
            </div>
          </div>

          <div className="version">
            ComplyAI v1.0 • Agentic Compliance Engine
          </div>

        </div>

      </aside>


      {/* MAIN */}

      <main className="main-content">

        <header className="topbar">

          <div>
            <div className="eyebrow">
              COMPLIANCE OPERATIONS
            </div>

            <h1>
              Compliance Command Center
            </h1>

            <p>
              Analyze policies and contracts against regulatory frameworks.
            </p>
          </div>

          <div className="topbar-actions">
            <div
              className={`top-status ${backendStatus}`}
              title={`Target API: ${apiUrl}`}
            >
              <span className={`pulse ${backendStatus}`}></span>
              {backendStatus === "online"
                ? "AI ENGINE ONLINE"
                : backendStatus === "sleeping"
                ? "BACKEND SLEEPING"
                : backendStatus === "checking"
                ? "CONNECTING..."
                : "BACKEND OFFLINE"}
            </div>

            <button
              className="api-config-button"
              type="button"
              onClick={() => {
                setTempApiUrl(apiUrl);
                setShowSettings((prev) => !prev);
              }}
              title="Configure Backend API URL"
            >
              <Settings size={14} />
              <span>API URL</span>
            </button>
          </div>

        </header>

        {showSettings && (
          <div className="api-settings-panel">
            <form onSubmit={saveApiUrl} className="api-settings-form">
              <div className="api-settings-header">
                <Globe size={16} />
                <strong>Backend API Configuration</strong>
              </div>
              <p className="api-settings-desc">
                Current API URL: <code>{apiUrl}</code>. Enter your Render backend URL below if deploying custom endpoints:
              </p>
              <div className="api-input-group">
                <input
                  type="text"
                  value={tempApiUrl}
                  onChange={(e) => setTempApiUrl(e.target.value)}
                  placeholder="https://complyai-backend.onrender.com"
                  className="api-input"
                />
                <button type="submit" className="api-save-btn">Save</button>
                <button type="button" onClick={resetApiUrl} className="api-reset-btn">Reset</button>
              </div>
            </form>
          </div>
        )}


        <section className="hero-grid">

          <div className="upload-card">

            <div className="card-heading">

              <div>
                <span className="section-kicker">
                  01 / DOCUMENT INGESTION
                </span>

                <h2>
                  Upload a policy or contract
                </h2>

                <p>
                  ComplyAI will inspect clauses, detect risk
                  exposure and generate compliant rewrites.
                </p>
              </div>

              <div className="sparkle">
                <Sparkles size={21} />
              </div>

            </div>


            <div
              className={`dropzone ${
                file ? "has-file" : ""
              }`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
            >

              <input
                ref={inputRef}
                type="file"
                hidden
                accept=".pdf,.docx,.txt,.md"
                onChange={(e) =>
                  selectFile(e.target.files?.[0])
                }
              />

              {file ? (
                <>
                  <div className="file-icon">
                    <FileText size={28} />
                  </div>

                  <div className="file-name">
                    {file.name}
                  </div>

                  <div className="file-meta">
                    {(file.size / 1024).toFixed(1)} KB
                    <span>•</span>
                    Ready for analysis
                  </div>
                </>
              ) : (
                <>
                  <div className="upload-icon">
                    <UploadCloud size={30} />
                  </div>

                  <strong>
                    Drop your document here
                  </strong>

                  <span>
                    or click to browse
                  </span>

                  <small>
                    PDF • DOCX • TXT • MD
                  </small>
                </>
              )}

            </div>


            <div className="configuration">

              <div className="config-title">
                Compliance framework
              </div>

              <div className="framework-grid">

                {FRAMEWORKS.map((item) => (
                  <button
                    key={item}
                    className={
                      framework === item
                        ? "framework selected"
                        : "framework"
                    }
                    onClick={() => setFramework(item)}
                  >
                    {item}
                  </button>
                ))}

              </div>

            </div>


            {error && (
              <div className="error-box">
                <AlertTriangle size={18} />
                <span>{error}</span>
              </div>
            )}


            <button
              className="analyze-button"
              onClick={analyze}
              disabled={loading || !file}
            >
              {loading ? (
                <>
                  <RefreshCw
                    size={18}
                    className="spin"
                  />
                  Analyzing document...
                </>
              ) : (
                <>
                  Analyze Compliance
                  <ArrowRight size={18} />
                </>
              )}
            </button>

          </div>


          {/* QUICK INFO */}

          <div className="info-column">

            <div className="info-card dark">

              <div className="info-icon">
                <ShieldCheck size={20} />
              </div>

              <div>
                <span>ACTIVE FRAMEWORK</span>
                <strong>{framework}</strong>
              </div>

              <ChevronDown size={16} />

            </div>


            <div className="info-card">

              <div className="mini-icon purple">
                <Search size={19} />
              </div>

              <div>
                <strong>Clause Intelligence</strong>
                <span>
                  Finds evidence instead of generic warnings.
                </span>
              </div>

            </div>


            <div className="info-card">

              <div className="mini-icon orange">
                <AlertTriangle size={19} />
              </div>

              <div>
                <strong>Risk Detection</strong>
                <span>
                  Prioritizes HIGH and CRITICAL exposures.
                </span>
              </div>

            </div>


            <div className="info-card">

              <div className="mini-icon green">
                <CheckCircle2 size={19} />
              </div>

              <div>
                <strong>Compliant Rewrite</strong>
                <span>
                  Generates practical alternative language.
                </span>
              </div>

            </div>

          </div>

        </section>


        {/* REPORT */}

        {report && (
          <section className="report-section">

            <div className="report-header">

              <div>
                <span className="section-kicker">
                  02 / AUDIT RESULTS
                </span>

                <h2>
                  Compliance Assessment
                </h2>

                <p>
                  {report.document_name} • {report.framework}
                </p>
              </div>

              <div className="score-card">

                <div className="score-number">
                  {report.compliance_score}
                </div>

                <div>
                  <span>COMPLIANCE</span>
                  <strong>/ 100</strong>
                </div>

              </div>

            </div>


            <div className="summary-card">

              <div className="summary-icon">
                <Sparkles size={20} />
              </div>

              <div>
                <span className="summary-label">
                  EXECUTIVE SUMMARY
                </span>

                <p>
                  {report.executive_summary}
                </p>
              </div>

              <div
                className={`overall-status ${
                  report.overall_status === "COMPLIANT"
                    ? "good"
                    : report.overall_status ===
                      "NON_COMPLIANT"
                    ? "bad"
                    : "review"
                }`}
              >
                {report.overall_status.replaceAll(
                  "_",
                  " "
                )}
              </div>

            </div>


            <div className="metrics">

              <Metric
                label="Total Findings"
                value={report.total_findings}
                icon={<FileText size={18} />}
              />

              <Metric
                label="High Risk"
                value={stats.high}
                icon={<AlertTriangle size={18} />}
                danger
              />

              <Metric
                label="Critical"
                value={stats.critical}
                icon={<ShieldAlert size={18} />}
                danger
              />

              <Metric
                label="Compliant"
                value={stats.compliant}
                icon={<CheckCircle2 size={18} />}
                good
              />

            </div>


            <div className="findings-header">

              <div>
                <h3>Findings & Evidence</h3>
                <p>
                  Each result is tied to document evidence.
                </p>
              </div>

              <div className="audit-badge">
                <Clock3 size={15} />
                AI AUDIT LOG
              </div>

            </div>


            <div className="findings-list">

              {report.findings?.map((finding, index) => {

                const isOpen =
                  expanded === index;

                return (
                  <div
                    className={`finding ${
                      isOpen ? "open" : ""
                    }`}
                    key={finding.id || index}
                  >

                    <button
                      className="finding-head"
                      onClick={() =>
                        setExpanded(
                          isOpen ? null : index
                        )
                      }
                    >

                      <div className="finding-index">
                        {String(index + 1).padStart(2, "0")}
                      </div>

                      <div className="finding-main">

                        <div className="finding-topline">

                          <span
                            className={`status-pill ${statusClass(
                              finding.status
                            )}`}
                          >
                            {finding.status ===
                            "compliant" ? (
                              <CheckCircle2 size={13} />
                            ) : finding.status ===
                              "non_compliant" ? (
                              <XCircle size={13} />
                            ) : (
                              <Clock3 size={13} />
                            )}

                            {finding.status.replaceAll(
                              "_",
                              " "
                            )}
                          </span>

                          <span
                            className={`severity-pill ${severityClass(
                              finding.severity
                            )}`}
                          >
                            {finding.severity}
                          </span>

                          <span className="category-pill">
                            {finding.category}
                          </span>

                        </div>

                        <h4>
                          {finding.requirement}
                        </h4>

                        <div className="citation">
                          <FileText size={13} />
                          {finding.citation}
                        </div>

                      </div>

                      <ChevronDown
                        size={19}
                        className={
                          isOpen
                            ? "chevron rotate"
                            : "chevron"
                        }
                      />

                    </button>


                    {isOpen && (
                      <div className="finding-body">

                        <div className="evidence-grid">

                          <div>
                            <span className="body-label">
                              DOCUMENT CLAUSE
                            </span>

                            <blockquote>
                              “{finding.clause}”
                            </blockquote>
                          </div>

                          <div>
                            <span className="body-label">
                              RISK REASON
                            </span>

                            <p>
                              {finding.risk_reason}
                            </p>
                          </div>

                        </div>


                        <div className="rewrite-box">

                          <div className="rewrite-header">
                            <Sparkles size={16} />
                            COMPLIANT ALTERNATIVE
                          </div>

                          <p>
                            {finding.compliant_rewrite}
                          </p>

                        </div>

                      </div>
                    )}

                  </div>
                );
              })}

            </div>

          </section>
        )}


        {!report && !loading && (
          <section className="empty-state">

            <div className="empty-icon">
              <ShieldCheck size={27} />
            </div>

            <div>
              <strong>
                Your compliance report will appear here
              </strong>

              <p>
                Upload a policy or contract above to begin
                an AI-powered compliance audit.
              </p>
            </div>

          </section>
        )}

      </main>

    </div>
  );
}


function Metric({
  label,
  value,
  icon,
  danger,
  good,
}) {
  return (
    <div className="metric">

      <div
        className={`metric-icon ${
          danger
            ? "danger"
            : good
            ? "good"
            : ""
        }`}
      >
        {icon}
      </div>

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>

    </div>
  );
}


export default App;