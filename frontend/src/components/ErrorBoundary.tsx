import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("ErrorBoundary caught error:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: '2rem', color: 'var(--error)', background: 'var(--bg-elevated)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <h3>Something went wrong rendering this component.</h3>
                    <pre style={{ fontSize: '0.8rem', marginTop: '1rem', overflow: 'auto' }}>
                        {this.state.error?.message}
                    </pre>
                    <button
                        onClick={() => this.setState({ hasError: false })}
                        style={{ marginTop: '1rem', padding: '8px 16px', background: 'var(--primary)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        Try Again
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}
