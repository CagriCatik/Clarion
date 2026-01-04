import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";

export const Tooltip = ({ text, children }: { text: string; children: React.ReactNode }) => {
    const [visible, setVisible] = useState(false);
    const [coords, setCoords] = useState({ top: 0, left: 0 });
    const triggerRef = useRef<HTMLDivElement>(null);

    const updatePosition = () => {
        if (triggerRef.current) {
            const rect = triggerRef.current.getBoundingClientRect();
            const tooltipHeight = 60; // Approximate
            const topSpace = rect.top;

            let top = rect.top + window.scrollY - 8;
            let left = rect.left + window.scrollX + rect.width / 2;

            // Smart repositioning if not enough space at top
            if (topSpace < tooltipHeight + 20) {
                top = rect.bottom + window.scrollY + 8;
                setCoords({ top, left, position: 'bottom' } as any);
            } else {
                setCoords({ top, left, position: 'top' } as any);
            }
        }
    };

    useEffect(() => {
        if (visible) {
            updatePosition();
            window.addEventListener('scroll', updatePosition);
            window.addEventListener('resize', updatePosition);
        }
        return () => {
            window.removeEventListener('scroll', updatePosition);
            window.removeEventListener('resize', updatePosition);
        };
    }, [visible]);

    return (
        <div
            ref={triggerRef}
            className="tooltip-trigger"
            onMouseEnter={() => setVisible(true)}
            onMouseLeave={() => setVisible(false)}
        >
            {children}
            {visible && coords.top !== 0 && createPortal(
                <div
                    className={`tooltip-content ${(coords as any).position || 'top'}`}
                    style={{
                        top: coords.top,
                        left: coords.left,
                    }}
                >
                    {text}
                </div>,
                document.body
            )}
        </div>
    );
};
