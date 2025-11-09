"""
Ingress Panel HTML template for HA Cursor Agent
"""

def generate_ingress_html(api_key: str, agent_version: str) -> str:
    """Generate HTML for Ingress Panel"""
    
    # Full JSON config for user to copy
    json_config = f'''{{
  "mcpServers": {{
    "home-assistant": {{
      "command": "npx",
      "args": ["-y", "@coolver/mcp-home-assistant@latest"],
      "env": {{
        "HA_AGENT_URL": "http://homeassistant.local:8099",
        "HA_AGENT_KEY": "{api_key}"
      }}
    }}
  }}
}}'''
    
    # Masked key for display
    masked_key = f"{api_key[:12]}...{api_key[-12:]}" if len(api_key) > 24 else api_key
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>HA Cursor Agent</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                padding: 20px;
                background: #0d1117;
                color: #c9d1d9;
                line-height: 1.6;
            }}
            
            .container {{
                max-width: 900px;
                margin: 0 auto;
            }}
            
            h1 {{
                color: #58a6ff;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 28px;
            }}
            
            .version {{
                font-size: 14px;
                color: #8b949e;
                font-weight: normal;
                background: #161b22;
                padding: 4px 12px;
                border-radius: 12px;
            }}
            
            .card {{
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 28px;
                margin: 20px 0;
            }}
            
            .card h2 {{
                color: #58a6ff;
                font-size: 20px;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .config-block {{
                background: #0d1117;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 20px;
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
                font-size: 13px;
                overflow-x: auto;
                margin: 16px 0;
                position: relative;
                max-height: 400px;
                overflow-y: auto;
            }}
            
            .config-block pre {{
                margin: 0;
                color: #79c0ff;
                line-height: 1.5;
            }}
            
            .copy-btn {{
                background: #238636;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                transition: all 0.2s;
                width: 100%;
                justify-content: center;
            }}
            
            .copy-btn:hover {{
                background: #2ea043;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
            }}
            
            .copy-btn:active {{
                transform: translateY(0);
            }}
            
            .copy-btn.copied {{
                background: #2ea043;
                animation: pulse 0.3s ease;
            }}
            
            @keyframes pulse {{
                0%, 100% {{
                    transform: scale(1);
                }}
                50% {{
                    transform: scale(1.02);
                }}
            }}
            
            .step {{
                display: flex;
                gap: 16px;
                margin: 20px 0;
                align-items: flex-start;
            }}
            
            .step-number {{
                background: #238636;
                color: white;
                min-width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 16px;
                flex-shrink: 0;
            }}
            
            .step-content {{
                flex: 1;
                padding-top: 4px;
            }}
            
            .step-content h3 {{
                color: #c9d1d9;
                font-size: 16px;
                margin-bottom: 8px;
            }}
            
            .step-content p {{
                color: #8b949e;
                font-size: 14px;
            }}
            
            .step-content code {{
                background: #161b22;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 13px;
                color: #79c0ff;
            }}
            
            .info-box {{
                background: #1c2128;
                border-left: 3px solid #58a6ff;
                padding: 14px 18px;
                margin: 16px 0;
                border-radius: 4px;
                font-size: 14px;
            }}
            
            .info-box.warning {{
                border-left-color: #d29922;
                background: #22201c;
            }}
            
            .advanced {{
                margin-top: 12px;
            }}
            
            .advanced-toggle {{
                background: transparent;
                border: 1px solid #30363d;
                color: #8b949e;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                width: 100%;
                text-align: left;
                display: flex;
                align-items: center;
                justify-content: space-between;
                transition: all 0.2s;
            }}
            
            .advanced-toggle:hover {{
                background: #161b22;
                border-color: #58a6ff;
                color: #c9d1d9;
            }}
            
            .advanced-content {{
                display: none;
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid #30363d;
            }}
            
            .advanced-content.show {{
                display: block;
            }}
            
            .key-display {{
                background: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 12px 16px;
                font-family: 'SF Mono', Monaco, monospace;
                font-size: 13px;
                color: #79c0ff;
                margin: 12px 0;
                word-break: break-all;
            }}
            
            .btn-secondary {{
                background: #21262d;
                border: 1px solid #30363d;
                color: #c9d1d9;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s;
                text-decoration: none;
            }}
            
            .btn-secondary:hover {{
                background: #30363d;
            }}
            
            .btn-danger {{
                background: #da3633;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s;
            }}
            
            .btn-danger:hover {{
                background: #e5534b;
            }}
            
            .success-message {{
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: #238636;
                color: white;
                padding: 20px 32px;
                border-radius: 8px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.6);
                display: none;
                animation: popIn 0.3s ease;
                z-index: 1000;
                font-size: 18px;
                font-weight: 600;
            }}
            
            @keyframes slideIn {{
                from {{
                    transform: translateX(400px);
                    opacity: 0;
                }}
                to {{
                    transform: translateX(0);
                    opacity: 1;
                }}
            }}
            
            @keyframes popIn {{
                0% {{
                    transform: translate(-50%, -50%) scale(0.8);
                    opacity: 0;
                }}
                100% {{
                    transform: translate(-50%, -50%) scale(1);
                    opacity: 1;
                }}
            }}
            
            .chevron {{
                transition: transform 0.2s;
            }}
            
            .chevron.rotate {{
                transform: rotate(180deg);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>
                🔑 HA Cursor Agent
                <span class="version">v{agent_version}</span>
            </h1>
            
            <p style="color: #8b949e; margin: 10px 0 20px 0;">
                Connect Cursor AI to your Home Assistant
            </p>
            
            <div class="card">
                <h2>📋 Step 1: Copy Configuration</h2>
                <p style="color: #8b949e; margin-bottom: 16px;">
                    This is your complete Cursor MCP configuration. Copy and paste it in Cursor Settings.
                </p>
                
                <div class="config-block">
                    <pre id="configText">{json_config}</pre>
                </div>
                
                <button class="copy-btn" id="copyBtn" onclick="copyConfig()">
                    <span id="copyBtnIcon">📋</span> <span id="copyBtnText">Copy Configuration to Clipboard</span>
                </button>
            </div>
            
            <div class="card">
                <h2>🚀 Step 2: Setup Cursor</h2>
                
                <div class="step">
                    <div class="step-number">1</div>
                    <div class="step-content">
                        <h3>Open Cursor Settings</h3>
                        <p><strong>Settings</strong> → <strong>Tools & MCP</strong> → <strong>New MCP Server</strong></p>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">2</div>
                    <div class="step-content">
                        <h3>Add Custom MCP Server</h3>
                        <p>Click <strong>Add a Custom MCP Server</strong> and paste the JSON configuration you copied above</p>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">3</div>
                    <div class="step-content">
                        <h3>Restart Cursor</h3>
                        <p>Fully quit and reopen Cursor (Cmd+Q on Mac, Alt+F4 on Windows)</p>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">4</div>
                    <div class="step-content">
                        <h3>Test connection</h3>
                        <p>Ask Cursor AI: <em>"List my Home Assistant entities"</em></p>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>💡 Additional Info</h2>
                
                <div class="info-box">
                    <strong>🔒 Security:</strong> Your Agent Key is used to authenticate with this agent.
                </div>
                
                <div class="info-box warning">
                    <strong>⚠️ Keep your key safe:</strong> Don't share it publicly or commit to git repositories.
                </div>
                
                <div class="advanced">
                    <button class="advanced-toggle" onclick="toggleAdvanced()">
                        <span>🔧 Advanced: View/Regenerate Agent Key</span>
                        <span class="chevron" id="chevron">▼</span>
                    </button>
                    
                    <div class="advanced-content" id="advancedContent">
                        <h3 style="color: #c9d1d9; font-size: 16px; margin-bottom: 12px;">Your Agent Key:</h3>
                        <div class="key-display" id="keyDisplay">{masked_key}</div>
                        
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <button class="btn-secondary" onclick="toggleKeyVisibility()">
                                <span id="eyeIcon">👁️</span> <span id="toggleText">Show Full Key</span>
                            </button>
                            <button class="btn-danger" onclick="confirmRegenerate()">
                                🔄 Regenerate Key
                            </button>
                        </div>
                        
                        <div class="info-box warning" style="margin-top: 16px; font-size: 13px;">
                            <strong>⚠️ Regenerating the key:</strong> Your current Cursor configuration will stop working. You'll need to update ~/.cursor/mcp.json with the new key.
                        </div>
                        
                        <p style="color: #8b949e; font-size: 13px; margin-top: 12px;">
                            <strong>File location:</strong> <code>/config/.ha_cursor_agent_key</code><br>
                            <strong>To regenerate manually:</strong> Delete the file above and restart the add-on.
                        </p>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>📚 Resources</h2>
                <ul style="margin-left: 20px; color: #8b949e;">
                    <li><a href="/docs" target="_blank" style="color: #58a6ff; text-decoration: none;">API Documentation</a></li>
                    <li><a href="https://github.com/Coolver/home-assistant-cursor-agent" target="_blank" style="color: #58a6ff; text-decoration: none;">GitHub Repository</a></li>
                    <li><a href="https://www.npmjs.com/package/@coolver/mcp-home-assistant" target="_blank" style="color: #58a6ff; text-decoration: none;">MCP Package</a></li>
                </ul>
            </div>
        </div>
        
        <div class="success-message" id="successMessage">
            ✅ Copied to Clipboard!
        </div>
        
        <script>
            const fullConfig = `{json_config}`;
            const fullKey = "{api_key}";
            const maskedKey = "{masked_key}";
            let keyVisible = false;
            
            function copyConfig() {{
                const btn = document.getElementById('copyBtn');
                const btnIcon = document.getElementById('copyBtnIcon');
                const btnText = document.getElementById('copyBtnText');
                
                try {{
                    // Try modern Clipboard API first
                    if (navigator.clipboard && navigator.clipboard.writeText) {{
                        navigator.clipboard.writeText(fullConfig).then(() => {{
                            showCopiedState(btn, btnIcon, btnText);
                        }}).catch(err => {{
                            // Fallback to legacy method
                            if (copyToClipboardFallback(fullConfig)) {{
                                showCopiedState(btn, btnIcon, btnText);
                            }} else {{
                                showErrorState(btn, btnIcon, btnText, err);
                            }}
                        }});
                    }} else {{
                        // Use legacy method directly
                        if (copyToClipboardFallback(fullConfig)) {{
                            showCopiedState(btn, btnIcon, btnText);
                        }} else {{
                            showErrorState(btn, btnIcon, btnText, 'Clipboard API not available');
                        }}
                    }}
                }} catch (err) {{
                    showErrorState(btn, btnIcon, btnText, err);
                }}
            }}
            
            function copyToClipboardFallback(text) {{
                // Legacy method that works without HTTPS
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.left = '-9999px';
                textarea.style.top = '-9999px';
                document.body.appendChild(textarea);
                textarea.focus();
                textarea.select();
                
                try {{
                    const successful = document.execCommand('copy');
                    document.body.removeChild(textarea);
                    return successful;
                }} catch (err) {{
                    document.body.removeChild(textarea);
                    return false;
                }}
            }}
            
            function showCopiedState(btn, btnIcon, btnText) {{
                // Change button appearance
                btn.classList.add('copied');
                btnIcon.textContent = '✅';
                btnText.textContent = 'Copied!';
                
                // Show center popup
                showSuccess();
                
                // Reset button after 2 seconds
                setTimeout(() => {{
                    btn.classList.remove('copied');
                    btnIcon.textContent = '📋';
                    btnText.textContent = 'Copy Configuration to Clipboard';
                }}, 2000);
            }}
            
            function showErrorState(btn, btnIcon, btnText, error) {{
                // Error state
                btnIcon.textContent = '❌';
                btnText.textContent = 'Failed to copy';
                console.error('Copy failed:', error);
                
                // Show alert with manual copy instructions
                alert('Failed to copy automatically.\\n\\nPlease manually select and copy the configuration above.');
                
                // Reset after 3 seconds
                setTimeout(() => {{
                    btnIcon.textContent = '📋';
                    btnText.textContent = 'Copy Configuration to Clipboard';
                }}, 3000);
            }}
            
            function showSuccess() {{
                const message = document.getElementById('successMessage');
                message.style.display = 'block';
                setTimeout(() => {{
                    message.style.display = 'none';
                }}, 2000);
            }}
            
            function toggleAdvanced() {{
                const content = document.getElementById('advancedContent');
                const chevron = document.getElementById('chevron');
                content.classList.toggle('show');
                chevron.classList.toggle('rotate');
            }}
            
            function toggleKeyVisibility() {{
                const display = document.getElementById('keyDisplay');
                const toggleText = document.getElementById('toggleText');
                const eyeIcon = document.getElementById('eyeIcon');
                keyVisible = !keyVisible;
                
                if (keyVisible) {{
                    display.textContent = fullKey;
                    toggleText.textContent = 'Hide Full Key';
                    eyeIcon.textContent = '🙈';
                }} else {{
                    display.textContent = maskedKey;
                    toggleText.textContent = 'Show Full Key';
                    eyeIcon.textContent = '👁️';
                }}
            }}
            
            function confirmRegenerate() {{
                if (confirm('⚠️ Regenerate API Key?\\n\\nThis will invalidate your current key. Your Cursor configuration will stop working until you update ~/.cursor/mcp.json with the new key.\\n\\nContinue?')) {{
                    regenerateKey();
                }}
            }}
            
            function regenerateKey() {{
                // TODO: Implement key regeneration endpoint
                alert('Key regeneration is not yet implemented.\\n\\nTo regenerate manually:\\n1. Delete /config/.ha_cursor_agent_key\\n2. Restart add-on\\n3. Come back here to get new key');
            }}
        </script>
    </body>
    </html>
    """
    
    return html

