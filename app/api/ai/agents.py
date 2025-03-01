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
        
        Args:
            context (Dict[str, Any]): A dictionary containing values for prompt placeholders.
        
        Returns:
            str: The generated report section, as text.
        
        Raises:
            Exception: Propagates any errors from the API call.
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


class ExecutiveSummaryAgent(BaseAIAgent):
    """
    AI Agent for generating the Executive Summary & Investment Rationale section.
    Covers: Overview, Key Investment Considerations, Investment Readiness Overview,
    Investment Risks & Considerations, plus short-, medium-, and long-term recommendations.
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting an Executive Summary for a GFV Investment Readiness Report.\n\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "\n"
            "Please structure your response with these sub-sections:\n"
            "1) Overview\n"
            "2) Key Investment Considerations\n"
            "3) Investment Readiness Overview\n"
            "4) Investment Risks & Considerations\n"
            "5) Investment Recommendations & Next Steps:\n"
            "   - Short-Term (1–3 Months)\n"
            "   - Medium-Term (3–6 Months)\n"
            "   - Long-Term (6–12 Months)\n"
            "\n"
            "Include relevant insights from the following context:\n"
            "Key Findings: {key_findings}\n"
            "Additional Notes: {notes}\n"
        )
        super().__init__(prompt_template)


class MarketAnalysisAgent(BaseAIAgent):
    """
    AI Agent for generating the Market Opportunity & Competitive Landscape section.
    Covers: Market Overview, Market Size & Growth Projections, Competitive Positioning,
    Competitive Landscape, Key Market Takeaways, Challenges & Expansion Opportunities,
    Market Fit Assessment.
    """
    def __init__(self):
        prompt_template = (
            "You are an expert in Market Analysis for a GFV Investment Readiness Report.\n\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "\n"
            "Please structure your response with these sub-sections:\n"
            "1) Market Overview\n"
            "2) Market Size & Growth Projections\n"
            "3) Competitive Positioning\n"
            "4) Competitive Landscape\n"
            "5) Key Market Takeaways\n"
            "6) Challenges & Expansion Opportunities\n"
            "7) Market Fit Assessment\n"
            "\n"
            "Use the following context:\n"
            "Market Trends: {market_trends}\n"
            "Competitors: {competitors}\n"
            "Any Other Relevant Info: {other_market_info}\n"
        )
        super().__init__(prompt_template)


class FinancialsAgent(BaseAIAgent):
    """
    AI Agent for generating the Financial Performance & Investment Readiness section.
    Covers: Revenue Growth & Profitability Overview, Investment Raised & Fund Utilization,
    Revenue Streams & Financial Risk Analysis, Key Financial Risks & Considerations,
    Financial Risk Assessment.
    """
    def __init__(self):
        prompt_template = (
            "You are an expert in Financial Performance & Investment Readiness analysis.\n\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "\n"
            "Please structure your response with these sub-sections:\n"
            "1) Revenue Growth & Profitability Overview\n"
            "2) Investment Raised & Fund Utilization\n"
            "3) Revenue Streams & Financial Risk Analysis\n"
            "4) Key Financial Risks & Considerations\n"
            "5) Financial Risk Assessment\n"
            "\n"
            "Use the following context for data:\n"
            "Revenue Growth Data: {revenue_growth}\n"
            "Current Profitability: {profitability}\n"
            "Investment Raised: {investment_raised}\n"
            "Fund Utilization Plans: {fund_utilization}\n"
            "Financial Risks: {financial_risks}\n"
            "Additional Financial Context: {financial_context}\n"
        )
        super().__init__(prompt_template)


class GTMStrategyAgent(BaseAIAgent):
    """
    AI Agent for generating the Go-To-Market (GTM) Strategy & Customer Traction section.
    Covers: Customer Acquisition Strategy, Customer Retention & LTV, Challenges & Market Expansion,
    Market Expansion Strategy, GTM Performance Assessment.
    """
    def __init__(self):
        prompt_template = (
            "You are an expert in Go-To-Market (GTM) strategy and customer traction analysis.\n\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "\n"
            "Please structure your response with these sub-sections:\n"
            "1) Customer Acquisition Strategy\n"
            "2) Customer Retention & Lifetime Value\n"
            "3) Challenges & Market Expansion Plan\n"
            "4) Market Expansion Strategy\n"
            "5) GTM Performance Assessment\n"
            "\n"
            "Relevant Context:\n"
            "Current Acquisition Tactics: {acquisition_strategies}\n"
            "Customer Retention Data: {retention_data}\n"
            "Growth Barriers or Challenges: {growth_challenges}\n"
            "Market Expansion Opportunities: {expansion_opportunities}\n"
        )
        super().__init__(prompt_template)


class LeadershipAgent(BaseAIAgent):
    """
    AI Agent for generating the Leadership & Team section.
    Covers: Leadership Expertise & Strategic Decision-Making, Organizational Structure & Growth Plan,
    Strategic Hiring Roadmap, Leadership Stability & Investor Confidence,
    Leadership & Organizational Stability Assessment.
    """
    def __init__(self):
        prompt_template = (
            "You are an expert in assessing Leadership & Team dynamics for a GFV Investment Readiness Report.\n\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "\n"
            "Please structure your response with these sub-sections:\n"
            "1) Leadership Expertise & Strategic Decision-Making\n"
            "2) Organizational Structure & Growth Plan\n"
            "3) Strategic Hiring Roadmap\n"
            "4) Leadership Stability & Investor Confidence\n"
            "5) Leadership & Organizational Stability Assessment\n"
            "\n"
            "Additional Context:\n"
            "Leadership Team Background: {leadership_background}\n"
            "Org Structure Details: {organization_structure}\n"
            "Key Hiring Needs: {hiring_needs}\n"
            "Stability / Succession Plans: {leadership_stability}\n"
        )
        super().__init__(prompt_template)


class InvestorFitAgent(BaseAIAgent):
    """
    AI Agent for generating the Investor Fit, Exit Strategy & Funding Narrative section.
    Covers: Investor Profile & Strategic Alignment, Exit Strategy Analysis,
    Current Funding Narrative & Investor Messaging, Investor Messaging & Priorities,
    Investor Fit Assessment.
    """
    def __init__(self):
        prompt_template = (
            "You are an expert in evaluating Investor Fit, Exit Strategy & Funding Narratives.\n\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "\n"
            "Please structure your response with these sub-sections:\n"
            "1) Investor Profile & Strategic Alignment\n"
            "2) Exit Strategy Analysis\n"
            "3) Current Funding Narrative & Investor Messaging\n"
            "4) Investor Messaging & Priorities\n"
            "5) Investor Fit Assessment\n"
            "\n"
            "Relevant Context:\n"
            "Funding History: {funding_history}\n"
            "Target Investor Profile: {target_investors}\n"
            "Proposed Exit Strategies: {exit_strategies}\n"
        )
        super().__init__(prompt_template)


class FinalRecommendationsAgent(BaseAIAgent):
    """
    AI Agent for generating the Final Recommendations & Next Steps section.
    Covers: Key Strengths Supporting Investment, Key Investment Risks & Mitigation,
    Prioritized Action Plan, Strategic Roadmap for Growth & Exit, 
    Investment Readiness & Market Positioning, Final Recommendation, Next Steps, Conclusion.
    """
    def __init__(self):
        prompt_template = (
            "You are an expert in formulating final investment recommendations and next steps "
            "for a GFV Investment Readiness Report.\n\n"
            "Company: {company}\n"
            "Industry: {industry}\n"
            "\n"
            "Please structure your response with these sub-sections:\n"
            "1) Key Strengths Supporting Investment Consideration\n"
            "2) Key Investment Risks & Mitigation Strategies\n"
            "3) Prioritized Action Plan for Investment Readiness\n"
            "4) Strategic Roadmap for Growth & Exit Planning\n"
            "5) Investment Readiness & Market Positioning\n"
            "6) Final Investment Recommendation\n"
            "7) Next Steps for Investment Consideration\n"
            "8) Final Conclusion\n"
            "\n"
            "Use the following context:\n"
            "High-Level Strengths: {key_strengths}\n"
            "Major Risks: {key_risks}\n"
            "Action Plan Details: {action_plan}\n"
            "Growth & Exit Strategies: {growth_and_exit}\n"
            "Overall Positioning: {positioning}\n"
        )
        super().__init__(prompt_template)
