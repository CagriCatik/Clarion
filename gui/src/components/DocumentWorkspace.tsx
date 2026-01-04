import React, { useMemo } from 'react';
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Mermaid } from './Mermaid';
import { IconFile, IconXCircle, IconZoomIn, IconZoomOut, IconDownload } from './Icons';

interface DocResult {
    filename: string;
    markdown?: string;
    json?: any;
    error?: string;
}

interface DocumentWorkspaceProps {
    results: DocResult[];
    activeTab: number;
    setActiveTab: (i: number) => void;
    isEditing: boolean;
    setIsEditing: (v: boolean) => void;
    editContent: string;
    setEditContent: (v: string) => void;
    handleSave: () => void;
    isSaving: boolean;
    closeDocument: (i: number) => void;
}

// Minimal Icon for empty state if not in icons file, otherwise import
const IconEmptyStateDefault = () => (
    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--text-muted)', opacity: 0.5 }}>
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
        <polyline points="13 2 13 9 20 9" />
    </svg>
);

export const DocumentWorkspace: React.FC<DocumentWorkspaceProps> = ({
    results, activeTab, setActiveTab,
    isEditing, setIsEditing,
    editContent, setEditContent,
    handleSave, isSaving, closeDocument
}) => {

    const markdownComponents = useMemo(() => ({
        code(props: any) {
            const { children, className, node, ...rest } = props;
            const match = /language-(\w+)/.exec(className || "");

            if (match && match[1] === "mermaid") {
                return <Mermaid chart={String(children).replace(/\n$/, "")} />;
            }

            const language = match ? match[1] : "";
            return match ? (
                <SyntaxHighlighter
                    {...rest}
                    children={String(children).replace(/\n$/, "")}
                    style={vscDarkPlus}
                    language={language}
                    PreTag="div"
                    className="syntax-highlighter"
                />
            ) : (
                <code {...rest} className={className}>
                    {children}
                </code>
            );
        },
    }), []);

    const [zoomLevel, setZoomLevel] = React.useState(100);

    const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 10, 200));
    const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 10, 50));
    const handlePrint = () => window.print();

    const handleEditClick = () => {
        setEditContent(results[activeTab]?.markdown || "");
        setIsEditing(true);
    };

    if (results.length === 0) {
        return (
            <div className="main-content">
                <div className="empty-state">
                    <IconEmptyStateDefault />
                    <h3>No Documents Generated</h3>
                    <p>Upload a transcript and click Run to generate documentation.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="main-content">
            <div className="tabs-header">
                {results.map((r, i) => (
                    <div
                        key={i}
                        className={`tab-item ${i === activeTab ? "active" : ""}`}
                        onClick={() => setActiveTab(i)}
                    >
                        <IconFile />
                        <span className="tab-name">{r.filename}</span>
                        <span
                            className="tab-close"
                            onClick={(e) => {
                                e.stopPropagation();
                                closeDocument(i);
                            }}
                        >
                            <IconXCircle />
                        </span>
                    </div>
                ))}
            </div>

            <div className="document-toolbar">
                <div className="toolbar-group">
                    <button className="toolbar-btn" onClick={handleZoomOut} title="Zoom Out">
                        <IconZoomOut />
                    </button>
                    <span className="zoom-label">{zoomLevel}%</span>
                    <button className="toolbar-btn" onClick={handleZoomIn} title="Zoom In">
                        <IconZoomIn />
                    </button>

                    <div className="toolbar-divider" />

                    <button className="toolbar-btn" onClick={handlePrint} title="Export PDF">
                        <IconDownload />
                    </button>
                </div>

                <div className="toolbar-group">
                    {isEditing ? (
                        <>
                            <button className="action-btn primary" onClick={handleSave} disabled={isSaving}>
                                {isSaving ? "Saving..." : "Save Changes"}
                            </button>
                            <button className="action-btn secondary" onClick={() => setIsEditing(false)}>Cancel</button>
                        </>
                    ) : (
                        <button className="action-btn secondary" onClick={handleEditClick}>Edit Code</button>
                    )}
                </div>
            </div>

            <div className="document-container">
                {results[activeTab] && (
                    <>
                        {isEditing ? (
                            <div className="editor-pane">
                                <textarea
                                    className="code-editor"
                                    value={editContent}
                                    onChange={(e) => setEditContent(e.target.value)}
                                />
                            </div>
                        ) : (
                            <div className="markdown-preview">
                                <div style={{ fontSize: `${zoomLevel}%` }}>
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={markdownComponents}
                                    >
                                        {results[activeTab].markdown || ""}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
};
