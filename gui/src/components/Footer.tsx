import { useState, useEffect } from "react";
import { IconFolder } from "./Icons";

interface FooterProps {
    version: string;
    onOpenFolder: () => void;
}

export const Footer = ({ version, onOpenFolder }: FooterProps) => {
    const [metrics, setMetrics] = useState<{ cpu: number, ram: number, gpu?: number | null }>({ cpu: 0, ram: 0, gpu: null });

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const res = await fetch("/v1/metrics");
                const data = await res.json();
                setMetrics(data);
            } catch (e) {
                console.error("Failed to fetch metrics", e);
            }
        };
        const interval = setInterval(fetchMetrics, 3000);
        fetchMetrics();
        return () => clearInterval(interval);
    }, []);

    return (
        <footer className="footer">
            <div className="footer-left">
                <span className="footer-item">v{version}</span>
            </div>
            <div className="footer-right">
                <div className="metrics-bar">
                    <div className="metric-item">
                        <span className="metric-label">CPU</span>
                        <span className={`metric-value ${metrics.cpu > 80 ? 'high' : metrics.cpu > 50 ? 'med' : ''}`}>{metrics.cpu}%</span>
                    </div>
                    <div className="metric-item">
                        <span className="metric-label">RAM</span>
                        <span className={`metric-value ${metrics.ram > 80 ? 'high' : metrics.ram > 50 ? 'med' : ''}`}>{metrics.ram}%</span>
                    </div>
                    {metrics.gpu !== null && metrics.gpu !== undefined && (
                        <div className="metric-item">
                            <span className="metric-label">GPU</span>
                            <span className={`metric-value ${metrics.gpu > 80 ? 'high' : metrics.gpu > 50 ? 'med' : ''}`}>{Math.round(metrics.gpu)}%</span>
                        </div>
                    )}
                </div>
                <button className="footer-btn" onClick={onOpenFolder}>
                    <IconFolder /> Open Outputs
                </button>
            </div>
        </footer>
    );
};
