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

    market_opportunity_competitive_landscape = generate_with_retry(
        market_opportunity_agent,
        section_context,
        "Market Opportunity & Competitive Landscape"
    )

    financial_performance_investment_readiness = generate_with_retry(
        financial_performance_agent,
        section_context,
        "Financial Performance & Investment Readiness"
    )

    go_to_market_strategy_customer_traction = generate_with_retry(
        gtm_strategy_agent,
        section_context,
        "Go-To-Market (GTM) Strategy & Customer Traction"
    )

    leadership_team = generate_with_retry(
        leadership_team_agent,
        section_context,
        "Leadership & Team"
    )

    investor_fit_exit_strategy_funding = generate_with_retry(
        investor_fit_agent,
        section_context,
        "Investor Fit, Exit Strategy & Funding Narrative"
    )

    final_recommendations_next_steps = generate_with_retry(
        recommendations_agent,
        section_context,
        "Final Recommendations & Next Steps"
    )

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
