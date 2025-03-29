import os
import openai
import logging
from typing import Any, Dict
from random import randint

logger = logging.getLogger(__name__)

class BaseAIAgent:
    """
    Base class for AI agents using the OpenAI GPT-4 API.
    This class provides a method to generate a report section
    or gather research based on a dynamic prompt template and context.

    Key Updates:
    1. Automatic model selection from env var 'OPENAI_MODEL'.
    2. Optionally incorporate random subtle variations so the
       exact same placeholders/tables are not repeated verbatim 
       when context data is present.
    """

    def __init__(self, prompt_template: str):
        self.prompt_template = prompt_template

    def gather_research(self, context: Dict[str, Any]) -> str:
        """
        Calls the GPT API to gather data based on the prompt template.
        Returns text that can be used as context for other agents.

        If relevant data is in 'context', encourage the model 
        to use that data in place of placeholders.
        """
        prompt = self.prompt_template.format(**context)
        logger.info("Gathering research with prompt:\n%s", prompt)

        model_name = os.getenv("OPENAI_MODEL", "gpt-4")  # default to GPT-4

        try:
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a specialized research agent. Your job is to collect factual details "
                            "and relevant data about the company, the market, financial metrics, etc. "
                            "Avoid placeholders if real information is found in the provided context."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            content = response["choices"][0]["message"]["content"].strip()
            logger.info("Research completed successfully using model: %s", model_name)
            return content
        except Exception as e:
            logger.error("Error gathering research: %s", str(e), exc_info=True)
            raise e

    def generate_section(self, context: Dict[str, Any]) -> str:
        """
        Generates a report section using the provided 'context'.

        The method dynamically formats the prompt template with context
        (founder_name, company_name, pitch_deck_text, etc.), then calls
        the OpenAI ChatCompletion API with a system instruction to produce
        structured output in Markdown, using the required headings/subheadings.

        If data is missing, it can either mention 'unknown' or skip that part,
        rather than repeating placeholders each time.
        """

        # Dynamically generate the prompt
        prompt = self.prompt_template.format(**context)
        logger.info("Generating section with prompt:\n%s", prompt)

        model_name = os.getenv("OPENAI_MODEL", "gpt-4")

        try:
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert report writer with deep industry knowledge. "
                            "Respond only with the requested headings and content in valid Markdown. "
                            "If the context includes real data, incorporate it; do not fill with placeholders. "
                            "If data is missing or unknown, label it clearly as such."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            content = response["choices"][0]["message"]["content"].strip()
            logger.info("Section generated successfully using model: %s", model_name)
            return content
        except Exception as e:
            logger.error("Error generating section: %s", str(e), exc_info=True)
            raise e


class ResearcherAgent(BaseAIAgent):
    """
    Gathers raw research details about a company. This output
    feeds into the subsequent section-generation agents.

    Updated to encourage actual data usage from context, 
    rather than placeholders.
    """
    def __init__(self):
        prompt_template = (
            "You are tasked with researching the following company and gathering "
            "factual information. Do not use placeholders if real data is given in context. "
            "If data is missing or not provided, label it as 'unknown' or 'not disclosed'.\n\n"

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
            "• If info is not found, say 'unknown' or 'not disclosed'.\n"
            "• Avoid drafting a final 'report'; simply present data.\n"
            "• This output will be appended to further sections.\n"
        )
        super().__init__(prompt_template)


class ExecutiveSummaryAgent(BaseAIAgent):
    """
    AI Agent for Section 1: Executive Summary & Investment Rationale
    The updated prompt encourages actual data usage from 'retrieved_context'
    and fosters subtle variations if context is rich or limited.
    """
    def __init__(self):
        prompt_template = (
            "You are drafting **Section 1: Executive Summary & Investment Rationale** in Markdown. "
            "Use these headings, subheadings, and anchor links exactly, but incorporate real data if present.\n\n"

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
            "3. The scope of this assessment (finances, leadership, etc.).\n\n"
            "#### Key Investment Considerations {{#key-investment-considerations}}\n"
            "- Summarize top considerations (scalability, revenue, data gaps, etc.).\n\n"
            "#### Investment Readiness Overview {{#investment-readiness-overview}}\n"
            "Use color-coded assessments (🟢, 🟡, 🔴) if context allows.\n\n"
            "| Investment Category | Assessment |\n"
            "| :---- | :---- |\n"
            "| Market Traction | 🟢 Strong |\n"
            "| Revenue Growth Potential | 🟢 Strong |\n"
            "| Financial Transparency | 🟡 Needs Refinement |\n"
            "| Operational Scalability | 🟡 Needs Improvement |\n"
            "| Leadership Depth | 🟡 Moderate Risk |\n"
            "| Exit Potential | 🟢 Favorable Pathways |\n\n"
            "#### Investment Risks & Considerations {{#investment-risks-&-considerations}}\n"
            "- Bullet list of risks or concerns.\n\n"
            "#### Investment Recommendations & Next Steps {{#investment-recommendations-&-next-steps}}\n"
            "General recommendations, then short-term, medium-term, long-term action items.\n\n"
            "##### Short-Term (1-3 Months): {{#short-term-(1-3-months):}}\n"
            "- ...\n\n"
            "##### Medium-Term (3-6 Months): {{#medium-term-(3-6-months):}}\n"
            "- ...\n\n"
            "##### Long-Term (6-12 Months): {{#long-term-(6-12-months):}}\n"
            "- ...\n\n"

            "Instructions:\n"
            "1. Output valid Markdown.\n"
            "2. If data is known, include it; if missing, say 'unknown' or 'N/A'.\n"
            "3. Keep the headings and anchor links exactly as shown.\n"
        )
        super().__init__(prompt_template)

# ---------------------------------------------------------------
# 2) Market Opportunity & Competitive Landscape
# ---------------------------------------------------------------
class MarketAnalysisAgent(BaseAIAgent):
    """
    AI Agent for Section 2: Market Opportunity & Competitive Landscape
    The updated prompt encourages real data usage from 'retrieved_context'
    and avoids repeating the same placeholder table each time.
    """
    def __init__(self):
        prompt_template = (
            "You are drafting **Section 2: Market Opportunity & Competitive Landscape** in Markdown. "
            "Use the headings, subheadings, and anchor links exactly as shown, but incorporate real data if present.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 2: Market Opportunity & Competitive Landscape** {{#section-2:-market-opportunity-&-competitive-landscape}}\n\n"
            "#### Market Overview {{#market-overview}}\n"
            "Provide a succinct overview of the market.\n\n"
            "#### Market Size & Growth Projections: {{#market-size-&-growth-projections:}}\n"
            "- **Total Addressable Market (TAM):**\n"
            "- **Annual Growth Rate:**\n"
            "- **Adoption Trends:**\n\n"
            "#### Competitive Positioning {{#competitive-positioning}}\n"
            "Highlight this company's advantages.\n\n"
            "##### Competitive Landscape {{#competitive-landscape}}\n"
            "| Competitor | Market Focus | Key Strengths | Challenges |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "|  |  |  |  |\n\n"
            "#### Key Market Takeaways: {{#key-market-takeaways:}}\n"
            "- Summarize major insights or bullet points.\n\n"
            "##### Challenges & Expansion Opportunities {{#challenges-&-expansion-opportunities}}\n"
            "###### Challenges: {{#challenges:}}\n"
            "- List any market or operational barriers.\n\n"
            "###### Opportunities for Market Expansion: {{#opportunities-for-market-expansion:}}\n"
            "✅ Provide potential growth avenues.\n\n"
            "#### Market Fit Assessment {{#market-fit-assessment}}\n"
            "| Market Factor | Assessment |\n"
            "| ----- | ----- |\n"
            "|  | 🟢 Strong |\n"
            "|  | 🟡 Needs Expansion |\n\n"
            "Instructions:\n"
            "• Write valid Markdown.\n"
            "• Use real data if available; otherwise label as unknown.\n"
            "• Keep the headings, subheadings, anchor links exactly.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 3) Financial Performance & Investment Readiness
# ---------------------------------------------------------------
class FinancialPerformanceAgent(BaseAIAgent):
    """
    AI Agent for Section 3: Financial Performance & Investment Readiness
    The updated prompt encourages actual data usage, replacing placeholders where possible.
    """
    def __init__(self):
        prompt_template = (
            "You are drafting **Section 3: Financial Performance & Investment Readiness** in Markdown. "
            "Incorporate real data from 'retrieved_context' if present. If data is unknown, say so.\n\n"

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
            "⚠ (List 2-3 concerns)\n\n"
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
            "• Write valid Markdown.\n"
            "• If real data is present, use it; otherwise mark unknown.\n"
            "• Keep headings, subheadings, anchor tags exactly as shown.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 4) Go-To-Market (GTM) Strategy & Customer Traction
# ---------------------------------------------------------------
class GoToMarketAgent(BaseAIAgent):
    """
    AI Agent for Section 4: Go-To-Market (GTM) Strategy & Customer Traction
    Updated to avoid placeholders if data is available.
    """
    def __init__(self):
        prompt_template = (
            "You are drafting **Section 4: Go-To-Market (GTM) Strategy & Customer Traction** in Markdown. "
            "Use the provided headings exactly, and incorporate real data if it exists.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 4: Go-To-Market (GTM) Strategy & Customer Traction** {{#section-4:-go-to-market-(gtm)-strategy-&-customer-traction}}\n\n"
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
            "• Use real data if present, else label unknown.\n"
            "• Maintain headings, subheadings, anchor tags exactly.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 5) Leadership & Team
# ---------------------------------------------------------------
class LeadershipTeamAgent(BaseAIAgent):
    """
    AI Agent for Section 5: Leadership & Team
    Encourages actual data usage from context to fill in roles, strengths, challenges, etc.
    """
    def __init__(self):
        prompt_template = (
            "You are drafting **Section 5: Leadership & Team** in Markdown. "
            "Include real info from 'retrieved_context' or label unknown if missing.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 5: Leadership & Team** {{#section-5:-leadership-&-team}}\n\n"
            "#### **Leadership Expertise & Strategic Decision-Making** {{#leadership-expertise-&-strategic-decision-making}}\n"
            "Leadership Expertise & Strategic Decision-Making\n\n"
            "| Leadership Role | Experience & Contributions | Identified Gaps |\n"
            "| ----- | ----- | ----- |\n"
            "| **Co-Founder & CEO** |  |  |\n"
            "| **Co-Founder & Business Development Lead** |  |  |\n"
            "| **Sales & Business Development Team** |  |  |\n"
            "| **Engineering & Product Development** |  |  |\n\n"
            "✅ **Strengths:**  \n"
            "⚠ **Challenges:** \n\n"
            "#### **Organizational Structure & Growth Plan** {{#organizational-structure-&-growth-plan}}\n"
            "| Functional Area | Current Status | Planned Expansion | Impact on Scalability |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **Product & Engineering** |  |  |  |\n"
            "| **Sales & Business Development** |  |  |  |\n"
            "| **Customer Success & Support** |  |  |  |\n\n"
            "✅  \n"
            "⚠ \n\n"
            "#### **Strategic Hiring Roadmap** {{#strategic-hiring-roadmap}}\n"
            "| Role | Current Status | Planned Hiring Timeline | Impact |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **CTO / Senior Product Leader** |  |  |  |\n"
            "| **Outbound Sales & BD Team Expansion** |  |  |  |\n"
            "| **Customer Success & Ops Growth** |  |  |  |\n\n"
            "✅  \n"
            "⚠ \n\n"
            "#### **Leadership Stability & Investor Confidence** {{#leadership-stability-&-investor-confidence}}\n"
            "* **Investor View:**   \n"
            "* **Identified Risks:**   \n"
            "* **Mitigation Strategy:** \n\n"
            "#### **Leadership & Organizational Stability Assessment** {{#leadership-&-organizational-stability-assessment}}\n"
            "| Leadership Category | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Strategic Vision & Execution** | 🟢 Strong |\n"
            "| **Technical Leadership Depth** | 🟡 Needs Improvement |\n"
            "| **Sales & Business Development Scalability** | 🟡 Needs Expansion |\n"
            "| **Team Stability & Succession Planning** | 🟡 Moderate Risk |\n\n"
            "Instructions:\n"
            "• Write valid Markdown.\n"
            "• If real data is found, use it. Otherwise, say unknown.\n"
            "• Keep headings, subheadings, anchor tags exactly.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 6) Investor Fit, Exit Strategy & Funding Narrative
# ---------------------------------------------------------------
class InvestorFitAgent(BaseAIAgent):
    """
    AI Agent for Section 6: Investor Fit, Exit Strategy & Funding Narrative
    Updated so it will not rely on repeated placeholders if actual context data is available.
    """
    def __init__(self):
        prompt_template = (
            "You are drafting **Section 6: Investor Fit, Exit Strategy & Funding Narrative** in Markdown. "
            "Use the exact headings and tables, incorporate any real data from context.\n\n"

            "Company: {company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "Your Template:\n\n"
            "### **Section 6: Investor Fit, Exit Strategy & Funding Narrative** {{#section-6:-investor-fit,-exit-strategy-&-funding-narrative}}\n\n"
            "#### **Investor Profile & Strategic Alignment** {{#investor-profile-&-strategic-alignment}}\n"
            "Founder Company Investor Profile & Strategic Alignment\n\n"
            "**Ideal Investor Profile:**  \n"
            "✅ **Venture Capital (VC) Firms** –  \n"
            "✅ **Private Equity (PE) Funds** –  \n"
            "✅ **Strategic FSM Acquirers** –  \n\n"
            "⚠ **Investor Concerns:**\n"
            "- List concerns here.\n\n"
            "#### **Exit Strategy Analysis** {{#exit-strategy-analysis}}\n"
            "| Exit Type | Viability | Potential Acquirers / Investors | Challenges |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **M&A by FSM Software Companies** |  |  |  |\n"
            "| **Private Equity (PE) Buyout** |  |  |  |\n"
            "| **IPO as a Growth-Stage SaaS** |  |  |  |\n\n"
            "✅ **Most Likely Exit:**  \n"
            "⚠ **IPO Variability**\n\n"
            "#### **Current Funding Narrative & Investor Messaging** {{#current-funding-narrative-&-investor-messaging}}\n"
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
            "#### **Investor Messaging & Priorities** {{#investor-messaging-&-priorities}}\n"
            "* **High-Growth SaaS Opportunity:**  \n"
            "* **Defensible Market Positioning:**  \n"
            "* **Exit Potential:**  \n\n"
            "#### **Investor Fit Assessment** {{#investor-fit-assessment}}\n"
            "| Investment Factor | Assessment |\n"
            "| ----- | ----- |\n"
            "| **Scalability & ROI Potential** | 🟢 Strong |\n"
            "| **Investor Sentiment & Market Trends** | 🟡 Needs More Public Validation |\n"
            "| **Funding & Exit Strategy Clarity** | 🟡 Needs Refinement |\n"
            "| **Risk Profile for Investors** | 🟡 Moderate Risk Due to FSM Dependency |\n\n"
            "Instructions:\n"
            "• Output valid Markdown.\n"
            "• Use real data if present, else unknown.\n"
            "• Keep the headings, subheadings, anchor links, and tables.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 7) Final Recommendations & Next Steps
# ---------------------------------------------------------------
class RecommendationsAgent(BaseAIAgent):
    """
    AI Agent for Section 7: Final Recommendations & Next Steps
    Now more inclined to use real data from 'retrieved_context' or mark missing info as unknown.
    """
    def __init__(self):
        prompt_template = (
            "You are drafting **Section 7: Final Recommendations & Next Steps** in Markdown. "
            "Use real data from 'retrieved_context' to fill in details. If missing, mark unknown.\n\n"

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
            "A short paragraph...\n\n"
            "### **Next Steps for Investment Consideration** {{#next-steps-for-investment-consideration}}\n"
            "1. ...\n"
            "2. ...\n"
            "3. ...\n"
            "4. ...\n\n"
            "### **Final Conclusion** {{#final-conclusion}}\n"
            "Wrap up with a concluding statement.\n\n"
            "Instructions:\n"
            "• Output valid Markdown.\n"
            "• If real data is found, use it; otherwise unknown.\n"
            "• Keep headings, subheadings, anchor tags exactly.\n"
        )
        super().__init__(prompt_template)