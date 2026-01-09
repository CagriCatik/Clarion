import React, { useState, useEffect, useRef, useCallback } from "react";
import "./App.css";

// Components
import { Dashboard } from "./components/Dashboard";
import { MarkdownViewer } from "./components/MarkdownViewer";
import { ErrorBoundary } from "./components/ErrorBoundary";
import {
  IconX, IconRefresh, IconZoomIn, IconZoomOut, IconSparkles, IconStop,
  IconDownload, IconTrash, IconInfo, IconFile, IconDraft, IconReview, IconRepair, IconFolder
} from "./components/Icons";

// Types
import { ModelList, DocResult } from "./types";

// =====================================================
// MAIN APP COMPONENT
// =====================================================
function App() {
  // === STATE ===
  const [files, setFiles] = useState<File[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [results, setResults] = useState<DocResult[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStatus, setCurrentStatus] = useState("");
  const [statusLog, setStatusLog] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [elapsedTime, setElapsedTime] = useState(0);
  const [metrics, setMetrics] = useState<{ cpu: number; ram: number; gpu?: number | null }>({ cpu: 0, ram: 0, gpu: null });
  const [backendOnline, setBackendOnline] = useState(false);
  const [ollamaOnline, setOllamaOnline] = useState(false);

  // Configuration State
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [instruction, setInstruction] = useState("Generate comprehensive technical documentation.");
  const [activeSettingsTab, setActiveSettingsTab] = useState('general');

  // Advanced Settings
  const [temp, setTemp] = useState(0.3); // Lower temp for technical accuracy
  const [topP, setTopP] = useState(0.9);
  const [numCtx, setNumCtx] = useState(8192); // Larger context for docs
  const [numPredict, setNumPredict] = useState(-1);
  const [topK, setTopK] = useState(40);
  const [repeatPenalty, setRepeatPenalty] = useState(1.1);
  const [presencePenalty, setPresencePenalty] = useState(0.0);
  const [frequencyPenalty, setFrequencyPenalty] = useState(0.0);

  // Multi-Model / Workflow Settings
  const [genModel, setGenModel] = useState("");
  const [revModel, setRevModel] = useState("");
  const [fastMode, setFastMode] = useState(false);
  const [interactiveReview, interactiveReviewSet] = useState(false);

  // View State
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [mdZoom, setMdZoom] = useState(1);
  const [recentOutputs, setRecentOutputs] = useState<string[]>([]);

  // Refs
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // === INITIALIZATION ===
  useEffect(() => {
    fetchModels();
    fetchRecentOutputs();
    checkConnections();
    fetchMetrics();
    const interval = setInterval(() => {
      checkConnections();
      fetchMetrics();
    }, 5000);
    return () => {
      stopTimer();
      clearInterval(interval);
    };
  }, []);

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  // === API CALLS ===
  const fetchModels = async () => {
    try {
      const res = await fetch("/v1/models");
      const data: ModelList = await res.json();
      setModels(data.models);
      if (data.models.length > 0 && !selectedModel) {
        setSelectedModel(data.models[0]);
        setGenModel(data.models[0]);
        setRevModel(data.models[0]);
      }
      setBackendOnline(true);
    } catch (e) {
      console.error("Failed to fetch models", e);
      setBackendOnline(false);
    }
  };

  const checkConnections = async () => {
    try {
      const res = await fetch("/v1/models");
      setBackendOnline(res.ok);
      setOllamaOnline(res.ok);
    } catch {
      setBackendOnline(false);
      setOllamaOnline(false);
    }
  };

  const fetchMetrics = async () => {
    try {
      const res = await fetch("/v1/metrics");
      const data = await res.json();
      setMetrics(data);
    } catch (e) {
      console.error("Failed to fetch metrics", e);
    }
  };

  const fetchRecentOutputs = async () => {
    try {
      const res = await fetch("/v1/outputs");
      const data: any = await res.json();
      // Handle both array and object format if backend changed
      const list = Array.isArray(data) ? data : (data.outputs || []);
      setRecentOutputs(list.slice(0, 5));
    } catch (e) { console.error("Failed to fetch outputs", e); }
  };

  const handleStop = async () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    stopTimer();
    setIsProcessing(false);
    setCurrentStatus("Stopped by user");

    // Also tell backend to stop if possible (optional based on API)
    try {
      await fetch("/v1/stop", { method: "POST" });
    } catch (e) { /* ignore */ }
  };

  const loadDocument = async (filename: string) => {
    try {
      const res = await fetch(`/v1/outputs/${filename}`);
      const data = await res.json();
      const existingIdx = results.findIndex(r => r.filename === filename);
      if (existingIdx >= 0) {
        setActiveTab(existingIdx);
      } else {
        setResults(prev => [...prev, { filename, markdown: data.markdown }]);
        setActiveTab(results.length);
      }
    } catch (e) {
      console.error("Failed to load document:", e);
    }
  };

  // === GENERATION ===
  const handleGenerate = async () => {
    if (files.length === 0) return;

    setIsProcessing(true);
    setError("");
    setStatusLog([]);
    setElapsedTime(0);

    abortRef.current = new AbortController();
    timerRef.current = setInterval(() => setElapsedTime(t => t + 1), 1000);

    const formData = new FormData();
    files.forEach(f => formData.append("files", f));
    formData.append("model", selectedModel);
    formData.append("instruction", instruction);
    formData.append("word_budget", "2000");
    formData.append("overlap", "2");
    formData.append("temperature", temp.toString());
    formData.append("top_p", topP.toString());
    formData.append("num_ctx", numCtx.toString());
    formData.append("num_predict", numPredict.toString());
    formData.append("presence_penalty", presencePenalty.toString());
    formData.append("frequency_penalty", frequencyPenalty.toString());
    formData.append("repeat_penalty", repeatPenalty.toString());
    formData.append("top_k", topK.toString());
    formData.append("skip_refinement", fastMode ? "true" : "false");

    // Multi-Model Params
    if (genModel) formData.append("generator_model", genModel);
    if (revModel) formData.append("reviewer_model", revModel);
    formData.append("interactive_review", interactiveReview ? "true" : "false");

    try {
      const response = await fetch("/v1/docgen", {
        method: "POST",
        body: formData,
        signal: abortRef.current.signal,
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const json = JSON.parse(line.slice(6));
            if (json.status) {
              setCurrentStatus(json.status);
              setStatusLog(prev => [...prev, json.status]);
            }
            if (json.result) {
              const newResult: DocResult = {
                filename: json.result.filename || json.result.saved_to?.split(/[/\\]/).pop() || "doc.md",
                markdown: json.result.markdown,
                json: json.result.json,
                reviewReport: json.result.review_report,
              };
              setResults(prev => [...prev, newResult]);
              setActiveTab(prev => prev + 1);
            }
            if (json.error) {
              setError(json.error);
              setStatusLog(prev => [...prev, `Error: ${json.error}`]);
            }
            if (json.complete) {
              setStatusLog(prev => [...prev, "Generation complete!"]);
            }
          } catch { }
        }
      }
    } catch (e: any) {
      if (e.name !== "AbortError") {
        setError(e.message || "An error occurred");
      }
    } finally {
      setIsProcessing(false);
      stopTimer();
      fetchRecentOutputs();
    }
  };

  const handleEditSave = async () => {
    if (!results[activeTab]) return;
    setIsSaving(true);
    try {
      await fetch(`/v1/outputs/${results[activeTab].filename}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markdown: editContent })
      });
      setResults(prev => {
        const updated = [...prev];
        updated[activeTab] = { ...updated[activeTab], markdown: editContent };
        return updated;
      });
      setIsEditing(false);
    } catch (e) {
      alert("Failed to save changes.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleOpenFolder = async () => {
    try {
      await fetch("/v1/open_outputs", { method: "POST" });
    } catch (e) {
      alert("Failed to open outputs folder.");
    }
  };

  const closeDocument = (idx: number) => {
    setResults(prev => prev.filter((_, i) => i !== idx));
    if (activeTab >= idx && activeTab > 0) setActiveTab(activeTab - 1);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const deleteOutput = async (filename: string) => {
    if (!confirm(`Delete "${filename}"?`)) return;
    try {
      await fetch(`/v1/outputs/${filename}`, { method: "DELETE" });
      setRecentOutputs(prev => prev.filter(f => f !== filename));
      // Also close document if open
      const idx = results.findIndex(r => r.filename === filename);
      if (idx >= 0) closeDocument(idx);
    } catch (e) {
      alert("Failed to delete file.");
    }
  };

  const downloadMd = () => {
    const doc = results[activeTab];
    if (!doc?.markdown) return;
    const blob = new Blob([doc.markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = doc.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // === DRAG & DROP ===
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      f => f.name.endsWith('.md') || f.name.endsWith('.txt')
    );
    setFiles(prev => [...prev, ...droppedFiles.filter(f => !prev.find(p => p.name === f.name))]);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDownloadPdf = () => {
    // 1. Find the element
    const sourceElement = document.querySelector('.markdown-content');
    if (!sourceElement) return;

    // 2. Clone it to avoid modifying the live UI
    //    We explicitly cast to HTMLElement to access 'style'
    const clone = sourceElement.cloneNode(true) as HTMLElement;

    // 3. Create a temporary container off-screen
    const container = document.createElement('div');
    container.style.position = 'absolute';
    container.style.top = '-9999px';
    container.style.left = '-9999px';
    container.style.width = '210mm'; // A4 width

    // 4. Inject aggressive Print Styles
    //    Instead of just setting vars, we inject a style block to force overrides
    const style = document.createElement('style');
    style.innerHTML = `
      .markdown-content {
        color: #000000 !important;
        background: #ffffff !important;
        font-family: 'Times New Roman', serif; /* Better for reading reports */
      }
      .markdown-content * {
        color: #000000 !important;
        background-color: transparent !important;
      }
      /* Clean up Mermaid: Remove window UI, keep diagram */
      .mermaid-window {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        margin: 20px 0 !important;
        height: auto !important;
      }
      .mermaid-window > div:first-child {
        display: none !important; /* Hide window header */
      }
      .mermaid-viewport {
        background: transparent !important;
        height: auto !important;
        overflow: visible !important;
        display: block !important;
      }
      .mermaid-viewport > div {
        transform: none !important; /* Remove pan/zoom transforms */
        position: static !important; /* Let it flow */
        width: 100% !important;
        height: auto !important; 
        display: flex !important;
        justify-content: center !important;
      }
      svg {
        background: transparent !important;
        max-width: 100% !important;
        height: auto !important;
      }
      /* Force SVG text/lines to be black */
      g.node text, g.edgeLabel text, g.label text, text.actor {
         fill: #000 !important;
         stroke: none !important;
      }
      path, line, rect, circle, polygon {
         stroke: #000 !important;
      }
      /* But keep fills white for shapes so lines don't disappear */
      g.node rect, g.node circle, g.node polygon, g.actor rect {
        fill: #ffffff !important;
      }
      /* Code blocks */
      pre {
        border: 1px solid #ccc !important;
        background: #f5f5f5 !important;
      }
    `;
    container.appendChild(style);

    // Append clone to container
    container.appendChild(clone);
    document.body.appendChild(container);

    // @ts-ignore
    if (typeof window.html2pdf === 'undefined') {
      alert("PDF engine not loaded yet. Please wait a moment or refresh.");
      document.body.removeChild(container);
      return;
    }

    const opt = {
      margin: 15, // mm
      filename: results[activeTab]?.filename.replace(/\.(md|txt)$/i, '') + '.pdf' || 'document.pdf',
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, letterRendering: true, scrollY: 0 },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
    };

    // Use the Promise-based API to ensure cleanup happens AFTER save
    // @ts-ignore
    window.html2pdf().set(opt).from(clone).save().then(() => {
      // Cleanup
      document.body.removeChild(container);
    }).catch((err: any) => {
      console.error("PDF Export Error:", err);
      document.body.removeChild(container);
    });
  };

  // =====================================================
  // RENDER
  // =====================================================
  return (
    <div className="app-layout">
      {/* === HEADER === */}
      <header className="app-header">
        <div className="header-left">
          <div className="header-title">Clarion</div>
          <div className={`status-pill ${backendOnline ? 'online' : 'offline'}`}>
            <div className="status-dot"></div>
            <span>{backendOnline ? 'Connected' : 'Offline'}</span>
          </div>
          <div style={{ marginLeft: '12px', fontSize: '0.75rem', fontWeight: 600, display: 'flex', gap: '12px' }}>
            <span style={{ color: 'var(--accent)' }}>CPU {metrics.cpu?.toFixed(0)}%</span>
            <span style={{ color: '#a855f7' }}>RAM {metrics.ram?.toFixed(0)}%</span>
            {metrics.gpu !== null && metrics.gpu !== undefined && <span style={{ color: 'var(--success)' }}>GPU {metrics.gpu.toFixed(0)}%</span>}
          </div>
        </div>
        <div className="header-right">
          <button className="icon-btn" onClick={handleOpenFolder} title="Open Outputs Folder">
            <IconFolder />
          </button>
        </div>
      </header>

      <main className="app-content">
        {/* === INPUT PANEL === */}
        <aside className="input-panel">
          <div className="input-panel-scroll">
            {/* File Upload Region */}
            <div
              className={`dropzone ${isDragOver ? "dragover" : ""}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => document.getElementById("file-input")?.click()}
            >
              <input
                id="file-input"
                type="file"
                multiple
                accept=".md,.txt"
                onChange={(e) => {
                  if (e.target.files) {
                    const newFiles = Array.from(e.target.files);
                    setFiles(prev => [...prev, ...newFiles.filter(f => !prev.find(p => p.name === f.name))]);
                    e.target.value = ''; // reset so same file can be selected again if needed
                  }
                }}
                className="visually-hidden"
              />
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <IconFile />
                <span className="dropzone-text">
                  Drop context files (.md, .txt) here or click to browse
                </span>
              </div>
            </div>

            {files.length > 0 && (
              <ul className="file-list">
                {files.map((file, idx) => (
                  <li key={idx} className="file-item">
                    <div className="file-item-info">
                      <span className="file-item-name">{file.name}</span>
                      <span style={{ fontSize: '0.7em', color: 'var(--text-tertiary)' }}>{(file.size / 1024).toFixed(1)} KB</span>
                    </div>
                    <button className="file-item-remove" onClick={(e) => { e.stopPropagation(); removeFile(idx); }}>
                      &times;
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <div className="form-section">
              <label className="form-label">
                <IconDraft /> Instructions
              </label>
              <textarea
                className="form-textarea"
                placeholder="e.g., 'Generate an architecture overview based on these notes...'"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
              />
            </div>

            <button
              className={`hero-btn ${isProcessing ? 'loading' : ''}`}
              onClick={handleGenerate}
              disabled={isProcessing || files.length === 0}
            >
              <IconSparkles />
              {isProcessing ? "Processing..." : "Generate Documentation"}
            </button>

            {/* STATUS & LOGS */}
            {isProcessing && (
              <div className="processing-card">
                <div className="processing-header">
                  <span className="processing-timer">{elapsedTime}s</span>
                  <button className="processing-stop" onClick={handleStop} title="Stop">
                    <IconStop />
                  </button>
                </div>
                <div className="processing-status">{currentStatus || "Initializing..."}</div>
              </div>
            )}

            {error && (
              <div style={{ padding: '12px', background: 'var(--error-bg)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '8px', color: 'var(--error)', fontSize: '0.85rem' }}>
                {error}
              </div>
            )}

            <div className="separator" style={{ margin: '24px 0', borderTop: '1px solid var(--border)' }}></div>

            {/* RECENT OUTPUTS */}
            <div className="recent-section">
              <div className="recent-header">
                <span className="recent-title">Recent Outputs</span>
                <button className="icon-btn" onClick={fetchRecentOutputs} title="Refresh">
                  <IconRefresh />
                </button>
              </div>
              <ul className="recent-list">
                {recentOutputs.length === 0 ? (
                  <li className="recent-empty">No recent documents</li>
                ) : (
                  recentOutputs.map((fname, i) => (
                    <li key={i} className="recent-item" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', flex: 1, overflow: 'hidden' }} onClick={() => loadDocument(fname)}>
                        <IconFile /> <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{fname}</span>
                      </span>
                      <button className="icon-btn" onClick={(e) => { e.stopPropagation(); deleteOutput(fname); }} title="Delete" style={{ color: 'var(--text-tertiary)' }}>
                        <IconTrash />
                      </button>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>
        </aside>

        {/* === MAIN PREVIEW PANEL === */}
        <section className="preview-panel">
          {results.length > 0 ? (
            <>
              {/* TABS */}
              <div className="preview-tabs">
                {results.map((res, i) => (
                  <div
                    key={i}
                    className={`preview-tab ${activeTab === i ? "active" : ""}`}
                    onClick={() => setActiveTab(i)}
                  >
                    <span>{res.filename}</span>
                    <button className="preview-tab-close" onClick={(e) => { e.stopPropagation(); closeDocument(i); }}>
                      &times;
                    </button>
                  </div>
                ))}
              </div>

              {/* TOOLBAR */}
              <div className="preview-toolbar">
                <div className="preview-toolbar-left">
                  {results[activeTab]?.reviewReport && (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <span className={`status-pill ${results[activeTab].reviewReport!.confidence_score > 0.8 ? 'online' : 'offline'}`}>
                        Confidence: {(results[activeTab].reviewReport!.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
                <div className="preview-toolbar-right">
                  {!isEditing ? (
                    <button className="toolbar-btn" onClick={() => { setEditContent(results[activeTab]?.markdown || ""); setIsEditing(true); }}>
                      Edit
                    </button>
                  ) : (
                    <>
                      <button className="toolbar-btn primary" onClick={handleEditSave} disabled={isSaving}>
                        {isSaving ? "Saving..." : "Save"}
                      </button>
                      <button className="toolbar-btn" onClick={() => setIsEditing(false)}>Cancel</button>
                    </>
                  )}
                  <button className="toolbar-btn" onClick={() => setMdZoom(z => Math.max(0.7, z - 0.1))}><IconZoomOut /></button>
                  <button className="toolbar-btn" onClick={() => setMdZoom(z => Math.min(2.0, z + 0.1))}><IconZoomIn /></button>
                  <button className="toolbar-btn" onClick={handleDownloadPdf} title="Download as PDF"><IconDownload /> Download PDF</button>
                  <button className="toolbar-btn" onClick={downloadMd}><IconDownload /> Export MD</button>
                </div>
              </div>

              {/* CONTENT */}
              <div className="preview-content">
                <div className="markdown-scroll">
                  {isEditing ? (
                    <textarea
                      style={{
                        width: '100%',
                        height: '100%',
                        background: 'var(--bg-surface)',
                        border: 'none',
                        outline: 'none',
                        padding: '16px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.9rem',
                        color: 'var(--text-primary)',
                        resize: 'vertical'
                      }}
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      autoFocus
                    />
                  ) : (
                    /* Use the newly extracted MarkdownViewer component */
                    <MarkdownViewer
                      content={results[activeTab]?.markdown || ""}
                      zoom={mdZoom}
                      filename={results[activeTab]?.filename || "untitled"}
                    />
                  )}
                </div>
              </div>

              {/* REVIEW REPORT FOOTER (Optional) */}
              {results[activeTab]?.reviewReport && (
                <div style={{ padding: '16px', borderTop: '1px solid var(--border)', background: 'var(--bg-elevated)', maxHeight: '200px', overflowY: 'auto' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>Review Insights</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>Text Issues</div>
                      {results[activeTab].reviewReport!.text_issues.map((issue, idx) => (
                        <div key={idx} style={{ fontSize: '0.8rem', color: 'var(--error)', marginTop: '4px' }}>&bull; {issue.description}</div>
                      ))}
                      {results[activeTab].reviewReport!.text_issues.length === 0 && <div style={{ fontSize: '0.8rem', color: 'var(--success)' }}>No text issues.</div>}
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>Diagram Issues</div>
                      {results[activeTab].reviewReport!.mermaid_errors.map((issue, idx) => (
                        <div key={idx} style={{ fontSize: '0.8rem', color: 'var(--warning)', marginTop: '4px' }}>&bull; {issue.description}</div>
                      ))}
                      {results[activeTab].reviewReport!.mermaid_errors.length === 0 && <div style={{ fontSize: '0.8rem', color: 'var(--success)' }}>No diagram errors.</div>}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <Dashboard onStartSession={() => document.getElementById('file-input')?.click()} />
          )}
        </section>

        {/* === RIGHT PANEL (CONFIGURATION) === */}
        <aside className="right-panel">
          <div className="right-panel-scroll">
            {/* ADVANCED SETTINGS (Tabbed) */}
            <div className="config-header">Configuration</div>

            <div className="settings-tabs" style={{ display: 'flex', gap: '4px', marginBottom: '16px', background: 'var(--bg-surface)', padding: '4px', borderRadius: '6px' }}>
              {['general', 'models', 'sampling'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveSettingsTab(tab)}
                  style={{
                    flex: 1,
                    textAlign: 'center',
                    padding: '6px',
                    fontSize: '0.75rem',
                    borderRadius: '4px',
                    background: activeSettingsTab === tab ? 'var(--bg-elevated)' : 'transparent',
                    color: activeSettingsTab === tab ? 'var(--accent)' : 'var(--text-secondary)',
                    border: 'none',
                    cursor: 'pointer',
                    fontWeight: 600
                  }}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            {activeSettingsTab === 'general' && (
              <div className="settings-pnl">
                <div className="toggle-row">
                  <span style={{ fontSize: '0.85rem' }}>Fast Mode</span>
                  <input
                    type="checkbox"
                    className="toggle-switch"
                    checked={fastMode}
                    onChange={(e) => setFastMode(e.target.checked)}
                  />
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '-10px' }}>skip refinement step</div>

                <div className="toggle-row">
                  <span style={{ fontSize: '0.85rem' }}>Interactive Review</span>
                  <input
                    type="checkbox"
                    className="toggle-switch"
                    checked={interactiveReview}
                    onChange={(e) => interactiveReviewSet(e.target.checked)}
                  />
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '-10px' }}>Human-in-the-loop audit</div>
              </div>
            )}

            {activeSettingsTab === 'models' && (
              <div className="settings-pnl">
                <div className="form-section">
                  <label className="form-label">
                    Primary Model
                    <span className="tooltip-trigger" data-tooltip="Quickly sets the model for both generation and review.">
                      <IconInfo />
                    </span>
                  </label>
                  <select className="form-select" value={selectedModel} onChange={e => { setSelectedModel(e.target.value); setGenModel(e.target.value); setRevModel(e.target.value); }}>
                    {models.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div className="separator" style={{ borderTop: '1px solid var(--border)' }}></div>
                <div className="form-section">
                  <label className="form-label">
                    Generator Model
                    <span className="tooltip-trigger" data-tooltip="The model responsible for drafting the initial documentation content.">
                      <IconInfo />
                    </span>
                  </label>
                  <select className="form-select" value={genModel} onChange={e => setGenModel(e.target.value)}>
                    {models.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div className="form-section">
                  <label className="form-label">
                    Reviewer Model
                    <span className="tooltip-trigger" data-tooltip="The model used to critique and refine the generated content (if Fast Mode is off).">
                      <IconInfo />
                    </span>
                  </label>
                  <select className="form-select" value={revModel} onChange={e => setRevModel(e.target.value)}>
                    {models.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </div>
            )}

            {activeSettingsTab === 'sampling' && (
              <div className="settings-pnl">
                {/* SAMPLING GROUP */}
                <div className="form-section">
                  <label className="form-label">
                    Temperature: <span style={{ color: 'var(--accent)' }}>{temp}</span>
                    <span className="tooltip-trigger" data-tooltip="Controls randomness. Lower values (e.g. 0.3) represent more deterministic, factual output.">
                      <IconInfo />
                    </span>
                  </label>
                  <input type="range" className="range-input" min="0" max="2" step="0.1" value={temp} onChange={e => setTemp(parseFloat(e.target.value))} />
                </div>
                <div className="form-section">
                  <label className="form-label">
                    Top P: <span style={{ color: 'var(--accent)' }}>{topP}</span>
                    <span className="tooltip-trigger" data-tooltip="Nucleus sampling. Limits choices to the top tokens with cumulative probability P.">
                      <IconInfo />
                    </span>
                  </label>
                  <input type="range" className="range-input" min="0" max="1" step="0.05" value={topP} onChange={e => setTopP(parseFloat(e.target.value))} />
                </div>
                <div className="form-section">
                  <label className="form-label">
                    Top K: <span style={{ color: 'var(--accent)' }}>{topK}</span>
                    <span className="tooltip-trigger" data-tooltip="Limits the next token selection to the K most likely tokens.">
                      <IconInfo />
                    </span>
                  </label>
                  <input type="range" className="range-input" min="0" max="128" step="1" value={topK} onChange={e => setTopK(parseInt(e.target.value))} />
                </div>

                <div className="separator" style={{ borderTop: '1px solid var(--border)', margin: '16px 0' }}></div>

                {/* PENALTY GROUP */}
                <div className="form-section">
                  <label className="form-label">
                    Repeat Penalty: <span style={{ color: 'var(--accent)' }}>{repeatPenalty}</span>
                    <span className="tooltip-trigger" data-tooltip="Penalizes repetition. Values > 1.0 reduce the likelihood of repeating the same text.">
                      <IconInfo />
                    </span>
                  </label>
                  <input type="range" className="range-input" min="1" max="2" step="0.1" value={repeatPenalty} onChange={e => setRepeatPenalty(parseFloat(e.target.value))} />
                </div>
                <div className="form-section">
                  <label className="form-label">
                    Frequency Penalty: <span style={{ color: 'var(--accent)' }}>{frequencyPenalty}</span>
                    <span className="tooltip-trigger" data-tooltip="Penalizes tokens based on their frequency. usage.">
                      <IconInfo />
                    </span>
                  </label>
                  <input type="range" className="range-input" min="-2" max="2" step="0.1" value={frequencyPenalty} onChange={e => setFrequencyPenalty(parseFloat(e.target.value))} />
                </div>
                <div className="form-section">
                  <label className="form-label">
                    Presence Penalty: <span style={{ color: 'var(--accent)' }}>{presencePenalty}</span>
                    <span className="tooltip-trigger" data-tooltip="Penalizes tokens based on their presence. usage.">
                      <IconInfo />
                    </span>
                  </label>
                  <input type="range" className="range-input" min="-2" max="2" step="0.1" value={presencePenalty} onChange={e => setPresencePenalty(parseFloat(e.target.value))} />
                </div>

                <div className="separator" style={{ borderTop: '1px solid var(--border)', margin: '16px 0' }}></div>

                {/* LIMITS GROUP */}
                <div className="form-section">
                  <label className="form-label">
                    Context Window: <span style={{ color: 'var(--accent)' }}>{numCtx}</span>
                    <span className="tooltip-trigger" data-tooltip="Maximum number of tokens the model can 'see' (prompt + generation).">
                      <IconInfo />
                    </span>
                  </label>
                  <input type="range" className="range-input" min="2048" max="32768" step="1024" value={numCtx} onChange={e => setNumCtx(parseInt(e.target.value))} />
                </div>
                <div className="form-section">
                  <label className="form-label">
                    Max Tokens (Pred): <span style={{ color: 'var(--accent)' }}>{numPredict === -1 ? 'Inf' : numPredict}</span>
                    <span className="tooltip-trigger" data-tooltip="Max tokens to predict. -1 for infinite.">
                      <IconInfo />
                    </span>
                  </label>
                  <input type="range" className="range-input" min="-1" max="8192" step="1" value={numPredict} onChange={e => setNumPredict(parseInt(e.target.value))} />
                </div>
              </div>
            )}

          </div>
        </aside>
      </main>
    </div >
  );
}

export default App;
