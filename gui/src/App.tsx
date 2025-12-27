import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import mermaid from "mermaid";
import "./App.css";

// Interface for model response
interface ModelList {
  models: string[];
}

interface DocResult {
  filename: string;
  markdown?: string;
  json?: any;
  error?: string;
}

// Initialize mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: "base",
  themeVariables: {
    darkMode: true,
    primaryColor: '#4f46e5',
    lineColor: '#cbd5e1',
  }
});

// Mermaid Component
// Mermaid Component
const Mermaid = ({ chart }: { chart: string }) => {
  const [svg, setSvg] = useState<string>("");
  // Use a stable ID for this component instance
  const idRef = useRef(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    if (!chart) return;

    let mounted = true;
    const renderChart = async () => {
      try {
        console.log("Rendering Mermaid chart:", idRef.current);
        // Reset SVG while rendering to avoid stale state
        // setSvg(""); 
        const { svg } = await mermaid.render(idRef.current, chart);
        if (mounted) {
          setSvg(svg);
        }
      } catch (e: any) {
        console.error("Mermaid render failed:", e);
        if (mounted) {
          setSvg(`<div class="error" style="color: red; padding: 10px; border: 1px solid red;">
            Failed to render diagram: ${e.message || "Unknown error"}
            <pre style="font-size: 0.7em; overflow: auto; max-height: 100px;">${chart}</pre>
          </div>`);
        }
      }
    };
    renderChart();

    return () => {
      mounted = false;
    };
  }, [chart]);

  return (
    <div
      className="mermaid-wrapper"
      style={{ margin: "1rem 0", background: "transparent", minHeight: "50px" }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

// --- ICONS ---
const IconUpload = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>;
const IconFile = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" /><polyline points="13 2 13 9 20 9" /></svg>;
const IconPlay = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3" /></svg>;
const IconFolder = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /></svg>;
const IconCpu = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2" /><rect x="9" y="9" width="6" height="6" /><line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" /><line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" /><line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" /><line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" /></svg>;
const IconSettings = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>;
const IconSparkles = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /></svg>;

const IconThermometer = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" /></svg>;
const IconDice = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5" /><path d="M16 8h.01" /><path d="M8 8h.01" /><path d="M8 16h.01" /><path d="M16 16h.01" /><path d="M12 12h.01" /></svg>;
const IconLayers = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></svg>;
const IconRepeat = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9" /><path d="M3 11V9a4 4 0 0 1 4-4h14" /><polyline points="7 23 3 19 7 15" /><path d="M21 13v2a4 4 0 0 1-4 4H3" /></svg>;
const IconGhost = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 22H5C3 22 2 20 2 18V7C2 4 4 2 7 2H17C20 2 22 4 22 7V13C22 15 20 16 19 16H15" /><path d="M15 16L12 19L9 16" /></svg>;
const IconActivity = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>;
const IconHelp = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>;
const IconGithub = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>;
const IconCheckCircle = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>;
const IconXCircle = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>;
const IconMenu = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>;

// --- COMPONENTS ---
const Navbar = ({ connected, onToggleSidebar }: { connected: boolean; onToggleSidebar: () => void }) => (
  <nav className="navbar">
    <div className="nav-left">
      <button className="menu-btn mobile-only" onClick={onToggleSidebar}>
        <IconMenu />
      </button>
      <span className="nav-title"> </span>
      <span className="nav-divider"> </span>
      <span className="nav-breadcrumb"> </span>
    </div>
    <div className="nav-right">
      <div className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
        {connected ? <IconCheckCircle /> : <IconXCircle />}
        <span>{connected ? "System Online" : "Backend Offline"}</span>
      </div>
      <a href="https://github.com/CagriCatik/Clarion" target="_blank" rel="noreferrer" className="nav-link">
        <IconGithub />
      </a>
    </div>
  </nav>
);

const Footer = ({ version, onOpenFolder }: { version: string, onOpenFolder: () => void }) => (
  <footer className="footer">
    <div className="footer-left">
      <span className="footer-item">v{version}</span>
      <span className="footer-item">© 2025 Clarion AI</span>
    </div>
    <div className="footer-right">
      <button className="footer-btn" onClick={onOpenFolder}>
        <IconFolder /> Open Outputs
      </button>
    </div>
  </footer>
);

function App() {
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [instruction, setInstruction] = useState<string>("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Advanced Settings
  const [temp, setTemp] = useState(0.2);
  const [topP, setTopP] = useState(0.9);
  const [numCtx, setNumCtx] = useState(8192);
  // defaults for wordBudget/overlap (hidden)
  const wordBudget = 2000;
  const overlap = 2;

  // New Params
  const [presencePenalty, setPresencePenalty] = useState(0.0);
  const [frequencyPenalty, setFrequencyPenalty] = useState(0.0);
  const [repeatPenalty, setRepeatPenalty] = useState(1.1);
  const [topK, setTopK] = useState(40);

  const [isProcessing, setIsProcessing] = useState(false);
  const [statusLog, setStatusLog] = useState<string[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);

  const [results, setResults] = useState<DocResult[]>([]);
  const [error, setError] = useState<string>("");
  const [activeTab, setActiveTab] = useState<number>(0);

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [statusLog]);

  // Fetch models on load
  useEffect(() => {
    fetch("http://localhost:8000/v1/models")
      .then((res) => res.json())
      .then((data: ModelList) => {
        setModels(data.models);
        if (data.models.length > 0) {
          // Prefer qwen3 or llama3
          const pref = data.models.find(m => m.includes("qwen") || m.includes("llama3"));
          setSelectedModel(pref || data.models[0]);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch models", err);
        setError("Failed to connect to backend. Is server.py running?");
      });
  }, []);

  const handleGenerate = async () => {
    if (!files || files.length === 0) {
      setError("Please select at least one file.");
      return;
    }
    setError("");
    setResults([]);
    setStatusLog(["Starting job..."]);
    setIsProcessing(true);

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    formData.append("model", selectedModel);
    if (instruction) formData.append("instruction", instruction);
    formData.append("temperature", temp.toString());
    formData.append("top_p", topP.toString());
    formData.append("num_ctx", numCtx.toString());
    formData.append("word_budget", wordBudget.toString());
    formData.append("overlap", overlap.toString());

    // New params
    formData.append("presence_penalty", presencePenalty.toString());
    formData.append("frequency_penalty", frequencyPenalty.toString());
    formData.append("repeat_penalty", repeatPenalty.toString());
    formData.append("top_k", topK.toString());

    try {
      // Use fetch-event-source logic via standard fetch stream
      const response = await fetch("http://localhost:8000/v1/docgen", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("event: status")) {
            const data = line.split("data: ")[1];
            if (data) setStatusLog(prev => [...prev, data.trim()]);
          } else if (line.startsWith("event: error")) {
            const data = line.split("data: ")[1];
            if (data) setError(data);
          } else if (line.startsWith("event: result")) {
            const data = line.split("data: ")[1];
            if (data) {
              const parsed = JSON.parse(data);
              setResults(parsed.results || []);
              setActiveTab(0);
            }
          }
        }
      }

      setStatusLog(prev => [...prev, "Done."]);

    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleOpenFolder = async () => {
    try {
      await fetch("http://localhost:8000/v1/open_outputs", { method: "POST" });
    } catch (e) {
      console.error("Failed to open folder", e);
      alert("Failed to open outputs folder.");
    }
  };

  return (
    <div className="layout">
      {/* Sidebar */}
      <div className={`sidebar ${isSidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <div className="logo-area">
            <img src="/icon.png" alt="Clarion Logo" style={{ width: 24, height: 24, marginRight: 8 }} />
            <h1>CLARION</h1>
          </div>
          <span className="version">v1.2</span>
        </div>

        <div className="sidebar-scroll">
          <div className="sidebar-section">
            <label><div className="icon-label"><IconCpu /> Model</div></label>
            <div className="select-wrapper">
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={isProcessing}
              >
                {models.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
          </div>

          <div className="sidebar-section">
            <label><div className="icon-label"><IconSettings /> Context Limit</div></label>
            <div className="select-wrapper">
              <select value={numCtx} onChange={(e) => setNumCtx(parseInt(e.target.value))}>
                <option value="2048">2k (Fast)</option>
                <option value="4096">4k (Balanced)</option>
                <option value="8192">8k (Deep)</option>
                <option value="16384">16k (Huge)</option>
                <option value="32768">32k (Max)</option>
              </select>
            </div>
          </div>

          <hr />

          <div className="sidebar-section">
            <label>
              <div className="icon-label">
                <IconThermometer /> Temperature
                <span className="tooltip-wrapper" data-tooltip="Controls randomness. Lower (0.2) is focused/deterministic; Higher (0.8) is creative.">
                  <div className="icon-help"><IconHelp /></div>
                </span>
              </div>
            </label>
            <div className="range-wrap">
              <input type="range" min="0" max="1" step="0.1" value={temp} onChange={(e) => setTemp(parseFloat(e.target.value))} />
              <span className="range-val">{temp}</span>
            </div>
          </div>

          <div className="sidebar-section">
            <label>
              <div className="icon-label">
                <IconDice /> Top P
                <span className="tooltip-wrapper" data-tooltip="Nucleus Sampling. Restricts tokens to the top X% probability mass. 0.9 is standard.">
                  <div className="icon-help"><IconHelp /></div>
                </span>
              </div>
            </label>
            <div className="range-wrap">
              <input type="range" min="0" max="1" step="0.1" value={topP} onChange={(e) => setTopP(parseFloat(e.target.value))} />
              <span className="range-val">{topP}</span>
            </div>
          </div>

          <div className="sidebar-section">
            <label>
              <div className="icon-label">
                <IconLayers /> Top K
                <span className="tooltip-wrapper" data-tooltip="Limits vocabulary to the K most likely next tokens. Lower values reduce nonsense.">
                  <div className="icon-help"><IconHelp /></div>
                </span>
              </div>
            </label>
            <div className="range-wrap">
              <input type="range" min="1" max="100" step="1" value={topK} onChange={(e) => setTopK(parseInt(e.target.value))} />
              <span className="range-val">{topK}</span>
            </div>
          </div>

          <hr />

          <div className="sidebar-section">
            <label>
              <div className="icon-label">
                <IconRepeat /> Repeat Penalty
                <span className="tooltip-wrapper" data-tooltip="Discourages repetition. 1.1 is slight penalization; higher values prevent loops.">
                  <div className="icon-help"><IconHelp /></div>
                </span>
              </div>
            </label>
            <div className="range-wrap">
              <input type="range" min="1.0" max="2.0" step="0.1" value={repeatPenalty} onChange={(e) => setRepeatPenalty(parseFloat(e.target.value))} />
              <span className="range-val">{repeatPenalty}</span>
            </div>
          </div>

          <div className="sidebar-section">
            <label>
              <div className="icon-label">
                <IconGhost /> Presence Penalty
                <span className="tooltip-wrapper" data-tooltip="Penalizes new tokens based on whether they appear in the text so far. Encourages new topics.">
                  <div className="icon-help"><IconHelp /></div>
                </span>
              </div>
            </label>
            <div className="range-wrap">
              <input type="range" min="-2.0" max="2.0" step="0.1" value={presencePenalty} onChange={(e) => setPresencePenalty(parseFloat(e.target.value))} />
              <span className="range-val">{presencePenalty}</span>
            </div>
          </div>

          <div className="sidebar-section">
            <label>
              <div className="icon-label">
                <IconActivity /> Frequency Penalty
                <span className="tooltip-wrapper" data-tooltip="Penalizes tokens based on how many times they have effectively appeared. Reduces verbatim repetition.">
                  <div className="icon-help"><IconHelp /></div>
                </span>
              </div>
            </label>
            <div className="range-wrap">
              <input type="range" min="-2.0" max="2.0" step="0.1" value={frequencyPenalty} onChange={(e) => setFrequencyPenalty(parseFloat(e.target.value))} />
              <span className="range-val">{frequencyPenalty}</span>
            </div>
          </div>
        </div>
      </div>


      {/* Overlay for mobile sidebar */}
      {isSidebarOpen && <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />}

      {/* Main Content */}
      <div className="main">
        <Navbar connected={!error && models.length > 0} onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} />

        <div className="content-container split-layout">

          {/* Left Column: Preview */}
          <div className="preview-column">
            {results.length > 0 ? (
              <div className="results-container card full-height-card">
                <div className="tabs compact-tabs">
                  {results.map((r, idx) => (
                    <button
                      key={idx}
                      className={`tab ${activeTab === idx ? "active" : ""}`}
                      onClick={() => setActiveTab(idx)}
                    >
                      {r.filename}
                    </button>
                  ))}
                </div>

                <div className="result-area compact-area">
                  <div className="result-header compact-header">
                    <h3>Document Preview</h3>
                  </div>
                  <div className="markdown-preview compact-markdown">

                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code(props) {
                          const { children, className, node, ...rest } = props;
                          const match = /language-(\w+)/.exec(className || "");
                          if (match && match[1] === "mermaid") {
                            return <Mermaid chart={String(children).replace(/\n$/, "")} />;
                          }
                          return (
                            <code className={className} {...rest}>
                              {children}
                            </code>
                          );
                        },
                      }}
                    >
                      {results[activeTab].markdown || ""}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-state card full-height-card">
                <div className="empty-content">
                  <IconSparkles />
                  <h3>Ready to Create</h3>
                  <p>Select your transcripts on the right to begin.</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Inputs & Status */}
          <div className="control-column">
            <div className="card input-card compact-card">
              <div className="field compact-field">
                <label><div className="icon-label"><IconFile /> Upload Transcripts</div></label>
                <div className="file-upload-wrapper compact-upload">
                  <input
                    type="file"
                    id="file-upload"
                    className="file-upload-input"
                    accept=".md,.txt"
                    multiple
                    onChange={(e) => setFiles(e.target.files)}
                    disabled={isProcessing}
                  />
                  <label htmlFor="file-upload" className="file-upload-label compact-label">
                    <IconUpload />
                    <span>{files && files.length > 0 ? `${files.length} selected` : "Browse files..."}</span>
                  </label>
                </div>
                {files && files.length > 0 && (
                  <ul className="file-list compact-list">
                    {Array.from(files).map((f, i) => (
                      <li key={i}><IconFile /> <span className="fname">{f.name}</span></li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="field compact-field">
                <label><div className="icon-label"><IconSparkles /> Instructions</div></label>
                <textarea
                  rows={6}
                  className="compact-textarea"
                  placeholder="Write your instructions here..."
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  disabled={isProcessing}
                />
              </div>

              <div className="action-row compact-action">
                <button className="primary-btn compact-btn full-width" onClick={handleGenerate} disabled={isProcessing || !files}>
                  {isProcessing ? "Processing..." : <><IconPlay /> Run Pipeline</>}
                </button>
                {error && <div className="error-msg compact-error">{error}</div>}
              </div>
            </div>

            {/* Status Log */}
            <div className="card status-card compact-card flex-grow">
              <div className="card-header compact-header">
                <h3>Status</h3>
                {isProcessing && <div className="spinner-mini"></div>}
              </div>
              <div className="log-window compact-log">
                {statusLog.map((log, i) => (
                  <div key={i} className="log-line">{log}</div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          </div>

        </div>
        <Footer version="1.2" onOpenFolder={handleOpenFolder} />
      </div>
    </div>
  );
}
export default App;
