import { useState, useRef, useEffect } from "react";
import mermaid from "mermaid";

// Initialize mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: "base",
    themeVariables: {
        darkMode: true,
        primaryColor: '#6366f1', // Indigo-500
        lineColor: '#94a3b8',   // Slate-400
        textColor: '#f8fafc',   // Slate-50
        mainBkg: '#1e293b',     // Slate-800
        nodeBorder: '#6366f1',
    }
});

// Mermaid Component
export const Mermaid = ({ chart }: { chart: string }) => {
    const [svg, setSvg] = useState<string>("");
    const idRef = useRef(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

    useEffect(() => {
        if (!chart) return;
        let mounted = true;
        const renderChart = async () => {
            try {
                const { svg } = await mermaid.render(idRef.current, chart);
                if (mounted) setSvg(svg);
            } catch (e: any) {
                console.error("Mermaid render failed:", e);
                if (mounted) {
                    setSvg(`<div class="error" style="color: red; padding: 10px; border: 1px solid red;">
            Failed to render diagram: ${e.message || "Unknown error"}
            <pre style="font-size: 0.7em; overflow: auto; max-height: 100px;">${chart}</pre>
          </div>`);
                }
            }
        };
        renderChart();
        return () => { mounted = false; };
    }, [chart]);

    return (
        <div
            className="mermaid-wrapper"
            style={{ margin: "1rem 0", background: "transparent", minHeight: "50px" }}
            dangerouslySetInnerHTML={{ __html: svg }}
        />
    );
};
