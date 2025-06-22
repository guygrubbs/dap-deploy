import os
import openai
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

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
            "| Category | Status* | Evidence (1 sentence) |\n"
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
    AI Agent for **Section 2 – Market Opportunity & Competitive Landscape**

    Key updates (2025‑06):
    • Inject richer competitor detail → include **capital raised (latest public round)** and an explicit
      “Similarity vs Subject” column.
    • Preserve existing heading / anchor scheme so downstream PDF pipeline remains intact.
    • Still adapts depth and tone to company stage.
    • Keeps “Competitive Action Items”, retention call‑outs, and compliance flags.
    """

    def __init__(self):
        # ------------------------------------------------------------------
        # Template – every anchor / heading must stay unchanged
        # ------------------------------------------------------------------
        prompt_template = (
            "You are an expert market analyst drafting **Section 2: Market Opportunity & Competitive Landscape** "
            "in **Markdown**.\n\n"

            "**Company:** {founder_company}\n"
            "**Stage:** {funding_stage}\n"
            "**Industry / Domain:** {industry}\n\n"

            "Retrieved Context:\n{retrieved_context}\n\n"

            "## Your Task\n"
            "Write Section 2 using the exact heading hierarchy below.  "
            "Tailor emphasis according to **{funding_stage}**:\n"
            "• *Early‑stage* → spotlight market potential, unmet needs, and validation hurdles.\n"
            "• *Growth / Later‑stage* → emphasise traction proof, scaling metrics, and efficiency benchmarks.\n\n"

            "Also **expand the competitor grid** as follows:\n"
            "• Add each rival’s **latest known funding raised** (publicly disclosed).\n"
            "• Briefly state **how they are most similar** and **how they differ** from the subject company.\n"
            "• Minimum 3 competitors if data is available; otherwise mark “Not publicly available”.\n\n"

            "Finally, include **2‑3 Tactical Recommendations** under *Competitive Action Items*.\n\n"

            "### **Section 2: Market Opportunity & Competitive Landscape** {{#section-2:-market-opportunity-&-competitive-landscape}}\n\n"

            "#### Market Overview {{#market-overview}}\n"
            "Concise, stage‑appropriate overview of problem, target users, and structural trends.\n\n"

            "#### Market Size & Growth Projections {{#market-size-&-growth-projections:}}\n"
            "- **Total Addressable Market (TAM):**\n"
            "- **Annual Growth Rate:**\n"
            "- **Adoption / Retention Trends:** _(note if long‑term retention is critical)_\n\n"

            "#### Competitive Positioning {{#competitive-positioning}}\n"
            "Summarise the company’s core advantages vs rivals, calibrated to {funding_stage}.\n\n"

            "##### Competitive Landscape {{#competitive-landscape}}\n"
            "| Competitor | Latest Funding ($) | Market Focus | Similarities | Key Strengths | Differences / Gaps |\n"
            "| ---------- | ------------------ | ------------ | ------------ | ------------- | ------------------ |\n"
            "|            |                    |              |              |               |                    |\n\n"

            "##### Competitive Action Items {{#competitive-action-items}}\n"
            "- **Action 1:**\n"
            "- **Action 2:**\n"
            "- **Action 3:** _(optional)_\n\n"

            "#### Key Market Takeaways {{#key-market-takeaways:}}\n"
            "- Bullet summary of the most important insights (size, growth, competition, retention cues).\n\n"

            "##### Challenges & Expansion Opportunities {{#challenges-&-expansion-opportunities}}\n"
            "###### Challenges {{#challenges:}}\n"
            "- Regulatory hurdles, competitive barriers, retention risks, etc.\n\n"
            "###### Opportunities for Market Expansion {{#opportunities-for-market-expansion:}}\n"
            "✅ Adjacent verticals / geographies to pursue post‑traction.\n\n"

            "#### Market Fit Assessment {{#market-fit-assessment}}\n"
            "| Market Factor | Status* | Evidence (1 sentence) |\n"
            "| ------------- | ------- | --------------------- |\n"
            "| Problem–Solution Fit | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Competitive Intensity | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Regulatory Complexity | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| Customer Retention Dynamics | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n\n"

            "### Instructions\n"
            "1. Output **valid Markdown only** – keep every heading & anchor unchanged.\n"
            "2. Populate competitor grid with funding amounts & similarity/difference notes; mark as *Not publicly available* if data is missing.\n"
            "3. Ratings must be evidence‑based; replace [🟢/🟡/🔴] accordingly.\n"
            "4. Use plain descriptors (Strong / Moderate / Weak) to justify each rating.\n"
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
            "| Risk Factor | Status* | Evidence (1 sentence) |\n"
            "| ----------- | ------- | --------------------- |\n"
            "| **Revenue Concentration Risk** | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Funding Transparency** | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Burn Rate & Cash Flow Stability** | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Profitability & Sustainability** | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n\n"
            "### Instructions\n"
            "1. Write your final answer in valid **Markdown**.\n"
            "2. For unknown data, you may use placeholders.\n"
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
            "| Category | Status* | Evidence (1 sentence) |\n"
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
    AI Agent for **Section 5 – Leadership & Team**

    ► 2025‑06 revisions (based on reviewer feedback)
    ------------------------------------------------------------------
    1. Add a “Key Personnel Snapshot” table – names, pedigree, recent news, red‑flag notes.
    2. Insert a new subsection **Use of Funds vs Identified Gaps** to verify that the
       stated funding allocation actually closes the talent / capability gaps surfaced in
       this section.
    3. Maintain all original anchors so the downstream PDF compositor keeps working.
    """

    def __init__(self):
        prompt_template = (
            "You are an expert analyst drafting **Section 5: Leadership & Team** in **Markdown**.  "
            "Follow the exact heading / anchor framework below.\n\n"

            "**Company:** {founder_company}\n"
            "Retrieved Context:\n{retrieved_context}\n\n"

            "## Your Task\n"
            "• Populate every table cell with evidence‑based detail.  Use *Not publicly available* where data is missing.\n"
            "• In “Key Personnel Snapshot” add **names** of all disclosed execs or key hires plus any notable advisors.  \n"
            "  – Column ‘Recent News / Media’ should cite noteworthy press (funding rounds, awards, controversies).  \n"
            "  – Column ‘Concerns / Red Flags’ flags lawsuits, departures, reputation risks that may hurt investability.\n"
            "• In “Use of Funds vs Identified Gaps” analyse whether the stated raise (see Section 3) addresses gaps "
            "found in leadership, hiring or compliance.\n"
            "• Replace every [🟢/🟡/🔴] with the correct colour rating and one‑word descriptor (Strong 🟢 etc.).\n\n"

            "### **Section 5: Leadership & Team** {{#section-5:-leadership-&-team}}\n\n"

            "#### **Leadership Expertise & Strategic Decision-Making** {{#leadership-expertise-&-strategic-decision-making}}\n"
            "Leadership Expertise & Strategic Decision-Making\n\n"
            "| Leadership Role | Experience & Contributions | Identified Gaps |\n"
            "| ----- | ----- | ----- |\n"
            "| **Co‑Founder & CEO** |  |  |\n"
            "| **Co‑Founder & Business Development Lead** |  |  |\n"
            "| **Sales & Business Development Team** |  |  |\n"
            "| **Engineering & Product Development** |  |  |\n\n"

            "##### Key Personnel Snapshot {{#key-personnel-snapshot}}\n"
            "| Name | Title / Role | Notable Pedigree | Recent News / Media | Concerns / Red Flags |\n"
            "| ---- | ------------ | ---------------- | ------------------- | --------------------- |\n"
            "|      |              |                  |                     |                       |\n\n"

            "✅ **Strengths:**  \n"
            "⚠ **Challenges:** \n\n"

            "#### **Organizational Structure & Growth Plan** {{#organizational-structure-&-growth-plan}}\n"
            "| Functional Area | Current Team Depth | Planned Expansion | Impact on Scalability |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **Product & Engineering** |  |  |  |\n"
            "| **Sales & Business Development** |  |  |  |\n"
            "| **Customer Success & Support** |  |  |  |\n\n"

            "#### **Strategic Hiring Roadmap** {{#strategic-hiring-roadmap}}\n"
            "| Role | Current Status | Planned Hiring Timeline | Impact |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **CTO / Senior Product Leader** |  |  |  |\n"
            "| **Outbound Sales & BD Expansion** |  |  |  |\n"
            "| **Customer Success & Ops Growth** |  |  |  |\n\n"

            "#### **Use of Funds vs Identified Gaps** {{#use-of-funds-vs-identified-gaps}}\n"
            "| Funding Allocation Area | Gap Addressed | Adequacy Rating [🟢/🟡/🔴] | Commentary |\n"
            "| ----------------------- | ------------- | --------------------------- | ----------- |\n"
            "| Talent / Key Hires |  |  |  |\n"
            "| Compliance / Governance |  |  |  |\n"
            "| GTM / Sales Enablement |  |  |  |\n\n"

            "#### **Leadership Stability & Investor Confidence** {{#leadership-stability-&-investor-confidence}}\n"
            "* **Investor View:**   \n"
            "* **Identified Risks:**   \n"
            "* **Mitigation Strategy:** \n\n"

            "#### **Leadership & Organizational Stability Assessment** {{#leadership-&-organizational-stability-assessment}}\n"
            "| Leadership Category | Status* | Evidence (1 sentence) |\n"
            "| ------------------- | ------- | --------------------- |\n"
            "| **Strategic Vision & Execution**            | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Technical Leadership Depth**             | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Sales & BD Scalability**                 | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Team Stability & Succession Planning**    | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n\n"

            "### Instructions\n"
            "1. Output valid **Markdown only**; do not alter anchors or heading levels.\n"
            "2. Fill all tables; use *Not publicly available* where appropriate.\n"
            "3. Every colour code must reflect evidence from `retrieved_context`.\n"
        )
        super().__init__(prompt_template)


# ---------------------------------------------------------------
# 6) Investor Fit, Exit Strategy & Funding Narrative
# ---------------------------------------------------------------
class InvestorFitAgent(BaseAIAgent):
    """
    AI Agent for **Section 6 – Investor Fit, Exit Strategy & Funding Narrative**

    2025‑06 update (review‑driven)
    ---------------------------------------------------------------
    • Clarifies that a “Weak” assessment = **High Risk** (explicitly
      labelled in the tables to avoid confusion).
    • Removes hard‑coded “FSM” references; now inserts a generic
      placeholder **Strategic {industry} Acquirers** so reports stay
      industry‑agnostic.
    • Adds a one‑line *Status Legend*.
    • Keeps every existing anchor so the downstream PDF renderer
      remains compatible.
    """

    def __init__(self):
        prompt_template = (
            "You are an expert venture analyst drafting **Section 6: Investor Fit, Exit Strategy & Funding Narrative** "
            "in **Markdown**.  Follow the fixed heading / anchor scaffold below.\n\n"

            "**Company:** {founder_company}\n"
            "**Industry:** {industry}\n"
            "Retrieved Context:\n{retrieved_context}\n\n"

            "## Your Task\n"
            "1. Populate each table cell with data grounded in the context; if not available, write “*Not publicly available*”.\n"
            "2. Use 🟢 Strong (= Low Risk / High Fit), 🟡 Moderate, 🔴 Weak (= High Risk / Low Fit).  \n"
            "3. *Weak = High risk* – make this explicit in the assessment row.\n"
            "4. Substitute `{industry}` into any placeholder that references strategic acquirers.\n"
            "5. Retain all anchors exactly.\n\n"

            "### **Section 6: Investor Fit, Exit Strategy & Funding Narrative** {{#section-6:-investor-fit,-exit-strategy-&-funding-narrative}}\n\n"

            "#### **Investor Profile & Strategic Alignment** {{#investor-profile-&-strategic-alignment}}\n"
            "Founder Company Investor Profile & Strategic Alignment\n\n"
            "**Ideal Investor Profile:**  \n"
            "✅ **Venture Capital (VC) Firms** – sector‑savvy funds comfortable with {industry} SaaS multiples.  \n"
            "✅ **Private Equity (PE) Funds** – growth‑stage buy‑out or minority stakes in tech‑enabled platforms.  \n"
            "✅ **Strategic {industry} Acquirers** – incumbents seeking product expansion or cross‑sell synergies.  \n\n"
            "⚠ **Investor Concerns:**\n"
            "- List 2‑3 major concerns (e.g., pre‑revenue risk, valuation premium, regulatory headwinds).\n\n"

            "#### **Exit Strategy Analysis** {{#exit-strategy-analysis}}\n"
            "| Exit Type | Viability | Potential Acquirers / Investors | Challenges |\n"
            "| ----- | ----- | ----- | ----- |\n"
            "| **M&A by Strategic {industry} Software Firms** |  |  |  |\n"
            "| **Private Equity (PE) Buy‑out / Roll‑up** |  |  |  |\n"
            "| **IPO as a Growth‑Stage SaaS** |  |  |  |\n\n"
            "✅ **Most Likely Exit:**  _state rationale_  \n"
            "⚠ **IPO Variability:**  _comment if applicable_\n\n"

            "#### **Current Funding Narrative & Investor Messaging** {{#current-funding-narrative-&-investor-messaging}}\n"
            "* **Total Funding Raised:**  \n"
            "* **Current Round:**  \n"
            "* **Valuation Transparency:**  \n\n"
            "| Funding Stage | Founder Company Status | Industry Benchmark |\n"
            "| ----- | ----- | ----- |\n"
            "| **Pre‑Seed → Seed** |  |  |\n"
            "| **Total Funding Raised** |  |  |\n"
            "| **Planned Raise** |  |  |\n"
            "| **Valuation Transparency** |  |  |\n\n"
            "✅ **Strengths:**  _bullet list_  \n"
            "⚠ **Challenges:** _bullet list_\n\n"

            "#### **Investor Messaging & Priorities** {{#investor-messaging-&-priorities}}\n"
            "* **High‑Growth SaaS Opportunity:**  \n"
            "* **Defensible Market Positioning:**  \n"
            "* **Exit Potential:**  \n\n"

            "#### **Investor Fit Assessment** {{#investor-fit-assessment}}\n"
            "| Investment Factor | Status* | Evidence (1 sentence) |\n"
            "| ----------------- | ------- | --------------------- |\n"
            "| **Scalability & ROI Potential**            | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Investor Sentiment & Market Trends**     | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Funding & Exit Strategy Clarity**        | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "| **Risk Profile for Investors** *(Weak = High Risk)* | [🟢/🟡/🔴] {{derive}} | {{evidence}} |\n"
            "\n"
            "_Status Legend: 🟢 Strong / Low Risk   🟡 Moderate   🔴 Weak / High Risk_\n\n"

            "### Instructions\n"
            "• Output valid **Markdown only**.  \n"
            "• Do **not** alter any anchor IDs or heading levels.  \n"
            "• Replace all status placeholders with the correct colour & descriptor based on evidence from the context.\n"
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
            "| Category | Status* | Evidence (1 sentence) |\n"
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
