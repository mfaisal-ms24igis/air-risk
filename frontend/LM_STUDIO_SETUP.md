# 🤖 LM Studio Setup Guide for AIR RISK
**AI-Powered Air Quality Insights Integration**

## Overview
LM Studio provides local AI inference for generating intelligent air quality insights and recommendations in PDF reports. This guide covers complete setup and configuration.

---

## 📥 Installation

### Step 1: Download LM Studio
1. Visit [https://lmstudio.ai/](https://lmstudio.ai/)
2. Download for Windows
3. Install (no special permissions needed)

### Step 2: Download AI Model
1. Open LM Studio
2. Click **"Search"** tab
3. Search for: `TheBloke/Mistral-7B-Instruct-v0.3-GGUF`
4. Download: `mistral-7b-instruct-v0.3.Q4_K_M.gguf` (Recommended - 4.4GB)
   - Q4_K_M = Good balance of quality and speed
   - Alternative: Q5_K_M (better quality, slower) or Q3_K_M (faster, lower quality)

### Step 3: Load Model
1. Go to **"Chat"** tab in LM Studio
2. Select downloaded model from dropdown
3. Click **"Load Model"**
4. Wait for confirmation (model loads into RAM)

---

## 🔧 Server Configuration

### Step 1: Start Local Server
1. In LM Studio, click **"Local Server"** tab (left sidebar)
2. Ensure model is loaded (shown at top)
3. Configure settings:
   ```
   Port: 1234 (default)
   Context Length: 4096 tokens
   Temperature: 0.7 (balanced creativity)
   Max Tokens: 500 (per response)
   ```
4. Click **"Start Server"**
5. Verify status shows: `Server running on http://localhost:1234`

### Step 2: Test Server
Open PowerShell and run:
```powershell
curl http://localhost:1234/v1/models
```

Expected response:
```json
{
  "data": [
    {
      "id": "mistral-7b-instruct-v0.3",
      "object": "model",
      "owned_by": "organization-owner"
    }
  ]
}
```

---

## 🔐 Backend Integration

### Step 1: Configure Django Settings
Your backend is already configured! Verify in `backend/.env`:
```env
# LM Studio Configuration
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=mistral-7b-instruct-v0.3
LM_STUDIO_ENABLED=true
```

### Step 2: Verify Integration
The backend integration is in `backend/reports/services/ai_insights.py`. Test it:

```powershell
cd backend
python manage.py shell
```

```python
from reports.services.ai_insights import generate_air_quality_recommendations

# Test data
test_context = {
    'location_name': 'Lahore',
    'avg_aqi': 165,
    'max_aqi': 220,
    'primary_pollutant': 'PM2.5',
    'trend': 'increasing'
}

# Generate insights
recommendations = generate_air_quality_recommendations(test_context)
print(recommendations)
```

Expected output:
```
Based on the air quality data for Lahore, here are personalized recommendations:

1. Health Precautions: The average AQI of 165 indicates unhealthy air quality...
2. Timing: Avoid outdoor activities during peak pollution hours (6-9 AM, 6-9 PM)...
3. Protection: Use N95 masks when going outside...
[etc.]
```

---

## 📊 How It Works

### Data Flow
```
┌─────────────────────────────────────────────────────────────┐
│  Frontend: User requests custom report                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Django API: /api/v1/reports/reports/                       │
│  - Fetches air quality data (PostgreSQL)                    │
│  - Calculates exposure metrics                              │
│  - Prepares context for AI                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  reports/services/ai_insights.py                            │
│  - Builds prompt from context                               │
│  - Calls LM Studio API (localhost:1234)                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  LM Studio: Mistral-7B-Instruct model                       │
│  - Analyzes air quality data                                │
│  - Generates health recommendations                         │
│  - Returns personalized insights (JSON)                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  ReportLab: PDF Generation                                  │
│  - Combines data, charts, AI insights                       │
│  - Creates professional PDF report                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Frontend: Download PDF with AI recommendations             │
└─────────────────────────────────────────────────────────────┘
```

### Sample AI Prompt
```
You are an air quality health advisor. Analyze this data and provide recommendations:

Location: Lahore, Pakistan
Date Range: 2025-12-01 to 2025-12-07
Average AQI: 165 (Unhealthy)
Max AQI: 220 (Very Unhealthy)
Primary Pollutant: PM2.5
Trend: Increasing over the past week

Provide:
1. Health risk assessment
2. Activity recommendations
3. Protective measures
4. Best times for outdoor activities
```

---

## ⚡ Performance Optimization

### Model Selection
| Model | Size | Speed | Quality | Recommended For |
|-------|------|-------|---------|----------------|
| Q3_K_M | 3.2GB | Fast | Good | Testing, BASIC users |
| Q4_K_M | 4.4GB | Balanced | Very Good | **Production** |
| Q5_K_M | 5.2GB | Slower | Excellent | PREMIUM users |

### System Requirements
- **Minimum**: 8GB RAM, 4 CPU cores
- **Recommended**: 16GB RAM, 8 CPU cores
- **Storage**: 5-10GB for model + cache

### Speed Benchmarks (Q4_K_M on Core i7)
- Report generation: **8-15 seconds**
- Concurrent users: Up to **3-5** (before queuing)
- Token generation: ~25 tokens/second

### Tips for Faster Inference
1. **GPU Acceleration** (if available):
   - LM Studio → Settings → GPU Offload
   - Set layers: 32 (offload entire model to GPU)
   - Requires NVIDIA GPU with 6GB+ VRAM

2. **Optimize Context**:
   - Keep prompts concise (<500 words)
   - Reduce `max_tokens` to 300 if responses too long

3. **Pre-load Model**:
   - Start LM Studio server on system boot
   - Configure as Windows service (optional)

---

## 🛠️ Troubleshooting

### Issue: "Connection refused" Error
**Cause**: LM Studio server not running

**Solution**:
1. Open LM Studio
2. Go to "Local Server" tab
3. Click "Start Server"
4. Verify `http://localhost:1234` is accessible

### Issue: Slow Response (>30s)
**Cause**: Model too large for system RAM

**Solutions**:
1. Use lighter model (Q3_K_M instead of Q4_K_M)
2. Reduce context length to 2048
3. Close other applications to free RAM
4. Enable GPU offload (if available)

### Issue: Generic/Poor Quality Responses
**Cause**: Prompt needs refinement

**Solution**: Edit `backend/reports/services/ai_insights.py`:
```python
# Add more specific instructions
prompt = f"""You are an expert air quality analyst for Pakistan.
Use EPA AQI standards and provide culturally relevant advice.

Context: {json.dumps(context, indent=2)}

Provide exactly 5 recommendations in this format:
1. [Category]: [Specific action]
..."""
```

### Issue: "Model not found" Error
**Cause**: Model name mismatch in .env

**Solution**: Check loaded model name in LM Studio, update `.env`:
```env
LM_STUDIO_MODEL=mistral-7b-instruct-v0.3  # Match exact name
```

---

## 🚀 Production Deployment

### Option 1: Local LM Studio (Current Setup)
**Pros**: Free, private, no API limits
**Cons**: Requires server to run LM Studio

**Setup**:
1. Install LM Studio on production server
2. Start server on boot (Windows Task Scheduler)
3. Ensure firewall allows `localhost:1234`

### Option 2: Ollama (Alternative - Open Source)
**Pros**: Lighter than LM Studio, CLI-friendly, Docker support
**Cons**: Requires manual model setup

**Setup**:
```powershell
# Install Ollama
winget install Ollama.Ollama

# Pull Mistral model
ollama pull mistral

# Start server
ollama serve

# Update .env
LM_STUDIO_URL=http://localhost:11434/v1
```

### Option 3: Cloud API (Future)
**Pros**: No local resources, scalable
**Cons**: Costs, data privacy concerns

**Options**:
- OpenAI GPT-4 ($0.03/1K tokens)
- Anthropic Claude ($0.015/1K tokens)
- Cohere ($0.001/1K tokens - cheapest)

---

## 📊 Monitoring & Analytics

### Track AI Usage
Add to `backend/reports/services/ai_insights.py`:
```python
import logging

logger = logging.getLogger(__name__)

def generate_air_quality_recommendations(context):
    start_time = time.time()
    
    # ... existing code ...
    
    duration = time.time() - start_time
    logger.info(f"AI insight generated in {duration:.2f}s")
    
    return recommendations
```

### Log Viewing
```powershell
cd backend
tail -f logs/django.log | findstr "AI insight"
```

---

## ✅ Verification Checklist

- [ ] LM Studio downloaded and installed
- [ ] Mistral-7B-Instruct model downloaded (Q4_K_M)
- [ ] Model loaded in LM Studio
- [ ] Local server running on `http://localhost:1234`
- [ ] Backend `.env` configured with LM_STUDIO_URL
- [ ] Test API call successful (`curl http://localhost:1234/v1/models`)
- [ ] Django shell test passes (imports + sample generation)
- [ ] Frontend report generation works end-to-end
- [ ] AI recommendations appear in downloaded PDF

---

## 📚 Additional Resources

### LM Studio Documentation
- Official Docs: https://lmstudio.ai/docs
- GitHub: https://github.com/lmstudio-ai

### Model Information
- Mistral AI: https://mistral.ai/
- Hugging Face: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF

### Prompt Engineering
- Mistral Prompt Guide: https://docs.mistral.ai/guides/prompting/
- Best Practices: Use clear instructions, provide examples, specify format

---

## 🎓 Learning Path

1. **Basic Setup** (10 mins)
   - Install LM Studio
   - Download model
   - Start server

2. **Test Integration** (15 mins)
   - Run Django shell test
   - Generate sample report
   - Verify AI insights in PDF

3. **Customize Prompts** (30 mins)
   - Edit `ai_insights.py`
   - Experiment with temperature/tokens
   - Test different contexts

4. **Optimize Performance** (1 hour)
   - Try different model quantizations
   - Enable GPU offload
   - Monitor response times

5. **Production Deployment** (2 hours)
   - Set up auto-start
   - Configure monitoring
   - Load testing

---

**Status**: ✅ Backend integration complete, ready for testing
**Next Steps**: Run frontend report generation, verify PDF downloads
**Support**: Check troubleshooting section or Django logs for errors

