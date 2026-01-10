import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Mermaid } from './Mermaid';
import { ErrorBoundary } from './ErrorBoundary';

interface Props {
    content: string;
    zoom: number;
    filename: string;
}

export const MarkdownViewer = ({ content, zoom, filename }: Props) => {
    const components = useMemo(() => ({
        // Map paragraphs to divs to prevent 'div inside p' crashes when replacing pre with Mermaid
        p: ({ node, ...props }: any) => <div {...props} />,

        pre({ children, ...props }: any) {
            // Helper to get text content from children
            const childArray = React.Children.toArray(children);

            // Find any child that looks like a code block with mermaid content
            const codeElement = childArray.find((child: any) => {
                if (!React.isValidElement(child)) return false;

                // It's a match if it has the mermaid class...
                const hasClass = (child.props as any).className?.includes('language-mermaid');

                // ...OR if its content looks like a mermaid diagram (heuristic)
                const content = String((child.props as any).children || '').trim();
                const hasPattern = /^(graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|requirementDiagram|gitGraph|mindmap|timeline)/.test(content);

                return hasClass || hasPattern;
            });

            if (codeElement && React.isValidElement(codeElement)) {
                const content = String((codeElement.props as any).children || '').trim();
                return (
                    <div className="mermaid-wrapper-block">
                        <Mermaid chart={content} />
                    </div>
                );
            }
            return <pre {...props}>{children}</pre>;
        },
        code({ node, inline, className, children, ...props }: any) {
            return <code className={className} {...props}>{children}</code>;
        }
    }), []);

    return (
        <div className="markdown-content" style={{ zoom: zoom }}>
            {/* 
         We use the filename as a specific key for the ErrorBoundary.
         This forces a complete remount of the markdown viewer (and Mermaid diagrams)
         whenever the active document changes, preventing DOM node reuse crashes.
      */}
            <ErrorBoundary key={filename}>
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                    {content || ""}
                </ReactMarkdown>
            </ErrorBoundary>
        </div>
    );
};
