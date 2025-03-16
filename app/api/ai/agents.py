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
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

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
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

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

            "Company Name: {{company_name}}\n"
            "Industry or Sector: {{industry}}\n"
            "Additional Context Provided:\n"
            "{{retrieved_context}}\n\n"

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
    
    Now produces markdown aligned with the desired layout:
    
    ### **Section 1: Executive Summary & Investment Rationale** {#section-1:-executive-summary-&-investment-rationale}

    #### Overview {#overview}
    ...
    #### Key Investment Considerations {#key-investment-considerations}
    ...
    #### Investment Readiness Overview {#investment-readiness-overview}
    ...
    #### Investment Risks & Considerations {#investment-risks-&-considerations}
    ...
    #### Investment Recommendations & Next Steps {#investment-recommendations-&-next-steps}
    ...
    ##### Short-Term (1-3 Months): {#short-term-(1-3-months):}
    ...
    ##### Medium-Term (3-6 Months): {#medium-term-(3-6-months):}
    ...
    ##### Long-Term (6-12 Months): {#long-term-(6-12-months):}
    ...
    """
    def __init__(self):
        # This prompt instructs GPT to produce the Markdown structure matching your sample
        prompt_template = (
            "You are an expert at drafting the **Executive Summary & Investment Rationale** section "
            "of an investment readiness report in Markdown format. Use **the exact headings, subheadings, "
            "and anchor links** provided below. Where relevant, include color-coded maturity assessments "
            "(🟢, 🟡, 🔴) and incorporate any details from the 'retrieved_context'.\n\n"

            "The company details are:\n"
            "- Founder Name: {{founder_name}}\n"
            "- Company Name: {{company}}\n"
            "- Company Type: {{company_type}}\n"
            "- Company Provides: {{company_description}}\n\n"

            "Retrieved Context (Docs, Pitch Deck, or Research Output):\n"
            "{{retrieved_context}}\n\n"

            "## Your Task\n"
            "Generate **Section 1** in the following markdown structure:\n\n"
            "### **Section 1: Executive Summary & Investment Rationale** {#section-1:-executive-summary-&-investment-rationale}\n\n"
            "#### Overview {#overview}\n"
            "1. Briefly describe the company (name, type, what it provides).\n"
            "2. Mention relevant revenue growth, customer traction, or market potential details.\n"
            "3. Indicate the scope of this assessment (finances, leadership, market fit, etc.).\n\n"
            "#### Key Investment Considerations {#key-investment-considerations}\n"
            "- Add bullet points for top considerations (e.g., scalability, revenue strength, differentiation, data gaps, etc.).\n\n"
            "#### Investment Readiness Overview {#investment-readiness-overview}\n"
            "Create a table showing relevant investment categories and an assessment (🟢, 🟡, or 🔴). For example:\n\n"
            "| Investment Category | Assessment |\n"
            "| :---- | :---- |\n"
            "| Market Traction | 🟢 Strong |\n"
            "| Revenue Growth Potential | 🟢 Strong |\n"
            "| Financial Transparency | 🟡 Needs Refinement |\n"
            "| Operational Scalability | 🟡 Needs Improvement |\n"
            "| Leadership Depth | 🟡 Moderate Risk |\n"
            "| Exit Potential | 🟢 Favorable Pathways |\n\n"
            "#### Investment Risks & Considerations {#investment-risks-&-considerations}\n"
            "- Provide a bullet list of risks or concerns (financial, operational, market-based, etc.).\n\n"
            "#### Investment Recommendations & Next Steps {#investment-recommendations-&-next-steps}\n"
            "- Provide general recommendations, then break them down by timeframe.\n\n"
            "##### Short-Term (1-3 Months): {#short-term-(1-3-months):}\n"
            "- List short-term action items.\n\n"
            "##### Medium-Term (3-6 Months): {#medium-term-(3-6-months):}\n"
            "- List medium-term action items.\n\n"
            "##### Long-Term (6-12 Months): {#long-term-(6-12-months):}\n"
            "- List long-term action items.\n\n"
            "### Instructions\n"
            "1. Write your final answer in valid **Markdown**.\n"
            "2. Fill placeholders with relevant data from the context.\n"
            "3. For any unknown or missing data, you may use placeholders or mark it as an area needing more info.\n"
            "4. Maintain the headings, subheadings, and anchor tags exactly as shown.\n"
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

            "Company: {{company}}\n"
            "Industry: {{industry}}\n"
            "\n"
            "Retrieved Context:\n"
            "{{retrieved_context}}\n\n"

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

            "Company: {{company}}\n"
            "Industry: {{industry}}\n\n"
            "Retrieved Context:\n"
            "{{retrieved_context}}\n\n"

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

    Desired Markdown Template:

    ### **Section 4: Go-To-Market (GTM) Strategy & Customer Traction** {#section-4:-go-to-market-(gtm)-strategy-&-customer-traction}

    #### **Customer Acquisition Strategy** {#customer-acquisition-strategy}
    - Potential bullet points, table of channels, etc.

    | Acquisition Channel | Performance | Challenges |
    | ----- | ----- | ----- |
    |  |  |  |
    |  |  |  |

    ✅ **Strengths:**
    ⚠ **Challenges:**

    #### **Customer Retention & Lifetime Value** {#customer-retention-&-lifetime-value}
    (Table example)

    | Retention Metric | Founder Company Performance | Industry Benchmark |
    | ----- | ----- | ----- |
    | **Customer Retention Rate** |  |  |
    | **Churn Rate** |  |  |
    | **Referral-Based Growth** |  |  |

    ✅ **Strengths:**
    ⚠ **Challenges:**

    #### **Challenges & Market Expansion Plan** {#challenges-&-market-expansion-plan}
    ⚠ **Customer Acquisition Cost (CAC) Optimization Needed**

    - **Challenge:** ...
    - **Solution:** ...

    ⚠ **Revenue Concentration Risk**

    - **Challenge:** ...
    - **Solution:** ...

    #### **Market Expansion Strategy** {#market-expansion-strategy}
    ✅ **Franchise Pilot Growth** –
    ✅ **Supplier Network Growth** –
    ✅ **AI-Driven Enhancements** –

    #### **GTM Performance Assessment** {#gtm-performance-assessment}
    | Category | Performance | Assessment |
    | ----- | ----- | ----- |
    | **Lead Generation Efficiency** |  |  |
    | **Customer Retention** |  |  |
    | **Revenue Growth** |  |  |
    | **Outbound Sales Effectiveness** |  |  |
    | **Market Diversification** |  |  |
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting **Section 4: Go-To-Market (GTM) Strategy & Customer Traction** "
            "in Markdown format. Please use **the exact headings, subheadings, anchor links, and tables** "
            "outlined below, incorporating relevant information from 'retrieved_context' and applying "
            "color-coded references (🟢, 🟡, 🔴) where appropriate.\n\n"

            "Company: {{company}}\n"
            "Industry: {{industry}}\n\n"
            "Retrieved Context:\n"
            "{{{retrieved_context}}}\n\n"

            "## Your Task\n"
            "Generate **Section 4** in the following markdown structure:\n\n"
            "### **Section 4: Go-To-Market (GTM) Strategy & Customer Traction** {#section-4:-go-to-market-(gtm)-strategy-&-customer-traction}\n\n"
            "#### **Customer Acquisition Strategy** {#customer-acquisition-strategy}\n"
            "Discuss acquisition channels, lead generation tactics, etc.\n\n"
            "| Acquisition Channel | Performance | Challenges |\n"
            "| ----- | ----- | ----- |\n"
            "|  |  |  |\n"
            "|  |  |  |\n\n"
            "✅ **Strengths:**\n"
            "⚠ **Challenges:**\n\n"
            "#### **Customer Retention & Lifetime Value** {#customer-retention-&-lifetime-value}\n"
            "Provide a brief overview, then this table:\n\n"
            "| Retention Metric | Founder Company Performance | Industry Benchmark |\n"
            "| ----- | ----- | ----- |\n"
            "| **Customer Retention Rate** |  |  |\n"
            "| **Churn Rate** |  |  |\n"
            "| **Referral-Based Growth** |  |  |\n\n"
            "✅ **Strengths:**\n"
            "⚠ **Challenges:**\n\n"
            "#### **Challenges & Market Expansion Plan** {#challenges-&-market-expansion-plan}\n"
            "Include sub-bullets for specific challenges & solutions. For example:\n\n"
            "⚠ **Customer Acquisition Cost (CAC) Optimization Needed**\n"
            "* **Challenge:**\n"
            "* **Solution:**\n\n"
            "⚠ **Revenue Concentration Risk**\n"
            "* **Challenge:**\n"
            "* **Solution:**\n\n"
            "#### **Market Expansion Strategy** {#market-expansion-strategy}\n"
            "List or bullet examples (e.g., 'Franchise Pilot Growth', 'Supplier Network Growth', etc.)\n\n"
            "#### **GTM Performance Assessment** {#gtm-performance-assessment}\n"
            "Use this table:\n\n"
            "| Category | Performance | Assessment |\n"
            "| ----- | ----- | ----- |\n"
            "| **Lead Generation Efficiency** |  |  |\n"
            "| **Customer Retention** |  |  |\n"
            "| **Revenue Growth** |  |  |\n"
            "| **Outbound Sales Effectiveness** |  |  |\n"
            "| **Market Diversification** |  |  |\n\n"
            "### Instructions\n"
            "1. Write your final answer in valid **Markdown**.\n"
            "2. For unknown data, you may use placeholders or note missing info.\n"
            "3. Maintain the headings, subheadings, and anchor tags exactly as shown.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 5) Leadership & Team
# ---------------------------------------------------------------
class LeadershipTeamAgent(BaseAIAgent):
    """
    AI Agent for Section 5: Leadership & Team

    Desired Markdown structure:
    ### **Section 5: Leadership & Team** {#section-5:-leadership-&-team}

    #### **Leadership Expertise & Strategic Decision-Making** {#leadership-expertise-&-strategic-decision-making}
    Leadership Expertise & Strategic Decision-Making

    | Leadership Role | Experience & Contributions | Identified Gaps |
    | ----- | ----- | ----- |
    | **Co-Founder & CEO** |  |  |
    | **Co-Founder & Business Development Lead** |  |  |
    | **Sales & Business Development Team** |  |  |
    | **Engineering & Product Development** |  |  |

    ✅ **Strengths:**  
    ⚠ **Challenges:** 

    #### **Organizational Structure & Growth Plan** {#organizational-structure-&-growth-plan}
    | Functional Area | Current Status | Planned Expansion | Impact on Scalability |
    | ----- | ----- | ----- | ----- |
    | **Product & Engineering** |  |  |  |
    | **Sales & Business Development** |  |  |  |
    | **Customer Success & Support** |  |  |  |

    ✅  
    ⚠ 

    #### **Strategic Hiring Roadmap** {#strategic-hiring-roadmap}
    | Role | Current Status | Planned Hiring Timeline | Impact |
    | ----- | ----- | ----- | ----- |
    | **CTO / Senior Product Leader** |  |  |  |
    | **Outbound Sales & BD Team Expansion** |  |  |  |
    | **Customer Success & Ops Growth** |  |  |  |

    ✅  
    ⚠ 

    #### **Leadership Stability & Investor Confidence** {#leadership-stability-&-investor-confidence}
    * **Investor View:**   
    * **Identified Risks:**   
    * **Mitigation Strategy:** 

    #### **Leadership & Organizational Stability Assessment** {#leadership-&-organizational-stability-assessment}
    | Leadership Category | Assessment |
    | ----- | ----- |
    | **Strategic Vision & Execution** | 🟢 Strong |
    | **Technical Leadership Depth** | 🟡 Needs Improvement |
    | **Sales & Business Development Scalability** | 🟡 Needs Expansion |
    | **Team Stability & Succession Planning** | 🟡 Moderate Risk |
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting **Section 5: Leadership & Team** in Markdown format. "
            "Use **the exact headings, subheadings, anchor links, and tables** provided below, "
            "incorporating details from 'retrieved_context' and mentioning color-coded references (🟢, 🟡, 🔴) if relevant.\n\n"

            "Company: {{company}}\n"
            "Industry: {{industry}}\n\n"
            "Retrieved Context:\n"
            "{{retrieved_context}}\n\n"

            "## Your Task\n"
            "Generate **Section 5** in the following markdown structure:\n\n"
            "### **Section 5: Leadership & Team** {#section-5:-leadership-&-team}\n\n"
            "#### **Leadership Expertise & Strategic Decision-Making** {#leadership-expertise-&-strategic-decision-making}\n"
            "Leadership Expertise & Strategic Decision-Making\n\n"
            "| Leadership Role | Experience & Contributions | Identified Gaps |\n"
            "| ----- | ----- | ----- |\n"
            "| **Co-Founder & CEO** |  |  |\n"
            "| **Co-Founder & Business Development Lead** |  |  |\n"
            "| **Sales & Business Development Team** |  |  |\n"
            "| **Engineering & Product Development** |  |  |\n\n"
            "✅ **Strengths:**  \n"
            "⚠ **Challenges:** \n\n"
            "#### **Organizational Structure & Growth Plan** {#organizational-structure-&-growth-plan}\n"
            "| Functional Area | Current Status | Planned Expansion | Impact on Scalability |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **Product & Engineering** |  |  |  |\n"
            "| **Sales & Business Development** |  |  |  |\n"
            "| **Customer Success & Support** |  |  |  |\n\n"
            "✅  \n"
            "⚠ \n\n"
            "#### **Strategic Hiring Roadmap** {#strategic-hiring-roadmap}\n"
            "| Role | Current Status | Planned Hiring Timeline | Impact |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **CTO / Senior Product Leader** |  |  |  |\n"
            "| **Outbound Sales & BD Team Expansion** |  |  |  |\n"
            "| **Customer Success & Ops Growth** |  |  |  |\n\n"
            "✅  \n"
            "⚠ \n\n"
            "#### **Leadership Stability & Investor Confidence** {#leadership-stability-&-investor-confidence}\n"
            "* **Investor View:**   \n"
            "* **Identified Risks:**   \n"
            "* **Mitigation Strategy:** \n\n"
            "#### **Leadership & Organizational Stability Assessment** {#leadership-&-organizational-stability-assessment}\n"
            "| Leadership Category | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Strategic Vision & Execution** | 🟢 Strong |\n"
            "| **Technical Leadership Depth** | 🟡 Needs Improvement |\n"
            "| **Sales & Business Development Scalability** | 🟡 Needs Expansion |\n"
            "| **Team Stability & Succession Planning** | 🟡 Moderate Risk |\n\n"
            "### Instructions\n"
            "1. Write your final answer in valid **Markdown**.\n"
            "2. Use placeholders or note gaps for unknown data.\n"
            "3. Retain the exact headings, subheadings, and anchor tags as shown.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 6) Investor Fit, Exit Strategy & Funding Narrative
# ---------------------------------------------------------------
class InvestorFitAgent(BaseAIAgent):
    """
    AI Agent for Section 6: Investor Fit, Exit Strategy & Funding Narrative

    Desired Markdown structure:
    ### **Section 6: Investor Fit, Exit Strategy & Funding Narrative** {#section-6:-investor-fit,-exit-strategy-&-funding-narrative}

    #### **Investor Profile & Strategic Alignment** {#investor-profile-&-strategic-alignment}
    Founder Company Investor Profile & Strategic Alignment

    **Ideal Investor Profile:**  
    ✅ **Venture Capital (VC) Firms** –  
    ✅ **Private Equity (PE) Funds** –  
    ✅ **Strategic FSM Acquirers** –  

    ⚠ **Investor Concerns:**
    - 

    #### **Exit Strategy Analysis** {#exit-strategy-analysis}
    | Exit Type | Viability | Potential Acquirers / Investors | Challenges |
    | ----- | ----- | ----- | ----- |
    | **M&A by FSM Software Companies** |  |  |  |
    | **Private Equity (PE) Buyout** |  |  |  |
    | **IPO as a Growth-Stage SaaS** |  |  |  |

    ✅ **Most Likely Exit:**  
    ⚠ **IPO Variability**

    #### **Current Funding Narrative & Investor Messaging** {#current-funding-narrative-&-investor-messaging}
    * **Total Funding Raised:**  
    * **Current Round:**  
    * **Valuation Transparency:**  

    | Funding Stage | Founder Company Status | Industry Benchmark |
    | ----- | ----- | ----- |
    | **Pre-Seed → Seed** |  |  |
    | **Total Funding Raised** |  |  |
    | **Planned Raise** |  |  |
    | **Valuation Transparency** |  |  |

    ✅ **Strengths:**  
    ⚠ **Challenges:** 

    #### **Investor Messaging & Priorities** {#investor-messaging-&-priorities}
    * **High-Growth SaaS Opportunity:**  
    * **Defensible Market Positioning:**  
    * **Exit Potential:**  

    #### **Investor Fit Assessment** {#investor-fit-assessment}
    | Investment Factor | Assessment |
    | ----- | ----- |
    | **Scalability & ROI Potential** | 🟢 Strong |
    | **Investor Sentiment & Market Trends** | 🟡 Needs More Public Validation |
    | **Funding & Exit Strategy Clarity** | 🟡 Needs Refinement |
    | **Risk Profile for Investors** | 🟡 Moderate Risk Due to FSM Dependency |
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting **Section 6: Investor Fit, Exit Strategy & Funding Narrative** "
            "in Markdown format. Use **the exact headings, subheadings, anchor links, tables, and bullet points** "
            "as shown in the template below. Incorporate relevant details from 'retrieved_context' and use "
            "color-coded references (🟢, 🟡, 🔴) if needed.\n\n"

            "Company: {{company}}\n"
            "Industry: {{industry}}\n\n"
            "Retrieved Context:\n"
            "{{retrieved_context}}\n\n"

            "## Your Task\n"
            "Generate **Section 6** in the following markdown structure:\n\n"
            "### **Section 6: Investor Fit, Exit Strategy & Funding Narrative** {#section-6:-investor-fit,-exit-strategy-&-funding-narrative}\n\n"
            "#### **Investor Profile & Strategic Alignment** {#investor-profile-&-strategic-alignment}\n"
            "Founder Company Investor Profile & Strategic Alignment\n\n"
            "**Ideal Investor Profile:**  \n"
            "✅ **Venture Capital (VC) Firms** –  \n"
            "✅ **Private Equity (PE) Funds** –  \n"
            "✅ **Strategic FSM Acquirers** –  \n\n"
            "⚠ **Investor Concerns:**\n"
            "- List concerns here.\n\n"
            "#### **Exit Strategy Analysis** {#exit-strategy-analysis}\n"
            "| Exit Type | Viability | Potential Acquirers / Investors | Challenges |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **M&A by FSM Software Companies** |  |  |  |\n"
            "| **Private Equity (PE) Buyout** |  |  |  |\n"
            "| **IPO as a Growth-Stage SaaS** |  |  |  |\n\n"
            "✅ **Most Likely Exit:**  \n"
            "⚠ **IPO Variability**\n\n"
            "#### **Current Funding Narrative & Investor Messaging** {#current-funding-narrative-&-investor-messaging}\n"
            "* **Total Funding Raised:**  \n"
            "* **Current Round:**  \n"
            "* **Valuation Transparency:**  \n\n"
            "| Funding Stage | Founder Company Status | Industry Benchmark |\n"
            "| ----- | ----- | ----- |\n"
            "| **Pre-Seed → Seed** |  |  |\n"
            "| **Total Funding Raised** |  |  |\n"
            "| **Planned Raise** |  |  |\n"
            "| **Valuation Transparency** |  |  |\n\n"
            "✅ **Strengths:**  \n"
            "⚠ **Challenges:** \n\n"
            "#### **Investor Messaging & Priorities** {#investor-messaging-&-priorities}\n"
            "* **High-Growth SaaS Opportunity:**  \n"
            "* **Defensible Market Positioning:**  \n"
            "* **Exit Potential:**  \n\n"
            "#### **Investor Fit Assessment** {#investor-fit-assessment}\n"
            "| Investment Factor | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Scalability & ROI Potential** | 🟢 Strong |\n"
            "| **Investor Sentiment & Market Trends** | 🟡 Needs More Public Validation |\n"
            "| **Funding & Exit Strategy Clarity** | 🟡 Needs Refinement |\n"
            "| **Risk Profile for Investors** | 🟡 Moderate Risk Due to FSM Dependency |\n\n"
            "### Instructions\n"
            "1. Write your final answer in valid **Markdown**.\n"
            "2. Use placeholders or note gaps for missing data.\n"
            "3. Keep the headings, subheadings, anchor tags, and tables exactly as shown.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 7) Final Recommendations & Next Steps
# ---------------------------------------------------------------
class RecommendationsAgent(BaseAIAgent):
    """
    AI Agent for Section 7: Final Recommendations & Next Steps

    Desired Markdown structure (matching your provided template):

    ### **Section 7: Final Recommendations & Next Steps** {#section-7:-final-recommendations-&-next-steps}

    #### **Key Strengths Supporting Investment Consideration** {#key-strengths-supporting-investment-consideration}
    ✅ **High Market Traction & Growth Metrics**
    * 
    ✅ **Scalable SaaS Business Model**
    * 
    ✅ **Potential for Strategic M&A Exit**
    * 

    #### **Key Investment Risks & Mitigation Strategies** {#key-investment-risks-&-mitigation-strategies}
    ⚠ **Over-Reliance on ...**
    * **Risk:**  
    * **Mitigation:**  
    ⚠ **Limited Financial Transparency** 
    * **Risk:**  
    * **Mitigation:**  

    #### **Prioritized Action Plan for Investment Readiness** {#prioritized-action-plan-for-investment-readiness}
    | Priority Level | Action Item | Impact | Feasibility |
    | ----- | ----- | ----- | ----- |
    | **Short-Term (1-3 Months)** |  |  |  |
    | **Medium-Term (3-6 Months)** |  |  |  |
    | **Long-Term (6-12 Months)** |  |  |  |

    #### **Strategic Roadmap for Growth & Exit Planning** {#strategic-roadmap-for-growth-&-exit-planning}
    | Phase | Actionable Steps | Key Performance Indicators (KPIs) |
    | ----- | ----- | ----- |
    | **Short-Term (1-3 Months)** |  |  |
    | **Medium-Term (3-6 Months)** |  |  |
    | **Long-Term (6-12 Months)** |  |  |

    #### **Investment Readiness & Market Positioning** {#investment-readiness-&-market-positioning}
    | Category | Assessment |
    | ----- | ----- |
    | **Investment Readiness** | 🟢 Strong Alignment |
    | **Market Positioning & Competitive Strength** | 🟢 Strong Fit |
    | **Funding Transparency & Investor Reporting** | 🟡 Needs Improvement |
    | **Leadership & Operational Scalability** | 🟡 Moderate Risk |
    | **Exit Viability & M&A Potential** | 🟢 Favorable Pathways |

    ### **Final Investment Recommendation** {#final-investment-recommendation}

    ### **Next Steps for Investment Consideration** {#next-steps-for-investment-consideration}
    1. 
    2. 
    3. 
    4. 

    ### **Final Conclusion** {#final-conclusion}
    ...
    """
    def __init__(self):
        prompt_template = (
            "You are an expert at drafting **Section 7: Final Recommendations & Next Steps** in Markdown format. "
            "Use **the exact headings, subheadings, anchor links, and tables** shown in the sample below, "
            "incorporating data from 'retrieved_context' and applying color-coded references (🟢, 🟡, 🔴) if relevant.\n\n"
            
            "Company: {{company}}\n"
            "Industry: {{industry}}\n\n"
            "Retrieved Context:\n"
            "{{retrieved_context}}\n\n"

            "## Your Task\n"
            "Generate **Section 7** in the following markdown structure:\n\n"
            "### **Section 7: Final Recommendations & Next Steps** {#section-7:-final-recommendations-&-next-steps}\n\n"
            "#### **Key Strengths Supporting Investment Consideration** {#key-strengths-supporting-investment-consideration}\n"
            "Use bullet points or short paragraphs for each strength, e.g.:\n"
            "✅ **High Market Traction & Growth Metrics**\n"
            "* Some detail...\n"
            "✅ **Scalable SaaS Business Model**\n"
            "* Some detail...\n"
            "✅ **Potential for Strategic M&A Exit**\n"
            "* Some detail...\n\n"
            "#### **Key Investment Risks & Mitigation Strategies** {#key-investment-risks-&-mitigation-strategies}\n"
            "List each risk with a label like '⚠ **Over-Reliance on ___**', then provide Risk/Mitigation.\n\n"
            "#### **Prioritized Action Plan for Investment Readiness** {#prioritized-action-plan-for-investment-readiness}\n"
            "| Priority Level | Action Item | Impact | Feasibility |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **Short-Term (1-3 Months)** |  |  |  |\n"
            "| **Medium-Term (3-6 Months)** |  |  |  |\n"
            "| **Long-Term (6-12 Months)** |  |  |  |\n\n"
            "#### **Strategic Roadmap for Growth & Exit Planning** {#strategic-roadmap-for-growth-&-exit-planning}\n"
            "| Phase | Actionable Steps | Key Performance Indicators (KPIs) |\n"
            "| ----- | ----- | ----- |\n"
            "| **Short-Term (1-3 Months)** |  |  |\n"
            "| **Medium-Term (3-6 Months)** |  |  |\n"
            "| **Long-Term (6-12 Months)** |  |  |\n\n"
            "#### **Investment Readiness & Market Positioning** {#investment-readiness-&-market-positioning}\n"
            "| Category | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Investment Readiness** | 🟢 Strong Alignment |\n"
            "| **Market Positioning & Competitive Strength** | 🟢 Strong Fit |\n"
            "| **Funding Transparency & Investor Reporting** | 🟡 Needs Improvement |\n"
            "| **Leadership & Operational Scalability** | 🟡 Moderate Risk |\n"
            "| **Exit Viability & M&A Potential** | 🟢 Favorable Pathways |\n\n"
            "### **Final Investment Recommendation** {#final-investment-recommendation}\n"
            "A short paragraph summarizing the recommendation.\n\n"
            "### **Next Steps for Investment Consideration** {#next-steps-for-investment-consideration}\n"
            "A numbered list:\n"
            "1. ...\n"
            "2. ...\n"
            "3. ...\n"
            "4. ...\n\n"
            "### **Final Conclusion** {#final-conclusion}\n"
            "Wrap up with a concluding statement.\n\n"
            "### Instructions\n"
            "1. Write your final answer in valid **Markdown**.\n"
            "2. For unknown data, use placeholders or note missing info.\n"
            "3. Keep the headings, subheadings, anchor tags, and tables exactly as shown.\n"
        )
        super().__init__(prompt_template)
