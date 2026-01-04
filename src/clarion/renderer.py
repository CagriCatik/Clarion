import re
from clarion.schemas import FlexDoc

def sanitize_mermaid(markdown: str) -> str:
    """
    Scans for mermaid code blocks and fixes common syntax errors:
    1. Unquoted labels containing () or [] -> wraps in quotes.
       e.g. node[Label (Text)] -> node["Label (Text)"]
    2. Node IDs with spaces in edge definitions -> removes spaces from IDs.
    """
    
    # Pattern to find mermaid blocks
    block_pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
    
    def fix_block(match):
        content = match.group(1)
        
        # Regex to find unquoted node definitions: id[Content] or id(Content)
        # We want to match cases where Content has special chars but NO quotes.
        # Captures: 1=id, 2=opener([, 3=content, 4=closer)]
        
        # Heuristic: Match id[...], check if internals have ( or ) and are NOT quoted.
        # This is hard with single regex. simpler approach: iterate lines.
        
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Check for pattern:  NodeID[Text with (parens)]  (and ensuring it's not already quoted)
            # We look for [ or ( that is NOT followed by "
            
            # 1. Square brackets:  id[Content]
            # Match:  something[  ...  ]  
            # If ... doesn't start with ", replace [ ... ] with [" ... "]
            
            def quoter(m):
                opener = m.group(1) # [ or ( or {
                inner = m.group(2)
                closer = m.group(3) # ] or ) or }
                
                # If already quoted, skip
                if inner.startswith('"') and inner.endswith('"'):
                    return f"{opener}{inner}{closer}"
                
                # If purely alphanumeric/space, strictly speaking usually fine, 
                # but if it has () or [] or special chars, quote it.
                if re.search(r"[()\[\]]", inner):
                     return f'{opener}"{inner}"{closer}'
                
                return f"{opener}{inner}{closer}"

            # Regex for Square brackets:  (\[)(.*?)(])
            # We use non-greedy matching? No, labels can be long.
            # But we don't want to match across multiple nodes on one line if possible 
            # (though mermaid usually one per line or separated by arrow)
            
            # Look for:  \[  ( [^"\]]+ )  \]    <-- matches [ ... ] where ... has no " and no ]
            # Issue: [Nested [brackets]] are rare but possible? Mermaid doesn't nest brackets easily.
            
            # FIX 1a: Database shapes with inner quotes - Remove extra quotes
            # Transform: Database["("Data Store")"] -> Database[(Data Store)]
            line = re.sub(
                r'(\w+)\["\("([^"]+)"\)"\]',  # Match: ID["("text")"]
                r'\1[(\2)]',                   # Replace: ID[(text)]
                line
            )
            
            # FIX 1b: Database shapes without inner quotes - Fix brackets
            # Transform: Database["(Customer Database)"] -> Database[(Customer Database)]
            line = re.sub(
                r'(\w+)\["(\([^)]+\))"\]',  # Match: ID["(text)"]
                r'\1[\2]',                   # Replace: ID[(text)]
                line
            )
            
            # FIX 2: Quote labels with special characters (excluding Database shapes)
            # Match [Text (Info)] and wrap in quotes
            # BUT: Don't match database shapes like [(text)] - they start with [(
            line = re.sub(
                r'\[(?!\()([^"\]]*?\(.*?\)[^"\]]*?)\]',  # Negative lookahead for [(
                r'["\1"]',
                line
            )
            
            # Parentheses: (Text (Info)) -> ("Text (Info)")
            line = re.sub(r'\(([^"\)]*?\(.*?\)[^"\)]*?)\)', r'("\1")', line)
            
            # FIX 2: Remove spaces from node IDs in edge definitions
            # Pattern: NodeA-->Multi Word NodeB[Label]
            # Also: Multi Word NodeA-->NodeB[Label]
            
            # First, fix DESTINATION nodes (after arrow): A-->Multi Word Node[Label]
            def fix_dest_node_id(m):
                arrow = m.group(1)  # --> or -.-> or ==>
                node_with_spaces = m.group(2)  # "Multi Word Node"
                shape_and_label = m.group(3)  # ["Label"] or ("Label") etc
                
                # Remove spaces from the node ID
                fixed_node = node_with_spaces.replace(' ', '')
                return f"{arrow}{fixed_node}{shape_and_label}"
            
            # Match: (arrow pattern) (text with spaces) ([shape pattern])
            line = re.sub(
                r'((?:--|==|\.-|\.\.)>)\s*([A-Za-z][A-Za-z0-9 _]*?)(\[|\(|\{)',
                fix_dest_node_id,
                line
            )
            
            # Second, fix SOURCE nodes (before arrow): Multi Word Node-->B
            # We need to find standalone node IDs with spaces that appear before arrows
            # Pattern: (start of line or whitespace)(Node With Spaces)(arrow)
            def fix_source_node_id(m):
                prefix = m.group(1)  # whitespace/start
                node_with_spaces = m.group(2)  # "Multi Word Node"
                arrow = m.group(3)  # -->
                
                fixed_node = node_with_spaces.replace(' ', '')
                return f"{prefix}{fixed_node}{arrow}"
            
            # Match: (whitespace or start)(multi-word identifier)(arrow)
            # Only match if there are actually spaces in the identifier
            line = re.sub(
                r'(^|\s)([A-Za-z][A-Za-z0-9_]+ [A-Za-z0-9_ ]+?)((?:--|==|\.-|\.\.)>)',
                fix_source_node_id,
                line
            )
            
            fixed_lines.append(line)
            
        return f"```mermaid\n{chr(10).join(fixed_lines)}\n```"

    return block_pattern.sub(fix_block, markdown)

def render_markdown(doc: FlexDoc) -> str:
    """
    Renders FlexDoc content to markdown.
    Includes a failsafe to unwrap raw JSON if it was accidentally saved as content.
    """
    content = doc.content.strip()
    
    # Failsafe: If content is a raw JSON string, try to extract the inner content
    if content.startswith('{') and content.endswith('}'):
        try:
            import json
            data = json.loads(content, strict=False)
            if isinstance(data, dict):
                # Check various common content keys
                for key in ["content", "text", "markdown", "output"]:
                    if key in data and isinstance(data[key], str):
                        content = data[key]
                        break
        except:
            pass
            
    return sanitize_mermaid(content)
