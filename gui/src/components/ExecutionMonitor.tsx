import React from 'react';
import { IconActivity } from './Icons';

interface ExecutionMonitorProps {
    statusLog: string[];
    logEndRef: React.RefObject<HTMLDivElement | null>;
    isProcessing: boolean;
    error?: string;
}

export const ExecutionMonitor: React.FC<ExecutionMonitorProps> = ({
    statusLog, logEndRef, isProcessing, error
}) => {
    return (
        <div className={`card status-card compact-card flex-grow ${error ? 'has-error' : ''}`}>
            <div className="card-header compact-header">
                <div className="icon-label">
                    <IconActivity />
                    <span>Execution Monitor</span>
                </div>
                {isProcessing && <div className="spinner-mini"></div>}
            </div>
            {error && (
                <div className="monitor-error-banner">
                    <strong>Error:</strong> {error}
                </div>
            )}
            <div className="log-window compact-log">
                {statusLog.map((log, i) => <div key={i} className="log-line">{log}</div>)}
                <div ref={logEndRef} />
            </div>
        </div>
    );
};
