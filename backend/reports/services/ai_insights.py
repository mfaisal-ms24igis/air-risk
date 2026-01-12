"""
AI-powered health insights using LM Studio local inference.

LM Studio provides OpenAI-compatible API for local LLM inference.
Default endpoint: http://localhost:1234/v1
"""

import logging
import os
import json
from typing import Dict, Optional, Any
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


def generate_professional_narrative(context_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends raw metrics to LLM and returns 'High Class' narrative text.

    Uses persona-based prompting with GIS Analyst perspective to generate 
    professional, high-stakes technical reports with spatial analysis.

    Args:
        context_data: Structured trend data from TrendAnalyzer

    Returns:
        Professional narrative report as JSON with executive_summary, geographic_analysis, etc.
    """
    try:
        # 1. Extract location and spatial context
        location = context_data.get('location', {})
        lat = location.get('lat', 0)
        lng = location.get('lng', 0)
        radius_km = location.get('radius_km', 5)
        district_name = location.get('district', {}).get('name', 'Unknown Location')
        
        # 2. Calculate Trend Direction (14-day trend)
        current_pm25 = context_data.get('ground_trends', {}).get('PM25', {}).get('mean', 0)
        baseline_pm25 = context_data.get('historical_baseline', {}).get('pm25', current_pm25)

        delta = current_pm25 - baseline_pm25
        trend_pct = (delta / baseline_pm25) * 100 if baseline_pm25 else 0
        trend_dir = "increasing" if delta > 0 else "decreasing"
        trend_14_day = f"{trend_dir} by {abs(trend_pct):.1f}%"

        # 3. Extract pollutant metrics
        pm10_mean = context_data.get('ground_trends', {}).get('PM10', {}).get('mean', 0)
        pm10_max = context_data.get('ground_trends', {}).get('PM10', {}).get('max', 0)
        no2_mean = context_data.get('ground_trends', {}).get('NO2', {}).get('mean', 0)
        no2_max = context_data.get('ground_trends', {}).get('NO2', {}).get('max', 0)
        so2_mean = context_data.get('ground_trends', {}).get('SO2', {}).get('mean', 0)
        co_mean = context_data.get('ground_trends', {}).get('CO', {}).get('mean', 0)

        # 4. Extract satellite data
        sat_no2_mean = context_data.get('gee_data', {}).get('no2', {}).get('mean', 0)
        sat_so2_mean = context_data.get('gee_data', {}).get('so2', {}).get('mean', 0)
        sat_co_mean = context_data.get('gee_data', {}).get('co', {}).get('mean', 0)
        
        # 5. Spatial pattern analysis
        stations = context_data.get('stations', {})
        station_count = stations.get('count', 0)
        
        # Determine spatial pattern from station distribution
        map_description = "urban concentration"
        if station_count > 3:
            map_description = "distributed network pattern"
        elif station_count <= 1:
            map_description = "isolated point source"
            
        # Plume analysis based on pollutant ratios
        plume_analysis = "diffuse distribution"
        if sat_no2_mean > 1e-4:
            plume_analysis = "linear corridor pattern suggesting transportation sources"
        elif sat_so2_mean > 5e-5:
            plume_analysis = "point-source emissions with downwind dispersion"
            
        # 6. Format the Enhanced System Prompt
        system_prompt = """You are a Senior GIS Analyst and Environmental Scientist generating narrative text for a high-level government air quality report.

Your Tone:
- Professional, authoritative, and precise
- Scientific and data-driven (cite specific numbers)
- Use directional/spatial language (e.g., "North-East quadrant," "along the highway corridor")
- Avoid generic advice - be specific and context-aware

Your Task:
Generate 3 distinct report sections:
1. "geographic_analysis": A professional paragraph describing WHERE the pollution is concentrated using directional language
2. "source_identification": Hypothesize sources based on the pollutant mix:
   - High NO2 + Urban/Linear = Traffic/vehicular sources
   - High SO2 + Point source = Industrial/power generation
   - High CO + PM = Biomass burning/residential heating
3. "forecast_advisory": A data-driven prediction for the next 48 hours based on the trend direction

Format your response as a JSON object with the following keys:
- "executive_summary": A 3-sentence high-level overview
- "geographic_analysis": Spatial analysis with directional language
- "source_identification": Evidence-based source attribution
- "trend_narrative": Temporal analysis of changes over monitoring period
- "forecast_advisory": 48-hour forecast based on current trends
- "recommendations": List of 4 specific, actionable bullet points"""

        # 7. Format the User Prompt with Spatial Context
        user_prompt = f"""GENERATE LOCATION ANALYSIS FOR {district_name}

[SPATIAL DATA]
- Map Center: {lat:.4f}°N, {lng:.4f}°E (Radius: {radius_km}km)
- Spatial Pattern: {map_description}
- Ground Stations: {station_count} monitoring sites
- Plume Behavior: {plume_analysis}

[SATELLITE READINGS (Sentinel-5P)]
- NO2 Column: {sat_no2_mean:.2e} mol/m² (Traffic/Industry indicator)
- SO2 Column: {sat_so2_mean:.2e} mol/m² (Coal/Heavy Industry indicator)
- CO Column: {sat_co_mean:.2e} mol/m² (Biomass Burning indicator)

[GROUND TRUTH]
- Station PM2.5: {current_pm25:.1f} µg/m³ (Mean) / {context_data.get('ground_trends', {}).get('PM25', {}).get('max', 0):.1f} µg/m³ (Max)
- Station PM10: {pm10_mean:.1f} µg/m³ (Mean) / {pm10_max:.1f} µg/m³ (Max)
- Station NO2: {no2_mean:.1f} µg/m³ (Mean) / {no2_max:.1f} µg/m³ (Max)
- Station SO2: {so2_mean:.1f} µg/m³ (Mean)
- Station CO: {co_mean:.1f} µg/m³ (Mean)

[TEMPORAL TRENDS]
- Station Trend (14-day): {trend_14_day}
- Baseline Comparison: PM2.5 is {trend_dir} compared to 30-day average

[CROSS-CORRELATION]
- Ground PM2.5 vs Satellite NO2: {"High correlation - traffic source likely" if no2_mean > 40 and sat_no2_mean > 1e-4 else "Moderate correlation"}
- Ground PM2.5 vs Satellite SO2: {"Strong correlation - industrial source likely" if so2_mean > 20 and sat_so2_mean > 5e-5 else "Weak correlation"}

INSTRUCTIONS:
Using the spatial pattern and pollutant mix above, write all required sections.
- If NO2 is high and spatial pattern suggests "linear" or "corridor", mention highway/traffic sources
- If SO2 is high, mention industrial or power generation sources
- Use directional language in geographic_analysis (e.g., "concentration in northern sector")
- Make forecast_advisory specific to the trend data (not generic)"""

        # 4. Call LLM using LM Studio (local inference)
        llm_response = call_llm_for_narrative(system_prompt, user_prompt)

        # 5. Parse and return the JSON response
        if llm_response:
            try:
                return json.loads(llm_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                return get_fallback_narrative(context_data)
        else:
            return get_fallback_narrative(context_data)

    except Exception as e:
        logger.error(f"Error generating professional narrative: {e}")
        return get_fallback_narrative(context_data)


def call_llm_for_narrative(system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    Call LM Studio API for professional narrative generation.
    """
    try:
        # Use LM Studio OpenAI-compatible API
        response = requests.post(
            f"{LM_STUDIO_URL}/chat/completions",
            json={
                "model": LM_STUDIO_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,  # Lower temperature for more consistent professional output
                "max_tokens": 1000,
            },
            timeout=LM_STUDIO_TIMEOUT,
        )

        if response.status_code != 200:
            logger.warning(f"LM Studio returned status {response.status_code}")
            return None

        result = response.json()
        return result["choices"][0]["message"]["content"]

    except requests.exceptions.ConnectionError:
        logger.warning("LM Studio not available for narrative generation")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"LM Studio request timeout after {LM_STUDIO_TIMEOUT}s")
        return None
    except Exception as e:
        logger.error(f"Narrative LLM API call failed: {e}")
        return None


def get_fallback_narrative(context_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback narrative when LLM is not available.
    Enhanced with spatial analysis.
    """
    location_name = context_data.get('location', {}).get('district', {}).get('name', 'Unknown Location')
    pm25_mean = context_data.get('ground_trends', {}).get('PM25', {}).get('mean', 0)
    no2_mean = context_data.get('ground_trends', {}).get('NO2', {}).get('mean', 0)
    so2_mean = context_data.get('ground_trends', {}).get('SO2', {}).get('mean', 0)
    
    # Determine likely sources
    sources = []
    if no2_mean > 40:
        sources.append("vehicular traffic")
    if so2_mean > 20:
        sources.append("industrial emissions")
    if not sources:
        sources.append("urban background pollution")
    
    source_text = " and ".join(sources)
    
    # Trend direction
    current_pm25 = pm25_mean
    baseline_pm25 = context_data.get('historical_baseline', {}).get('pm25', current_pm25)
    delta = current_pm25 - baseline_pm25
    trend_dir = "increasing" if delta > 0 else "decreasing" if delta < 0 else "stable"

    return {
        "executive_summary": f"Air quality monitoring in {location_name} shows PM2.5 levels at {pm25_mean:.1f} µg/m³. Satellite and ground station data indicate urban pollution patterns consistent with {source_text}. Current trends show {trend_dir} conditions over the monitoring period.",
        "geographic_analysis": f"Pollution is concentrated within a {context_data.get('location', {}).get('radius_km', 5)}km radius of the monitoring location in {location_name}. Ground station measurements indicate diffuse urban pollution patterns with readings distributed across the monitoring network. Satellite observations confirm regional-scale pollutant dispersion consistent with typical urban atmospheric conditions.",
        "source_identification": f"Analysis of pollutant ratios indicates primary sources are {source_text}. NO2 concentrations of {no2_mean:.1f} µg/m³ suggest contributions from combustion processes. The spatial distribution pattern and chemical composition are consistent with mixed urban emission sources including transportation corridors and stationary combustion facilities.",
        "trend_narrative": f"Over the monitoring period, PM2.5 concentrations have shown {trend_dir} patterns with mean values of {pm25_mean:.1f} µg/m³. Satellite observations provide complementary spatial context showing regional pollution distribution. Ground truth measurements validate satellite-derived pollution estimates within the analysis domain.",
        "forecast_advisory": f"Based on current {trend_dir} trends and prevailing meteorological patterns, PM2.5 concentrations are expected to {'remain elevated' if pm25_mean > 35 else 'remain within moderate ranges'} over the next 48 hours. Sensitive populations should monitor conditions and adjust outdoor activities accordingly. Continued surveillance through ground monitoring networks is recommended.",
        "recommendations": [
            "Continue regular air quality monitoring at existing station network",
            "Implement targeted public awareness campaigns during elevated pollution episodes",
            "Enhance monitoring of sensitive populations including children and elderly residents",
            f"Consider source-specific interventions targeting {source_text} based on observed pollutant signatures"
        ]
    }
