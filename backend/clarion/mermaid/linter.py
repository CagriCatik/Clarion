import re
from typing import List
from .schemas import LintReport, LintError

class MermaidLinter:
    """
    Deterministic linter for Mermaid Flowcharts.
    Enforces the strict subset of syntax defined in the system constraints.
    """

    # Compiled Regex Patterns
    RGX_NODE_LINE = re.compile(r'^\s*([A-Za-z0-9]+)\["([^"]*)"\]\s*$')
    RGX_EDGE_SOLID = re.compile(r'^\s*([A-Za-z0-9]+)\s+-->\s+([A-Za-z0-9]+)\s*$')
    RGX_EDGE_DOTTED = re.compile(r'^\s*([A-Za-z0-9]+)\s+-\.->\s+([A-Za-z0-9]+)\s*$')
    RGX_EDGE_LABEL_SOLID = re.compile(r'^\s*([A-Za-z0-9]+)\s+-->\|([^|]+)\|\s+([A-Za-z0-9]+)\s*$')
    RGX_EDGE_LABEL_DOTTED = re.compile(r'^\s*([A-Za-z0-9]+)\s+-\.->\|([^|]+)\|\s+([A-Za-z0-9]+)\s*$')
    RGX_EDGE_LABEL_QUOTED = re.compile(r'^\s*([A-Za-z0-9]+)\s+--\s+"([^"]+)"\s+-->\s+([A-Za-z0-9]+)\s*$')
    
    RGX_ID_VALID = re.compile(r'^[A-Za-z0-9]+$')
    
    FORBIDDEN_TOKENS = [
        "|>", "->>", "==>", ":::", "subgraph", "style", "classDef", "click", "linkStyle"
    ]

    @classmethod
    def lint(cls, code: str) -> LintReport:
        errors: List[LintError] = []
        lines = code.strip().splitlines()
        
        # 0. Basic Cleanup Check
        if not lines:
            return LintReport(is_valid=False, errors=[LintError(line=0, issue="Empty code block", suggested_fix="Add graph TD")])

        # 1. Header Check
        header = lines[0].strip()
        if header not in ["graph TD", "graph LR"]:
            errors.append(LintError(
                line=1, 
                issue=f"Invalid header '{header}'", 
                suggested_fix="Must be exactly 'graph TD' or 'graph LR'"
            ))

        declared_nodes = set()
        
        # 2. Line-by-Line Scan
        for idx, line in enumerate(lines[1:], start=2): # 1-based index, skipping header
            raw = line.strip()
            if not raw: continue
            
            # A. Forbidden Tokens
            for token in cls.FORBIDDEN_TOKENS:
                if token in raw:
                    errors.append(LintError(
                        line=idx, 
                        issue=f"Forbidden token '{token}' found", 
                        suggested_fix=f"Remove usages of '{token}'"
                    ))
            
            # B. Parse Structure
            matched = False
            
            # Check Node Decl
            m_node = cls.RGX_NODE_LINE.match(raw)
            if m_node:
                node_id = m_node.group(1)
                declared_nodes.add(node_id)
                matched = True
                
            # Check Edges (various forms)
            edge_match = (
                cls.RGX_EDGE_SOLID.match(raw) or 
                cls.RGX_EDGE_DOTTED.match(raw) or 
                cls.RGX_EDGE_LABEL_SOLID.match(raw) or 
                cls.RGX_EDGE_LABEL_DOTTED.match(raw) or
                cls.RGX_EDGE_LABEL_QUOTED.match(raw)
            )
            
            if edge_match:
                src, tgt = edge_match.group(1), edge_match.group(edge_match.lastindex) # source is 1, target is last group
                
                # Check IDs
                if not cls.RGX_ID_VALID.match(src):
                    errors.append(LintError(line=idx, issue=f"Invalid Source ID '{src}'", suggested_fix="Use alphanumeric only"))
                if not cls.RGX_ID_VALID.match(tgt):
                    errors.append(LintError(line=idx, issue=f"Invalid Target ID '{tgt}'", suggested_fix="Use alphanumeric only"))
                
                # We defer "undeclared node" check to post-pass/renderer, 
                # OR we enforce it here if we want strict "declare before use". 
                # Let's enforce it loosely (must be declared somewhere) - actually linter runs on text.
                # If we want strict, we verify existence.
                # But simple regex linter might miss "declared later". 
                # For robust pipeline, we usually enforce "declare first" in Renderer.
                matched = True

            if not matched and "-->" in raw or "-.->" in raw:
                 # It looked like an edge but failed strict regex (e.g. bad spaces or forbidden chars)
                 errors.append(LintError(line=idx, issue="Malformed edge syntax", suggested_fix="Check spacing or forbidden chars"))
            elif not matched and not m_node:
                 # Likely garbage or unparseable line
                 errors.append(LintError(line=idx, issue="Unknown syntax", suggested_fix="Remove or format as Node or Edge"))

        return LintReport(is_valid=(len(errors) == 0), errors=errors)
