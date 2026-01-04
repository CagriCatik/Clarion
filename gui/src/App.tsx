import { useState, useEffect, useRef } from "react";
import "./App.css";

// Components
import { Navbar } from "./components/Navbar";
import { Footer } from "./components/Footer";
import { Sidebar } from "./components/Sidebar";
import { JobControl } from "./components/JobControl";
import { KnowledgeBase } from "./components/KnowledgeBase";
import { ExecutionMonitor } from "./components/ExecutionMonitor";
import { DocumentWorkspace } from "./components/DocumentWorkspace";

// Interface for model response
interface ModelList {
  models: string[];
  embeddings: string[];
}

interface DocResult {
  filename: string;
  markdown?: string;
  json?: any;
  error?: string;
}

function App() {
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [embeddingModels, setEmbeddingModels] = useState<string[]>([]);
  const [selectedEmbeddingModel, setSelectedEmbeddingModel] = useState<string>("");
  const [files, setFiles] = useState<File[]>([]);
  const [instruction, setInstruction] = useState<string>("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Advanced Settings
  const [temp, setTemp] = useState<number>(0.2);
  const [topP, setTopP] = useState<number>(0.9);
  const [topK, setTopK] = useState<number>(40);
  const [numCtx, setNumCtx] = useState<number>(8192);
  const [numPredict, setNumPredict] = useState<number>(4096);
  const [wordBudget, setWordBudget] = useState<number>(2000);
  const overlap = 2; // Fixed internal value

  const [repeatPenalty, setRepeatPenalty] = useState<number>(1.1);
  const [presencePenalty, setPresencePenalty] = useState<number>(0.0);
  const [frequencyPenalty, setFrequencyPenalty] = useState<number>(0.0);
  const [fastMode, setFastMode] = useState(false);
  const [useRag, setUseRag] = useState(false);
  const [ragK, setRagK] = useState<number>(5);
  const [chunkSize, setChunkSize] = useState<number>(4000);
  const [chunkOverlap, setChunkOverlap] = useState<number>(500);

  const [kbDocuments, setKbDocuments] = useState<any[]>([]);
  const [selectedKbIds, setSelectedKbIds] = useState<string[]>([]);

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

        setEmbeddingModels(data.embeddings);
        if (data.embeddings.length > 0) {
          const prefEmbed = data.embeddings.find(m => m.includes("nomic") || m.includes("bge"));
          setSelectedEmbeddingModel(prefEmbed || data.embeddings[0]);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch models", err);
        setError("Failed to connect to backend. Is server.py running?");
      });

    fetchRecentOutputs();
    fetchKbDocuments();
  }, []);

  const fetchKbDocuments = async () => {
    try {
      const res = await fetch("/v1/kb/documents");
      const data = await res.json();
      setKbDocuments(data.documents || []);
    } catch (e) {
      console.error("Failed to fetch KB documents", e);
    }
  };

  const fetchRecentOutputs = async () => {
    try {
      const res = await fetch("/v1/outputs");
      const data = await res.json();
      setRecentOutputs(data.outputs || []);
    } catch (e) {
      console.error("Failed to fetch recent outputs", e);
    }
  };

  const handleGenerate = async () => {
    if (files.length === 0 && selectedKbIds.length === 0) {
      setError("Please select at least one file or Knowledge Base document.");
      alert("Please select at least one file or Knowledge Base document."); // Added alert for visibility
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
    if (files.length === 0 && selectedKbIds.length > 0) {
      // Create a dummy placeholder file
      const dummyContent = instruction || "Generate documentation based on the selected Knowledge Base documents.";
      const dummyFile = new File([dummyContent], "KB_Context_Request.txt", { type: "text/plain" });
      formData.append("files", dummyFile);
    } else {
      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }
    }

    formData.append("model", selectedModel);
    if (selectedEmbeddingModel) formData.append("embedding_model", selectedEmbeddingModel);
    if (instruction) formData.append("instruction", instruction);
    formData.append("temperature", temp.toString());
    formData.append("top_p", topP.toString());
    formData.append("top_k", topK.toString());
    formData.append("repeat_penalty", repeatPenalty.toString());
    formData.append("presence_penalty", presencePenalty.toString());
    formData.append("frequency_penalty", frequencyPenalty.toString());
    formData.append("num_ctx", numCtx.toString());
    formData.append("word_budget", wordBudget.toString());
    formData.append("overlap", overlap.toString());
    formData.append("num_predict", numPredict.toString());
    formData.append("fast_mode", fastMode.toString());
    formData.append("use_rag", useRag.toString());

    // RAG Tuning Bindings
    formData.append("rag_k", ragK.toString());
    formData.append("chunk_size", chunkSize.toString());
    formData.append("chunk_overlap", chunkOverlap.toString());
    formData.append("selected_kb_ids", JSON.stringify(selectedKbIds));

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
              // Handle new MultiDocResponse format
              if (parsed.documents && Array.isArray(parsed.documents)) {
                const docResults: DocResult[] = parsed.documents.map((doc: any) => ({
                  filename: doc.filename,
                  markdown: doc.content,
                  json: { thought_process: doc.thought_process }
                }));
                setResults(docResults);
              } else {
                // Backward compatibility
                setResults(parsed.results || []);
              }
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

  const handleIndexToKb = async () => {
    if (files.length === 0) return;
    setIsProcessing(true);
    setCurrentStatus("Indexing files to KB...");
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        if (selectedEmbeddingModel) formData.append("embedding_model", selectedEmbeddingModel);

        await fetch("/v1/kb/index", {
          method: "POST",
          body: formData
        });
      }
      setCurrentStatus("Indexing complete.");
      fetchKbDocuments();
    } catch (e) {
      console.error("Failed to index to KB", e);
      setError("Failed to index files to Knowledge Base.");
    } finally {
      setIsProcessing(false);
      setCurrentStatus("");
    }
  };

  return (
    <div className="layout">
      {/* Sidebar */}
      <Sidebar
        isSidebarOpen={isSidebarOpen} setIsSidebarOpen={setIsSidebarOpen}
        models={models} selectedModel={selectedModel} setSelectedModel={setSelectedModel}
        embeddingModels={embeddingModels} selectedEmbeddingModel={selectedEmbeddingModel} setSelectedEmbeddingModel={setSelectedEmbeddingModel}
        useRag={useRag} setUseRag={setUseRag}
        fastMode={fastMode} setFastMode={setFastMode}
        numCtx={numCtx} setNumCtx={setNumCtx}
        ragK={ragK} setRagK={setRagK}
        chunkSize={chunkSize} setChunkSize={setChunkSize}
        chunkOverlap={chunkOverlap} setChunkOverlap={setChunkOverlap}
        numPredict={numPredict} setNumPredict={setNumPredict}
        wordBudget={wordBudget} setWordBudget={setWordBudget}
        temp={temp} setTemp={setTemp}
        topP={topP} setTopP={setTopP}
        topK={topK} setTopK={setTopK}
        repeatPenalty={repeatPenalty} setRepeatPenalty={setRepeatPenalty}
        presencePenalty={presencePenalty} setPresencePenalty={setPresencePenalty}
        frequencyPenalty={frequencyPenalty} setFrequencyPenalty={setFrequencyPenalty}
        recentOutputs={recentOutputs} fetchRecentOutputs={fetchRecentOutputs}
        loadDocument={loadDocument} isProcessing={isProcessing}
      />

      <div className="main-wrapper">
        <Navbar connected={true} onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} />

        <div className="content-area">
          {/* Main Center Area */}
          <DocumentWorkspace
            results={results}
            activeTab={activeTab} setActiveTab={setActiveTab}
            isEditing={isEditing} setIsEditing={setIsEditing}
            editContent={editContent} setEditContent={setEditContent}
            handleSave={handleSave} isSaving={isSaving}
            closeDocument={closeDocument}
          />

          {/* Right Control Column */}
          <div className="control-column">
            <JobControl
              files={files} setFiles={setFiles}
              instruction={instruction} setInstruction={setInstruction}
              isProcessing={isProcessing} elapsedTime={elapsedTime}
              handleGenerate={handleGenerate} handleStop={handleStop}
              currentStatus={currentStatus}
              hasSelection={files.length > 0 || selectedKbIds.length > 0}
            />

            <KnowledgeBase
              kbDocuments={kbDocuments}
              selectedKbIds={selectedKbIds} setSelectedKbIds={setSelectedKbIds}
              handleIndexToKb={handleIndexToKb}
              isProcessing={isProcessing}
              hasFilesToIndex={files.length > 0}
              fileCount={files.length}
            />

            <ExecutionMonitor
              statusLog={statusLog}
              logEndRef={logEndRef}
              isProcessing={isProcessing}
              error={error}
            />
          </div>
        </div>

        <Footer version="1.2" onOpenFolder={handleOpenFolder} />
      </div>
    </div>
  );
}

export default App;
