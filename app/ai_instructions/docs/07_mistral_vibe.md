# 🦙 MISTRAL VIBE INTEGRATION

## Overview

Mistral Vibe is now available as an alternative AI backend for the HA Vibecode Agent!  
This allows you to leverage Mistral's powerful language models alongside or instead of other AI assistants.

**Key Features:**
- ✅ **Multiple Model Support**: Access various Mistral models
- ✅ **Chat Completion**: Generate intelligent responses and automations
- ✅ **Embeddings**: Create text embeddings for semantic search
- ✅ **Seamless Integration**: Works with existing HA Vibecode Agent workflows

## Configuration

To enable Mistral Vibe, set these environment variables:

```bash
# Required
MISTRAL_VIBE_API_URL="https://api.mistral.ai/v1"
MISTRAL_VIBE_API_KEY="your-api-key-here"

# Optional
MISTRAL_VIBE_DEFAULT_MODEL="mistral-tiny"  # Default: mistral-tiny
MISTRAL_VIBE_TIMEOUT=30                    # Default: 30 seconds
MISTRAL_VIBE_MAX_RETRIES=3                 # Default: 3 retries
```

**Add-on Configuration:**
You can also configure Mistral Vibe through the add-on settings in the Home Assistant UI.

## API Endpoints

### Health Check

```bash
GET /api/mistral/health
```

Check if Mistral Vibe is configured and available:

```json
{
  "status": "healthy",
  "enabled": true,
  "api_url": "https://api.mistral.ai/v1",
  "default_model": "mistral-tiny",
  "models_available": ["mistral-tiny", "mistral-small", "mistral-medium"],
  "message": "Mistral Vibe API is available"
}
```

### Chat Completion

```bash
POST /api/mistral/chat
```

Generate responses using Mistral models:

**Request:**
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful Home Assistant automation expert."},
    {"role": "user", "content": "Create an automation to turn on lights when motion is detected."}
  ],
  "model": "mistral-small",
  "temperature": 0.7,
  "max_tokens": 500
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "mistral-small",
    "choices": [{
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Here's the YAML for your motion detection automation..."
      },
      "finish_reason": "stop"
    }],
    "usage": {
      "prompt_tokens": 50,
      "completion_tokens": 200,
      "total_tokens": 250
    }
  },
  "model_used": "mistral-small"
}
```

### List Available Models

```bash
GET /api/mistral/models
```

Get information about available Mistral models:

```json
{
  "models": [
    {
      "id": "mistral-tiny",
      "object": "model",
      "created": 1687134122,
      "owned_by": "mistral"
    },
    {
      "id": "mistral-small",
      "object": "model",
      "created": 1687134122,
      "owned_by": "mistral"
    }
  ],
  "default_model": "mistral-tiny",
  "count": 2
}
```

### Create Embeddings

```bash
POST /api/mistral/embeddings
```

Generate text embeddings for semantic search or similarity:

**Request:**
```json
{
  "input": "Smart home automation with Home Assistant",
  "model": "mistral-embed"
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "object": "list",
    "data": [{
      "object": "embedding",
      "embedding": [0.01, 0.02, ..., 0.99],
      "index": 0
    }],
    "model": "mistral-embed",
    "usage": {
      "prompt_tokens": 5,
      "total_tokens": 5
    }
  },
  "model_used": "mistral-embed"
}
```

## Usage Examples

### Example 1: Creating Automations with Mistral Vibe

```python
# Step 1: Check Mistral Vibe availability
health = await ha_mistral_health()
if health["status"] != "healthy":
    raise Exception("Mistral Vibe is not available")

# Step 2: Generate automation YAML
response = await ha_mistral_chat({
    "messages": [
        {"role": "system", "content": "You are a Home Assistant automation expert. Respond with only the YAML code, no explanations."},
        {"role": "user", "content": "Create an automation that turns on the living room lights when motion is detected after sunset, but only if someone is home."}
    ],
    "model": "mistral-small",
    "temperature": 0.3
})

automation_yaml = response["result"]["choices"][0]["message"]["content"]

# Step 3: Apply the automation
await ha_apply_automation({
    "automation_yaml": automation_yaml,
    "filename": "motion_lights.yaml"
})
```

### Example 2: Analyzing Home Assistant Setup

```python
# Get entity list
entities = await ha_list_entities()

# Ask Mistral to analyze and suggest improvements
analysis = await ha_mistral_chat({
    "messages": [
        {"role": "system", "content": "You are a smart home optimization expert."},
        {"role": "user", "content": f"Here are my Home Assistant entities: {entities}. Suggest 3 automation ideas that would improve my smart home setup."}
    ],
    "model": "mistral-medium",
    "temperature": 0.8
})

suggestions = analysis["result"]["choices"][0]["message"]["content"]
```

### Example 3: Creating Dashboard Descriptions

```python
# Generate dashboard description
dashboard_desc = await ha_mistral_chat({
    "messages": [
        {"role": "system", "content": "You create concise, user-friendly descriptions for smart home dashboards."},
        {"role": "user", "content": "Write a 2-sentence description for a 'Climate Control' dashboard that shows 7 TRV thermostats, boiler status, and energy usage."}
    ],
    "temperature": 0.5
})

description = dashboard_desc["result"]["choices"][0]["message"]["content"]
```

## Best Practices

### 1. Model Selection

Choose the right model for your task:

- **`mistral-tiny`**: Fast, cost-effective for simple tasks
- **`mistral-small`**: Balanced performance for most automation tasks
- **`mistral-medium`**: Higher quality for complex reasoning
- **`mistral-embed`**: For semantic search and similarity tasks

### 2. Temperature Settings

Adjust temperature based on task:

- **0.3-0.5**: Structured outputs (YAML, code generation)
- **0.7**: General conversation and suggestions
- **0.8-1.0**: Creative tasks and brainstorming

### 3. Error Handling

Always check if Mistral Vibe is available before using:

```python
health = await ha_mistral_health()
if health["status"] != "healthy":
    # Fall back to alternative method or inform user
    return "Mistral Vibe is not available, using fallback method..."
```

### 4. Rate Limiting

Be mindful of API rate limits:

- Cache frequent requests when possible
- Use appropriate `max_tokens` to avoid unnecessary costs
- Implement retry logic with exponential backoff

### 5. Prompt Engineering

For best results with automation generation:

```python
# ✅ Good: Specific and structured
{"role": "user", "content": "Create a Home Assistant automation in YAML format that turns on the 'light.living_room' when 'binary_sensor.motion_living_room' changes to 'on' after sunset. Include a 5-minute auto-off timer. Respond with only the YAML code."}

# ❌ Avoid: Vague requests
{"role": "user", "content": "Make me an automation for lights."}
```

## Troubleshooting

### "Mistral Vibe is not configured"

**Solution:** Set `MISTRAL_VIBE_API_URL` and `MISTRAL_VIBE_API_KEY` environment variables or configure through the add-on settings.

### Connection Errors

1. Check your internet connection
2. Verify the API URL is correct
3. Ensure your API key is valid
4. Check Mistral Vibe status page for outages

### Authentication Errors

1. Verify your API key is correct
2. Check for typos in the API key
3. Ensure the key hasn't expired
4. Regenerate the key if needed

### Rate Limit Errors

1. Reduce request frequency
2. Implement caching for repeated requests
3. Consider upgrading your Mistral Vibe plan
4. Use smaller models for less critical tasks

## Security Considerations

- 🔒 **API Key Protection**: Never expose your Mistral Vibe API key
- 📁 **Environment Variables**: Store keys in environment variables, not in code
- 🔄 **Key Rotation**: Rotate API keys periodically
- 📊 **Usage Monitoring**: Monitor API usage to detect anomalies

## Migration from Other AI Backends

Mistral Vibe can work alongside other AI assistants:

```python
# Try Mistral Vibe first, fall back to Cursor AI
def generate_automation(prompt):
    try:
        response = await ha_mistral_chat({
            "messages": [{"role": "user", "content": prompt}],
            "model": "mistral-small"
        })
        return response["result"]["choices"][0]["message"]["content"]
    except:
        # Fall back to Cursor AI or other backend
        return await ha_cursor_generate(prompt)
```

## Advanced: Custom Model Configuration

You can add custom models by extending the configuration:

```bash
# Add custom model endpoint
MISTRAL_VIBE_CUSTOM_MODELS='[{"name": "custom-model", "endpoint": "/v1/custom"}]'
```

## Support

For Mistral Vibe specific issues:
- Check Mistral Vibe documentation
- Contact Mistral Vibe support
- Review API status page

For HA Vibecode Agent integration issues:
- Open an issue on GitHub
- Check the HA Vibecode Agent documentation
- Review integration examples

---

**Happy automating with Mistral Vibe! 🚀**

Mistral Vibe brings powerful language models to your Home Assistant setup, 
enabling smarter automations, better natural language understanding, and 
more intelligent home management.