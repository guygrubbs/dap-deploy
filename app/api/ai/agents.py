import os
import openai
import logging
import json
from dataclasses import dataclass
from typing import Dict, Any, ClassVar

logger = logging.getLogger(__name__)

try:
    import sanitize_html
except ModuleNotFoundError:
    import re
    def sanitize_html(text: str) -> str:
        """Extremely naive HTML tag stripper (replace in production)."""
        return re.sub(r"<[^>]+?>", "", text)

def _openai_chat_completion(messages: list[dict[str, str]]) -> str:
    """Centralised OpenAI call – keeps each agent tiny."""
    model = os.getenv("OPENAI_MODEL", "o1")
    resp = openai.ChatCompletion.create(model=model, messages=messages)
    return resp["choices"][0]["message"]["content"].strip()

# --------------------------------------------------------------------------- #
# Base class
# --------------------------------------------------------------------------- #

@dataclass
class BaseJSONAgent:
    """Base class – concrete subclasses only need to fill `name`, `schema`, and optionally `guidance`."""
    name: ClassVar[str] = "base"
    schema: ClassVar[str] = "{}"   # override – JSON skeleton (string placeholders for values)
    guidance: ClassVar[str] = ""   # optional field-level guidance and examples

    system_prompt: ClassVar[str] = (
        "You are an AI assistant that converts a long due-diligence report into "
        "structured JSON objects for database storage. "
        "Follow the schema and guidance exactly. Respond with **ONLY** the JSON object – no markdown, "
        "headings or commentary."
    )

    def generate_json(self, report_text: str) -> str:
        """Return the raw JSON string (NOT parsed) for this summary section."""
        user_prompt = (
            f"Using the following full report content, create the JSON for **{self.name}** "
            f"that matches this schema:\n{self.schema}"
        )
        if self.guidance:
            user_prompt += f"\n\nField Guidance & Example Values:\n{self.guidance}"
        user_prompt += f"\n\nFull report:\n{report_text}"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            content = _openai_chat_completion(messages)
            # Ensure it's valid JSON
            _ = json.loads(content)
            logger.info("%s JSON generated, %s characters.", self.name, len(content))
            return content
        except Exception as exc:
            logger.error("Failed to generate JSON for %s: %s", self.name, exc, exc_info=True)
            return ""

    def generate_and_clean(self, report_text: str) -> Dict[str, Any]:
        """Return a dict with all string fields sanitised (except JSONB numeric fields)."""
        raw = self.generate_json(report_text)
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        def cleanse(val):
            if isinstance(val, str):
                return sanitize_html(val)
            if isinstance(val, list):
                return [cleanse(v) for v in val]
            if isinstance(val, dict):
                return {k: cleanse(v) for k, v in val.items()}
            return val
        return cleanse(data)
    

class BaseAIAgent:
    """
    Base class for AI agents using the OpenAI GPT o1 API.
    This class provides methods to generate report sections based on a dynamic prompt template and context.
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

        # Retrieve model name from environment or default to "o1"
        model_name = os.getenv("OPENAI_MODEL", "o1")

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
        Generates a report section using the provided context.
        Dynamically formats the prompt template with the given context and calls the GPT API.
        """
        prompt = self.prompt_template.format(**context)
        logger.info("Generating section with prompt:\n%s", prompt)

        model_name = os.getenv("OPENAI_MODEL", "o1")
        try:
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert report writer with deep industry knowledge. Respond only with the requested headings and content. Do not include disclaimers or source references. If analysis information is missing for a section or table entry, report that it was not provided. This should be a weakness for the analysis of each section. Assume all ratings shown in prompts should be updated to rate the information in the retrieved context and not just use the ratings shown."
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
    Consolidates essential research prompts to gather high-level data about a company.
    Output is used as context for subsequent agents.  Updated to:
      • Tailor research depth to company stage (early vs. late) and domain
      • Expand competitive research with weaknesses / strategic moves
      • Retrieve regulatory-compliance and scalability benchmarks
      • Capture customer-retention trends
      • Preserve strict Markdown output structure
    """
    def __init__(self):
        prompt_template = (
            "You are a professional research analyst. Collect clear, factual information for the "
            "company below. **Tailor your depth and tone to the company’s current stage** "
            "(early-stage, growth, late-stage) and its industry domain.\n\n"

            "**Company Name:** {founder_company}\n"
            "**Stage:** {funding_stage}  <!-- e.g. pre-MVP, early-stage, Series-A, growth -->\n"
            "**Industry / Domain:** {industry}\n\n"
            "Additional founder-supplied context:\n"
            "{retrieved_context}\n\n"

            "## Research Objectives\n"
            "### 1) Market & Industry Overview\n"
            "- Define the market focus, key segments, and current trends.\n"
            "- Identify direct and indirect competitors **with each rival’s strengths *and* weaknesses / gaps / recent strategic moves**.\n"
            "- Highlight pain points the company solves and differentiation vs. existing solutions.\n"
            "- Note any unclear or missing market data.\n\n"

            "### 2) Customer Traction & Revenue\n"
            "- Summarize traction metrics appropriate to **{funding_stage}** "
            "(e.g., pre-MVP → user interviews / wait-list sign-ups, Series-A → MRR, CAC, LTV).\n"
            "- List revenue drivers or channels.  Flag unknowns (e.g., churn, CSAT) where data is absent.\n\n"

            "### 3) Financial & Growth Indicators\n"
            "- Capture funding rounds, investors, total raised, valuation, burn / runway if public.\n"
            "- Provide profitability or growth metrics relative to stage.\n"
            "- Note gaps impeding a full assessment.\n\n"

            "### 4) Go-To-Market & Competitive Position\n"
            "- Outline acquisition + retention approaches.\n"
            "- Compare tactics to competitor strategies identified above.\n"
            "- Flag any missing GTM effectiveness data.\n\n"

            "### 5) Regulatory Compliance & Scalability Readiness\n"
            "- List **industry-specific regulations** (e.g., SOC 2, HIPAA, GDPR) and certification benchmarks.\n"
            "- Summarize scalability challenges typical for {industry} startups "
            "(infrastructure, people, cross-border compliance).\n\n"

            "### 6) Customer Success & Retention Trends\n"
            "- Provide industry benchmarks for retention or churn where available.\n"
            "- Note early CS frameworks or onboarding best practices relevant to stage.\n\n"

            "### 7) Leadership & Team Snapshot\n"
            "- Summarize leadership experience, team size, hiring plans.\n"
            "- Identify any capability gaps tied to growth objectives.\n\n"

            "### 8) Investor Alignment & Key Risks\n"
            "- Explain how the opportunity fits typical investor theses.\n"
            "- List major risks (market, tech, regulatory, talent) with brief notes.\n\n"

            "### 9) Recommended Next Steps (Bullet List)\n"
            "- Suggest the **highest-priority research or validation tasks** to close data gaps.\n\n"

            "### Output Instructions\n"
            "• Write in **Markdown** using the section headers above (do NOT add new anchors).\n"
            "• Use bullet lists for clarity; keep each bullet concise.\n"
            "• If data is unavailable, state “*Not publicly available*”.\n"
            "• Do **not** draft a final narrative; provide raw findings only.\n"
        )
        super().__init__(prompt_template)

# ---------------------------------------------------------------
# 1) Executive Summary & Investment Rationale
# ---------------------------------------------------------------
class ExecutiveSummaryAgent(BaseAIAgent):
    """
    Section-1 agent updated to:
      • Briefly touch on all five improvement themes (stage-fit tone, competitive
        strategy, compliance/scalability, customer success, future expansion).
      • Remove any hard-coded emoji; ratings or colour language must be derived
        from context (or omitted if insufficient evidence).
      • Provide tone instructions so early-stage ↔ late-stage wording differs.
      • Preserve existing markdown headings / anchors.
    """

    def __init__(self):
        prompt_template = (
            "You are an executive-level report writer creating **Section 1: Executive Summary "
            "& Investment Rationale** in Markdown.  "
            "Use a tone that reflects the company’s maturity: **optimistic and visionary** if "
            "early-stage, or **confident and data-backed** if growth/late-stage.  "
            "Always remain succinct and professional. Use color codes depending on the rating where  "
            "[🟢/🟡/🔴] is shown.\n\n"

            "**Founder:** {founder_name}\n"
            "**Company:** {founder_company}  \n"
            "**Stage:** {funding_stage}  \n"
            "**Industry / Domain:** {industry}\n\n"
            "Retrieved Context:\n{retrieved_context}\n\n"

            "## Your Task\n"
            "Generate the summary below, ensuring you briefly address:\n"
            "• Stage-matched framing (agility & learning vs. scale & efficiency)  \n"
            "• Competitive differentiation strategy  \n"
            "• Compliance & scalability awareness  \n"
            "• Customer-success & retention focus  \n"
            "• Vision for expansion beyond the first market\n\n"

            "### **Section 1: Executive Summary & Investment Rationale** {{#section-1:-executive-summary-&-investment-rationale}}\n\n"

            "#### Overview {{#overview}}\n"
            "1. **Company Snapshot:** what the company provides and to whom.  \n"
            "2. **Stage Context:** e.g., “As an early-stage startup, we focus on validation…” "
            "or “As a growth-stage company, we emphasise scale…”.  \n"
            "3. **Problem & Solution Fit:** concise statement of market need and the offering.\n\n"

            "#### Key Investment Considerations {{#key-investment-considerations}}\n"
            "- Competitive edge and how we will **differentiate vs. rivals**.  \n"
            "- Compliance / scalability readiness (e.g., SOC 2, GDPR, infra scale).  \n"
            "- Customer-centric approach to drive **retention & lifetime value**.  \n"
            "- Clear roadmap to **expand into new markets/segments** once traction is secured.  \n"
            "- Any notable gaps or data needs investors should be aware of.\n\n"

            "#### Investment Readiness Snapshot {{#investment-readiness-overview}}\n"
            "| Category | Status | Analysis Outcome |\n"
            "| -------- | ------- | --------------------- |\n"
            "| Market Traction | [🟢/🟡/🔴] {{derive from context}} | {{evidence}} |\n"
            "| Revenue Potential | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Leadership Depth | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Operational Scalability | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Regulatory Compliance | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "*Use plain words such as Strong / Moderate / Weak and a matching color emoji.  "
            "Base each status on retrieved evidence.\n\n"

            "#### Investment Risks & Considerations {{#investment-risks-&-considerations}}\n"
            "- Summarise 2-3 key risks (market, compliance, tech, retention) with brief notes.\n\n"

            "#### Investment Recommendations & Next Steps {{#investment-recommendations-&-next-steps}}\n"
            "_Short-Term (1-3 M):_ …  \n"
            "_Medium-Term (3-6 M):_ …  \n"
            "_Long-Term (6-12 M):_ …\n\n"

            "### Instructions\n"
            "• Output valid **Markdown** only.  \n"
            "• Derive every status or claim from the provided context; if unknown, write "
            "“*Not publicly available*”.  \n"
            "• Keep all headings / anchors exactly as shown; do not add emoji in headings."
        )
        super().__init__(prompt_template)



# ---------------------------------------------------------------
# 2) Market Opportunity & Competitive Landscape
# ---------------------------------------------------------------
class MarketAnalysisAgent(BaseAIAgent):
    """
    AI Agent for Section 2: Market Opportunity & Competitive Landscape
    — updated to:
      • Adapt tone and depth to the company’s stage (`early-stage`, `growth`, etc.)
      • Add a “Competitive Action Items” subsection with 2-3 strategic responses
      • Call out customer-retention dynamics whenever relevant
      • Highlight compliance / market-entry constraints (e.g., SOC 2, GDPR)
      • Preserve all existing markdown anchors and heading hierarchy
    """
    def __init__(self):
        prompt_template = (
            "You are an expert market analyst writing **Section 2: Market Opportunity & Competitive Landscape** "
            "in Markdown.  Tailor your analysis to the startup’s **stage** and **audience**:\n"
            "• If **{funding_stage}** is early (pre-MVP / pre-revenue) → emphasize market potential, unmet needs, and validation hurdles.\n"
            "• If later stage → focus on evidence, scaling metrics, and efficiency benchmarks.\n\n"

            "**Company:** {founder_company}\n"
            "**Stage:** {funding_stage}\n"
            "**Industry / Domain:** {industry}\n\n"
            "Retrieved Context:\n{retrieved_context}\n\n"

            "## Your Task\n"
            "Generate **Section 2** in the exact markdown layout below.  "
            "After competitor analysis, include **2-3 tactical recommendations** on how the company can out-maneuver rivals.  "
            "Note any **customer-retention trends**, plus **regulatory or compliance constraints** that could impact market entry.\n\n"

            "### **Section 2: Market Opportunity & Competitive Landscape** {{#section-2:-market-opportunity-&-competitive-landscape}}\n\n"

            "#### Market Overview {{#market-overview}}\n"
            "Provide a concise stage-appropriate overview of the market (problem, target users, key trends).\n\n"

            "#### Market Size & Growth Projections {{#market-size-&-growth-projections:}}\n"
            "- **Total Addressable Market (TAM):**\n"
            "- **Annual Growth Rate:**\n"
            "- **Adoption / Retention Trends:** _(mention if long-term customer relationships are critical in this market)_\n\n"

            "#### Competitive Positioning {{#competitive-positioning}}\n"
            "Summarize the company’s core advantages vs. competitors, factoring in {funding_stage} context.\n\n"

            "#### Competitive Landscape {{#competitive-landscape}}\n"
            "| Competitor | Market Focus | Key Strengths | Weaknesses / Gaps |\n"
            "| ---------- | ------------ | ------------- | ----------------- |\n"
            "|            |              |               |                   |\n\n"

            "#### Competitive Action Items {{#competitive-action-items}}\n"
            "- **Action 1:** _e.g., “Leverage lower pricing to undercut Competitor A’s enterprise premium.”_\n"
            "- **Action 2:** _e.g., “Develop missing Feature X to neutralize Competitor B’s advantage.”_\n"
            "- **Action 3:** _(optional)_\n\n"

            "#### Key Market Takeaways {{#key-market-takeaways:}}\n"
            "- Bullet summary of the most important insights (size, growth, competition, retention cues).\n\n"

            "#### Challenges {{#challenges:}}\n"
            "- List regulatory hurdles, competitive barriers, retention risks, etc.\n\n"
            "#### Opportunities for Market Expansion {{#opportunities-for-market-expansion:}}\n"
            "✅ Describe adjacent verticals / geographies the startup could pursue after initial traction.\n\n"

            "#### Market Fit Assessment {{#market-fit-assessment}}\n"
            "| Market Factor | Status | Analysis Outcome |\n"
            "| ------------- | ------- | --------------------- |\n"
            "| Problem–Solution Fit | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Competitive Intensity | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Regulatory Complexity | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Customer Retention Dynamics | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n\n"

            "### Instructions\n"
            "1. Output **valid Markdown** only; keep every heading & anchor unchanged except where new anchors are specified above.\n"
            "2. All color-coded ratings must reflect evidence from `retrieved_context` (do **not** leave static placeholders).\n"
            "3. If data is missing, state “*Not publicly available*”.\n"
            "4. Replace [🟢/🟡/🔴] with the correct color to match the rating for the category.\n"
            "5. Use plain words such as Strong / Moderate / Weak and a matching color emoji.\n"
            "6. Base each status on retrieved evidence.\n"
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
      ### **Section 3: Financial Performance & Investment Readiness** {{#section-3:-financial-performance-&-investment-readiness}

      #### **Revenue Growth & Profitability Overview** {{#revenue-growth-&-profitability-overview}
      | Metric | Founder Company Performance | Industry Benchmark |
      | ----- | ----- | ----- |
      |  |  |  |
      |  |  |  |

      #### **Investment Raised & Fund Utilization** {{#investment-raised-&-fund-utilization}
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

      #### **Revenue Streams & Financial Risk Analysis** {{#revenue-streams-&-financial-risk-analysis}
      | Revenue Source | Contribution | Risk Factor |
      | ----- | ----- | ----- |
      | **SaaS Subscriptions** |  |  |
      | **Other Streams** |  |  |

      #### **Key Financial Risks & Considerations** {{#key-financial-risks-&-considerations}
      - bullet points

      #### **Financial Risk Assessment** {{#financial-risk-assessment}
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
            "Incorporate any relevant details from '{{retrieved_context}}' and apply color-coded references (🟢, 🟡, 🔴) if needed.\n\n"

            "Company: {founder_company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "## Your Task\n"
            "Generate **Section 3** in the following markdown structure:\n\n"
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
            "⚠ (list 2-3 concerns)\n\n"
            "#### **Revenue Streams & Financial Risk Analysis** {{#revenue-streams-&-financial-risk-analysis}}\n"
            "| Revenue Source | Contribution | Risk Factor |\n"
            "| ----- | ----- | ----- |\n"
            "| **SaaS Subscriptions** |  |  |\n"
            "| **Other Streams** |  |  |\n\n"
            "#### **Key Financial Risks & Considerations** {{#key-financial-risks-&-considerations}}\n"
            "- Provide bullet points.\n\n"
            "#### **Financial Risk Assessment** {{#financial-risk-assessment}}\n"
            "| Risk Factor | Status | Analysis Outcome |\n"
            "| ----------- | ------- | --------------------- |\n"
            "| **Revenue Concentration Risk** | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Funding Transparency** | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Burn Rate & Cash Flow Stability** | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Profitability & Sustainability** | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n\n"
            "### Instructions\n"
            "1. Output valid **Markdown** only; keep every heading & anchor unchanged.\n"
            "2. Use the emoji scoring system exactly; no static placeholders.\n"
            "3. Keep headings, subheadings, anchor tags exactly as shown.\n"
            "4. Replace [🟢/🟡/🔴] with the correct color to match the rating for the category.\n"
            "5. Use plain words such as Strong / Moderate / Weak and a matching color emoji.\n"
            "6. Base each status on retrieved evidence.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 4) Go-To-Market (GTM) Strategy & Customer Traction
# ---------------------------------------------------------------
class GoToMarketAgent(BaseAIAgent):
    """
    Section-4 agent — now stage-aware, retention-focused, and expansion-oriented.
    Adds:
      • Customer Retention Strategy subsection
      • Explicit scaling plan beyond the first market
      • Competitive-aware differentiation guidance
      • Tone adaptation based on funding_stage (early vs. growth/late)
    """
    def __init__(self):
        prompt_template = (
            "You are a go-to-market strategist drafting **Section 4: Go-To-Market (GTM) Strategy & Customer Traction** "
            "in Markdown.  Adjust tone and depth to **{funding_stage}**:\n"
            "• *Early-stage* – emphasize agile experiments, budget awareness, learning cycles.\n"
            "• *Growth / later stage* – emphasize proven channels, scale efficiency, aggressive expansion.\n\n"

            "**Company:** {founder_company}\n"
            "**Stage:** {funding_stage}\n"
            "**Industry / Domain:** {industry}\n\n"
            "Retrieved Context:\n{retrieved_context}\n\n"

            "## Your Task\n"
            "Follow the exact markdown layout below.  Be sure to:\n"
            "1. **Include competitive differentiation** — reference how our GTM counters rivals’ strengths.\n"
            "2. Add a **Customer Retention Strategy** subsection outlining onboarding, success, and loyalty tactics.\n"
            "3. Provide an **Expansion Plan** for new markets/segments once initial traction is achieved.\n"
            "4. Use 🟢🟡🔴 ratings only if evidence supports them; never hard-code."
            "5. Wherever [🟢/🟡/🔴] is used, replace with correct rating unless no rating is possible.\n\n"

            "### **Section 4: Go-To-Market (GTM) Strategy & Customer Traction** {{#section-4:-go-to-market-(gtm)-strategy-&-customer-traction}}\n\n"

            "#### **Customer Acquisition Strategy** {{#customer-acquisition-strategy}}\n"
            "| Acquisition Channel | Performance | Challenges |\n"
            "| ------------------- | ----------- | ---------- |\n"
            "|                    |             |            |\n"
            "|                    |             |            |\n\n"
            "✅ **Strengths:**\n"
            "⚠ **Challenges:**\n"
            "_Given competitor approaches, highlight how these channels differentiate us._\n\n"

            "#### **Customer Retention & Lifetime Value** {{#customer-retention-&-lifetime-value}}\n"
            "| Retention Metric | Founder Company Performance | Industry Benchmark |\n"
            "| ---------------- | --------------------------- | ------------------ |\n"
            "| **Customer Retention Rate** |  |  |\n"
            "| **Churn Rate**              |  |  |\n"
            "| **Referral-Based Growth**   |  |  |\n\n"

            "#### **Customer Retention Strategy** {{#customer-retention-strategy}}\n"
            "- Onboarding program: step-by-step guidance to first value.\n"
            "- Proactive success touch-points and QBRs.\n"
            "- Loyalty / referral incentives and community building.\n\n"

            "#### **Challenges & Market Expansion Plan** {{#challenges-&-market-expansion-plan}}\n"
            "⚠ **Customer Acquisition Cost (CAC) Optimization Needed**\n"
            "* **Challenge:**\n"
            "* **Solution:**\n\n"
            "⚠ **Revenue Concentration Risk**\n"
            "* **Challenge:**\n"
            "* **Solution:**\n\n"

            "#### **Expansion Plan – Scaling Beyond Initial Market** {{#expansion-plan}}\n"
            "- **Next Markets / Segments:** list 1-2 logical geographies or verticals.\n"
            "- **Prerequisites:** localization, compliance, partnerships, hiring.\n"
            "- **Go-Live Timeline:** staged milestones post-traction.\n\n"

            "#### **Market Expansion Strategy** {{#market-expansion-strategy}}\n"
            "✅ **Franchise Pilot Growth** –\n"
            "✅ **Supplier Network Growth** –\n"
            "✅ **AI-Driven Enhancements** –\n\n"

            "#### **GTM Performance Assessment** {{#gtm-performance-assessment}}\n"
            "| Category | Status | Analysis Outcome |\n"
            "| -------- | ------- | --------------------- |\n"
            "| **Lead Generation Efficiency**  | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Customer Retention**          | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Revenue Growth**              | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Outbound Sales Effectiveness**| [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Market Diversification**      | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n\n"

            "### Instructions\n"
            "1. Output valid **Markdown** only; keep all heading anchors intact.\n"
            "2. If data is missing, state “*Not publicly available*”.\n"
            "3. Ensure tone reflects **{funding_stage}** (experimental vs. scaled).\n"
            "4. Replace [🟢/🟡/🔴] with the correct color to match the rating for the category.\n"
            "5. Use plain words such as Strong / Moderate / Weak and a matching color emoji.\n"
            "6. Base each status on retrieved evidence.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 5) Leadership & Team
# ---------------------------------------------------------------
class LeadershipTeamAgent(BaseAIAgent):
    """
    AI Agent for Section 5: Leadership & Team

    Desired Markdown structure:
    ### **Section 5: Leadership & Team** {{#section-5:-leadership-&-team}

    #### **Leadership Expertise & Strategic Decision-Making** {{#leadership-expertise-&-strategic-decision-making}
    Leadership Expertise & Strategic Decision-Making

    | Leadership Role | Experience & Contributions | Identified Gaps |
    | ----- | ----- | ----- |
    | **Co-Founder & CEO** |  |  |
    | **Co-Founder & Business Development Lead** |  |  |
    | **Sales & Business Development Team** |  |  |
    | **Engineering & Product Development** |  |  |

    ✅ **Strengths:**  
    ⚠ **Challenges:** 

    #### **Organizational Structure & Growth Plan** {{#organizational-structure-&-growth-plan}
    | Functional Area | Current Status | Planned Expansion | Impact on Scalability |
    | ----- | ----- | ----- | ----- |
    | **Product & Engineering** |  |  |  |
    | **Sales & Business Development** |  |  |  |
    | **Customer Success & Support** |  |  |  |

    ✅  
    ⚠ 

    #### **Strategic Hiring Roadmap** {{#strategic-hiring-roadmap}
    | Role | Current Status | Planned Hiring Timeline | Impact |
    | ----- | ----- | ----- | ----- |
    | **CTO / Senior Product Leader** |  |  |  |
    | **Outbound Sales & BD Team Expansion** |  |  |  |
    | **Customer Success & Ops Growth** |  |  |  |

    ✅  
    ⚠ 

    #### **Leadership Stability & Investor Confidence** {{#leadership-stability-&-investor-confidence}
    * **Investor View:**   
    * **Identified Risks:**   
    * **Mitigation Strategy:** 

    #### **Leadership & Organizational Stability Assessment** {{#leadership-&-organizational-stability-assessment}
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
            "incorporating details from '{{retrieved_context}}' and mentioning color-coded references if relevant."
            "Wherever [🟢/🟡/🔴] is used, repplace with the appropriate color for the assessment based on evidence.\n\n"

            "Company: {founder_company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "## Your Task\n"
            "Generate **Section 5** in the following markdown structure:\n\n"
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
            "| Leadership Category | Status | Analysis Outcome |\n"
            "| ------------------- | ------- | --------------------- |\n"
            "| **Strategic Vision & Execution**            | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Technical Leadership Depth**             | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Sales & Business Development Scalability**| [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Team Stability & Succession Planning**    | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n\n"
            "### Instructions\n"
            "1. Output valid **Markdown** only; keep all heading anchors intact.\n\n"
            "2. If data is missing, state “*Not publicly available*”.\n"
            "3. Retain the exact headings, subheadings, anchor tags as shown.\n"
            "4. Replace [🟢/🟡/🔴] with the correct color to match the rating for the category.\n"
            "5. Use plain words such as Strong / Moderate / Weak and a matching color emoji.\n"
            "6. Base each status on retrieved evidence.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 6) Investor Fit, Exit Strategy & Funding Narrative
# ---------------------------------------------------------------
class InvestorFitAgent(BaseAIAgent):
    """
    AI Agent for Section 6: Investor Fit, Exit Strategy & Funding Narrative

    Desired Markdown structure:
    ### **Section 6: Investor Fit, Exit Strategy & Funding Narrative** {{#section-6:-investor-fit,-exit-strategy-&-funding-narrative}

    #### **Investor Profile & Strategic Alignment** {{#investor-profile-&-strategic-alignment}
    Founder Company Investor Profile & Strategic Alignment

    **Ideal Investor Profile:**  
    ✅ **Venture Capital (VC) Firms** –  
    ✅ **Private Equity (PE) Funds** –  
    ✅ **Strategic FSM Acquirers** –  

    ⚠ **Investor Concerns:**
    - 

    #### **Exit Strategy Analysis** {{#exit-strategy-analysis}
    | Exit Type | Viability | Potential Acquirers / Investors | Challenges |
    | ----- | ----- | ----- | ----- |
    | **M&A by FSM Software Companies** |  |  |  |
    | **Private Equity (PE) Buyout** |  |  |  |
    | **IPO as a Growth-Stage SaaS** |  |  |  |

    ✅ **Most Likely Exit:**  
    ⚠ **IPO Variability**

    #### **Current Funding Narrative & Investor Messaging** {{#current-funding-narrative-&-investor-messaging}
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

    #### **Investor Messaging & Priorities** {{#investor-messaging-&-priorities}
    * **High-Growth SaaS Opportunity:**  
    * **Defensible Market Positioning:**  
    * **Exit Potential:**  

    #### **Investor Fit Assessment** {{#investor-fit-assessment}
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
            "as shown in the template below. Incorporate relevant details from '{{retrieved_context}}' and use "
            "color-coded references (🟢, 🟡, 🔴) if needed."
            "Wherever [🟢/🟡/🔴] is used, repplace with the appropriate color for the assessment based on evidence.\n\n"

            "Company: {founder_company}\n"
            "Retrieved Context:\n"
            "{retrieved_context}\n\n"

            "## Your Task\n"
            "Generate **Section 6** in the following markdown structure:\n\n"
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
            "| Investment Factor | Status | Analysis Outcome |\n"
            "| ----------------- | ------- | --------------------- |\n"
            "| **Scalability & ROI Potential**            | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Investor Sentiment & Market Trends**     | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Funding & Exit Strategy Clarity**        | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Risk Profile for Investors**             | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n\n"
            "### Instructions\n"
            "1. Output valid **Markdown** only; keep all heading anchors intact.\n\n"
            "2. If data is missing, state “*Not publicly available*”.\n"
            "3. Keep the headings, subheadings, anchor tags, and tables exactly as shown.\n"
            "4. Replace [🟢/🟡/🔴] with the correct color to match the rating for the category.\n"
            "5. Use plain words such as Strong / Moderate / Weak and a matching color emoji.\n"
            "6. Base each status on retrieved evidence.\n"            
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 7) Final Recommendations & Next Steps
# ---------------------------------------------------------------
class RecommendationsAgent(BaseAIAgent):
    """
    Section-7 agent updated for dynamic risk ratings and expanded categories.
    Key upgrades:
      • Removes hard-coded emoji; model now assigns 🟢🟡🔴 based on evidence.
      • Provides explicit scoring criteria inside the prompt.
      • Expands rating table to include Regulatory Compliance, Scalability,
        and Customer Retention Risk.
      • Instructs model to cross-reference earlier research before rating.
      • Keeps all anchor tags / headings unchanged.
    """

    def __init__(self):
        prompt_template = (
            "You are an expert analyst drafting **Section 7: Final Recommendations & Next Steps** "
            "in Markdown.  Base your judgments on the full context below and use the dynamic "
            "emoji scoring system:\n"
            "• 🟢 Low Risk / Strong (well-managed, no major concerns)\n"
            "• 🟡 Medium Risk / Moderate (some concerns, partially mitigated)\n"
            "• 🔴 High Risk / Weak (serious unresolved issues)\n\n"
            "Always justify each rating with 1-sentence evidence extracted from `retrieved_context`.  "
            "Cross-check with prior research; never assign 🟢 by default.\n\n"

            "**Company:** {founder_company}\n"
            "**Stage:** {funding_stage}\n\n"
            "Retrieved Context:\n{retrieved_context}\n\n"

            "## Your Task\n"
            "Generate **Section 7** in the structure below.  "
            "Replace all rating placeholders with the appropriate colored icon and a concise rationale.\n\n"

            "### **Section 7: Final Recommendations & Next Steps** {{#section-7:-final-recommendations-&-next-steps}}\n\n"

            "#### **Key Strengths Supporting Investment Consideration** {{#key-strengths-supporting-investment-consideration}}\n"
            "✅ **High Market Traction & Growth Metrics** – …\n"
            "✅ **Scalable {industry} Business Model** – …\n"
            "✅ **Potential for Strategic M&A Exit** – …\n\n"

            "#### **Key Investment Risks & Mitigation Strategies** {{#key-investment-risks-&-mitigation-strategies}}\n"
            "- **Risk 1:** _Describe risk_  \n"
            "  • **Mitigation:** _Proposed fix_\n"
            "- **Risk 2:** _Describe risk_  \n"
            "  • **Mitigation:** _Proposed fix_\n\n"

            "#### **Prioritized Action Plan for Investment Readiness** {{#prioritized-action-plan-for-investment-readiness}}\n"
            "| Priority Level | Action Item | Impact | Feasibility |\n"
            "| -------------- | ----------- | ------ | ----------- |\n"
            "| **Short-Term (1-3 M)** |  |  |  |\n"
            "| **Medium-Term (3-6 M)**|  |  |  |\n"
            "| **Long-Term (6-12 M)** |  |  |  |\n\n"

            "#### **Strategic Roadmap for Growth & Exit Planning** {{#strategic-roadmap-for-growth-&-exit-planning}}\n"
            "| Phase | Actionable Steps | Key Performance Indicators (KPIs) |\n"
            "| ----- | --------------- | --------------------------------- |\n"
            "| **Short-Term (1-3 M)** |  |  |\n"
            "| **Medium-Term (3-6 M)**|  |  |\n"
            "| **Long-Term (6-12 M)** |  |  |\n\n"

            "#### **Investment Readiness & Market Positioning** {{#investment-readiness-&-market-positioning}}\n"
            "| Category | Status | Analysis Outcome |\n"
            "| -------- | ------- | --------------------- |\n"
            "| Investment Readiness                          | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Market Positioning & Competitive Strength     | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Regulatory Compliance                         | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Scalability (Ops & Tech)                      | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Customer Retention Risk                       | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Funding Transparency & Reporting              | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Leadership Depth & Succession                 | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Exit Viability / M&A Potential                | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n\n"

            "### **Final Investment Recommendation** {{#final-investment-recommendation}}\n"
            "Provide a brief recommendation statement aligned with the above ratings.\n\n"

            "### **Next Steps for Investment Consideration** {{#next-steps-for-investment-consideration}}\n"
            "1. …\n"
            "2. …\n"
            "3. …\n"
            "4. …\n\n"

            "### **Final Conclusion** {{#final-conclusion}}\n"
            "Conclude with a forward-looking statement.\n\n"

            "### Instructions\n"
            "1. Output valid **Markdown** only; keep every heading & anchor unchanged.\n"
            "2. Use the emoji scoring system exactly; no static placeholders.\n"
            "3. Each rating must include a short justification referencing context data.\n"
            "4. Replace [🟢/🟡/🔴] with the correct color to match the rating for the category.\n"
            "5. Use plain words such as Strong / Moderate / Weak and a matching color emoji.\n"
            "6. Base each status on retrieved evidence.\n"
        )
        super().__init__(prompt_template)

# --------------------------------------------------------------------------- #
# Concrete agents with schemas and guidance
# --------------------------------------------------------------------------- #

class ExecutiveSummaryJSONAgent(BaseJSONAgent):
    name = "Executive Summary"
    schema = """{
      "context_purpose": string,
      "investment_attractiveness": { "level": string, "description": string },
      "key_metrics": [ { "label": string, "value": string, "color": string }, ... ],
      "strengths": [ string, ... ],
      "challenges": [ string, ... ]
    }"""
    guidance = """- context_purpose: (string) Brief one-liner on the context and purpose of the deal/company.
- investment_attractiveness.level: (string) Overall attractiveness level, e.g. "high", "moderate", or "low".
- investment_attractiveness.description: (string) Short explanation of why the deal is attractive at that level.
- key_metrics: (list of objects) Key metrics summary, each with:
    - label: (string) Name of the metric (e.g. "Annual Revenue").
    - value: (string) Value of the metric with units (e.g. "$1M", "50% growth").
    - color: (string) Status color ("green"/"yellow"/"red" indicating good/ok/poor).
- strengths: (list of strings) Bullet points of key strengths.
- challenges: (list of strings) Bullet points of key challenges.
"""

class StrategicRecommendationsJSONAgent(BaseJSONAgent):
    name = "Strategic Recommendations"
    schema = """{
      "recommendations": [
        { "priority": string, "timeframe": string, "items": [ string, ... ] },
        ...
      ]
    }"""
    guidance = """- recommendations: (list of objects) Each strategic recommendation group with:
    - priority: (string) Priority level, e.g. "High", "Medium", or "Low" importance.
    - timeframe: (string) Target timeframe, e.g. "Short-term (1-3 months)", "Medium-term (3-6 months)", "Long-term (6-12 months)".
    - items: (list of strings) Specific recommended actions for this priority/timeframe.
"""

class MarketAnalysisJSONAgent(BaseJSONAgent):
    name = "Market Analysis"
    schema = """{
      "executive_summary": string,
      "trends": [
        {
          "trend": string,
          "insight": string,
          "relevance": string,
          "icon_type": string
        },
        ...
      ],
      "opportunity": { "description": string, "value": string, "label": string },
      "challenges": { "description": string, "status": string }
    }"""
    guidance = """- executive_summary: (string) One-sentence summary of the market landscape or context.
- trends: (list of objects) Key market trends affecting the deal:
    - trend: (string) Trend name (e.g. "Regulation", "Technology").
    - insight: (string) Insight or fact about this trend.
    - relevance: (string) Why this trend is relevant to the deal.
    - icon_type: (string) Icon identifier for the trend (e.g. "shield", "trending").
- opportunity: (object) Major market opportunity related to this deal:
    - description: (string) Description of the opportunity.
    - value: (string) Numeric value or market size (include symbols if applicable, e.g. "$650B").
    - label: (string) Label for the value (e.g. "Global Staffing TAM").
- challenges: (object) Key market challenge or risk:
    - description: (string) Description of the main challenge.
    - status: (string) Status or flag for the challenge (could include an emoji, e.g. "🟡 Refinement Needed").
"""

class FinancialOverviewJSONAgent(BaseJSONAgent):
    name = "Financial Overview"
    schema = """{
      "metrics": [
        {
          "metric": string,
          "current": string,
          "projected": string,
          "benchmark": string,
          "status": string
        },
        ...
      ],
      "risks": [ string, ... ],
      "recommendations": [ string, ... ]
    }"""
    guidance = """- metrics: (list of objects) Financial performance metrics:
    - metric: (string) Metric name (e.g. "Annual Revenue").
    - current: (string) Current value (e.g. "$0" or "N/A").
    - projected: (string) Projected future value (e.g. "$0.85M (Y1) → $200M (Y5)").
    - benchmark: (string) Relevant benchmark or target (e.g. "$150-500k ARR within 12 months").
    - status: (string) Status evaluation for this metric (e.g. "low", "moderate", "high").
- risks: (list of strings) Key financial risks identified.
- recommendations: (list of strings) Financial-related recommendations or next steps.
"""

class CompetitiveLandscapeJSONAgent(BaseJSONAgent):
    name = "Competitive Landscape"
    schema = """{
      "positioning": string,
      "competitors": [
        {
          "name": string,
          "cost": string,
          "timeline": string,
          "strengths": [ string, ... ],
          "weaknesses": [ string, ... ],
          "icon_type": string
        },
        ...
      ],
      "advantages": [
        { "title": string, "description": string },
        ...
      ]
    }"""
    guidance = """- positioning: (string) Summary of how the company is positioned vs. competitors (e.g. cost and time advantages).
- competitors: (list of objects) Main competitor categories or products:
    - name: (string) Competitor name/category (e.g. "Traditional Agencies").
    - cost: (string) Typical cost for competitor (e.g. "$15k–$50k per hire").
    - timeline: (string) Typical delivery timeline (e.g. "30–90 days").
    - strengths: (list of strings) Competitor’s strengths.
    - weaknesses: (list of strings) Competitor’s weaknesses.
    - icon_type: (string) Icon identifier for competitor (e.g. "users", "zap").
- advantages: (list of objects) Key competitive advantages of our company:
    - title: (string) Title of the advantage (e.g. "Cost Leadership").
    - description: (string) Explanation of that advantage.
"""

class ActionPlanJSONAgent(BaseJSONAgent):
    name = "Action Plan"
    schema = """{
      "timeframes": [
        {
          "period": string,
          "color": string,
          "icon_type": string,
          "actions": [ string, ... ]
        },
        ...
      ],
      "final_call_to_action": {
        "title": string,
        "sections": [
          { "title": string, "description": string },
          ...
        ]
      }
    }"""
    guidance = """- timeframes: (list of objects) Planned actions grouped by timeframe:
    - period: (string) Label for the timeframe (e.g. "Short-term (1-3 months)").
    - color: (string) Color code for urgency/priority (e.g. "red" for immediate, "yellow" for medium, "green" for long-term).
    - icon_type: (string) Icon identifier for this timeframe (e.g. "target" for short-term, "clock" for medium-term).
    - actions: (list of strings) Specific actions to be taken in that period.
- final_call_to_action: (object) Final call-to-action section:
    - title: (string) Title of this section (e.g. "Final Call-to-Action").
    - sections: (list of objects) Subsections of the call-to-action:
        - title: (string) Audience or group (e.g. "Investors:").
        - description: (string) Message or directive for that audience.
"""

class InvestmentReadinessJSONAgent(BaseJSONAgent):
    name = "Investment Readiness"
    schema = """{
      "overall_score": number,
      "overall_rating": string,
      "categories": [
        { "name": string, "score": number, "status": string, "details": string },
        ...
      ],
      "key_strengths": [ string, ... ],
      "improvement_areas": [ string, ... ],
      "recommendation": string
    }"""
    guidance = """- overall_score: (number) Overall readiness score (e.g. 0–100 scale).
- overall_rating: (string) Rating corresponding to the overall_score (e.g. "low", "moderate", "high").
- categories: (list of objects) Detailed scores by category:
    - name: (string) Category name (e.g. "Market Opportunity").
    - score: (number) Score for this category.
    - status: (string) Status label for that score (e.g. "excellent", "moderate", "critical").
    - details: (string) Explanation of the category’s score.
- key_strengths: (list of strings) Key strengths identified in the due diligence.
- improvement_areas: (list of strings) Key areas needing improvement.
- recommendation: (string) Overall recommendation statement (e.g. "Refinement Needed – suitable for early-stage venture investors").
"""

class KeyMetricsJSONAgent(BaseJSONAgent):
    """
    Outputs structured numeric data; caller should store the parsed dict in a JSONB column.
    """
    name = "Key Metrics"
    schema = """{
      "revenue": { "current": number, "projected_y1": number, "projected_y5": number },
      "growth_rate": { "cagr": number, "benchmark": number },
      "cost_metrics": { "cost_per_hire": number, "traditional_cost": number, "savings_percentage": number }
    }"""
    guidance = """- revenue: (object) Revenue figures:
    - current: (number) Current annual revenue (e.g. 0 if pre-revenue).
    - projected_y1: (number) Projected revenue in Year 1 (in dollars, no formatting or symbols).
    - projected_y5: (number) Projected revenue in Year 5.
- growth_rate: (object) Growth rate metrics:
    - cagr: (number) Compound annual growth rate (as a percentage value, e.g. 400 for 400%).
    - benchmark: (number) Benchmark growth rate for comparison (also as percentage, e.g. 250 for 250%).
- cost_metrics: (object) Cost savings metrics:
    - cost_per_hire: (number) Cost per hire using the product (in dollars).
    - traditional_cost: (number) Traditional cost per hire for comparison (in dollars).
    - savings_percentage: (number) Percentage savings (e.g. 90 for 90% cost savings).
"""

class FinancialProjectionsJSONAgent(BaseJSONAgent):
    name = "Financial Projections"
    schema = """{
      "revenue_forecast": [ { "year": number, "revenue": number }, ... ],
      "funding_rounds": [
        { "stage": string, "amount": number, "valuation_cap": number },
        ...
      ],
      "unit_economics": {
        "cac": number, "payback_months": number, "gross_margin": number
      }
    }"""
    guidance = """- revenue_forecast: (list of objects) Projected revenue for upcoming years:
    - year: (number) Year number in sequence (e.g. 1 for first year, 2 for second year).
    - revenue: (number) Projected revenue for that year (numeric value, no currency symbol).
- funding_rounds: (list of objects) Details of funding rounds:
    - stage: (string) Stage name (e.g. "SAFE", "Seed").
    - amount: (number) Amount raised in that round (numeric, in dollars).
    - valuation_cap: (number) Valuation cap or post-money valuation for that round (numeric, in dollars).
- unit_economics: (object) Key unit economics metrics:
    - cac: (number) Customer Acquisition Cost (in dollars).
    - payback_months: (number) Payback period in months for the CAC.
    - gross_margin: (number) Gross margin percentage (e.g. 65 for 65%)."""