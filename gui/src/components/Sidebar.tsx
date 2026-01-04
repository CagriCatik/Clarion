import React from 'react';
import {
    IconLogo, IconCpu, IconHelp, IconLayers, IconSparkles,
    IconSettings, IconSearch, IconScissors, IconActivity,
    IconThermometer, IconFile, IconDice, IconRepeat,
    IconRefresh
} from './Icons';
import { Tooltip } from './Tooltip';

interface SidebarProps {
    isSidebarOpen: boolean;
    setIsSidebarOpen: (v: boolean) => void;
    models: string[];
    selectedModel: string;
    setSelectedModel: (v: string) => void;
    embeddingModels: string[];
    selectedEmbeddingModel: string;
    setSelectedEmbeddingModel: (v: string) => void;
    useRag: boolean;
    setUseRag: (v: boolean) => void;
    fastMode: boolean;
    setFastMode: (v: boolean) => void;
    numCtx: number;
    setNumCtx: (v: number) => void;
    ragK: number;
    setRagK: (v: number) => void;
    chunkSize: number;
    setChunkSize: (v: number) => void;
    chunkOverlap: number;
    setChunkOverlap: (v: number) => void;
    numPredict: number;
    setNumPredict: (v: number) => void;
    wordBudget: number;
    setWordBudget: (v: number) => void;
    temp: number;
    setTemp: (v: number) => void;
    topP: number;
    setTopP: (v: number) => void;
    topK: number;
    setTopK: (v: number) => void;
    repeatPenalty: number;
    setRepeatPenalty: (v: number) => void;
    presencePenalty: number;
    setPresencePenalty: (v: number) => void;
    frequencyPenalty: number;
    setFrequencyPenalty: (v: number) => void;
    recentOutputs: string[];
    fetchRecentOutputs: () => void;
    loadDocument: (fname: string) => void;
    isProcessing: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
    isSidebarOpen, setIsSidebarOpen,
    models, selectedModel, setSelectedModel,
    embeddingModels, selectedEmbeddingModel, setSelectedEmbeddingModel,
    useRag, setUseRag,
    fastMode, setFastMode,
    numCtx, setNumCtx,
    ragK, setRagK,
    chunkSize, setChunkSize,
    chunkOverlap, setChunkOverlap,
    numPredict, setNumPredict,
    wordBudget, setWordBudget,
    temp, setTemp,
    topP, setTopP,
    topK, setTopK,
    repeatPenalty, setRepeatPenalty,
    presencePenalty, setPresencePenalty,
    frequencyPenalty, setFrequencyPenalty,
    recentOutputs, fetchRecentOutputs, loadDocument, isProcessing
}) => {
    return (
        <>
            <div className={`sidebar ${isSidebarOpen ? "open" : ""}`}>
                <div className="sidebar-header">
                    <div className="logo-area">
                        <IconLogo />
                        <h1>CLARION</h1>
                    </div>
                    <span className="version">v1.2</span>
                </div>

                <div className="sidebar-scroll">
                    <div className="sidebar-group">
                        <div className="sidebar-group-title">
                            <div className="icon-label">
                                <IconCpu />
                                <span>Engine Config</span>
                            </div>
                        </div>
                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconCpu />
                                    <span>Generation Model</span>
                                    <Tooltip text="Select the primary LLM for drafting and refining content.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
                            <div className="select-wrapper">
                                <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} disabled={isProcessing}>
                                    {models.map((m) => <option key={m} value={m}>{m}</option>)}
                                </select>
                            </div>
                        </div>

                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconLayers />
                                    <span>Embedding Model</span>
                                    <Tooltip text="Select the model for RAG embeddings. Nomic-embed-text is highly recommended.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
                            <div className="select-wrapper">
                                <select value={selectedEmbeddingModel} onChange={(e) => setSelectedEmbeddingModel(e.target.value)} disabled={isProcessing}>
                                    {embeddingModels.map((m) => <option key={m} value={m}>{m}</option>)}
                                    {embeddingModels.length === 0 && <option value="">No embeddings found</option>}
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="sidebar-group">
                        <div className="sidebar-group-title">
                            <div className="icon-label">
                                <IconSparkles />
                                <span>AI Optimization</span>
                            </div>
                        </div>
                        <div className="sidebar-section">
                            <div className="toggle-row">
                                <label>
                                    <IconLayers />
                                    <span>RAG Optimization</span>
                                    <input type="checkbox" checked={useRag} onChange={(e) => setUseRag(e.target.checked)} className="toggle-checkbox" disabled={isProcessing} />
                                    <Tooltip text="Retrieval-Augmented Generation: Dynamically inject only relevant guidelines to save tokens and reduce latency.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </label>
                            </div>
                        </div>

                        <div className="sidebar-section">
                            <div className="toggle-row">
                                <label>
                                    <IconSparkles />
                                    <span>Fast Mode</span>
                                    <input type="checkbox" checked={fastMode} onChange={(e) => setFastMode(e.target.checked)} className="toggle-checkbox" disabled={isProcessing} />
                                    <Tooltip text="Skip refinement pass for 2x faster performance. Best for large, capable models.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </label>
                            </div>
                        </div>

                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconSettings />
                                    <span>Context Limit</span>
                                    <Tooltip text="Max input tokens per chunk. Higher values capture more context but use more VRAM.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
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

                        {useRag && (
                            <div className="sidebar-section">
                                <label>
                                    <div className="icon-label">
                                        <IconSearch />
                                        <span>Top K Docs</span>
                                        <Tooltip text="Number of relevant guideline chunks to retrieve for each context block.">
                                            <div className="icon-help"><IconHelp /></div>
                                        </Tooltip>
                                    </div>
                                </label>
                                <div className="range-wrap">
                                    <input type="range" min="1" max="15" step="1" value={ragK} onChange={(e) => setRagK(parseInt(e.target.value))} />
                                    <span className="range-val">{ragK}</span>
                                </div>
                            </div>
                        )}

                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconScissors />
                                    <span>Chunk Size</span>
                                    <Tooltip text="Character limit for each processing block. Affects RAG precision and context depth.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
                            <div className="range-wrap">
                                <input type="range" min="1000" max="10000" step="500" value={chunkSize} onChange={(e) => setChunkSize(parseInt(e.target.value))} />
                                <span className="range-val">{chunkSize}</span>
                            </div>
                        </div>

                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconActivity />
                                    <span>Chunk Overlap</span>
                                    <Tooltip text="Character overlap between semantic blocks to maintain context continuity.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
                            <div className="range-wrap">
                                <input type="range" min="0" max="2000" step="100" value={chunkOverlap} onChange={(e) => setChunkOverlap(parseInt(e.target.value))} />
                                <span className="range-val">{chunkOverlap}</span>
                            </div>
                        </div>
                    </div>

                    <div className="sidebar-group">
                        <div className="sidebar-group-title">
                            <div className="icon-label">
                                <IconThermometer />
                                <span>Generation Tuning</span>
                            </div>
                        </div>
                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconActivity />
                                    <span>Output Budget</span>
                                    <Tooltip text="Maximum tokens for the generated response.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
                            <div className="range-wrap">
                                <input type="range" min="-1" max="8192" step="64" value={numPredict} onChange={(e) => setNumPredict(parseInt(e.target.value))} />
                                <span className="range-val">{numPredict === -1 ? "Max" : numPredict}</span>
                            </div>
                        </div>

                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconFile />
                                    <span>Word Target</span>
                                    <Tooltip text="Direct target for document length. Affects how much detail the model includes.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
                            <div className="range-wrap">
                                <input type="range" min="500" max="10000" step="100" value={wordBudget} onChange={(e) => setWordBudget(parseInt(e.target.value))} />
                                <span className="range-val">{wordBudget}</span>
                            </div>
                        </div>

                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconThermometer />
                                    <span>Creativity (Temp)</span>
                                    <Tooltip text="Higher values (0.8+) are more creative/random; lower (0.2) are more focused.">
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
                                    <IconDice />
                                    <span>Nucleus (Top P)</span>
                                    <Tooltip text="Limits vocabulary to the top probability mass. 0.9 is ideal for most tasks.">
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
                                    <IconDice />
                                    <span>Top K</span>
                                    <Tooltip text="Lower values (e.g. 40) make the model more deterministic by only considering the top K tokens.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
                            <div className="range-wrap">
                                <input type="range" min="0" max="100" step="1" value={topK} onChange={(e) => setTopK(parseInt(e.target.value))} />
                                <span className="range-val">{topK}</span>
                            </div>
                        </div>

                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconRepeat />
                                    <span>Repeat Penalty</span>
                                    <Tooltip text="Prevents the model from repeating the same phrases. 1.1 is standard.">
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
                                    <IconActivity />
                                    <span>Presence Penalty</span>
                                    <Tooltip text="Encourages the model to talk about new topics.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
                            <div className="range-wrap">
                                <input type="range" min="0.0" max="2.0" step="0.1" value={presencePenalty} onChange={(e) => setPresencePenalty(parseFloat(e.target.value))} />
                                <span className="range-val">{presencePenalty}</span>
                            </div>
                        </div>

                        <div className="sidebar-section">
                            <label>
                                <div className="icon-label">
                                    <IconActivity />
                                    <span>Freq. Penalty</span>
                                    <Tooltip text="Reduces the likelihood of repeating words or phrases.">
                                        <div className="icon-help"><IconHelp /></div>
                                    </Tooltip>
                                </div>
                            </label>
                            <div className="range-wrap">
                                <input type="range" min="0.0" max="2.0" step="0.1" value={frequencyPenalty} onChange={(e) => setFrequencyPenalty(parseFloat(e.target.value))} />
                                <span className="range-val">{frequencyPenalty}</span>
                            </div>
                        </div>
                    </div>

                    <div className="sidebar-group">
                        <div className="sidebar-group-title">
                            <div className="icon-label">
                                <IconRepeat />
                                <span>Output History</span>
                                <button className="icon-btn mini-btn" onClick={fetchRecentOutputs} title="Refresh Files">
                                    <IconRefresh />
                                </button>
                            </div>
                        </div>
                        <div className="sidebar-section">
                            <ul className="file-list compact-list history-list">
                                {recentOutputs.length === 0 ? <li className="empty-history">No documents found</li> :
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
            </div>
            {isSidebarOpen && <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />}
        </>
    );
};
