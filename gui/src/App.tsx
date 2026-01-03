import { useState, useEffect, useRef, useMemo } from "react";
import { createPortal } from "react-dom";
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
const Mermaid = ({ chart }: { chart: string }) => {
  const [svg, setSvg] = useState<string>("");
  const idRef = useRef(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    if (!chart) return;
    let mounted = true;
    const renderChart = async () => {
      try {
        const { svg } = await mermaid.render(idRef.current, chart);
        if (mounted) setSvg(svg);
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
    return () => { mounted = false; };
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
const IconRefresh = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>;
const IconMenu = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>;

// --- TOOLTIP COMPONENT (PORTAL) ---
const Tooltip = ({ text, children }: { text: string; children: React.ReactNode }) => {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);

  const updatePosition = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const tooltipHeight = 60; // Approximate
      const topSpace = rect.top;

      let top = rect.top + window.scrollY - 8;
      let left = rect.left + window.scrollX + rect.width / 2;

      // Smart repositioning if not enough space at top
      if (topSpace < tooltipHeight + 20) {
        top = rect.bottom + window.scrollY + 8;
        setCoords({ top, left, position: 'bottom' } as any);
      } else {
        setCoords({ top, left, position: 'top' } as any);
      }
    }
  };

  useEffect(() => {
    if (visible) {
      updatePosition();
      window.addEventListener('scroll', updatePosition);
      window.addEventListener('resize', updatePosition);
    }
    return () => {
      window.removeEventListener('scroll', updatePosition);
      window.removeEventListener('resize', updatePosition);
    };
  }, [visible]);

  return (
    <div
      ref={triggerRef}
      className="tooltip-trigger"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && createPortal(
        <div
          className={`tooltip-content ${(coords as any).position || 'top'}`}
          style={{ top: coords.top, left: coords.left }}
        >
          {text}
        </div>,
        document.body
      )}
    </div>
  );
};

// --- COMPONENTS ---
const Navbar = ({ connected, onToggleSidebar, isProcessing, currentStatus, elapsedTime, onStop }: { connected: boolean; onToggleSidebar: () => void; isProcessing: boolean; currentStatus: string; elapsedTime: number; onStop: () => void }) => (
  <nav className="navbar">
    <div className="nav-left">
      <button className="menu-btn mobile-only" onClick={onToggleSidebar}>
        <IconMenu />
      </button>
      <span className="nav-title"> </span>
    </div>
    <div className="nav-right">
      {isProcessing && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="generating-indicator">
            <div className="generating-dot"></div>
            <span className="timer-val">{elapsedTime}s</span>
            <span className="status-text">{currentStatus || "Generating..."}</span>
          </div>
          <button className="stop-btn" onClick={onStop} title="Stop Generation">
            <IconXCircle />
          </button>
        </div>
      )}
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

const Footer = ({ version, onOpenFolder }: { version: string, onOpenFolder: () => void }) => {
  const [metrics, setMetrics] = useState<{ cpu: number, ram: number, gpu?: number | null }>({ cpu: 0, ram: 0, gpu: null });

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch("/v1/metrics");
        const data = await res.json();
        setMetrics(data);
      } catch (e) {
        console.error("Failed to fetch metrics", e);
      }
    };
    const interval = setInterval(fetchMetrics, 3000);
    fetchMetrics();
    return () => clearInterval(interval);
  }, []);

  return (
    <footer className="footer">
      <div className="footer-left">
        <img src="/icon.png" alt="Clarion" className="footer-logo-img" />
        <span className="footer-item" style={{ marginLeft: "8px", fontWeight: 600 }}>Clarion AI</span>
        <div className="footer-divider"></div>
        <span className="footer-item">v{version}</span>
      </div>
      <div className="footer-right">
        <div className="metrics-bar">
          <div className="metric-item">
            <span className="metric-label">CPU</span>
            <span className={`metric-value ${metrics.cpu > 80 ? 'high' : metrics.cpu > 50 ? 'med' : ''}`}>{metrics.cpu}%</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">RAM</span>
            <span className={`metric-value ${metrics.ram > 80 ? 'high' : metrics.ram > 50 ? 'med' : ''}`}>{metrics.ram}%</span>
          </div>
          {metrics.gpu !== null && metrics.gpu !== undefined && (
            <div className="metric-item">
              <span className="metric-label">GPU</span>
              <span className={`metric-value ${metrics.gpu > 80 ? 'high' : metrics.gpu > 50 ? 'med' : ''}`}>{Math.round(metrics.gpu)}%</span>
            </div>
          )}
        </div>
        <button className="footer-btn" onClick={onOpenFolder}>
          <IconFolder /> Open Outputs
        </button>
      </div>
    </footer>
  );
};

function App() {
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [files, setFiles] = useState<File[]>([]);
  const [instruction, setInstruction] = useState<string>("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Advanced Settings
  const [temp, setTemp] = useState(0.2);
  const [topP, setTopP] = useState(0.9);
  const [numCtx, setNumCtx] = useState(8192);
  const [numPredict, setNumPredict] = useState(2048);
  const wordBudget = 2000;
  const overlap = 2;

  const [presencePenalty, setPresencePenalty] = useState(0.0);
  const [frequencyPenalty, setFrequencyPenalty] = useState(0.0);
  const [repeatPenalty, setRepeatPenalty] = useState(1.1);
  const [topK, setTopK] = useState(40);
  const [fastMode, setFastMode] = useState(false);

  const [isProcessing, setIsProcessing] = useState(false);
  const [statusLog, setStatusLog] = useState<string[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);

  const [results, setResults] = useState<DocResult[]>([]);
  const [error, setError] = useState<string>("");
  const [activeTab, setActiveTab] = useState<number>(0);

  const [currentStatus, setCurrentStatus] = useState<string>("");

  const [recentOutputs, setRecentOutputs] = useState<string[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const timerRef = useRef<any>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Timer management
  useEffect(() => {
    if (isProcessing) {
      setElapsedTime(0);
      timerRef.current = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isProcessing]);

  // Fetch models on load
  useEffect(() => {
    fetch("/v1/models")
      .then((res) => res.json())
      .then((data: ModelList) => {
        setModels(data.models);
        if (data.models.length > 0) {
          const pref = data.models.find(m => m.includes("qwen") || m.includes("llama3"));
          setSelectedModel(pref || data.models[0]);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch models", err);
        setError("Failed to connect to backend. Is server.py running?");
      });

    fetchRecentOutputs();
  }, []);

  const fetchRecentOutputs = async () => {
    try {
      const res = await fetch("/v1/outputs");
      const data = await res.json();
      setRecentOutputs(data.outputs || []);
    } catch (e) {
      console.error("Failed to fetch recent outputs", e);
    }
  };

  // Memoize markdown components to prevent flickering
  const markdownComponents = useMemo(() => ({
    code(props: any) {
      const { children, className } = props;
      const match = /language-(\w+)/.exec(className || "");
      if (match && match[1] === "mermaid") return <Mermaid chart={String(children).replace(/\n$/, "")} />;
      return <code className={className}>{children}</code>;
    },
  }), []);

  const handleGenerate = async () => {
    if (files.length === 0) {
      setError("Please select at least one file.");
      return;
    }

    // Create new abort controller
    const controller = new AbortController();
    abortControllerRef.current = controller;

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
    formData.append("num_predict", numPredict.toString());
    formData.append("presence_penalty", presencePenalty.toString());
    formData.append("frequency_penalty", frequencyPenalty.toString());
    formData.append("repeat_penalty", repeatPenalty.toString());
    formData.append("top_k", topK.toString());
    formData.append("fast_mode", fastMode.toString());

    try {
      const response = await fetch("/v1/docgen", {
        method: "POST",
        body: formData,
        signal: controller.signal
      });

      if (!response.ok) throw new Error(`Server error: ${response.statusText}`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No response body");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (!part.trim()) continue;
          if (part.startsWith("event: status")) {
            const data = part.substring(part.indexOf("data: ") + 6).trim();
            setStatusLog(prev => [...prev, data]);
            setCurrentStatus(data);
          } else if (part.startsWith("event: error")) {
            const data = part.substring(part.indexOf("data: ") + 6).trim();
            setError(data);
          } else if (part.startsWith("event: result")) {
            const data = part.substring(part.indexOf("data: ") + 6).trim();
            try {
              const parsed = JSON.parse(data);
              setResults(parsed.results || []);
              setActiveTab(0);
            } catch (e) {
              console.error("JSON parse error", e);
            }
          }
        }
      }
      setStatusLog(prev => [...prev, "Done."]);
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setStatusLog(prev => [...prev, "Process stopped by user."]);
      } else {
        console.error("Generation failed", err);
        setError(err instanceof Error ? err.message : "Generation failed");
      }
    } finally {
      setIsProcessing(false);
      setCurrentStatus("");
      abortControllerRef.current = null;
      fetchRecentOutputs();
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setStatusLog(prev => [...prev, "Aborting process..."]);
    }
  };

  const loadDocument = async (filename: string) => {
    try {
      const res = await fetch(`/v1/outputs/${filename}`);
      const data = await res.json();
      const newResult: DocResult = {
        filename: data.filename,
        markdown: data.markdown
      };
      setResults(prev => {
        const existingIdx = prev.findIndex(r => r.filename === filename);
        if (existingIdx !== -1) {
          const updated = [...prev];
          updated[existingIdx] = newResult;
          return updated;
        }
        return [newResult, ...prev];
      });
      setActiveTab(0);
      setIsEditing(false);
    } catch (e) {
      console.error("Failed to load document", e);
      setError("Failed to load document.");
    }
  };

  const closeDocument = (index: number) => {
    setResults(prev => {
      const updated = prev.filter((_, i) => i !== index);
      // Adjust active tab if needed
      if (activeTab >= updated.length && updated.length > 0) {
        setActiveTab(updated.length - 1);
      }
      return updated;
    });
  };

  const handleSave = async () => {
    if (!results[activeTab]) return;
    setIsSaving(true);
    try {
      const filename = results[activeTab].filename;
      await fetch(`/v1/outputs/${filename}`, {
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
      console.error("Failed to save document", e);
      alert("Failed to save changes.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleOpenFolder = async () => {
    try {
      await fetch("/v1/open_outputs", { method: "POST" });
    } catch (e) {
      console.error("Failed to open folder", e);
      alert("Failed to open outputs folder.");
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="layout">
      {/* Sidebar */}
      <div className={`sidebar ${isSidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <div className="logo-area"><h1>CLARION</h1></div>
          <span className="version">v1.2</span>
        </div>

        <div className="sidebar-scroll">
          <div className="sidebar-section">
            <label><div className="icon-label">
              <IconCpu /> Model
              <Tooltip text="Select the LLM for processing. Large models like 20b take longer.">
                <div className="icon-help"><IconHelp /></div>
              </Tooltip>
            </div></label>
            <div className="select-wrapper">
              <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} disabled={isProcessing}>
                {models.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
          </div>

          <div className="sidebar-section">
            <label><div className="icon-label">
              <IconSettings /> Context Limit
              <Tooltip text="The maximum amount of text processed at once. Higher uses more memory.">
                <div className="icon-help"><IconHelp /></div>
              </Tooltip>
            </div></label>
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

          <div className="sidebar-section">
            <div className="toggle-row">
              <label><div className="icon-label">
                <IconSparkles /> Fast Mode
                <Tooltip text="Skip refinement pass for 2x faster performance. Recommended for 20b models.">
                  <div className="icon-help"><IconHelp /></div>
                </Tooltip>
              </div></label>
              <input type="checkbox" checked={fastMode} onChange={(e) => setFastMode(e.target.checked)} className="toggle-checkbox" disabled={isProcessing} />
            </div>
          </div>

          <hr />

          <div className="sidebar-section">
            <label>
              <div className="icon-label">
                <IconActivity /> Max Output Tokens
                <Tooltip text="Maximum number of tokens to generate. -1 = Infinite/Default.">
                  <div className="icon-help"><IconHelp /></div>
                </Tooltip>
              </div>
            </label>
            <div className="range-wrap">
              <input
                type="range"
                min="-1"
                max="8192"
                step="1"
                value={numPredict}
                onChange={(e) => setNumPredict(parseInt(e.target.value))}
              />
              <span className="range-val">{numPredict === -1 ? "Max" : numPredict}</span>
            </div>
          </div>

          <div className="sidebar-section">
            <label>
              <div className="icon-label">
                <IconThermometer /> Temperature
                <Tooltip text="Controls randomness. Lower (0.2) is focused/deterministic; Higher (0.8) is creative.">
                  <div className="icon-help"><IconHelp /></div>
                </Tooltip>
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
                <Tooltip text="Nucleus Sampling. Restricts tokens to the top X% probability mass. 0.9 is standard.">
                  <div className="icon-help"><IconHelp /></div>
                </Tooltip>
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
                <Tooltip text="Limits vocabulary to the K most likely next tokens. Lower values reduce nonsense.">
                  <div className="icon-help"><IconHelp /></div>
                </Tooltip>
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
                <Tooltip text="Discourages repetition. 1.1 is slight penalization; higher values prevent loops.">
                  <div className="icon-help"><IconHelp /></div>
                </Tooltip>
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
                <Tooltip text="Penalizes new tokens based on whether they appear in the text so far. Encourages new topics.">
                  <div className="icon-help"><IconHelp /></div>
                </Tooltip>
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
                <Tooltip text="Penalizes tokens based on how many times they have effectively appeared. Reduces verbatim repetition.">
                  <div className="icon-help"><IconHelp /></div>
                </Tooltip>
              </div>
            </label>
            <div className="range-wrap">
              <input type="range" min="-2.0" max="2.0" step="0.1" value={frequencyPenalty} onChange={(e) => setFrequencyPenalty(parseFloat(e.target.value))} />
              <span className="range-val">{frequencyPenalty}</span>
            </div>
          </div>

          <hr />

          <div className="sidebar-section">
            <label>
              <div className="icon-label">
                <IconFolder /> Recent Outputs
                <button className="icon-btn mini-btn" onClick={fetchRecentOutputs} title="Refresh Files">
                  <IconRefresh />
                </button>
              </div>
            </label>
            <ul className="file-list compact-list history-list">
              {recentOutputs.length === 0 ? <li className="empty-history">No recent documents</li> :
                recentOutputs.map((fname, i) => (
                  <li key={i} className="history-item" onClick={() => loadDocument(fname)}>
                    <IconFile /> <span className="fname">{fname}</span>
                  </li>
                ))
              }
            </ul>
          </div>
        </div>
      </div>

      {isSidebarOpen && <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />}

      {/* Main Content */}
      <div className="main">
        <Navbar
          connected={!error && models.length > 0}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          isProcessing={isProcessing}
          currentStatus={currentStatus}
          elapsedTime={elapsedTime}
          onStop={handleStop}
        />

        <div className="content-container split-layout">
          <div className="preview-column">
            {results.length > 0 ? (
              <div className="results-container card full-height-card">
                <div className="tabs compact-tabs">
                  {results.map((r, idx) => (
                    <div key={idx} className={`tab-item ${activeTab === idx ? "active" : ""}`} onClick={() => setActiveTab(idx)}>
                      <span className="tab-name">{r.filename}</span>
                      <button
                        className="close-tab-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          closeDocument(idx);
                        }}
                        title="Close tab"
                      >
                        <IconXCircle />
                      </button>
                    </div>
                  ))}
                </div>

                <div className="result-area compact-area">
                  <div className="result-header compact-header">
                    <h3>Document Preview</h3>
                    <div className="header-actions">
                      {isEditing ? (
                        <>
                          <button className="secondary-btn mini-btn" onClick={() => setIsEditing(false)}>Cancel</button>
                          <button className="primary-btn mini-btn" onClick={handleSave} disabled={isSaving}>{isSaving ? "Saving..." : "Save Changes"}</button>
                        </>
                      ) : (
                        <button className="secondary-btn mini-btn" onClick={() => { setEditContent(results[activeTab].markdown || ""); setIsEditing(true); }}>Edit Content</button>
                      )}
                    </div>
                  </div>
                  <div className="markdown-preview compact-markdown">
                    {isEditing ? (
                      <textarea className="edit-textarea" value={editContent} onChange={(e) => setEditContent(e.target.value)} autoFocus />
                    ) : (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={markdownComponents}
                      >{results[activeTab].markdown || ""}</ReactMarkdown>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-state card full-height-card">
                <div className="empty-content"><IconSparkles /><h3>Documentation Engine</h3><p>Upload files or select a recent document to begin.</p></div>
              </div>
            )}
          </div>

          <div className="control-column">
            <div className="card input-card compact-card">
              <div className="field compact-field">
                <label><div className="icon-label"><IconFile /> Input Transcripts</div></label>
                <div className="file-upload-wrapper compact-upload">
                  <input type="file" id="file-upload" className="file-upload-input" accept=".md,.txt" multiple onChange={(e) => {
                    if (e.target.files) {
                      const newFiles = Array.from(e.target.files);
                      setFiles(prev => [...prev, ...newFiles.filter(f => !prev.find(p => p.name === f.name))]);
                      e.target.value = "";
                    }
                  }} disabled={isProcessing} />
                  <label htmlFor="file-upload" className="file-upload-label compact-label"><IconUpload /><span>{files.length > 0 ? `${files.length} selected` : "Load files..."}</span></label>
                </div>
                {files.length > 0 && (
                  <ul className="file-list compact-list">
                    {files.map((f, i) => (
                      <li key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", overflow: "hidden" }}><IconFile /> <span className="fname">{f.name}</span></div>
                        <button onClick={() => removeFile(i)} style={{ background: "transparent", border: "none", color: "#ef4444", cursor: "pointer", padding: "4px" }}><IconXCircle /></button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="field compact-field">
                <label><div className="icon-label"><IconSparkles /> Custom Instructions</div></label>
                <textarea rows={6} className="compact-textarea" placeholder="Optional: specific rules for this document..." value={instruction} onChange={(e) => setInstruction(e.target.value)} disabled={isProcessing} />
              </div>

              <div className="action-row compact-action">
                <button className="primary-btn compact-btn full-width" onClick={handleGenerate} disabled={isProcessing || files.length === 0}>
                  {isProcessing ? "Processing..." : <><IconPlay /> Run Generation</>}
                </button>
                {error && <div className="error-msg compact-error">{error}</div>}
              </div>
            </div>

            <div className="card status-card compact-card flex-grow">
              <div className="card-header compact-header"><h3>Process Status</h3>{isProcessing && <div className="spinner-mini"></div>}</div>
              <div className="log-window compact-log">
                {statusLog.map((log, i) => <div key={i} className="log-line">{log}</div>)}
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
