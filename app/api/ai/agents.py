import openai
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class BaseAIAgent:
    """
    Base class for AI agents using the OpenAI GPT-4 API.
    This class provides a method to generate a report section based on a dynamic prompt template and context.
    In a full implementation, these agents can be integrated with the CrewAI framework for orchestration.
    """
    def __init__(self, prompt_template: str):
        self.prompt_template = prompt_template

    def generate_section(self, context: Dict[str, Any]) -> str:
        """
        Generates a report section using the provided context.
        
        The method dynamically formats the prompt template with the given context,
        ensuring that details like industry, company name, and other specifics tailor the output.
        It then calls the GPT-4 API to generate the corresponding section of the report.
        
        Args:
            context (Dict[str, Any]): A dictionary containing values to replace in the prompt template.
        
        Returns:
            str: The generated report section.
        
        Raises:
            Exception: Propagates any errors encountered during the API call.
        """
        # Dynamically generate the prompt based on input context.
        prompt = self.prompt_template.format(**context)
        logger.info("Generating section with prompt: %s", prompt)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert report writer with deep industry knowledge."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            content = response["choices"][0]["message"]["content"].strip()
            logger.info("Section generated successfully.")
            return content
        except Exception as e:
            logger.error("Error generating section: %s", str(e), exc_info=True)
            raise e

class ExecutiveSummaryAgent(BaseAIAgent):
    """
    AI Agent for generating the Executive Summary section of a report.
    This agent's prompt is dynamically customized based on the industry, company, and key findings provided.
    """
    def __init__(self):
        prompt_template = (
            "Generate an Executive Summary for a report in the {industry} industry for {company}. "
            "Highlight key insights and overarching themes. "
            "Context:\n"
            "Key Findings: {key_findings}\n"
            "Additional Notes: {notes}\n"
        )
        super().__init__(prompt_template)

class MarketAnalysisAgent(BaseAIAgent):
    """
    AI Agent for generating the Market Analysis section of a report.
    The prompt includes dynamic fields for industry trends and competitive landscape, tailored to the provided context.
    """
    def __init__(self):
        prompt_template = (
            "Generate a detailed Market Analysis for the {industry} industry, with a focus on {company}'s competitive environment. "
            "Include analysis based on the following context:\n"
            "Market Trends: {market_trends}\n"
            "Competitors: {competitors}\n"
        )
        super().__init__(prompt_template)

class RecommendationsAgent(BaseAIAgent):
    """
    AI Agent for generating the Recommendations section of a report.
    This prompt is customized dynamically with the company's performance and improvement areas.
    """
    def __init__(self):
        prompt_template = (
            "Generate actionable Recommendations for {company}, a player in the {industry} industry. "
            "Consider the following context:\n"
            "Company Performance: {performance}\n"
            "Areas for Improvement: {improvements}\n"
            "Provide clear, strategic advice tailored to these specifics."
        )
        super().__init__(prompt_template)
