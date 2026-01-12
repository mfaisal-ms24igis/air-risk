"""
AI service for generating report insights and summaries.
"""

import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class AIService:
    """
    Service for interacting with local AI API for report enhancement.
    """

    def __init__(self):
        self.base_url = getattr(settings, 'AI_API_BASE_URL', 'http://localhost:1234')
        self.model = getattr(settings, 'AI_MODEL', 'mistralai/mistral-7b-instruct-v0.3')
        self.timeout = getattr(settings, 'AI_API_TIMEOUT', 30)

    def generate_report_insights(self, report_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate AI insights for a report based on the data.

        Args:
            report_data: Dictionary containing report information

        Returns:
            AI-generated insights text or None if failed
        """
        try:
            # Prepare the context from report data
            context = self._prepare_report_context(report_data)

            # Create the prompt
            prompt = f"""
Based on the following air quality report data, provide a comprehensive analysis and insights:

{context}

Please provide:
1. A summary of the air quality situation
2. Key trends and patterns observed
3. Health implications for the population
4. Recommendations for improvement
5. Any notable observations or concerns

Answer in a professional, informative tone suitable for environmental reports.
"""

            # Make API call
            response = self._call_ai_api(prompt)
            if response:
                return response.strip()
            return None

        except Exception as e:
            logger.error(f"Failed to generate AI insights: {e}")
            return None

    def generate_executive_summary(self, report_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate an executive summary for the report.

        Args:
            report_data: Dictionary containing report information

        Returns:
            AI-generated executive summary or None if failed
        """
        try:
            context = self._prepare_report_context(report_data)

            prompt = f"""
Create a concise executive summary (200-300 words) for this air quality report:

{context}

The summary should cover:
- Overall air quality status
- Key findings
- Population impact
- Recommendations

Write in a formal, executive-level tone.
"""

            response = self._call_ai_api(prompt)
            if response:
                return response.strip()
            return None

        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            return None

    def _prepare_report_context(self, report_data: Dict[str, Any]) -> str:
        """
        Prepare context information from report data for AI processing.
        """
        context_parts = []

        # Basic report info
        if 'district_name' in report_data:
            context_parts.append(f"District: {report_data['district_name']}")
        if 'report_type' in report_data:
            context_parts.append(f"Report Type: {report_data['report_type']}")
        if 'date_range' in report_data:
            context_parts.append(f"Date Range: {report_data['date_range']}")

        # Air quality data
        if 'air_quality_data' in report_data:
            aq_data = report_data['air_quality_data']
            context_parts.append("Air Quality Data:")
            for pollutant, data in aq_data.items():
                if isinstance(data, dict):
                    avg_value = data.get('average', 'N/A')
                    max_value = data.get('maximum', 'N/A')
                    context_parts.append(f"  {pollutant}: Average {avg_value}, Max {max_value}")
                else:
                    context_parts.append(f"  {pollutant}: {data}")

        # Population exposure
        if 'population_exposure' in report_data:
            exposure = report_data['population_exposure']
            context_parts.append("Population Exposure:")
            if isinstance(exposure, dict):
                for level, count in exposure.items():
                    context_parts.append(f"  {level}: {count} people")

        # Health impacts
        if 'health_impacts' in report_data:
            impacts = report_data['health_impacts']
            context_parts.append("Health Impacts:")
            for impact, description in impacts.items():
                context_parts.append(f"  {impact}: {description}")

        return "\n".join(context_parts)

    def _call_ai_api(self, prompt: str) -> Optional[str]:
        """
        Make API call to the local AI service.
        """
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert environmental scientist and air quality analyst. Provide accurate, evidence-based analysis of air quality data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": False
            }

            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
                else:
                    logger.error(f"Unexpected AI API response format: {data}")
                    return None
            else:
                logger.error(f"AI API request failed with status {response.status_code}: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"AI API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling AI API: {e}")
            return None


# Global instance
ai_service = AIService()