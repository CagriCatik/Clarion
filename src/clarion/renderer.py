import re
from clarion.schemas import FlexDoc

def sanitize_mermaid(markdown: str) -> str:
    """
    Scans for mermaid code blocks and fixes common syntax errors:
    1. Unquoted labels containing () or [] -> wraps in quotes.
       e.g. node[Label (Text)] -> node["Label (Text)"]
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
            
            # Simple approach: Replace unquoted [Text (Detail)] with ["Text (Detail)"]
            # Look for:  \[  ( [^"\]]+ )  \]    <-- matches [ ... ] where ... has no " and no ]
            # Issue: [Nested [brackets]] are rare but possible? Mermaid doesn't nest brackets easily.
            
            # Let's try to match simplest bad case:  [Text (Info)]
            line = re.sub(r'\[([^"\]]*?\(.*?\)[^"\]]*?)\]', r'["\1"]', line)
            
            # Parentheses:  (Text (Info)) is valid? No, id(Text) uses parens for round edges.
            # id(Text (Info)) -> id("Text (Info)")
            line = re.sub(r'\(([^"\)]*?\(.*?\)[^"\)]*?)\)', r'("\1")', line)
            
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
