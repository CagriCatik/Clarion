import React from 'react';
import {
    IconPlay, IconFile, IconUpload, IconXCircle,
    IconSettings, IconHourglass
} from './Icons';
import { Tooltip } from './Tooltip';

interface JobControlProps {
    files: File[];
    setFiles: React.Dispatch<React.SetStateAction<File[]>>;
    instruction: string;
    setInstruction: (v: string) => void;
    isProcessing: boolean;
    elapsedTime: number;
    handleGenerate: () => void;
    handleStop: () => void;
    currentStatus: string;
    hasSelection: boolean; // Derived prop: files.length > 0 || selectedKbIds.length > 0
}

export const JobControl: React.FC<JobControlProps> = ({
    files, setFiles,
    instruction, setInstruction,
    isProcessing, elapsedTime,
    handleGenerate, handleStop,
    currentStatus, hasSelection
}) => {

    const removeFile = (index: number) => {
        setFiles((prev) => prev.filter((_, i) => i !== index));
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
        }
    };

    return (
        <div className="card input-card compact-card sidebar-group">
            <div className="sidebar-group-title">
                <div className="icon-label">
                    <IconPlay />
                    <span>Job Execution</span>
                </div>
            </div>
            <div className="field compact-field">
                <label>
                    <div className="icon-label">
                        <IconFile />
                        <span>Input Transcripts</span>
                    </div>
                </label>
                <div className="file-upload-wrapper compact-upload">
                    <input
                        type="file"
                        id="file-upload"
                        className="file-upload-input"
                        accept=".md,.txt"
                        multiple
                        onChange={handleFileUpload}
                    />
                    <label htmlFor="file-upload" className="compact-label">
                        <IconUpload /> <span>Select or Drop Files</span>
                    </label>
                </div>
            </div>

            {files.length > 0 && (
                <div className="selected-files-list">
                    {files.map((f, i) => (
                        <div key={i} className="selected-file-item">
                            <div className="file-info">
                                <IconFile /> <span>{f.name}</span>
                            </div>
                            <button className="remove-file-btn" onClick={() => removeFile(i)}><IconXCircle /></button>
                        </div>
                    ))}
                </div>
            )}

            <div className="field compact-field">
                <label>
                    <div className="icon-label">
                        <IconSettings />
                        <span>Custom Instructions</span>
                    </div>
                </label>
                <textarea
                    className="mini-textarea"
                    placeholder="e.g. Focus on the key takeaways and action items"
                    value={instruction}
                    onChange={(e) => setInstruction(e.target.value)}
                />
            </div>

            <div className="execution-wrap">
                <button
                    className="primary-btn"
                    onClick={handleGenerate}
                    disabled={isProcessing || !hasSelection}
                >
                    {isProcessing ? (
                        <>
                            <div className="hourglass-frame"><IconHourglass /></div>
                            <span>Processing {elapsedTime}s</span>
                        </>
                    ) : (
                        <>
                            <IconPlay />
                            <span>Run Documentation Engine</span>
                        </>
                    )}
                </button>
                {isProcessing && (
                    <div className="sidebar-status-row">
                        <Tooltip text="Stop current generation process">
                            <button className="sidebar-stop-btn" onClick={handleStop}>
                                <IconXCircle />
                            </button>
                        </Tooltip>
                        <div className="sidebar-current-status">
                            <div className="status-pulse"></div>
                            <div className="status-text-col">
                                {currentStatus.startsWith("[") && currentStatus.includes("]") ? (
                                    <>
                                        <span className="status-fname">{currentStatus.split("]")[0].replace("[", "")}</span>
                                        <span className="status-msg">{currentStatus.split("]")[1].trim()}</span>
                                    </>
                                ) : (
                                    <span>{currentStatus || "Thinking..."}</span>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
