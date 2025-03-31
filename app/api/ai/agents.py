
# app/api/ai/agents.py

import os
import openai
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class BaseAIAgent:
    """
    Base class for AI agents using the OpenAI GPT API.
    Provides methods for:
      1) gather_research(...) => collects data from a shorter system prompt
      2) generate_section(...) => produces a Markdown section from a shorter system prompt

    (Some unchanged docstring lines omitted for brevity)
    """

    def __init__(self, prompt_template: str):
        self.prompt_template = prompt_template

    def gather_research(self, context: Dict[str, Any]) -> str:
        """
        Calls the GPT API with a short system message for specialized research,
        then merges it with the user prompt from 'prompt_template'.
        If data is missing, it's marked 'unknown' or 'not disclosed'.
        """
        prompt = self.prompt_template.format(**context)
        logger.info("Gathering research with prompt:\n%s", prompt)

        model_name = os.getenv("OPENAI_MODEL", "gpt-4")  # default or fallback

        # Shortened system instructions
        system_msg = (
            "You are a specialized research agent. Provide factual details from the context. "
            "If data is missing or unknown, label it. Avoid using placeholders if real data is found."
        )

        try:
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ]
            )
            content = response["choices"][0]["message"]["content"].strip()
            logger.info("Research completed with model: %s", model_name)
            return content
        except Exception as e:
            logger.error("Error in gather_research: %s", str(e), exc_info=True)
            raise e

    def generate_section(self, context: Dict[str, Any]) -> str:
        """
        Generates a Markdown report section from a short system message plus the template.
        If context is incomplete, the AI can label data as unknown.
        """
        prompt = self.prompt_template.format(**context)
        logger.info("Generating section with prompt:\n%s", prompt)

        model_name = os.getenv("OPENAI_MODEL", "gpt-4")
        system_msg = (
            "You are an expert report writer. Return only the requested headings in valid Markdown. "
            "If data is missing, say 'unknown' rather than placeholders."
        )

        try:
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ]
            )
            content = response["choices"][0]["message"]["content"].strip()
            logger.info("Section generated with model: %s", model_name)
            return content
        except Exception as e:
            logger.error("Error in generate_section: %s", str(e), exc_info=True)
            raise e

class ResearcherAgent(BaseAIAgent):
    """
    Gathers raw research details about a company and relevant context.
    If any data is missing or not provided, it will label that field as:
    'the user did not provide the relevant information'.
    """

    def __init__(self):
        prompt_template = (
            "You are tasked with researching the following company and gathering "
            "factual information. For any field missing data, explicitly say: "
            "'the user did not provide the relevant information'.\n\n"

            "Company Name: {company_name}\n"
            "Additional Context:\n"
            "{retrieved_context}\n\n"

            "Research Objectives:\n"
            "1) Market & Industry Overview\n"
            "2) Customer Traction & Revenue\n"
            "3) Financial & Growth Indicators\n"
            "4) Go-To-Market & Competitive Position\n"
            "5) Leadership & Team\n"
            "6) Investor Alignment & Risks\n"
            "7) Recommendations or Next Steps (High-Level)\n\n"

            "Instructions:\n"
            "• Provide factual details wherever possible.\n"
            "• If any info is not found or not provided, say: 'the user did not provide the relevant information'.\n"
            "• Avoid drafting a final 'report'; simply present data.\n"
            "• This output will be appended to further sections.\n"
        )
        super().__init__(prompt_template)


class ExecutiveSummaryAgent(BaseAIAgent):
    """
    AI Agent for Section 1: Executive Summary & Investment Rationale.
    If data is missing, say: 'the user did not provide the relevant information'.
    """

    def __init__(self):
        prompt_template = (
            "You are drafting **Section 1: Executive Summary & Investment Rationale** in Markdown. "
            "Incorporate real data from 'retrieved_context' where available. "
            "If data is missing, say: 'the user did not provide the relevant information'.\n\n"

            "The company details:\n"
            "- Founder Name: {founder_name}\n"
            "- Company Name: {company}\n"
            "- Company Type: {company_type}\n"
            "- Company Provides: {company_description}\n\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 1: Executive Summary & Investment Rationale** {{#section-1:-executive-summary-&-investment-rationale}}\n\n"
            "#### Overview {{#overview}}\n"
            "1. Brief overview of the company.\n"
            "2. Mention revenue growth, traction, or market potential if known.\n"
            "3. The scope of this assessment.\n\n"
            "#### Key Investment Considerations {{#key-investment-considerations}}\n"
            "- Summarize top considerations.\n\n"
            "#### Investment Readiness Overview {{#investment-readiness-overview}}\n"
            "| Investment Category | Assessment |\n"
            "| :---- | :---- |\n"
            "| Market Traction | 🟢 Strong |\n"
            "| Revenue Growth Potential | 🟢 Strong |\n"
            "| Financial Transparency | 🟡 Needs Refinement |\n"
            "| Operational Scalability | 🟡 Needs Improvement |\n"
            "| Leadership Depth | 🟡 Moderate Risk |\n"
            "| Exit Potential | 🟢 Favorable Pathways |\n\n"
            "#### Investment Risks & Considerations {{#investment-risks-&-considerations}}\n"
            "- Bullet list of notable risks.\n\n"
            "#### Investment Recommendations & Next Steps {{#investment-recommendations-&-next-steps}}\n"
            "Short general recommendations, then short-term, medium-term, long-term.\n\n"
            "##### Short-Term (1-3 Months): {{#short-term-(1-3-months):}}\n"
            "- ...\n\n"
            "##### Medium-Term (3-6 Months): {{#medium-term-(3-6-months):}}\n"
            "- ...\n\n"
            "##### Long-Term (6-12 Months): {{#long-term-(6-12-months):}}\n"
            "- ...\n\n"

            "Instructions:\n"
            "1. Output valid Markdown.\n"
            "2. If data is not provided or missing, explicitly say: 'the user did not provide the relevant information'.\n"
            "3. Use the headings/anchor tags exactly as shown.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 2) Market Opportunity & Competitive Landscape
# ---------------------------------------------------------------
class MarketAnalysisAgent(BaseAIAgent):
    """
    AI Agent for Section 2: Market Opportunity & Competitive Landscape.
    If data is missing, say: 'the user did not provide the relevant information'.
    """

    def __init__(self):
        prompt_template = (
            "You are drafting **Section 2: Market Opportunity & Competitive Landscape** in Markdown. "
            "If data is missing, explicitly say: 'the user did not provide the relevant information'.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 2: Market Opportunity & Competitive Landscape** {{#section-2:-market-opportunity-&-competitive-landscape}}\n\n"
            "#### Market Overview {{#market-overview}}\n"
            "Summarize the market.\n\n"
            "#### Market Size & Growth Projections: {{#market-size-&-growth-projections:}}\n"
            "- **Total Addressable Market (TAM):**\n"
            "- **Annual Growth Rate:**\n"
            "- **Adoption Trends:**\n\n"
            "#### Competitive Positioning {{#competitive-positioning}}\n"
            "Highlight the company's advantages.\n\n"
            "##### Competitive Landscape {{#competitive-landscape}}\n"
            "| Competitor | Market Focus | Key Strengths | Challenges |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "|  |  |  |  |\n\n"
            "#### Key Market Takeaways: {{#key-market-takeaways:}}\n"
            "- Major insights or bullet points.\n\n"
            "##### Challenges & Expansion Opportunities {{#challenges-&-expansion-opportunities}}\n"
            "###### Challenges: {{#challenges:}}\n"
            "- List any market or operational barriers.\n\n"
            "###### Opportunities for Market Expansion: {{#opportunities-for-market-expansion:}}\n"
            "✅ Possible growth avenues.\n\n"
            "#### Market Fit Assessment {{#market-fit-assessment}}\n"
            "| Market Factor | Assessment |\n"
            "| ----- | ----- |\n"
            "|  | 🟢 Strong |\n"
            "|  | 🟡 Needs Expansion |\n\n"
            "Instructions:\n"
            "• Provide valid Markdown.\n"
            "• If any data is missing, say: 'the user did not provide the relevant information'.\n"
            "• Keep the headings, subheadings, and anchor links exactly.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 3) Financial Performance & Investment Readiness
# ---------------------------------------------------------------
class FinancialPerformanceAgent(BaseAIAgent):
    """
    AI Agent for Section 3: Financial Performance & Investment Readiness.
    If data is missing, say: 'the user did not provide the relevant information'.
    """

    def __init__(self):
        prompt_template = (
            "You are drafting **Section 3: Financial Performance & Investment Readiness** in Markdown. "
            "If data is missing, say: 'the user did not provide the relevant information'.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 3: Financial Performance & Investment Readiness** {{#section-3:-financial-performance-&-investment-readiness}}\n\n"
            "#### **Revenue Growth & Profitability Overview** {{#revenue-growth-&-profitability-overview}}\n"
            "| Metric | Founder Company Performance | Industry Benchmark |\n"
            "| ----- | ----- | ----- |\n"
            "|  |  |  |\n"
            "|  |  |  |\n\n"
            "#### **Investment Raised & Fund Utilization** {{#investment-raised-&-fund-utilization}}\n"
            "| Funding Stage | Founder Company Status | Industry Benchmark |\n"
            "| ----- | ----- | ----- |\n"
            "| **Pre-Seed → Seed** |  |  |\n"
            "| **Total Funding Raised** |  |  |\n"
            "| **Planned Raise** |  |  |\n"
            "| **Valuation Transparency** |  |  |\n\n"
            "**Investor Concerns:**\n"
            "⚠ (List 2–3)\n\n"
            "#### **Revenue Streams & Financial Risk Analysis** {{#revenue-streams-&-financial-risk-analysis}}\n"
            "| Revenue Source | Contribution | Risk Factor |\n"
            "| ----- | ----- | ----- |\n"
            "| **SaaS Subscriptions** |  |  |\n"
            "| **Other Streams** |  |  |\n\n"
            "#### **Key Financial Risks & Considerations** {{#key-financial-risks-&-considerations}}\n"
            "- Provide bullet points.\n\n"
            "#### **Financial Risk Assessment** {{#financial-risk-assessment}}\n"
            "| Risk Factor | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Revenue Concentration Risk** | 🟡 Moderate |\n"
            "| **Funding Transparency** | 🟡 Needs Improvement |\n"
            "| **Burn Rate & Cash Flow Stability** | 🟡 Requires Validation |\n"
            "| **Profitability & Sustainability** | 🟡 Long-Term Risk |\n\n"
            "Instructions:\n"
            "• Use real data if present. If missing, say: 'the user did not provide the relevant information'.\n"
            "• Keep headings, subheadings, anchor tags exactly as shown.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 4) Go-To-Market (GTM) Strategy & Customer Traction
# ---------------------------------------------------------------
class GoToMarketAgent(BaseAIAgent):
    """
    AI Agent for Section 4: Go-To-Market (GTM) Strategy & Customer Traction.
    If data is missing, say: 'the user did not provide the relevant information'.
    """

    def __init__(self):
        prompt_template = (
            "You are drafting **Section 4: Go-To-Market (GTM) Strategy & Customer Traction** in Markdown. "
            "If data is missing, say: 'the user did not provide the relevant information'.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 4: Go-To-Market (GTM) Strategy & Customer Traction** "
            "{{#section-4:-go-to-market-(gtm)-strategy-&-customer-traction}}\n\n"
            "#### **Customer Acquisition Strategy** {{#customer-acquisition-strategy}}\n"
            "| Acquisition Channel | Performance | Challenges |\n"
            "| ----- | ----- | ----- |\n"
            "|  |  |  |\n"
            "|  |  |  |\n\n"
            "✅ **Strengths:**\n"
            "⚠ **Challenges:**\n\n"
            "#### **Customer Retention & Lifetime Value** {{#customer-retention-&-lifetime-value}}\n"
            "| Retention Metric | Founder Company Performance | Industry Benchmark |\n"
            "| ----- | ----- | ----- |\n"
            "| **Customer Retention Rate** |  |  |\n"
            "| **Churn Rate** |  |  |\n"
            "| **Referral-Based Growth** |  |  |\n\n"
            "✅ **Strengths:**\n"
            "⚠ **Challenges:**\n\n"
            "#### **Challenges & Market Expansion Plan** {{#challenges-&-market-expansion-plan}}\n"
            "⚠ **Customer Acquisition Cost (CAC) Optimization Needed**\n"
            "* **Challenge:**\n"
            "* **Solution:**\n\n"
            "⚠ **Revenue Concentration Risk**\n"
            "* **Challenge:**\n"
            "* **Solution:**\n\n"
            "#### **Market Expansion Strategy** {{#market-expansion-strategy}}\n"
            "✅ **Franchise Pilot Growth** –\n"
            "✅ **Supplier Network Growth** –\n"
            "✅ **AI-Driven Enhancements** –\n\n"
            "#### **GTM Performance Assessment** {{#gtm-performance-assessment}}\n"
            "| Category | Performance | Assessment |\n"
            "| ----- | ----- | ----- |\n"
            "| **Lead Generation Efficiency** |  |  |\n"
            "| **Customer Retention** |  |  |\n"
            "| **Revenue Growth** |  |  |\n"
            "| **Outbound Sales Effectiveness** |  |  |\n"
            "| **Market Diversification** |  |  |\n\n"
            "Instructions:\n"
            "• Output valid Markdown.\n"
            "• If data is missing, say: 'the user did not provide the relevant information'.\n"
            "• Maintain headings, subheadings, anchor tags exactly.\n"
        )
        super().__init__(prompt_template)



# ---------------------------------------------------------------
# 5) Leadership & Team
# ---------------------------------------------------------------
class LeadershipTeamAgent(BaseAIAgent):
    """
    AI Agent for Section 5: Leadership & Team.
    If data is missing, say: 'the user did not provide the relevant information'.
    """

    def __init__(self):
        prompt_template = (
            "You are drafting **Section 5: Leadership & Team** in Markdown. "
            "If any data is missing, say: 'the user did not provide the relevant information'.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 5: Leadership & Team** {{#section-5:-leadership-&-team}}\n\n"
            "#### **Leadership Expertise & Strategic Decision-Making** {{#leadership-expertise-&-strategic-decision-making}}\n"
            "| Leadership Role | Experience & Contributions | Identified Gaps |\n"
            "| ----- | ----- | ----- |\n"
            "| **Co-Founder & CEO** |  |  |\n"
            "| **Co-Founder & Business Development Lead** |  |  |\n"
            "| **Sales & Business Development Team** |  |  |\n"
            "| **Engineering & Product Development** |  |  |\n\n"
            "✅ **Strengths:**\n"
            "⚠ **Challenges:**\n\n"
            "#### **Organizational Structure & Growth Plan** {{#organizational-structure-&-growth-plan}}\n"
            "| Functional Area | Current Status | Planned Expansion | Impact on Scalability |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **Product & Engineering** |  |  |  |\n"
            "| **Sales & Business Development** |  |  |  |\n"
            "| **Customer Success & Support** |  |  |  |\n\n"
            "✅\n"
            "⚠\n\n"
            "#### **Strategic Hiring Roadmap** {{#strategic-hiring-roadmap}}\n"
            "| Role | Current Status | Planned Hiring Timeline | Impact |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **CTO / Senior Product Leader** |  |  |  |\n"
            "| **Outbound Sales & BD Team Expansion** |  |  |  |\n"
            "| **Customer Success & Ops Growth** |  |  |  |\n\n"
            "✅\n"
            "⚠\n\n"
            "#### **Leadership Stability & Investor Confidence** {{#leadership-stability-&-investor-confidence}}\n"
            "* **Investor View:**\n"
            "* **Identified Risks:**\n"
            "* **Mitigation Strategy:**\n\n"
            "#### **Leadership & Organizational Stability Assessment** {{#leadership-&-organizational-stability-assessment}}\n"
            "| Leadership Category | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Strategic Vision & Execution** | 🟢 Strong |\n"
            "| **Technical Leadership Depth** | 🟡 Needs Improvement |\n"
            "| **Sales & Business Development Scalability** | 🟡 Needs Expansion |\n"
            "| **Team Stability & Succession Planning** | 🟡 Moderate Risk |\n\n"
            "Instructions:\n"
            "• Return valid Markdown.\n"
            "• If data is missing, say: 'the user did not provide the relevant information'.\n"
            "• Keep headings, subheadings, anchor tags exactly as shown.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 6) Investor Fit, Exit Strategy & Funding Narrative
# ---------------------------------------------------------------
class InvestorFitAgent(BaseAIAgent):
    """
    AI Agent for Section 6: Investor Fit, Exit Strategy & Funding Narrative.
    If data is missing, say: 'the user did not provide the relevant information'.
    """

    def __init__(self):
        prompt_template = (
            "You are drafting **Section 6: Investor Fit, Exit Strategy & Funding Narrative** in Markdown. "
            "If any data is missing, say: 'the user did not provide the relevant information'.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 6: Investor Fit, Exit Strategy & Funding Narrative** "
            "{{#section-6:-investor-fit,-exit-strategy-&-funding-narrative}}\n\n"
            "#### **Investor Profile & Strategic Alignment** {{#investor-profile-&-strategic-alignment}}\n"
            "**Ideal Investor Profile:**\n"
            "✅ **Venture Capital (VC) Firms**\n"
            "✅ **Private Equity (PE) Funds**\n"
            "✅ **Strategic FSM Acquirers**\n\n"
            "⚠ **Investor Concerns:**\n"
            "- Outline top concerns.\n\n"
            "#### **Exit Strategy Analysis** {{#exit-strategy-analysis}}\n"
            "| Exit Type | Viability | Potential Acquirers / Investors | Challenges |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **M&A** |  |  |  |\n"
            "| **Private Equity (PE) Buyout** |  |  |  |\n"
            "| **IPO** |  |  |  |\n\n"
            "✅ **Most Likely Exit:**\n"
            "⚠ **IPO Variability**\n\n"
            "#### **Current Funding Narrative & Investor Messaging** {{#current-funding-narrative-&-investor-messaging}}\n"
            "* **Total Funding Raised:**\n"
            "* **Current Round:**\n"
            "* **Valuation Transparency:**\n\n"
            "| Funding Stage | Founder Company Status | Industry Benchmark |\n"
            "| ----- | ----- | ----- |\n"
            "| **Pre-Seed → Seed** |  |  |\n"
            "| **Total Funding Raised** |  |  |\n"
            "| **Planned Raise** |  |  |\n"
            "| **Valuation Transparency** |  |  |\n\n"
            "✅ **Strengths:**\n"
            "⚠ **Challenges:**\n\n"
            "#### **Investor Messaging & Priorities** {{#investor-messaging-&-priorities}}\n"
            "* **High-Growth SaaS Opportunity:**\n"
            "* **Defensible Market Positioning:**\n"
            "* **Exit Potential:**\n\n"
            "#### **Investor Fit Assessment** {{#investor-fit-assessment}}\n"
            "| Investment Factor | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Scalability & ROI Potential** | 🟢 Strong |\n"
            "| **Investor Sentiment & Market Trends** | 🟡 Needs More Public Validation |\n"
            "| **Funding & Exit Strategy Clarity** | 🟡 Needs Refinement |\n"
            "| **Risk Profile for Investors** | 🟡 Moderate Risk |\n\n"
            "Instructions:\n"
            "• Return valid Markdown.\n"
            "• If data is missing, say: 'the user did not provide the relevant information'.\n"
            "• Keep headings, subheadings, anchor links, and tables.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 7) Final Recommendations & Next Steps
# ---------------------------------------------------------------
class RecommendationsAgent(BaseAIAgent):
    """
    AI Agent for Section 7: Final Recommendations & Next Steps.
    If data is missing, say: 'the user did not provide the relevant information'.
    """

    def __init__(self):
        prompt_template = (
            "You are drafting **Section 7: Final Recommendations & Next Steps** in Markdown. "
            "If data is missing, say: 'the user did not provide the relevant information'.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 7: Final Recommendations & Next Steps** {{#section-7:-final-recommendations-&-next-steps}}\n\n"
            "#### **Key Strengths Supporting Investment Consideration** {{#key-strengths-supporting-investment-consideration}}\n"
            "✅ **High Market Traction & Growth Metrics**\n"
            "* ...\n"
            "✅ **Scalable SaaS Business Model**\n"
            "* ...\n"
            "✅ **Potential for Strategic M&A Exit**\n"
            "* ...\n\n"
            "#### **Key Investment Risks & Mitigation Strategies** {{#key-investment-risks-&-mitigation-strategies}}\n"
            "⚠ **Over-Reliance on**\n"
            "* **Risk:**\n"
            "* **Mitigation:**\n\n"
            "⚠ **Limited Financial Transparency**\n"
            "* **Risk:**\n"
            "* **Mitigation:**\n\n"
            "#### **Prioritized Action Plan for Investment Readiness** {{#prioritized-action-plan-for-investment-readiness}}\n"
            "| Priority Level | Action Item | Impact | Feasibility |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **Short-Term (1-3 Months)** |  |  |  |\n"
            "| **Medium-Term (3-6 Months)** |  |  |  |\n"
            "| **Long-Term (6-12 Months)** |  |  |  |\n\n"
            "#### **Strategic Roadmap for Growth & Exit Planning** {{#strategic-roadmap-for-growth-&-exit-planning}}\n"
            "| Phase | Actionable Steps | Key Performance Indicators (KPIs) |\n"
            "| ----- | ----- | ----- |\n"
            "| **Short-Term (1-3 Months)** |  |  |\n"
            "| **Medium-Term (3-6 Months)** |  |  |\n"
            "| **Long-Term (6-12 Months)** |  |  |\n\n"
            "#### **Investment Readiness & Market Positioning** {{#investment-readiness-&-market-positioning}}\n"
            "| Category | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Investment Readiness** | 🟢 Strong Alignment |\n"
            "| **Market Positioning & Competitive Strength** | 🟢 Strong Fit |\n"
            "| **Funding Transparency & Investor Reporting** | 🟡 Needs Improvement |\n"
            "| **Leadership & Operational Scalability** | 🟡 Moderate Risk |\n"
            "| **Exit Viability & M&A Potential** | 🟢 Favorable Pathways |\n\n"
            "### **Final Investment Recommendation** {{#final-investment-recommendation}}\n"
            "A short paragraph summarizing the final recommendation.\n\n"
            "### **Next Steps for Investment Consideration** {{#next-steps-for-investment-consideration}}\n"
            "1. ...\n"
            "2. ...\n"
            "3. ...\n"
            "4. ...\n\n"
            "### **Final Conclusion** {{#final-conclusion}}\n"
            "Wrap up with a concluding statement.\n\n"
            "Instructions:\n"
            "• Provide valid Markdown.\n"
            "• If data is missing, say: 'the user did not provide the relevant information'.\n"
            "• Keep headings, subheadings, anchor tags exactly.\n"
        )
        super().__init__(prompt_template)