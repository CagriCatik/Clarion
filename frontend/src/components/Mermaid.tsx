import React, { useState, useEffect } from "react";
import mermaid from "mermaid";
import { IconZoomIn, IconZoomOut } from "./Icons";

// =====================================================
// MERMAID INITIALIZATION
// =====================================================
mermaid.initialize({
    startOnLoad: false,
    suppressErrorRendering: true,
    theme: "base",
    themeVariables: {
        darkMode: true,
        primaryColor: '#06b6d4',
        lineColor: '#a1a1aa',
        textColor: '#fafafa',
    }
});

// =====================================================
// MERMAID QUEUE (Prevents concurrency crashes)
// =====================================================
class MermaidQueue {
    private queue: Promise<any> = Promise.resolve();

    enqueue<T>(task: () => Promise<T>): Promise<T> {
        const next = this.queue.then(() => task().catch(e => {
            console.warn("Mermaid task error:", e);
            throw e;
        }));
        this.queue = next.then(() => { }, () => { }); // swallow error for queue continuation
        return next;
    }
}

const mermaidQueue = new MermaidQueue();

// =====================================================
// MERMAID COMPONENT
// =====================================================
export const Mermaid = ({ chart }: { chart: string }) => {
    const [svg, setSvg] = useState<string>("");
    const [scale, setScale] = useState(1);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (!chart) return;

        let mounted = true;
        setIsLoading(true);
        const renderId = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        const renderChart = async () => {
            // Wrap the render in our global queue
            await mermaidQueue.enqueue(async () => {
                if (!mounted) return; // check mounted inside queue execution

                try {
                    const { svg } = await mermaid.render(renderId, chart);
                    if (mounted) {
                        setSvg(svg);
                        setScale(1);
                        setPosition({ x: 0, y: 0 });
                        setIsLoading(false);
                    }
                    // Cleanup
                    try {
                        const tempElement = document.getElementById(renderId);
                        if (tempElement) tempElement.remove();
                    } catch (e) { /* ignore */ }

                } catch (e: any) {
                    console.error("Mermaid render failed:", e);
                    if (mounted) {
                        // Cleanup
                        try {
                            const tempElement = document.getElementById(renderId);
                            if (tempElement) tempElement.remove();
                        } catch (e) { /* ignore */ }

                        setSvg(`<div style="color: #ef4444; padding: 1rem; border: 1px solid #ef4444; border-radius: 0.5rem; background: rgba(239, 68, 68, 0.1); height: 100%; overflow: auto;">
                  <div style="font-weight: bold; margin-bottom: 0.5rem;">Diagram Syntax Error</div>
                  <pre style="white-space: pre-wrap; font-size: 0.8em; margin-bottom: 1rem;">${e.message || "Unknown error"}</pre>
                  <div style="font-weight: bold; margin-bottom: 0.5rem; font-size: 0.75rem; text-transform: uppercase;">Source:</div>
                  <pre style="background: rgba(0,0,0,0.3); padding: 0.5rem; border-radius: 4px; font-family: monospace; font-size: 0.75rem;">${chart.replace(/</g, '&lt;')}</pre>
                </div>`);
                        setIsLoading(false);
                    }
                }
            });
        };

        // Small delay to allow UI to update to loading state
        const timeout = setTimeout(renderChart, 50);

        return () => {
            mounted = false;
            clearTimeout(timeout);
            try {
                const tempElement = document.getElementById(renderId);
                if (tempElement) tempElement.remove();
            } catch (e) { /* ignore */ }
        };
    }, [chart]);

    // Simplified rendering without the "Window" chrome or manual zoom/pan
    // The user wants to see the diagram "directly" and "entirely".

    if (isLoading) {
        return (
            <div className="skeleton-loader" style={{ margin: "1.5rem 0" }}>
                <div className="skeleton-spinner"></div>
                <div className="skeleton-text">Generating Diagram...</div>
            </div>
        );
    }

    return (
        <div
            className="mermaid-container"
            style={{
                margin: "1.5rem 0",
                width: "100%",
                display: "flex",
                justifyContent: "center",
                overflowX: "auto" // Allow horizontal scroll only if absolutely wider than screen
            }}
        >
            <div
                style={{
                    width: "100%",
                    height: "auto",
                    // Reset standard mermaid SVG sizing quirks if needed
                    lineHeight: 0
                }}
                dangerouslySetInnerHTML={{ __html: svg }}
            />
        </div>
    );
};
