import re
from typing import List

class MarkdownSplitter:
    """
    Splits Markdown text into chunks that respect semantic boundaries 
    (Headers, Paragraphs) to preserve context for LLM processing.
    """
    def __init__(self, chunk_size: int = 4000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_text(self, text: str) -> List[str]:
        """
        Splits text recursively:
        1. By Headers (#, ##)
        2. By Paragraphs (\n\n)
        3. By Lines (\n)
        4. Hard limit (slicing)
        """
        return self._recursive_split(text)

    def _recursive_split(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        # 1. Split by Headers (Level 1-3)
        # Regex looks for # Header at start of line
        header_pattern = r'(^#{1,3}\s.*$)'
        parts = re.split(header_pattern, text, flags=re.MULTILINE)
        
        # If split wasn't effective (just one big block), try paragraphs
        if len(parts) < 2:
            return self._split_by_separator(text, "\n\n")
        
        # Reconstruct chunks from splits
        chunks = []
        current_chunk = ""
        
        for part in parts:
            if not part: continue
            
            # If adding this part exceeds chunk size, verify if we can emit current
            if len(current_chunk) + len(part) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # If the part ITSELF is too big, recurse down
                if len(part) > self.chunk_size:
                    sub_chunks = self._split_by_separator(part, "\n\n")
                    chunks.extend(sub_chunks)
                else:
                    current_chunk = part
            else:
                current_chunk += part
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        parts = text.split(separator)
        chunks = []
        current_chunk = ""
        
        for part in parts:
            # Re-add separator for context (except usually at very end)
            part_with_sep = part + separator
            
            if len(current_chunk) + len(part_with_sep) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                if len(part_with_sep) > self.chunk_size:
                    # Fallback: Split by lines if paragraphs are too huge
                    if separator == "\n\n":
                        chunks.extend(self._split_by_separator(part, "\n"))
                    else:
                        # Hard Slice fallback
                        chunks.extend(self._hard_slice(part))
                else:
                    current_chunk = part_with_sep
            else:
                current_chunk += part_with_sep
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def _hard_slice(self, text: str) -> List[str]:
        """Last resort: slice by character limit."""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.overlap):
            chunks.append(text[i : i + self.chunk_size])
        return chunks
