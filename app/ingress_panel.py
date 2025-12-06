"""
Ingress Panel for HA Cursor Agent
Renders configuration panel using Jinja2 template
"""
from pathlib import Path
from jinja2 import Template


def generate_ingress_html(api_key: str, agent_version: str) -> str:
    """
    Generate HTML for Ingress Panel using Jinja2 template
    
    Args:
        api_key: Agent API key
        agent_version: Current agent version
        
    Returns:
        Rendered HTML string
    """
    # Cursor JSON config for user to copy
    cursor_json_config = f'''{{
  "mcpServers": {{
    "home-assistant": {{
      "command": "npx",
      "args": ["-y", "@coolver/home-assistant-mcp@latest"],
      "env": {{
        "HA_AGENT_URL": "http://homeassistant.local:8099",
        "HA_AGENT_KEY": "{api_key}"
      }}
    }}
  }}
}}'''
    
    # VS Code + Copilot JSON config for user to copy (wrapped in servers object)
    vscode_json_config = f'''{{
  "servers": {{
    "home-assistant": {{
      "command": "npx",
      "args": ["-y", "@coolver/home-assistant-mcp@latest"],
      "env": {{
        "HA_AGENT_URL": "http://homeassistant.local:8099",
        "HA_AGENT_KEY": "{api_key}"
      }}
    }}
  }}
}}'''
    
    # Load Jinja2 template
    template_path = Path(__file__).parent / 'templates' / 'ingress_panel.html'
    template_content = template_path.read_text(encoding='utf-8')
    template = Template(template_content)
    
    # Render template with context
    html = template.render(
        api_key=api_key,
        agent_version=agent_version,
        cursor_json_config=cursor_json_config,
        vscode_json_config=vscode_json_config
    )
    
    return html
