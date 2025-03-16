import os
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

    def gather_research(self, context: Dict[str, Any]) -> str:
        """
        Calls the GPT API to gather data based on the prompt template.
        Returns text that can be used as context for other agents.
        """
        prompt = self.prompt_template.format(**context)
        logger.info("Gathering research with prompt:\n%s", prompt)

        # Retrieve model name from environment or default to "gpt-4"
        model_name = os.getenv("OPENAI_MODEL", "gpt-4")

        try:
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a specialized research agent focused on gathering factual details, "
                            "identifying missing data, and providing an objective overview of the company's "
                            "market position, traction, financial health, and other relevant insights."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
            )
            content = response["choices"][0]["message"]["content"].strip()
            logger.info("Research completed successfully using model: %s", model_name)
            return content
        except Exception as e:
            logger.error("Error gathering research: %s", str(e), exc_info=True)
            raise e

    def generate_section(self, context: Dict[str, Any]) -> str:
        """
        Generates a report section using the provided context.

        The method dynamically formats the prompt template with the given context,
        ensuring that details like industry, company name, key metrics, etc.,
        tailor the output. Then it calls the GPT API (default "gpt-4") to generate the section.

        If you want to reference a custom fine-tuned model (e.g. "ft:gpt-3.5-turbo-1234abc"),
        just set the environment variable OPENAI_MODEL to that string.
        """
        # Dynamically generate the prompt based on input context
        prompt = self.prompt_template.format(**context)
        logger.info("Generating section with prompt:\n%s", prompt)

        # Retrieve model name from environment or default to "gpt-4"
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        try:
            response = openai.ChatCompletion.create(
                model=model_name,
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
            logger.info("Section generated successfully using model: %s", model_name)
            return content
        except Exception as e:
            logger.error("Error generating section: %s", str(e), exc_info=True)
            raise e


class ResearcherAgent(BaseAIAgent):
    """
    A single agent that consolidates essential research prompts
    to gather high-level data about a company. The output is meant
    to be used as context for subsequent section-generation agents.
    
    This agent is company-agnostic and focuses on collecting 
    relevant details, key metrics, and identifying data gaps.
    """
    def __init__(self):
        # Consolidated prompt template—no specific section headings or color codes.
        prompt_template = (
            "You are tasked with researching the following company and gathering "
            "relevant information, focusing on clarity and data completeness. "
            "Please address each category below and note any missing or unclear details.\n\n"

            "Company Name: {company_name}\n"
            "Industry or Sector: {industry}\n"
            "Additional Context Provided:\n"
            "{retrieved_context}\n\n"

            "Research Objectives:\n"
            "1) Market & Industry Overview:\n"
            "   - Identify the company's market focus, key segments, and major industry trends.\n"
            "   - Pinpoint known competitors and where this company stands relative to them.\n"
            "   - Highlight any known pain points the company aims to solve and how they differ from existing solutions.\n"
            "   - Note missing or unclear market details.\n\n"

            "2) Customer Traction & Revenue:\n"
            "   - Summarize any publicly known traction (customer base, notable partnerships, revenue streams, or growth metrics).\n"
            "   - Identify any major revenue drivers or channels.\n"
            "   - Note missing data about customer satisfaction, sales metrics, or revenue reporting.\n\n"

            "3) Financial & Growth Indicators:\n"
            "   - Gather any available funding details (rounds, investors, total raised, valuation) and overall financial stability.\n"
            "   - Note key revenue trends or profitability metrics if disclosed.\n"
            "   - Identify gaps in financial data that impede a full assessment.\n\n"

            "4) Go-To-Market & Competitive Position:\n"
            "   - Outline the company's approach to acquiring and retaining customers.\n"
            "   - Highlight any noteworthy GTM strategies or channels.\n"
            "   - Compare or contrast with competitor approaches if possible.\n"
            "   - Note missing data on GTM effectiveness.\n\n"

            "5) Leadership & Team:\n"
            "   - Summarize the leadership team's background or expertise if available.\n"
            "   - Indicate known team size, skill sets, or hiring trends.\n"
            "   - Identify any leadership gaps or unclear organizational details.\n\n"

            "6) Investor Alignment & Risks:\n"
            "   - Describe how the company aligns (or not) with typical investor interests (e.g., growth potential, market fit).\n"
            "   - Note any major risks or red flags (e.g., data gaps, unproven market, regulatory concerns).\n\n"

            "7) Recommendations or Next Steps (High-Level):\n"
            "   - Based on the data gathered, suggest areas needing further validation or deeper diligence.\n"
            "   - Highlight the most significant missing elements that should be clarified.\n\n"

            "Instructions:\n"
            "• Provide factual details wherever possible.\n"
            "• Note clearly if certain data points (e.g., revenue, churn, or competitor analyses) are not publicly available.\n"
            "• Avoid drafting a final report narrative. Instead, focus on presenting raw research findings and data gaps.\n"
            "• Your output will be used as context in a later step.\n"
        )
        super().__init__(prompt_template)

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

    Now produces Markdown matching the desired layout:
    
    ### **Section 2: Market Opportunity & Competitive Landscape** {#section-2:-market-opportunity-&-competitive-landscape}

    #### Market Overview {#market-overview}

    #### Market Size & Growth Projections: {#market-size-&-growth-projections:}
    - ...
    - ...
    - ...

    #### Competitive Positioning {#competitive-positioning}

    ##### Competitive Landscape {#competitive-landscape}
    | Competitor | Market Focus | Key Strengths | Challenges |
    | ----- | ----- | ----- | ----- |
    |  |  |  |  |

    #### Key Market Takeaways: {#key-market-takeaways:}
    - ...

    ##### Challenges & Expansion Opportunities {#challenges-&-expansion-opportunities}
    ###### Challenges: {#challenges:}
    - ...
    ###### Opportunities for Market Expansion: {#opportunities-for-market-expansion:}
    ✅ ...
    ✅ ...
    ✅ ...

    #### Market Fit Assessment {#market-fit-assessment}
    | Market Factor | Assessment |
    | ----- | ----- |
    |  | 🟢 Strong |
    |  | 🟡 Needs Expansion |
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting **Section 2: Market Opportunity & Competitive Landscape** "
            "in Markdown format. Use **the exact headings, subheadings, and anchor links** provided below. "
            "Incorporate relevant details from 'retrieved_context' (e.g., industry trends, competition, "
            "market size) and mention color-coded assessments (🟢, 🟡, 🔴) where fitting.\n\n"

            "Company: {company}\n"
            "Industry: {industry}\n"
            "\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "## Your Task\n"
            "Generate **Section 2** in the following markdown structure:\n\n"
            "### **Section 2: Market Opportunity & Competitive Landscape** {#section-2:-market-opportunity-&-competitive-landscape}\n\n"
            "#### Market Overview {#market-overview}\n"
            "Provide a high-level description of the market in which this company operates. "
            "Include any known segments, growth drivers, or major trends.\n\n"
            "#### Market Size & Growth Projections: {#market-size-&-growth-projections:}\n"
            "- **Total Addressable Market (TAM):** If available\n"
            "- **Annual Growth Rate:** If known\n"
            "- **Adoption Trends:** (technical, demographic, etc.)\n\n"
            "#### Competitive Positioning {#competitive-positioning}\n"
            "Explain the company’s core advantages or differentiators vs. competitors.\n\n"
            "##### Competitive Landscape {#competitive-landscape}\n"
            "| Competitor | Market Focus | Key Strengths | Challenges |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "|  |  |  |  |\n"
            "|  |  |  |  |\n"
            "|  |  |  |  |\n\n"
            "#### Key Market Takeaways: {#key-market-takeaways:}\n"
            "- Provide bullet points on the most important insights.\n\n"
            "##### Challenges & Expansion Opportunities {#challenges-&-expansion-opportunities}\n"
            "###### Challenges: {#challenges:}\n"
            "- List any known market barriers, competitor threats, or data gaps.\n\n"
            "###### Opportunities for Market Expansion: {#opportunities-for-market-expansion:}\n"
            "✅ Outline potential growth channels, new segments, or partnerships.\n"
            "✅ Provide quick bullet points or short paragraphs.\n\n"
            "#### Market Fit Assessment {#market-fit-assessment}\n"
            "| Market Factor | Assessment |\n"
            "| ----- | ----- |\n"
            "|  | 🟢 Strong |\n"
            "|  | 🟡 Needs Expansion |\n\n"
            "### Instructions\n"
            "1. Write your final answer in valid **Markdown**.\n"
            "2. For any unknown or missing data, you may use placeholders or note the gap.\n"
            "3. Use color-coded references (🟢, 🟡, 🔴) if needed.\n"
            "4. Maintain the headings, subheadings, and anchor tags exactly as shown.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 3) Financial Performance & Investment Readiness
# ---------------------------------------------------------------
class FinancialPerformanceAgent(BaseAIAgent):
    """
    AI Agent for Section 3: Financial Performance & Investment Readiness
    Subheadings (from your Python docstring):
      1) Revenue Growth & Profitability Overview
      2) Investment Raised & Fund Utilization
      3) Revenue Streams & Financial Risk Analysis
      4) Key Financial Risks & Considerations
      5) Financial Risk Assessment

    The desired Markdown template includes:
      ### **Section 3: Financial Performance & Investment Readiness** {#section-3:-financial-performance-&-investment-readiness}

      #### **Revenue Growth & Profitability Overview** {#revenue-growth-&-profitability-overview}
      | Metric | Founder Company Performance | Industry Benchmark |
      | ----- | ----- | ----- |
      |  |  |  |
      |  |  |  |

      #### **Investment Raised & Fund Utilization** {#investment-raised-&-fund-utilization}
      | Funding Stage | Founder Company Status | Industry Benchmark |
      | ----- | ----- | ----- |
      | **Pre-Seed → Seed** |  |  |
      | **Total Funding Raised** |  |  |
      | **Planned Raise** |  |  |
      | **Valuation Transparency** |  |  |

      **Investor Concerns:**  
      ⚠  
      ⚠  
      ⚠  

      #### **Revenue Streams & Financial Risk Analysis** {#revenue-streams-&-financial-risk-analysis}
      | Revenue Source | Contribution | Risk Factor |
      | ----- | ----- | ----- |
      | **SaaS Subscriptions** |  |  |
      | **Other Streams** |  |  |

      #### **Key Financial Risks & Considerations** {#key-financial-risks-&-considerations}
      - bullet points

      #### **Financial Risk Assessment** {#financial-risk-assessment}
      | Risk Factor | Assessment |
      | ----- | ----- |
      | **Revenue Concentration Risk** | 🟡 Moderate |
      | **Funding Transparency** | 🟡 Needs Improvement |
      | **Burn Rate & Cash Flow Stability** | 🟡 Requires Validation |
      | **Profitability & Sustainability** | 🟡 Long-Term Risk |
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting **Section 3: Financial Performance & Investment Readiness** "
            "in Markdown format. Use **the exact headings, subheadings, and anchor links** below. "
            "Incorporate any relevant details from the 'retrieved_context' and apply color-coded references (🟢, 🟡, 🔴) where needed.\n\n"

            "Company: {company}\n"
            "Industry: {industry}\n\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "## Your Task\n"
            "Generate **Section 3** in the following markdown structure:\n\n"
            "### **Section 3: Financial Performance & Investment Readiness** {#section-3:-financial-performance-&-investment-readiness}\n\n"
            "#### **Revenue Growth & Profitability Overview** {#revenue-growth-&-profitability-overview}\n"
            "Provide a brief summary and this table:\n\n"
            "| Metric | Founder Company Performance | Industry Benchmark |\n"
            "| ----- | ----- | ----- |\n"
            "|  |  |  |\n"
            "|  |  |  |\n"
            "|  |  |  |\n\n"
            "Add any bullet points if helpful.\n\n"
            "#### **Investment Raised & Fund Utilization** {#investment-raised-&-fund-utilization}\n"
            "Include a table:\n\n"
            "| Funding Stage | Founder Company Status | Industry Benchmark |\n"
            "| ----- | ----- | ----- |\n"
            "| **Pre-Seed → Seed** |  |  |\n"
            "| **Total Funding Raised** |  |  |\n"
            "| **Planned Raise** |  |  |\n"
            "| **Valuation Transparency** |  |  |\n\n"
            "**Investor Concerns:**\n"
            "⚠ (list 2-3 concerns if known)\n\n"
            "#### **Revenue Streams & Financial Risk Analysis** {#revenue-streams-&-financial-risk-analysis}\n"
            "Here is a sample table:\n\n"
            "| Revenue Source | Contribution | Risk Factor |\n"
            "| ----- | ----- | ----- |\n"
            "| **SaaS Subscriptions** |  |  |\n"
            "| **Other Streams** |  |  |\n\n"
            "You can add bullet points or insights.\n\n"
            "#### **Key Financial Risks & Considerations** {#key-financial-risks-&-considerations}\n"
            "- Provide bullet points on major financial risks.\n\n"
            "#### **Financial Risk Assessment** {#financial-risk-assessment}\n"
            "Here is a table to show maturity model or color-coded assessments:\n\n"
            "| Risk Factor | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Revenue Concentration Risk** | 🟡 Moderate |\n"
            "| **Funding Transparency** | 🟡 Needs Improvement |\n"
            "| **Burn Rate & Cash Flow Stability** | 🟡 Requires Validation |\n"
            "| **Profitability & Sustainability** | 🟡 Long-Term Risk |\n\n"
            "### Instructions\n"
            "1. Write your final answer in valid **Markdown**.\n"
            "2. For unknown data, you may use placeholders or note missing info.\n"
            "3. Maintain the headings, subheadings, and anchor tags exactly as shown.\n"
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
