"""
AI Instructions Module
Loads and combines instruction markdown files
"""
from pathlib import Path
from typing import List

DOCS_DIR = Path(__file__).parent / 'docs'

def load_instruction_file(filename: str) -> str:
    """Load a single instruction markdown file"""
    file_path = DOCS_DIR / filename
    if file_path.exists():
        return file_path.read_text(encoding='utf-8')
    return f"<!-- {filename} not found -->\n"

def load_all_instructions(version: str = "2.6.1") -> str:
    """
    Load and combine all instruction markdown files into one document
    
    Args:
        version: Agent version to inject into overview
        
    Returns:
        Combined instruction text
    """
    # Order matters - load in logical sequence
    instruction_files = [
        '00_overview.md',
        '01_explain_before_executing.md',
        '02_output_formatting.md',
        '03_critical_safety.md',
        '04_dashboard_generation.md',
        '05_api_summary.md',
        '99_final_reminder.md',
    ]
    
    instructions = []
    
    for filename in instruction_files:
        content = load_instruction_file(filename)
        
        # Replace version placeholder in overview
        if filename == '00_overview.md':
            content = content.replace('2.6.1', version)
        
        instructions.append(content)
    
    # Combine with separators
    combined = '\n\n---\n\n'.join(instructions)
    
    return combined

def get_instruction_files() -> List[str]:
    """Get list of available instruction files"""
    if not DOCS_DIR.exists():
        return []
    return sorted([f.name for f in DOCS_DIR.glob('*.md')])


