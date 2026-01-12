# LM Studio Integration Guide

## Overview

AIR RISK uses **LM Studio** for local AI-powered health recommendations based on air quality data. This document covers installation, configuration, and integration with the Django backend.

---

## Why LM Studio?

- ✅ **100% Local**: No cloud dependencies, full data privacy
- ✅ **OpenAI-Compatible API**: Drop-in replacement for GPT APIs
- ✅ **Hardware Efficient**: Optimized for consumer GPUs (4GB+ VRAM)
- ✅ **Multi-Model Support**: Switch between Mistral, Llama, Phi, etc.
- ✅ **Free**: No API costs or rate limits

---

## Installation

### 1. Download LM Studio

Visit: [https://lmstudio.ai/](https://lmstudio.ai/)

- **Windows**: Download `.exe` installer
- **macOS**: Download `.dmg` installer
- **Linux**: Download `.AppImage`

Install and launch LM Studio.

---

### 2. Download a Model

**Recommended Models** (in order of preference):

| Model | Size | VRAM | Use Case | Download |
|-------|------|------|----------|----------|
| **Mistral-7B-Instruct-v0.3** (Q4) | 4.1 GB | 6 GB | **Production** (Best accuracy/speed) | `TheBloke/Mistral-7B-Instruct-v0.3-GGUF` |
| **Llama-3-8B-Instruct** (Q4) | 4.3 GB | 6 GB | Production (Alternative) | `Meta-Llama-3-8B-Instruct-Q4_K_M.gguf` |
| **Phi-3-Mini-4K-Instruct** (Q4) | 2.4 GB | 4 GB | **Development** (Low VRAM) | `microsoft/Phi-3-mini-4k-instruct-gguf` |
| **TinyLlama-1.1B** (Q4) | 0.6 GB | 2 GB | Testing (Fast, less accurate) | `TinyLlama/TinyLlama-1.1B-Chat-v1.0-GGUF` |

**Steps:**
1. Open LM Studio → **Search** tab
2. Search for model (e.g., "Mistral 7B Instruct")
3. Select **GGUF** format, **Q4_K_M** quantization (best balance)
4. Click **Download**
5. Wait for download to complete

---

### 3. Start the Local Server

1. Go to **Local Server** tab in LM Studio
2. Select your downloaded model from dropdown
3. Configure settings:
   - **Port**: `1234` (default)
   - **CORS**: Enable "Allow CORS"
   - **Context Length**: 4096 tokens (default)
   - **Temperature**: 0.7 (default)
4. Click **Start Server**

You should see:
```
Server running at http://localhost:1234
OpenAI compatible endpoint: http://localhost:1234/v1
```

---

## Django Backend Configuration

### Environment Variables

Add to your `.env` file:

```bash
# LM Studio Configuration
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=auto  # Auto-detect loaded model
LM_STUDIO_TIMEOUT=30  # Request timeout in seconds
```

**Optional Configuration:**

```bash
# Advanced Settings
LM_STUDIO_TEMPERATURE=0.7  # Response creativity (0.0-1.0)
LM_STUDIO_MAX_TOKENS=300   # Max response length
```

---

## Testing the Integration

### 1. Test LM Studio Connection

```bash
cd backend
python manage.py shell
```

```python
from reports.services.ai_insights import test_lm_studio_connection

# Test connection
result = test_lm_studio_connection()
print(result)
```

**Expected Output:**
```python
{
    'status': 'connected',
    'url': 'http://localhost:1234/v1',
    'models': ['mistral-7b-instruct-v0.3.Q4_K_M.gguf'],
    'active_model': 'mistral-7b-instruct-v0.3.Q4_K_M.gguf'
}
```

---

### 2. Test AI Recommendation Generation

```python
from reports.services.ai_insights import generate_health_recommendations

# Sample pollutant data
pollutant_data = {
    'PM2.5': {'current': 85.5, 'trend': 'increasing', 'aqi': 165},
    'NO2': {'current': 42.3, 'trend': 'stable', 'aqi': 95}
}

# Generate recommendations
result = generate_health_recommendations(
    pollutant_data=pollutant_data,
    location="Lahore, Pakistan",
    user_context="General public"
)

print(result['summary'])
print("\nRecommendations:")
for rec in result['recommendations']:
    print(f"  - {rec}")
```

**Expected Output:**
```python
{
    'summary': 'Air quality in Lahore is unhealthy with elevated PM2.5...',
    'recommendations': [
        'Avoid prolonged outdoor activities',
        'Use N95 masks when going outside',
        'Keep windows closed during peak pollution hours'
    ],
    'risk_level': 'high',
    'sensitive_groups': ['children', 'elderly', 'respiratory conditions']
}
```

---

### 3. Test with cURL

```bash
# Test chat completion endpoint
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [
      {"role": "user", "content": "What are health risks of PM2.5 at 85 µg/m³?"}
    ],
    "temperature": 0.7,
    "max_tokens": 150
  }'
```

---

## Fallback Behavior

If LM Studio is **not running** or **unreachable**, the system automatically falls back to **rule-based recommendations**:

```python
# Example fallback response (no AI)
{
    'summary': 'Based on current air quality index of 165 (Unhealthy)...',
    'recommendations': [
        'Limit outdoor activities, especially for sensitive groups',
        'Use air purifiers indoors',
        'Wear N95/N99 masks when outdoors'
    ],
    'risk_level': 'unhealthy',
    'ai_generated': False  # Indicates fallback mode
}
```

**Fallback Triggers:**
- LM Studio server not running
- Connection timeout (>30s)
- Model loading error
- API key mismatch (if configured)

---

## Production Deployment

### Option 1: Same Server as Django

```bash
# Install LM Studio CLI
sudo apt install lmstudio-cli  # Linux example

# Start server as systemd service
sudo systemctl enable lmstudio-server
sudo systemctl start lmstudio-server
```

**systemd unit file** (`/etc/systemd/system/lmstudio-server.service`):
```ini
[Unit]
Description=LM Studio Local Inference Server
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/lmstudio
ExecStart=/usr/local/bin/lmstudio server --port 1234 --model /models/mistral-7b.gguf
Restart=always

[Install]
WantedBy=multi-user.target
```

---

### Option 2: Dedicated Inference Server

For high-traffic deployments, run LM Studio on a **separate GPU server**:

1. **Inference Server** (GPU machine):
   - Install LM Studio
   - Load Mistral-7B or Llama-3-8B
   - Bind to `0.0.0.0:1234` (expose to network)
   - Configure firewall to allow Django server IP

2. **Django Server** (CPU machine):
   - Update `.env`:
     ```bash
     LM_STUDIO_URL=http://192.168.1.100:1234/v1
     ```

---

## Model Selection Guide

### For Development (Low VRAM)

- **Phi-3-Mini** (2.4 GB) - Fast, good for testing
- **TinyLlama** (0.6 GB) - Very fast, basic quality

### For Production (6+ GB VRAM)

- **Mistral-7B-Instruct** (4.1 GB) - **Best overall**
  - Excellent instruction following
  - Good medical/health knowledge
  - Balanced speed and accuracy

- **Llama-3-8B-Instruct** (4.3 GB) - Alternative
  - Slightly slower than Mistral
  - Better for longer reasoning chains

### For High-End Production (24+ GB VRAM)

- **Mixtral-8x7B-Instruct** (26 GB) - Best quality
  - State-of-the-art performance
  - Requires A100/H100 GPUs

---

## Prompt Engineering

The system uses this prompt template:

```
You are a public health expert analyzing air quality data for {location}.

Current pollutant levels:
- PM2.5: {pm25_value} µg/m³ (AQI: {pm25_aqi}, {trend})
- NO2: {no2_value} µg/m³ (AQI: {no2_aqi}, {trend})
...

User context: {user_context}

Provide:
1. Brief health impact summary (2-3 sentences)
2. 3-5 specific actionable recommendations
3. Risk level (low/moderate/high/very_high)
4. Vulnerable groups (children, elderly, respiratory conditions, etc.)

Keep response under 300 words.
```

To customize prompts, edit `reports/services/ai_insights.py` → `_build_health_prompt()`

---

## Troubleshooting

### Issue: "Connection refused" error

**Cause**: LM Studio server not running

**Fix**:
1. Open LM Studio → Local Server tab
2. Click "Start Server"
3. Verify `http://localhost:1234` is accessible

---

### Issue: "Model not loaded" error

**Cause**: No model selected in LM Studio

**Fix**:
1. Download a model (see Step 2 above)
2. Select model from dropdown in Local Server tab
3. Start server

---

### Issue: Slow response times (>10s)

**Cause**: Model too large for GPU

**Fix**:
1. Switch to smaller quantization (Q3_K_M instead of Q4_K_M)
2. Use faster model (Phi-3 instead of Mistral-7B)
3. Reduce `max_tokens` in prompt (300 → 150)

---

### Issue: Poor quality recommendations

**Cause**: Model too small or temperature too high

**Fix**:
1. Upgrade to larger model (Mistral-7B or Llama-3-8B)
2. Lower temperature in `.env`:
   ```bash
   LM_STUDIO_TEMPERATURE=0.5
   ```

---

## API Endpoint Reference

### Generate Location Report (with AI)

**PREMIUM users only**

```bash
POST /api/v1/exposure/reports/location/
Authorization: Bearer <jwt_token>

{
  "lat": 31.5204,
  "lng": 74.3587,
  "radius_km": 5.0,
  "start_date": "2025-11-11",
  "end_date": "2025-12-11",
  "include_ai": true  # Requires LM Studio
}
```

**Response:**
```json
{
  "report_id": 124,
  "status": "processing",
  "poll_url": "/api/v1/exposure/reports/124/",
  "estimated_time_seconds": 30
}
```

---

## Performance Benchmarks

| Model | Hardware | Tokens/sec | Avg Response Time | VRAM Usage |
|-------|----------|------------|-------------------|------------|
| Mistral-7B (Q4) | RTX 3060 (12GB) | 35 t/s | 8-12s | 6.2 GB |
| Mistral-7B (Q4) | Apple M2 Max | 22 t/s | 12-18s | Unified |
| Phi-3-Mini (Q4) | RTX 3060 | 60 t/s | 4-6s | 3.8 GB |
| Llama-3-8B (Q4) | RTX 4090 (24GB) | 50 t/s | 6-10s | 7.1 GB |

---

## Security Considerations

1. **No API Keys Required**: LM Studio runs locally, no OpenAI keys needed
2. **Data Privacy**: All inference happens on-premises, no data leaves server
3. **Firewall**: Only expose port 1234 to Django server IP (not public)
4. **Resource Limits**: Use Docker CPU/memory limits to prevent DoS

---

## Further Reading

- [LM Studio Documentation](https://lmstudio.ai/docs)
- [GGUF Format Guide](https://github.com/ggerganov/llama.cpp)
- [Model Quantization Explained](https://huggingface.co/docs/optimum/concept_guides/quantization)

---

## Support

For issues with:
- **LM Studio**: [Discord](https://discord.gg/lmstudio)
- **Django Integration**: Check `reports/services/ai_insights.py` logs
- **Model Selection**: See "Model Selection Guide" above
