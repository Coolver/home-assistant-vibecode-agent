"""YAML Editor Utility for safe YAML file modifications"""
import re
from typing import Optional


class YAMLEditor:
    """Utility for editing YAML files while preserving structure"""
    
    @staticmethod
    def remove_lines_from_end(content: str, num_lines: int) -> str:
        """
        Remove specified number of lines from end of file
        
        Args:
            content: File content
            num_lines: Number of lines to remove from end
            
        Returns:
            Content with lines removed
        """
        lines = content.rstrip().split('\n')
        if num_lines >= len(lines):
            return ""
        return '\n'.join(lines[:-num_lines]) + '\n'
    
    @staticmethod
    def remove_empty_yaml_section(content: str, section_name: str) -> str:
        """
        Remove empty YAML section (e.g., 'lovelace:' with empty 'dashboards:')
        
        Args:
            content: File content
            section_name: Section to remove if empty (e.g., 'lovelace')
            
        Returns:
            Content with empty section removed
        """
        # Pattern: section with only empty subsections
        # Example:
        # # Comment
        # lovelace:
        #   dashboards:
        #   (next section or EOF)
        
        # Remove comment + empty section
        pattern = rf'\n# .*{section_name.title()}.*\n{section_name}:\s*\n\s+\w+:\s*\n(?=\S|\Z)'
        content = re.sub(pattern, '\n', content, flags=re.IGNORECASE)
        
        # Also try without comment
        pattern = rf'\n{section_name}:\s*\n\s+\w+:\s*\n(?=\S|\Z)'
        content = re.sub(pattern, '\n', content, flags=re.IGNORECASE)
        
        return content
    
    @staticmethod
    def remove_yaml_entry(content: str, section: str, key: str) -> tuple[str, bool]:
        """
        Remove specific entry from YAML section
        
        Args:
            content: File content
            section: Parent section (e.g., 'lovelace')
            key: Entry key to remove (e.g., 'ai-dashboard')
            
        Returns:
            (modified_content, was_found)
        """
        # Pattern to match entry with all its properties
        # Example:
        #     ai-dashboard:
        #       mode: yaml
        #       title: ...
        pattern = rf'    {re.escape(key)}:\s*\n(?:      .*\n)*'
        
        if re.search(pattern, content):
            modified = re.sub(pattern, '', content)
            
            # Check if parent section is now empty and remove it
            modified = YAMLEditor.remove_empty_yaml_section(modified, section)
            
            return modified, True
        
        return content, False






