"""
AI-powered health insights using LM Studio local inference.

LM Studio provides OpenAI-compatible API for local LLM inference.
Default endpoint: http://localhost:1234/v1
"""

import logging
import os
from typing import Dict, Optional
import requests

logger = logging.getLogger(__name__)

# LM Studio configuration
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "local-model")  # Auto-detected by LM Studio
LM_STUDIO_TIMEOUT = int(os.getenv("LM_STUDIO_TIMEOUT", "30"))


def generate_health_recommendations(
    pollutant_data: Dict[str, Dict],
    location: Dict[str, float],
    user_context: Optional[Dict] = None,
) -> Optional[Dict]:
    """
    Generate AI-powered health recommendations based on pollutant data.
    
    Args:
        pollutant_data: Dictionary from TrendAnalyzer.get_ground_trends()
            Example: {
                "PM25": {"mean": 45.2, "max": 98.5, "p95": 85.3},
                "NO2": {"mean": 32.1, "max": 67.8, "p95": 58.4}
            }
        location: Location dict with "lat" and "lng"
        user_context: Optional user info (age, health conditions, etc.)
    
    Returns:
        Dictionary with AI-generated insights or None if LM Studio unavailable:
        {
            "summary": "Overall air quality assessment...",
            "recommendations": ["Avoid outdoor exercise...", "Use mask..."],
            "risk_level": "moderate",
            "sensitive_groups": ["children", "asthmatics"],
            "model": "mistral-7b-instruct"
        }
    """
    try:
        # Build prompt
        prompt = _build_health_prompt(pollutant_data, location, user_context)
        
        # Call LM Studio API (OpenAI-compatible)
        response = requests.post(
            f"{LM_STUDIO_URL}/chat/completions",
            json={
                "model": LM_STUDIO_MODEL,
                "messages": [
                    # Many local models don't support system role - combine into user message
                    {"role": "user", "content": (
                        "You are an air quality health advisor. Provide concise, "
                        "actionable health recommendations based on pollutant data. "
                        "Focus on practical advice for outdoor activities, vulnerable groups, "
                        "and protective measures. Keep responses under 200 words.\n\n"
                        f"{prompt}"
                    )},
                ],
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=LM_STUDIO_TIMEOUT,
        )
        
        if response.status_code != 200:
            logger.warning(f"LM Studio returned status {response.status_code}")
            return None
        
        result = response.json()
        ai_text = result["choices"][0]["message"]["content"]
        
        # Parse AI response into structured format
        insights = _parse_ai_response(ai_text, pollutant_data)
        insights["model"] = result.get("model", "unknown")
        
        logger.info(f"Generated AI insights using {insights['model']}")
        return insights
        
    except requests.exceptions.ConnectionError:
        logger.warning(
            "LM Studio not available. Start server: http://localhost:1234"
        )
        return None
    except requests.exceptions.Timeout:
        logger.error(f"LM Studio request timeout after {LM_STUDIO_TIMEOUT}s")
        return None
    except Exception as e:
        logger.error(f"AI insights generation failed: {e}")
        return None


def _build_health_prompt(
    pollutant_data: Dict,
    location: Dict,
    user_context: Optional[Dict],
) -> str:
    """Build prompt for LM Studio."""
    
    # Format pollutant concentrations
    pollutants_text = []
    for pollutant, stats in pollutant_data.items():
        if stats.get("mean"):
            pollutants_text.append(
                f"- {pollutant}: average {stats['mean']:.1f} µg/m³, "
                f"max {stats['max']:.1f} µg/m³"
            )
    
    pollutants_str = "\n".join(pollutants_text) if pollutants_text else "No data available"
    
    # User context (optional)
    user_str = ""
    if user_context:
        if user_context.get("age"):
            user_str += f"\nUser age: {user_context['age']}"
        if user_context.get("conditions"):
            user_str += f"\nHealth conditions: {', '.join(user_context['conditions'])}"
    
    prompt = f"""Analyze the following air quality data and provide health recommendations:

Location: {location['lat']:.2f}°N, {location['lng']:.2f}°E

Pollutant Concentrations (30-day period):
{pollutants_str}
{user_str}

Provide:
1. Overall air quality assessment
2. Specific health risks
3. Recommended protective actions
4. Advice for sensitive groups (children, elderly, asthmatics)
5. Best times for outdoor activities

Be concise and practical."""
    
    return prompt


def _parse_ai_response(ai_text: str, pollutant_data: Dict) -> Dict:
    """
    Parse AI response into structured format.
    
    Simple heuristic parsing - can be improved with more sophisticated NLP.
    """
    
    # Determine risk level based on PM2.5 (primary health indicator)
    pm25_mean = pollutant_data.get("PM25", {}).get("mean", 0)
    
    if pm25_mean > 150:
        risk_level = "very_high"
    elif pm25_mean > 55:
        risk_level = "high"
    elif pm25_mean > 35:
        risk_level = "moderate"
    elif pm25_mean > 12:
        risk_level = "low"
    else:
        risk_level = "good"
    
    # Extract recommendations (simple line-based parsing)
    lines = ai_text.split("\n")
    recommendations = []
    for line in lines:
        line = line.strip()
        # Look for bullet points or numbered items
        if line.startswith(("-", "•", "*")) or (line and line[0].isdigit() and line[1] in (".", ")")):
            # Remove bullet/number
            rec = line.lstrip("-•*0123456789.) ").strip()
            if len(rec) > 10:  # Filter out very short lines
                recommendations.append(rec)
    
    # Identify sensitive groups mentioned
    sensitive_groups = []
    text_lower = ai_text.lower()
    if "child" in text_lower or "kid" in text_lower:
        sensitive_groups.append("children")
    if "elderly" in text_lower or "senior" in text_lower:
        sensitive_groups.append("elderly")
    if "asthma" in text_lower or "respiratory" in text_lower:
        sensitive_groups.append("people with respiratory conditions")
    if "heart" in text_lower or "cardiovascular" in text_lower:
        sensitive_groups.append("people with heart disease")
    
    return {
        "summary": ai_text[:200] + "..." if len(ai_text) > 200 else ai_text,
        "full_text": ai_text,
        "recommendations": recommendations[:5],  # Top 5 recommendations
        "risk_level": risk_level,
        "sensitive_groups": list(set(sensitive_groups)),
    }


def test_lm_studio_connection() -> bool:
    """
    Test if LM Studio is running and accessible.
    
    Returns:
        True if LM Studio is available, False otherwise
    """
    try:
        response = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            logger.info(f"LM Studio available with {len(models.get('data', []))} models")
            return True
        return False
    except:
        logger.warning("LM Studio not available")
        return False


# Fallback health recommendations (used when LM Studio unavailable)
FALLBACK_RECOMMENDATIONS = {
    "good": {
        "summary": "Air quality is good. Outdoor activities are safe for everyone.",
        "recommendations": [
            "Enjoy outdoor activities",
            "No protective measures needed",
            "Good time for exercise",
        ],
        "risk_level": "good",
        "sensitive_groups": [],
    },
    "moderate": {
        "summary": "Air quality is acceptable. Sensitive individuals may experience minor issues.",
        "recommendations": [
            "Sensitive groups should limit prolonged outdoor exertion",
            "Monitor symptoms if you have respiratory conditions",
            "Close windows during peak pollution hours",
        ],
        "risk_level": "moderate",
        "sensitive_groups": ["people with respiratory conditions", "children", "elderly"],
    },
    "unhealthy_sensitive": {
        "summary": "Unhealthy for sensitive groups. General public may experience effects with prolonged exposure.",
        "recommendations": [
            "Sensitive groups should avoid outdoor activities",
            "Wear N95 masks if going outside",
            "Use air purifiers indoors",
            "Limit outdoor exercise",
        ],
        "risk_level": "high",
        "sensitive_groups": ["children", "elderly", "people with respiratory conditions", "people with heart disease"],
    },
    "unhealthy": {
        "summary": "Unhealthy air quality. Everyone may experience health effects.",
        "recommendations": [
            "Avoid outdoor activities",
            "Wear N95/N99 masks if you must go outside",
            "Keep windows closed",
            "Use HEPA air purifiers",
            "Reschedule outdoor events",
        ],
        "risk_level": "very_high",
        "sensitive_groups": ["everyone"],
    },
}


def get_fallback_recommendations(pollutant_data: Dict) -> Dict:
    """
    Get fallback recommendations when LM Studio is unavailable.
    
    Uses simple AQI-based categorization.
    """
    pm25_mean = pollutant_data.get("PM25", {}).get("mean", 0)
    
    if pm25_mean > 55:
        category = "unhealthy"
    elif pm25_mean > 35:
        category = "unhealthy_sensitive"
    elif pm25_mean > 12:
        category = "moderate"
    else:
        category = "good"
    
    fallback = FALLBACK_RECOMMENDATIONS[category].copy()
    fallback["model"] = "fallback-rules"
    return fallback
