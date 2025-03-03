import openai
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class BaseAIAgent:
    """
    Base class for AI agents using the OpenAI GPT-4 API.
    This class provides a method to generate a report section
    based on a dynamic prompt template and context.
    """
    def __init__(self, prompt_template: str):
        self.prompt_template = prompt_template

    def generate_section(self, context: Dict[str, Any]) -> str:
        """
        Generates a report section using the provided context.

        The method dynamically formats the prompt template with the given context,
        ensuring that details like industry, company name, key metrics, etc.,
        tailor the output. Then it calls the GPT-4 API to generate the section.
        """
        # Dynamically generate the prompt based on input context
        prompt = self.prompt_template.format(**context)
        logger.info("Generating section with prompt:\n%s", prompt)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert report writer with deep industry knowledge."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
            )
            content = response["choices"][0]["message"]["content"].strip()
            logger.info("Section generated successfully.")
            return content
        except Exception as e:
            logger.error("Error generating section: %s", str(e), exc_info=True)
            raise e


# ---------------------------------------------------------------
# 1) Executive Summary & Investment Rationale
# ---------------------------------------------------------------
class ExecutiveSummaryAgent(BaseAIAgent):
    """
    AI Agent for Section 1: Executive Summary & Investment Rationale
    Subheadings:
      - Overview
      - Key Investment Considerations
      - Investment Readiness Overview
      - Investment Risks & Considerations
      - Investment Recommendations & Next Steps
        * Short-Term (1–3 Months)
        * Medium-Term (3–6 Months)
        * Long-Term (6–12 Months)
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting Section 1: Executive Summary & Investment Rationale.\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "\n"
            "Retrieved Context (Pitch Decks, Docs, etc.):\n"
            "{retrieved_context}\n"
            "\n"
            "Please structure your response with the following subheadings:\n"
            "1) Overview\n"
            "2) Key Investment Considerations\n"
            "3) Investment Readiness Overview\n"
            "4) Investment Risks & Considerations\n"
            "5) Investment Recommendations & Next Steps\n"
            "   - Short-Term (1–3 Months)\n"
            "   - Medium-Term (3–6 Months)\n"
            "   - Long-Term (6–12 Months)\n"
            "\n"
            "Ensure each subheading is addressed. Where relevant, mention color-coded maturity model assessments "
            "(🟢, 🟡, 🔴) and data gap identification."
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 2) Market Opportunity & Competitive Landscape
# ---------------------------------------------------------------
class MarketAnalysisAgent(BaseAIAgent):
    """
    AI Agent for Section 2: Market Opportunity & Competitive Landscape
    Subheadings:
      - Market Overview
      - Market Size & Growth Projections
      - Competitive Positioning
      - Competitive Landscape
      - Key Market Takeaways
      - Challenges & Expansion Opportunities
        * Challenges
        * Opportunities for Market Expansion
      - Market Fit Assessment
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting Section 2: Market Opportunity & Competitive Landscape.\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n"
            "\n"
            "Please use these subheadings:\n"
            "1) Market Overview\n"
            "2) Market Size & Growth Projections\n"
            "3) Competitive Positioning\n"
            "4) Competitive Landscape\n"
            "5) Key Market Takeaways\n"
            "6) Challenges & Expansion Opportunities\n"
            "   - Challenges\n"
            "   - Opportunities for Market Expansion\n"
            "7) Market Fit Assessment\n"
            "\n"
            "Include color-coded maturity model references and highlight data gaps where applicable."
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 3) Financial Performance & Investment Readiness
# ---------------------------------------------------------------
class FinancialPerformanceAgent(BaseAIAgent):
    """
    AI Agent for Section 3: Financial Performance & Investment Readiness
    Subheadings:
      - Revenue Growth & Profitability Overview
      - Investment Raised & Fund Utilization
      - Revenue Streams & Financial Risk Analysis
      - Key Financial Risks & Considerations
      - Financial Risk Assessment
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting Section 3: Financial Performance & Investment Readiness.\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n"
            "\n"
            "Please structure your response with these subheadings:\n"
            "1) Revenue Growth & Profitability Overview\n"
            "2) Investment Raised & Fund Utilization\n"
            "3) Revenue Streams & Financial Risk Analysis\n"
            "4) Key Financial Risks & Considerations\n"
            "5) Financial Risk Assessment\n"
            "\n"
            "Use color-coded maturity model assessments (🟢, 🟡, 🔴) and highlight any missing data or gaps."
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 4) Go-To-Market (GTM) Strategy & Customer Traction
# ---------------------------------------------------------------
class GoToMarketAgent(BaseAIAgent):
    """
    AI Agent for Section 4: Go-To-Market (GTM) Strategy & Customer Traction
    Subheadings:
      - Customer Acquisition Strategy
      - Customer Retention & Lifetime Value
      - Challenges & Market Expansion Plan
      - Market Expansion Strategy
      - GTM Performance Assessment
    """
    def __init__(self):
        prompt_template = (
            "You are an expert in drafting Section 4: Go-To-Market (GTM) Strategy & Customer Traction.\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n"
            "\n"
            "Use these subheadings:\n"
            "1) Customer Acquisition Strategy\n"
            "2) Customer Retention & Lifetime Value\n"
            "3) Challenges & Market Expansion Plan\n"
            "4) Market Expansion Strategy\n"
            "5) GTM Performance Assessment\n"
            "\n"
            "Include color-coded maturity model references (🟢, 🟡, 🔴) and highlight data gaps or missing data."
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 5) Leadership & Team
# ---------------------------------------------------------------
class LeadershipTeamAgent(BaseAIAgent):
    """
    AI Agent for Section 5: Leadership & Team
    Subheadings:
      - Leadership Expertise & Strategic Decision-Making
      - Organizational Structure & Growth Plan
      - Strategic Hiring Roadmap
      - Leadership Stability & Investor Confidence
      - Leadership & Organizational Stability Assessment
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting Section 5: Leadership & Team.\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n"
            "\n"
            "Subheadings:\n"
            "1) Leadership Expertise & Strategic Decision-Making\n"
            "2) Organizational Structure & Growth Plan\n"
            "3) Strategic Hiring Roadmap\n"
            "4) Leadership Stability & Investor Confidence\n"
            "5) Leadership & Organizational Stability Assessment\n"
            "\n"
            "Where relevant, include color-coded maturity model references (🟢, 🟡, 🔴) and highlight data gaps."
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 6) Investor Fit, Exit Strategy & Funding Narrative
# ---------------------------------------------------------------
class InvestorFitAgent(BaseAIAgent):
    """
    AI Agent for Section 6: Investor Fit, Exit Strategy & Funding Narrative
    Subheadings:
      - Investor Profile & Strategic Alignment
      - Exit Strategy Analysis
      - Current Funding Narrative & Investor Messaging
      - Investor Messaging & Priorities
      - Investor Fit Assessment
    """
    def __init__(self):
        prompt_template = (
            "You are an expert in drafting Section 6: Investor Fit, Exit Strategy & Funding Narrative.\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n"
            "\n"
            "Subheadings:\n"
            "1) Investor Profile & Strategic Alignment\n"
            "2) Exit Strategy Analysis\n"
            "3) Current Funding Narrative & Investor Messaging\n"
            "4) Investor Messaging & Priorities\n"
            "5) Investor Fit Assessment\n"
            "\n"
            "Use color-coded maturity model references (🟢, 🟡, 🔴) and highlight data gaps where relevant."
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 7) Final Recommendations & Next Steps
# ---------------------------------------------------------------
class RecommendationsAgent(BaseAIAgent):
    """
    AI Agent for Section 7: Final Recommendations & Next Steps
    Subheadings:
      - Key Strengths Supporting Investment Consideration
      - Key Investment Risks & Mitigation Strategies
      - Prioritized Action Plan for Investment Readiness
      - Strategic Roadmap for Growth & Exit Planning
      - Investment Readiness & Market Positioning
      - Final Investment Recommendation
      - Next Steps for Investment Consideration
      - Final Conclusion
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting Section 7: Final Recommendations & Next Steps.\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n"
            "\n"
            "Subheadings:\n"
            "1) Key Strengths Supporting Investment Consideration\n"
            "2) Key Investment Risks & Mitigation Strategies\n"
            "3) Prioritized Action Plan for Investment Readiness\n"
            "4) Strategic Roadmap for Growth & Exit Planning\n"
            "5) Investment Readiness & Market Positioning\n"
            "6) Final Investment Recommendation\n"
            "7) Next Steps for Investment Consideration\n"
            "8) Final Conclusion\n"
            "\n"
            "Please provide maturity model references (🟢, 🟡, 🔴) and highlight any data gaps as needed."
        )
        super().__init__(prompt_template)
