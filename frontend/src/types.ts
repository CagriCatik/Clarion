export interface ModelList {
    models: string[];
}

export interface ReviewReport {
    confidence_score: number;
    text_issues: { description: string; severity: string; suggestion: string }[];
    mermaid_errors: { description: string; severity: string; fix_suggestion: string }[];
}

export interface DocResult {
    filename: string;
    markdown?: string;
    json?: any;
    reviewReport?: ReviewReport;
    error?: string;
}
