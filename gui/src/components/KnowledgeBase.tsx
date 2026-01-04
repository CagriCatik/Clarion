import React from 'react';
import { IconFolder, IconHelp } from './Icons';
import { Tooltip } from './Tooltip';

interface KbDocument {
    name: string;
    indexed_at: string;
}

interface KnowledgeBaseProps {
    kbDocuments: KbDocument[];
    selectedKbIds: string[];
    setSelectedKbIds: React.Dispatch<React.SetStateAction<string[]>>;
    handleIndexToKb: () => void;
    isProcessing: boolean;
    hasFilesToIndex: boolean;
    fileCount: number;
}

export const KnowledgeBase: React.FC<KnowledgeBaseProps> = ({
    kbDocuments, selectedKbIds, setSelectedKbIds,
    handleIndexToKb, isProcessing, hasFilesToIndex, fileCount
}) => {
    return (
        <div className="card compact-card sidebar-group">
            <div className="sidebar-group-title">
                <div className="icon-label">
                    <IconFolder />
                    <span>Knowledge Base</span>
                    <Tooltip text="Documents in the persistent vector store. Select to add directly to RAG context.">
                        <div className="icon-help"><IconHelp /></div>
                    </Tooltip>
                </div>
            </div>
            <div className="kb-document-list">
                {kbDocuments.length === 0 && (
                    <div className="kb-empty-state">No documents indexed yet.</div>
                )}
                {kbDocuments.map((doc) => (
                    <div key={doc.name} className="kb-document-item">
                        <label>
                            <input
                                type="checkbox"
                                checked={selectedKbIds.includes(doc.name)}
                                onChange={(e) => {
                                    if (e.target.checked) {
                                        setSelectedKbIds(prev => [...prev, doc.name]);
                                    } else {
                                        setSelectedKbIds(prev => prev.filter(id => id !== doc.name));
                                    }
                                }}
                            />
                            <div className="kb-doc-info">
                                <span className="kb-doc-name">{doc.name}</span>
                                <span className="kb-doc-date">{doc.indexed_at}</span>
                            </div>
                        </label>
                    </div>
                ))}
                <div className="sidebar-section-actions">
                    <button
                        className="action-btn-secondary"
                        onClick={handleIndexToKb}
                        disabled={isProcessing || !hasFilesToIndex}
                        style={{ width: '100%', marginTop: '0.5rem' }}
                    >
                        Index {fileCount} Selected File{fileCount !== 1 ? 's' : ''}
                    </button>
                </div>
            </div>
        </div>
    );
};
