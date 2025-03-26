import logging
import time
import os

from app.api.ai.agents import (
    ResearcherAgent,                 # Do research first
    ExecutiveSummaryAgent,           # Section 1: Executive Summary & Investment Rationale
    MarketAnalysisAgent,             # Section 2: Market Opportunity & Competitive Landscape
    FinancialPerformanceAgent,       # Section 3: Financial Performance & Investment Readiness
    GoToMarketAgent,                 # Section 4: Go-To-Market (GTM) Strategy & Customer Traction
    LeadershipTeamAgent,             # Section 5: Leadership & Team
    InvestorFitAgent,                # Section 6: Investor Fit, Exit Strategy & Funding Narrative
    RecommendationsAgent             # Section 7: Final Recommendations & Next Steps
)

from app.matching_engine.retrieval_utils import (
    retrieve_relevant_chunks,
    build_context_from_matches
)

logger = logging.getLogger(__name__)

def generate_with_retry(agent, context: dict, section_name: str, max_attempts: int = 3, delay: int = 2) -> str:
    """
    Attempt to generate a report section with retries.
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            logger.info("Attempt %s for generating '%s' section.", attempt + 1, section_name)
            result = agent.generate_section(context)
            logger.info("'%s' section generated successfully on attempt %s.", section_name, attempt + 1)
            return result
        except Exception as e:
            attempt += 1
            logger.error("Attempt %s failed for '%s' section: %s", attempt, section_name, str(e), exc_info=True)
            if attempt < max_attempts:
                logger.info("Retrying '%s' section generation in %s seconds...", section_name, delay)
                time.sleep(delay)
    logger.error("All %s attempts failed for '%s' section. Marking as failed.", max_attempts, section_name)
    return f"Error generating {section_name}."

def generate_report(request_params: dict) -> dict:
    """
    Generate a full Tier-2-based investment readiness report by calling AI agents
    in a specific order:
      1. Research Agent first (to gather external context).
      2. Sections 2–7 (Market, Financial, GTM, Leadership, Investor Fit, Recommendations).
      3. Section 1 (Executive Summary) last, referencing the other sections' output.

    The final naming and subheadings reflect the end-product structure:
      1) Executive Summary & Investment Rationale
      2) Market Opportunity & Competitive Landscape
      3) Financial Performance & Investment Readiness
      4) Go-To-Market (GTM) Strategy & Customer Traction
      5) Leadership & Team
      6) Investor Fit, Exit Strategy & Funding Narrative
      7) Final Recommendations & Next Steps

    Args:
        request_params (dict): Contains context, parameters, and optionally references
                               to uploaded docs (Pitch Decks, etc.).

    Returns:
        dict: The final report content with all seven sections.
    """
    safe_context = {k: request_params.get(k) for k in request_params if k != "sensitive"}
    logger.info("Starting report generation with context: %s", safe_context)

    # Gather any user query and environment for retrieval
    user_query = request_params.get("report_query", "Investment readiness analysis")
    endpoint_resource_name = os.getenv("VERTEX_ENDPOINT_RESOURCE_NAME", "")
    deployed_index_id = os.getenv("VERTEX_DEPLOYED_INDEX_ID", "")

    # Attempt to retrieve context from vector search
    if endpoint_resource_name and deployed_index_id:
        top_matches = retrieve_relevant_chunks(
            query_text=user_query,
            endpoint_resource_name=endpoint_resource_name,
            deployed_index_id=deployed_index_id,
            top_k=5
        )
        context_snippets = build_context_from_matches(top_matches)
    else:
        logger.warning("VERTEX_ENDPOINT_RESOURCE_NAME or VERTEX_DEPLOYED_INDEX_ID is not set. Skipping retrieval.")
        context_snippets = ""

    # Gather pitch-deck text if present
    pitch_deck_text = request_params.get("pitch_deck_text", "").strip()

    # Combine them into ephemeral_context for the ResearcherAgent
    ephemeral_context = ""
    if pitch_deck_text:
        ephemeral_context += f"Pitch Deck Text:\n{pitch_deck_text}\n\n"
    if context_snippets.strip():
        ephemeral_context += f"{context_snippets}\n"
    ephemeral_context += f"""You are given detailed context about startup stages and fundraising (the “GetFresh Maturity Model”), aggregated market data from “Carta State of Startups 2024,” and founder equity trends from the “Founder Ownership Report 2025.” Below is a pitch deck outline and relevant details for a hypothetical startup. Please provide a thorough analysis and feedback, referencing the maturity milestones, funding data, and ownership dynamics where appropriate. Identify any red flags, highlight strengths, and suggest how the startup could optimize its approach. Assume the audience is prospective investors and seasoned startup advisors.
    
    GetFresh Ventures Maturity Model v1 Draft - November 2024

    GetFresh Ventures
    Maturity Model
    Formation  Validation  Growth  Maturity

    Growth Stage  Concept  MVP  Growth  Scale
    Fundraising Stage  Ideation  Friends & Family  Pre-Seed  Seed  Seed+  Series A  Series B
    Readiness Dimensions  Dimensional Sub-Layer

    Targeted Input Maturity for GetFresh Portfolio

    Objective
    • Conceptual clarity on problem-solution alignment.
    • Validate product-market fit through early user feedback.
    • Build early traction and secure consistent revenue.
    • Strengthen traction, refine product features, and secure scalable growth channels.
    • Scale operations and achieve broader market penetration.
    • Expand market reach with operational efficiency, prepare for potential exit strategies.
    • Expand market reach with operational efficiency, focus on brand loyalty, and prepare for strategic exit options such as acquisition or IPO.

    Capital Investment Strategy
    • Seed funding or personal capital for MVP and testing.
    • Friends and family or angel funding for prototype, early validation.
    • Market validation funding, expanding product-market fit and revenue.
    • Scaling acquisition, marketing, and customer success efforts.
    • High growth-focused funding, expansion into new markets, partnerships.
    • Preparation for M&A, global scaling, or IPO readiness; funding for strategic growth.
    • Significant capital infusion directed at global expansion, new market entry, strategic partnerships, or infrastructure enhancements to support scalability and high operational capacity in preparation for exit strategies.

    Revenue
    • Pre-revenue.
    • Under $250K.
    • $250K - $2M.
    • $2M - $5M.
    • $5M - $25M.
    • $25M+ preparing for acquisition or strategic partnership.
    • $50-100M

    Team

    Team Size
    • 1-2 (founders).
    • 2-3 early team members in core roles.
    • 3-10, including sales, product, and customer support roles.
    • 11-15, with emerging leadership roles in sales and customer success.
    • 16-25+, dedicated team across all core functions.
    • 25+, fully structured with specialized department heads.
    • 25-50+, with fully structured departments and specialized functional heads in sales, marketing, customer success, finance, and operations.

    Team Composition
    • Founders only, potentially supported by advisors or consultants.
    • Initial team hires in product, tech lead, or early sales roles.
    • Core team with roles in sales, product, customer success, and early management emerging.
    • Expanded team covering customer success, sales, and marketing; emerging department heads.
    • Established management across functions, including finance, marketing, and operations.
    • Fully developed leadership team with specialized functional heads across departments.
    • Fully developed leadership team with specialized heads for each department (e.g., data science, business development, and compliance) and cross-functional project managers.

    Market Validation

    Understanding Mission-Critical Problem
    • Identify core problem areas and create initial hypotheses based on assumptions. Begin basic market research to understand possible customer pain points.
    • Refine understanding of the problem through personal networks. Initial insights are gathered to improve problem definition and solution scope.
    • Early adopters provide feedback on the MVP, validating the problem’s significance. Data collection processes begin, focusing on relevant insights.
    • Strong, consistent feedback from customers reinforces the product-market fit. Automated data collection and analysis start to build insights for scaling.
    • Problem validation expands as more customer segments engage. The solution’s applicability across broader markets is tested, with scalable insights derived from data.
    • Recognized solution for critical problems. Customer traction and market acceptance increase. AI integration begins to enhance solution value and insights.
    • Entrenched product-market fit with high customer loyalty and preference across primary and secondary markets.

    Captivated Audience
    • Develop hypotheses about target audience problems and potential solutions. Test ideas informally to gauge early interest.
    • Engage potential early adopters from personal networks for preliminary feedback. Build initial audience insights.
    • Engage a broader group of early adopters, developing more structured data collection to validate the core audience and its needs.
    • Expand outreach to validate more segments. The captivated audience broadens, validating solution fit across various customer types.
    • Scale the solution to a wider audience, refining the solution based on audience data and feedback. Audience personas are well-defined and actively engaged.
    • Strengthen relationships with a broad user base, reinforcing customer engagement and brand loyalty.
    • Entrenched product-market fit with high customer loyalty and preference across primary and secondary markets. Expand and diversify target audience while deepening relationships with core markets. Engage new audiences as the market leader.

    Holistic Solution Design
    • Conceptualize a solution that seems like a no-brainer, focusing on clear benefits to address customer pain points.
    • Develop a prototype that embodies the no-brainer solution approach, showing potential clear benefits to the problem.
    • MVP is positioned as a clear, no-brainer solution for initial users, with a simplified design focusing on solving the key problem areas.
    • Refine the MVP based on feedback, enhancing it to become a compelling choice for customers. Address user feedback for improved UX and usability.
    • Introduce advanced features while maintaining the simplicity of the core solution. Ensure each feature adds tangible value.
    • Scale the product with robust feature sets that remain focused on customer needs. The product is highly reliable, scalable, and indispensable for users.
    • Comprehensive product suite, with feature sets tailored to different customer segments for enhanced scalability and utility. Continuous innovation and product refinement. Solution evolves to anticipate market needs and maintain its no-brainer status.

    Product Development

    Product Evolution
    • Concept phase with potential features and core functions in planning stage.
    • Basic MVP addressing primary pain points for customer problem validation.
    • MVP refined with feedback, improved stability, and tested readiness for expanded adoption.
    • MVP includes advanced features tailored to the core audience, fully functional for scaled use.
    • Fully-functional product with scalability in mind; feature expansion for broader appeal.
    • Mature product suite, optimized for various customer segments; high reliability and availability. Focusing on advocacy and growth from an existing base.

    Ease of Use
    • Minimal learning curve envisioned, with ease-of-use features planned to lower the barrier to entry.
    • Initial ease-of-use testing is conducted with early adopters. Prototype is designed to be intuitive and easy to navigate.
    • MVP has friction points eliminated, allowing easy adoption. User guidance and basic support are provided.
    • Continuous improvements are made to simplify the product and reduce the need for intensive user training.
    • Easy integration of new features and updates. Support for customization and onboarding is enhanced to cater to different users.
    • Product simplicity is maintained while catering to larger audiences. Onboarding is seamless, and product is easy to learn.
    • Despite product complexity, ease of use is a priority. Advanced features are accessible without steep learning curves.

    Solution UX
    • Early concepts focus on a user-friendly design. UX considerations are high-level, aiming for simplicity and intuitiveness.
    • Basic UX implemented in the prototype, focusing on ease of use for early adopters. Initial user interactions guide UX design.
    • Highly intuitive UX designed to minimize friction for early adopters, with key usability features incorporated in the MVP.
    • UX enhancements based on direct user feedback, improving navigation, speed, and responsiveness.
    • UX is refined for scalability, with more options for customization and seamless user experiences across larger groups.
    • High standard UX is maintained, even as advanced features are added. The product remains accessible and user-friendly.
    • The UX is optimized for high performance, even as product complexity grows. Continues to be intuitive despite numerous features.

    Customer Time to Gratification
    • Quick wins and early benefits are envisioned to capture initial interest.
    • Early adopters can see basic benefits quickly, incentivizing continued use and feedback.
    • MVP delivers quick, tangible benefits, with initial success stories to motivate other users.
    • Faster time to value as product maturity improves. Customer success stories showcase rapid impact.
    • Accelerated benefit delivery, with advanced features providing faster and deeper value to end-users.
    • Significant benefits and results are seen quickly, supporting long-term customer retention and engagement.
    • Immediate and substantial value for users. Product is integral to customer operations, with proven ROI.

    Marketing

    Marketing Strategy
    • Minimal marketing; primarily founder-driven, focused on early awareness and networking.
    • Small-scale social media, early content marketing, basic email outreach for brand awareness.
    • Multi-channel marketing with content, social media, and SEO strategies; focus on early brand-building.
    • Digital marketing scaled with content, PPC, and partnerships; beginning brand-focused campaigns.
    • Integrated marketing across inbound, outbound, and paid channels; brand building in primary markets.
    • Sophisticated marketing with dedicated teams for global reach; brand-building and thought leadership focus.
    • Sophisticated, data-driven marketing with dedicated teams for content, demand generation, and thought leadership; global campaigns tailored by market segment.

    Market Positioning
    • Exploring different positioning ideas, gaining broad understanding of potential customer value.
    • Targeted positioning based on early feedback; identifying unique selling points (USPs) in market.
    • Positioning clear and aimed at niche market; refined messaging to match ICP expectations.
    • Strong positioning with high market recognition in niche; strategic differentiation from competitors.
    • Recognizable brand in defined market segment; positioning resonates deeply with target audience.
    • High market recognition with strong brand authority in multiple segments; thought leadership established.
    • High brand recognition in multiple segments, with thought leadership and brand differentiation well-established to support long-term market leadership.

    Customer Acquisition Channels
    • Founder’s network, informal outreach for initial market awareness.
    • Direct outreach with social media, early pilot projects, or partnerships.
    • Multi-channel acquisition through organic and limited paid channels.
    • Scalable acquisition through paid social, PPC, affiliate marketing.
    • Optimized acquisition across CAC, LTV, with targeted digital and offline strategies.
    • Diversified channels with high-ROI focus, including international and industry partnerships.
    • Fully optimized acquisition channels with high-ROI strategies, including partnerships, digital ads, PPC, affiliate marketing, and international outreach.

    Sales

    Sales Engine
    • Informal outreach by founders for early market interest; learning-focused conversations.
    • Direct outreach for product testing, consultative selling, and data gathering.
    • Structured sales process, repeatable framework for lead follow-ups; early CRM tool implementation.
    • Sales is formalized with team members, lead tracking, and pilot automation for outreach scaling.
    • Fully structured sales funnel; teams focus on segment or territory with clear targets.
    • Optimized, segmented sales approach with CRM integration and specialized sales support roles.
    • Optimized and segmented sales approach, leveraging CRM integration, specialized account managers, and AI-based insights for efficient, high-value conversion.

    Pricing
    • Early thoughts on pricing, typically focused on affordability and value perception. Simple models or free trials considered.
    • Introductory models or discounts are explored to encourage early adoption. Feedback on pricing expectations is gathered.
    • Trial pricing or introductory offers are implemented to attract early adopters and establish willingness to pay.
    • Refined pricing strategy based on customer feedback and competitive analysis, balancing affordability with value.
    • Tiered pricing models are introduced to cater to diverse customer segments. Pricing becomes strategic.
    • Pricing is optimized for scalability, offering packages that cater to different user needs and budgets, with predictable revenue.
    • Sophisticated pricing models with options for large-scale customers and enterprises. Pricing strategies are designed for maximizing long-term revenue.

    Customer Success

    Strategy
    • Ad hoc support by founders; initial conversations for feedback collection only.
    • Basic onboarding and support for feedback; focus on validating core product functionality.
    • Standardized onboarding, structured processes for support and retention.
    • Customer success team established with proactive customer onboarding and NPS tracking.
    • Dedicated customer success team with emphasis on advocacy, renewal, and expansion.
    • Comprehensive success strategy, using predictive analytics and advocacy programs.
    • Comprehensive customer success program, proactive retention strategies, predictive analytics, and customer advocacy for continued revenue growth.

    Customer Journey
    • Minimal definition, reactive and direct responses to immediate needs.
    • Initial onboarding process defined; ad hoc support for early adopters.
    • Standardized onboarding, defined renewal journey, and basic support documentation.
    • Scaled journey with automated, consistent engagement at each customer touchpoint.
    • Comprehensive customer journey tracking; key engagement points are optimized for retention and growth.
    • Fully optimized journey that includes seamless handoff from sales, to onboarding, to account management.
    • Fully optimized, seamless journey from sales to onboarding to customer success; consistent engagement for high customer satisfaction and retention.

    Adoption Effort
    • Limited setup required, aiming for a low-effort adoption process in the future.
    • Minimal setup and integration for the prototype, ensuring early adopters can start quickly.
    • Onboarding is simplified, with guided tutorials and initial support to ensure smooth adoption for early users.
    • Comprehensive onboarding resources are created, including guides, videos, and support resources for easy adoption.
    • Adoption is streamlined with personalized onboarding options and proactive customer support for smooth transitions.
    • Exceptional support is provided, with tailored onboarding, ensuring high adoption rates and user satisfaction.
    • Large-scale onboarding resources and support ensure minimal friction, even for complex integrations.

    Success Metrics
    • Minimal feedback gathering, mainly qualitative data by founders.
    • Basic health metrics (early customer satisfaction, retention).
    • Standardized usage, retention, and growth metrics with consistent tracking.
    • Predictive metrics introduced, e.g., NPS and churn forecasting.
    • Proactive metrics driving retention and growth, including renewal rates and usage frequency.
    • Comprehensive metrics for predictive modeling, retention, and advocacy.
    • Comprehensive, predictive metrics on retention, expansion, and advocacy; monitoring NPS, renewal rates, and upsell rates to ensure customer satisfaction and long-term value.

    Financials

    Financial Planning
    • Basic budgeting focused on minimal costs and essential expenses only.
    • Preliminary budget for MVP completion and initial market validation milestones.
    • Budgeting includes basic revenue forecasting, expense planning, and early unit economics.
    • Financial modeling for growth, tracking metrics like CAC, LTV, and cash flow to ensure sustainability.
    • Advanced financial modeling with unit economics guiding revenue growth and profitability.
    • Mature financial planning, strategic funding allocation for global scaling, acquisition readiness.
    • Mature financial strategy with advanced unit economics, detailed revenue forecasting, and funding diversification aligned with acquisition or IPO preparation.

    Revenue Model
    • Non-existent or exploratory; experimenting with pricing ideas.
    • Basic revenue model with initial traction, based on subscription or simple pricing.
    • Refined revenue model based on feedback, with focus on retention and upsells.
    • Established pricing and revenue model; introducing tiered options or add-ons.
    • Revenue model optimized with predictable streams; focus on growth via upsells and add-ons.
    • Diverse revenue channels with maximized LTV and clear upselling, cross-selling strategies.
    • Diverse revenue streams with high-LTV customers, clear upselling and cross-selling strategies, and a strong focus on customer value maximization through targeted packages.

    Clarity on Unit Economics
    • Basic cost estimations, focused on survival needs.
    • Unit economics for acquisition cost (CAC) and early revenue projections.
    • Refined understanding of CAC, LTV, and early revenue management.
    • Detailed unit economics to drive growth and financial health.
    • Unit economics optimized for predictable revenue, profitability.
    • Fully optimized unit economics guiding financial strategy and high-growth planning.
    • Integrated, cross-functional workflows with predictive problem-solving processes to support high-quality customer and internal operations.

    Operations

    Technology & Infrastructure
    • Basic tech setup; often outsourced or bootstrap-focused.
    • Simple tech stack supporting MVP, core monitoring in place for reliability.
    • Scalable infrastructure with stable metrics and monitoring.
    • Redundant systems and expanded tech stack for reliability and user support.
    • Advanced infrastructure with high-capacity systems and proactive monitoring.
    • Highly reliable, globally scalable infrastructure with continuous monitoring and system optimization.
    • Highly reliable, globally scalable infrastructure with continuous monitoring, redundancy, and system optimization for large-scale operations.

    Compliance & Security
    • Minimal legal oversight; little or no compliance.
    • Basic legal documents (NDA, terms of service), GDPR compliance as applicable.
    • Compliance focus on industry standards, especially for customer data handling.
    • Full compliance, including certifications like SOC 2, ISO as necessary.
    • Dedicated legal or compliance role ensuring all regulatory standards are met.
    • Comprehensive compliance with advanced risk management and regulatory alignment for public readiness.
    • Advanced compliance with data protection, risk management, and alignment with public market or M&A standards, including SOC 2 and ISO certifications as needed.

    Workflow & Problem-solving Processes
    • Ad hoc, all priorities equal; informal problem-solving.
    • Early processes emerging, with some communication and prioritization.
    • Structured workflows for key issues, with communication channels defined.
    • Developed customer feedback loop with responsive product changes.
    • Cross-functional collaboration; feedback loops integrated across functions.
    • Integrated workflows with predictive solutions for both customer and internal processes.
    • Comprehensive, predictive metrics on retention, expansion, and advocacy; monitoring NPS, renewal rates, and upsell rates to ensure customer satisfaction and long-term value.

    Overview
    • Report Title: Carta State of Startups 2024
    • Data Source: Aggregated, anonymized insights from over 45,000 US startups (and related VC funds) that use Carta as their cap table/fund administration provider.
    • Key Topics Covered:
     – Funding context and cash‐raising trends
     – Use of SAFEs, convertible notes, and priced rounds
     – Valuation trends across seed, Series A, Series B, and later rounds
     – Dilution, liquidation preferences, and equity splits
     – Market dynamics including geographic distribution of capital and compensation
     – Venture fund and SPV performance metrics
     – Exit activity (shutdowns, IPOs, M&A, tender offers)
     – Team dynamics such as founding team composition and employee equity

    (​​
    )

    Funding Trends & Cash-Raising
    • Overall Investment:
     – 2024 saw more total investment than 2023, with US Carta startups raising significantly higher cash totals across all stages.
     – The report breaks down cash raised by round type: from pre-seed/SAFEs through priced rounds (Seed, Series A, B, C, D, E+).
     – AI-related companies are highlighted as receiving a major share of investment across stages.

    • Round Volume & Changes:
     – Data on the number of rounds raised (e.g., over 30,000 rounds in recent years) shows variability year-over-year.
     – Early-stage rounds (like SAFEs and convertible notes) have grown in number historically but face recent headwinds; early rounds are “harder” now despite overall cash increases.
     – Bridge rounds have receded somewhat in later stages, and downrounds have reappeared in 2023–2024.

    Funding Instruments & Valuation Metrics
    • SAFEs & Convertible Notes:
     – Nearly 90% of pre-priced rounds in Q3 were raised using SAFEs.
     – For a typical round, expect to require 5–15 SAFEs; the data even gives estimates on the number of investors needed based on round size.
     – Over 90% of SAFEs carry a valuation cap, with a growing preference for post-money SAFE structures.  – For larger convertible note rounds, valuation caps increased in Q3 as interest rates on these instruments fell alongside Fed rate cuts.

    • Valuations:
     – Seed Rounds: Median pre-money valuations and cash raised show that AI companies are favored—with seed valuations and round sizes trending upward.
     – Series A & B Rounds:
      – Median Series A pre-money valuations are higher for AI companies compared to non-AI peers.
      – Series B rounds also exhibit higher median valuations (with increases of up to +50% noted in some comparisons) and corresponding cash raised data.  – Graduation rates (the percentage of seed rounds that advance to Series A and beyond) have been declining over recent years.

    • Dilution & Equity:
     – In Series B/C rounds, median dilution has fallen in Q3.
     – The data includes detailed percentiles of equity sold to investors in primary rounds versus bridge rounds—with bridge rounds settling around about half the dilution of primary rounds.  – Companies that “sell less” per round are seen as experiencing less dilution overall.

    Market & Geographic Insights
    • Geographic Distribution of Investment:
     – A significant portion of total capital in the last 12 months has been concentrated in California—with the Bay Area maintaining an edge in early-stage startups.
     – The report ranks US metro areas (e.g., Bay Area, New York, Boston, Los Angeles, Austin, Miami) by total capital invested by stage (Seed+ Series A).
     – For AI-specific rounds, Bay Area companies continue to dominate the market.  – Detailed “fundraising profiles” are provided for key regions:   – San Francisco Bay Area: Highest total cash raised, with top sectors identified.   – New York Metro Area, Greater Los Angeles, Greater Boston, and Greater Austin: Each with their own sector breakdowns and trends.   – Miami: Noted for its growing share in the overall $126B in total fundraising, underscoring that venture ecosystems take time to mature.

    • Timing & Deal Flow:
     – Data on deals signed by month shows seasonal variations—e.g., January tends to have fewer rounds (likely due to fewer December negotiations).  – There is also an analysis on whether differences in round sizes across metros may be explained by variations in startup salaries.

    • Compensation Trends:
     – The report includes extensive data on startup compensation relative to San Francisco benchmarks, broken out by region (West, Northeast, South, Midwest).
     – Many West Coast metros pay near 100% of SF rates, while other regions vary (e.g., DC at ~93%, many Midwest areas showing strong gains toward SF rates).
     – These compensation differences are compared to round sizes in Series A SaaS rounds.

    Venture Fund & SPV Performance (Market Funding Ecosystem)
    • VC Fund Analysis:
     – A total of 1,803 US funds (vintage years 2017–2022) were analyzed.
     – Deployment data shows that for 2022 vintage funds, about 43% of capital was deployed after 24 months.  – IRR (Internal Rate of Return) performance by vintage year is detailed, with median IRRs for 2021 trailing those of earlier vintages.  – Smaller funds tend to have higher IRRs at the 90th percentile.

    • SPV Insights:
     – Analysis of 2,442 US SPVs indicates that capital is heavily concentrated in a small percentage of SPVs (with 30% of SPV capital in the top 3% of SPVs by size).
     – Management fee benchmarks, the basis for fee calculations, and trends in common stock investments by SPVs are provided.  – Median SPV IRR for recent vintages has remained below zero, and TVPI (Total Value to Paid-In) data is also detailed.

    Exit Environment & Market Dynamics
    • Exits & Shutdowns:
     – The report tracks startup shutdowns (bankruptcies/dissolutions) by quarter—with an observed uptick as funding conditions tightened.  – Specifically, 109 startups that raised $20M+ eventually closed, highlighting risks even at later stages.  – Technology IPOs have “all but dried up,” while M&A activity nears record highs (with Q3 2024 showing the most transacted tender value since Q1 2022).

    • Tender Offers & M&A:
     – There is data on tender offers completed by US companies on Carta, underscoring that M&A activity is currently the dominant exit mechanism in the market.

    This comprehensive extraction captures the critical aspects of the funding landscape—from capital raised and valuation trends to geographic market dynamics and exit activity. You can use this context to inform analyses on startup investibility and market trends.

    Founder Ownership Report 2025 – Overview
    Purpose & Scope:
    • Tracks startup founder ownership from idea to IPO using anonymized data from over 45,000 US startups incorporated from 2015 to 2024.
    • Focuses on how founding teams are structured, how equity is initially divided among co-founders, and how that ownership evolves as startups raise venture capital.

    Executive Summary
    • Starting Point: Every startup begins with an idea and a founding team that initially owns 100% of the equity.
    • Equity as a Strategic Resource: The report emphasizes the critical decision of how to split equity among co-founders, investors, employees, and other stakeholders—a choice that shapes long-term control and incentives.
    • Data Use: Uses first-of-its-kind anonymized data to shed light on the composition of founding teams, their equity splits, and the evolution of founder ownership over multiple fundraising rounds.

    Report Highlights
    Solo Founders on the Rise:
    • The percentage of startups with a solo founder has more than doubled over the past decade—from 17% in 2017 to 35% in 2024.
    • Despite their growing numbers, solo founders are less likely to secure VC funding (only 17% of VC-funded startups in 2024 are solo-led, compared to 35% overall).

    Equity Splits Trends:
    • Equal equity splits among co-founders are becoming more common. For two-founder teams, an even split increased from 31.5% in 2015 to 45.9% in 2024.
    • Three-founder teams also show a rising trend in equal splits—from 12.1% to 26.9% over the same period.

    Dilution Through Fundraising:
    • Founder ownership declines steeply as startups progress through funding rounds:
      – After a seed round, the median founding team holds 56.2% of equity.
      – At Series A, the median drops to 36.1%.
      – At Series B, it falls further to 23%.
    • There is wide variance—for example, at Series A, founding teams range from as little as 10.3% ownership (10th percentile) to as high as 59.6% (90th percentile).

    Founding Team Composition:
    • The trend toward solo founders is clear—rising from 17% in 2017 to 35% in 2024.
    • Larger teams (three, four, or five founders) have become less common, with 2024 reporting only 16% three-founder teams, 7% four-founder, and 4% five-founder teams.
    • Among startups that have raised VC capital in 2024, solo founders make up only 17%, indicating that multi-founder teams tend to perform better in fundraising.

    Industry Differences:
    • Startups in software/digital sectors (e.g., SaaS, Fintech, Healthtech) generally have smaller founding teams and retain higher ownership percentages compared to those in capital-intensive, physical product sectors (e.g., Energy, Hardware, Biotech).
    • For instance, in biotech, the split might be around 60%–40% for a two-founder team, while SaaS startups show a more balanced 52%–48% split.

    Equity Allocation Details:
    • Two-Founder Teams:
      – Median split is approximately 55% for the lead founder and 45% for the second founder.
      – In recent years, this gap has narrowed (e.g., a near 51–49 split in 2024).
    • Larger Teams:
      – Three-founder teams: Median splits are roughly 47%, 33%, and 16%.
      – Four-founder teams: Around 42%, 26%, 17%, and 9%.
      – Five-founder teams: Typically around 36%, 23%, 16%, 12%, and 8%.
    • Equal splits are more common in smaller teams and have become increasingly prevalent over the past 10 years.

    Impact of Additional Funding:
    • With each subsequent fundraising round, new investors join the cap table, diluting the founding team’s overall stake.
    • Examples of dilution patterns:
      – After a priced seed round, median founder ownership is 56.2%.
      – At Series A and Series B, the ownership declines further (to 36.1% and 23%, respectively).
    • This dilution is most pronounced at early stages and can vary widely depending on factors such as pre-seed financing (often via SAFEs or convertible notes) and bridge rounds.

    Investor vs. Founder Dynamics:
    • As fundraising progresses, investor ownership increases:
      – At seed rounds, outside investors own a median of about 32% of equity.
      – By Series A, investor ownership rises to around 50%, and at Series B, it reaches approximately 61.6%.
    • The employee option pool also expands, growing from a median of 11.8% at seed to about 17.9% at Series D.

    Valuation & Cash Raised Correlations:
    • Founding team ownership tends to be higher in companies that have raised less capital (e.g., under $5 million) and declines once a company raises at least $10 million—where investor ownership typically surpasses 50%.
    • Similarly, once a startup reaches a post-money valuation between $50 million and $100 million, investor ownership begins to exceed 50%, increasing further with higher valuations.

    Lead Founder Focus:
    • The share retained by the lead founder (often the CEO) is particularly sensitive to team size.
    • Solo founders tend to retain more than a third of the business after Series A, whereas in three-person teams, the lead’s share can be less than 20%.
    • Over time, differentials between the lead and other co-founders narrow, partly due to equity refreshes when co-founders exit.

    Methodology
    • Dataset: Anonymized data from over 45,000 US startups incorporated between 2015 and 2024 using Carta.
    • Founder Definition: An individual is considered a founder if the company is US-incorporated, the individual holds at least 5% equity before any venture funding, and the company has no more than five founders (companies with more than five founders are excluded).
    • Scope: Analysis of initial equity splits and changes in founder ownership through key venture rounds (seed through Series D), with additional breakdowns by industry and total cash raised.

    Context for Funding Landscape & Market Analysis
    • Link to Funding: The report shows that as startups raise capital, founder ownership is diluted—this dynamic is critical for understanding control and decision-making power in startups.
    • Market Impact: Differences in founder team composition, equity splits, and dilution patterns across industries affect how startups position themselves in the market. For instance, higher founder retention in digital sectors versus more dilution in capital-intensive physical sectors can influence strategic choices and investor attractiveness.
    • Investor Dynamics: Shifts in ownership percentages between founders, investors, and employees help explain market trends in valuations and fundraising success, providing insights into the broader funding landscape.
    • Strategic Implications: This data informs both founders and investors about typical equity outcomes at each stage, influencing negotiations and long-term planning.

    Core Problem and Market Opportunity

    A concise description of the problem the startup is solving and why it matters.
    The size of the addressable market (TAM/SAM/SOM) and any market growth rates if available.
    Product/Technology Overview

    Clear explanation of what the product or service is, how it solves the problem, and why it’s unique.
    Any key differentiators or technological breakthroughs.
    Business Model & Revenue Streams

    How does the startup plan to make money? E.g., subscriptions, transaction fees, SaaS licensing, marketplace commissions, B2B enterprise deals, etc.
    Pricing structure or how revenues scale over time.
    Traction & Key Metrics

    Current user/customer numbers, monthly/annual growth rates, retention (churn), revenue run rate, or other relevant metrics (e.g., LTV, CAC).
    Any notable partnerships, pilot customers, or major brand references that validate the product.
    Go-to-Market Strategy

    How they plan to acquire customers (channels, marketing tactics, sales strategy).
    Unit economics around cost of acquisition (CAC) vs. lifetime value (LTV) if known.
    Competitive Landscape

    List major competitors or alternative solutions in the market.
    Summarize how this startup’s offering is better, cheaper, faster, or more innovative.
    Team Background

    Founders’ relevant expertise, prior startups, domain experience.
    Key hires or advisors who add credibility (especially in regulated or specialized industries).
    Financial Projections

    Revenue forecasts, cost breakdown, runway, and burn rate.
    Capital required to reach specific milestones or break-even points.
    Fundraising Needs

    The funding ask: how much they are looking to raise, the funding stage (pre-seed, seed, Series A, etc.).
    Use of funds: budget allocation (product development, hiring, marketing, expansion).
    Risks & Mitigations

    Known risks (technical, regulatory, market adoption) and how the startup intends to mitigate them.
    Exit Strategy (If relevant for investor audiences)
    Potential M&A or IPO path, timing, or industries/companies that might acquire them in the future."""

    # ----------------------------------------------------------------------------
    # Step 1: ResearcherAgent -> gather research details & incorporate them
    # ----------------------------------------------------------------------------
    researcher_agent = ResearcherAgent()
    # We pass in a minimal context about the company, plus ephemeral_context:
    researcher_input = {
        "company_name": request_params.get("company", "Unknown Company"),
        "industry": request_params.get("industry", "General Industry"),
        "retrieved_context": ephemeral_context
    }
    try:
        research_output = researcher_agent.gather_research(researcher_input)
        # Append the research findings to ephemeral_context
        ephemeral_context += f"\nRESEARCHER FINDINGS:\n{research_output}\n"
    except Exception as e:
        logger.error("Research agent failed: %s", str(e), exc_info=True)
        # We'll continue, but ephemeral_context might be incomplete
        ephemeral_context += "\n[Warning: ResearcherAgent failed to gather additional data.]\n"

    # ----------------------------------------------------------------------------
    # Step 2: Generate Sections 2–7 using the consolidated ephemeral_context
    # ----------------------------------------------------------------------------
    market_opportunity_agent = MarketAnalysisAgent()
    financial_performance_agent = FinancialPerformanceAgent()
    gtm_strategy_agent = GoToMarketAgent()
    leadership_team_agent = LeadershipTeamAgent()
    investor_fit_agent = InvestorFitAgent()
    recommendations_agent = RecommendationsAgent()

    # Shared context for these sections
    section_context = request_params.copy()
    section_context["retrieved_context"] = ephemeral_context
    time.sleep(90)

    market_opportunity_competitive_landscape = generate_with_retry(
        market_opportunity_agent,
        section_context,
        "Market Opportunity & Competitive Landscape"
    )
    time.sleep(90)

    financial_performance_investment_readiness = generate_with_retry(
        financial_performance_agent,
        section_context,
        "Financial Performance & Investment Readiness"
    )
    time.sleep(90)

    go_to_market_strategy_customer_traction = generate_with_retry(
        gtm_strategy_agent,
        section_context,
        "Go-To-Market (GTM) Strategy & Customer Traction"
    )
    time.sleep(90)

    leadership_team = generate_with_retry(
        leadership_team_agent,
        section_context,
        "Leadership & Team"
    )
    time.sleep(90)

    investor_fit_exit_strategy_funding = generate_with_retry(
        investor_fit_agent,
        section_context,
        "Investor Fit, Exit Strategy & Funding Narrative"
    )
    time.sleep(90)

    final_recommendations_next_steps = generate_with_retry(
        recommendations_agent,
        section_context,
        "Final Recommendations & Next Steps"
    )
    time.sleep(90)

    # ----------------------------------------------------------------------------
    # Step 3: Generate the Executive Summary LAST, referencing *all other* sections
    # ----------------------------------------------------------------------------
    # The user wants the Executive Summary to rely on the texts produced by sections 2–7,
    # not on the original pitch deck or researcher context. Let's compile the final texts:
    summary_context = request_params.copy()
    summary_context["retrieved_context"] = (
        f"SECTION 2: Market Opportunity\n{market_opportunity_competitive_landscape}\n\n"
        f"SECTION 3: Financial Performance\n{financial_performance_investment_readiness}\n\n"
        f"SECTION 4: Go-To-Market Strategy\n{go_to_market_strategy_customer_traction}\n\n"
        f"SECTION 5: Leadership & Team\n{leadership_team}\n\n"
        f"SECTION 6: Investor Fit\n{investor_fit_exit_strategy_funding}\n\n"
        f"SECTION 7: Final Recommendations\n{final_recommendations_next_steps}\n"
    )

    summary_context["founder_name"] = request_params.get("founder_name", "Unknown Founder")
    summary_context["company_type"] = request_params.get("company_type", "Unknown Type")
    summary_context["company_description"] = request_params.get("company_description", "Unknown Offering")

    executive_summary_agent = ExecutiveSummaryAgent()
    executive_summary_investment_rationale = generate_with_retry(
        executive_summary_agent,
        summary_context,
        "Executive Summary & Investment Rationale"
    )

    # ----------------------------------------------------------------------------
    # Build and return the final report dict
    # ----------------------------------------------------------------------------
    full_report = {
        "executive_summary_investment_rationale": executive_summary_investment_rationale,
        "market_opportunity_competitive_landscape": market_opportunity_competitive_landscape,
        "financial_performance_investment_readiness": financial_performance_investment_readiness,
        "go_to_market_strategy_customer_traction": go_to_market_strategy_customer_traction,
        "leadership_team": leadership_team,
        "investor_fit_exit_strategy_funding": investor_fit_exit_strategy_funding,
        "final_recommendations_next_steps": final_recommendations_next_steps
    }

    # Log statuses
    status_summary = {}
    for section_name, content in full_report.items():
        if "Error generating" in content:
            status_summary[section_name] = "failed"
        else:
            status_summary[section_name] = "generated"

    logger.info("Report generation completed. Section statuses: %s", status_summary)
    return full_report
