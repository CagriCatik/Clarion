import React from "react";
import { IconSparkles, IconDraft, IconReview, IconRepair, IconFile } from "./Icons";

interface DashboardProps {
    onStartSession: () => void;
}

export const Dashboard = ({ onStartSession }: DashboardProps) => {
    return (
        <div className="dashboard-container">
            <div className="dashboard-hero">
                <div className="dashboard-icon-ring">
                    <IconSparkles />
                </div>
                <h2 className="dashboard-title">Clarion Engine Ready</h2>
                <p className="dashboard-subtitle">Advanced Epistemic Documentation Assistant. Upload your context files to begin the autonomous drafting process.</p>
            </div>

            <div className="dashboard-grid">
                <div className="dash-card">
                    <div className="dash-card-icon"><IconDraft /></div>
                    <h3>Generator</h3>
                    <p>Drafts comprehensive technical documentation based on your input files and instructions.</p>
                </div>
                <div className="dash-card">
                    <div className="dash-card-icon"><IconReview /></div>
                    <h3>Reviewer</h3>
                    <p>Audits content for compliance, accuracy, and syntax validity using a critic role.</p>
                </div>
                <div className="dash-card">
                    <div className="dash-card-icon"><IconRepair /></div>
                    <h3>Repairer</h3>
                    <p>Automatically fixes detected errors and improves quality through iterative refinement.</p>
                </div>
            </div>

            <div className="dashboard-actions">
                <button
                    className="hero-btn primary"
                    style={{ width: 'auto', minWidth: '200px' }}
                    onClick={onStartSession}
                >
                    <IconFile /> Start New Session
                </button>
            </div>
        </div>
    );
};
