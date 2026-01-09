import re
from typing import List, Dict
from .schemas import DiagramSpec, MermaidNode, MermaidEdge

class MermaidRenderer:
    """
    Renders DiagramSpec to canonical Mermaid string.
    Implements normalization and 'declare-first' policy.
    """

    @staticmethod
    def normalize_id(raw_id: str) -> str:
        """Sanitize ID to be alphanumeric only."""
        clean = re.sub(r'[^A-Za-z0-9]', '', raw_id)
        if not clean:
            return "NodeX" # Fallback
        return clean

    @staticmethod
    def normalize_spec(spec: DiagramSpec) -> DiagramSpec:
        """
        1. Deduplicates nodes.
        2. Normalizes IDs.
        3. Ensures edges reference valid IDs.
        """
        node_map: Dict[str, MermaidNode] = {}
        
        # 1. Process Nodes
        for n in spec.nodes:
            nid = MermaidRenderer.normalize_id(n.id)
            if nid not in node_map:
                # Strip labels, ensure quotes escaped if needed (simple approach)
                clean_label = n.label.replace('"', "'").strip() 
                node_map[nid] = MermaidNode(id=nid, label=clean_label)
        
        # 2. Process Edges
        valid_edges = []
        for e in spec.edges:
            src = MermaidRenderer.normalize_id(e.source)
            tgt = MermaidRenderer.normalize_id(e.target)
            
            # Auto-create missing nodes if referenced?
            # Strategy: If missing, create stub node.
            if src not in node_map:
                node_map[src] = MermaidNode(id=src, label=src)
            if tgt not in node_map:
                node_map[tgt] = MermaidNode(id=tgt, label=tgt)
                
            clean_lbl = None
            if e.label:
                clean_lbl = e.label.replace('"', "'").strip()
                # Remove forbidden tokens from label
                clean_lbl = clean_lbl.replace("|>", "")
            
            valid_edges.append(
                MermaidEdge(source=src, target=tgt, label=clean_lbl, type=e.type)
            )
            
        return DiagramSpec(
            direction=spec.direction,
            nodes=list(node_map.values()),
            edges=valid_edges
        )

    @staticmethod
    def render(spec: DiagramSpec) -> str:
        norm_spec = MermaidRenderer.normalize_spec(spec)
        
        lines = []
        lines.append(f"graph {norm_spec.direction}")
        
        # Emit Nodes First
        # Sort for determinism
        sorted_nodes = sorted(norm_spec.nodes, key=lambda x: x.id)
        for n in sorted_nodes:
            lines.append(f'{n.id}["{n.label}"]')
            
        lines.append("") # Spacer
        
        # Emit Edges
        for e in norm_spec.edges:
            arrow = "-->" if e.type == "solid" else "-.->"
            if e.label:
                # simple validation of label
                lines.append(f"{e.source} {arrow}|{e.label}| {e.target}")
            else:
                lines.append(f"{e.source} {arrow} {e.target}")
                
        return "\n".join(lines)
