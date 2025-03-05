import logging
import time
import os

from app.api.ai.agents import (
    ExecutiveSummaryAgent,            # Section 1: Executive Summary & Investment Rationale
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
    for each of the seven sections, in sequence.

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
                               to uploaded documents (Pitch Decks, Office docs), etc.

    Returns:
        dict: The final report content with all seven sections.
    """
    safe_context = {k: request_params.get(k) for k in request_params if k != "sensitive"}
    logger.info("Starting report generation with context: %s", safe_context)

    user_query = request_params.get("report_query", "Investment readiness analysis")
    endpoint_resource_name = os.getenv("VERTEX_ENDPOINT_RESOURCE_NAME", "")
    deployed_index_id = os.getenv("VERTEX_DEPLOYED_INDEX_ID", "")

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

    # Grab ephemeral pitch-deck text if present
    pitch_deck_text = request_params.get("pitch_deck_text", "")

    # Combine them
    ephemeral_context = ""
    if pitch_deck_text.strip():
        ephemeral_context += f"Pitch Deck Text:\n{pitch_deck_text}\n\n"
    if context_snippets.strip():
        ephemeral_context += f"{context_snippets}\n"

    # Initialize AI agents
    executive_summary_agent = ExecutiveSummaryAgent()
    market_opportunity_agent = MarketAnalysisAgent()
    financial_performance_agent = FinancialPerformanceAgent()
    gtm_strategy_agent = GoToMarketAgent()
    leadership_team_agent = LeadershipTeamAgent()
    investor_fit_agent = InvestorFitAgent()
    recommendations_agent = RecommendationsAgent()

    # Make a copy of request_params to hold the final context
    context = request_params.copy()
    # Insert ephemeral context
    context["retrieved_context"] = ephemeral_context

    # Generate each section with retry logic
    executive_summary_investment_rationale = generate_with_retry(
        executive_summary_agent,
        context,
        "Executive Summary & Investment Rationale"
    )
    context["executive_summary_investment_rationale"] = executive_summary_investment_rationale

    market_opportunity_competitive_landscape = generate_with_retry(
        market_opportunity_agent,
        context,
        "Market Opportunity & Competitive Landscape"
    )
    context["market_opportunity_competitive_landscape"] = market_opportunity_competitive_landscape

    financial_performance_investment_readiness = generate_with_retry(
        financial_performance_agent,
        context,
        "Financial Performance & Investment Readiness"
    )
    context["financial_performance_investment_readiness"] = financial_performance_investment_readiness

    go_to_market_strategy_customer_traction = generate_with_retry(
        gtm_strategy_agent,
        context,
        "Go-To-Market (GTM) Strategy & Customer Traction"
    )
    context["go_to_market_strategy_customer_traction"] = go_to_market_strategy_customer_traction

    leadership_team = generate_with_retry(
        leadership_team_agent,
        context,
        "Leadership & Team"
    )
    context["leadership_team"] = leadership_team

    investor_fit_exit_strategy_funding = generate_with_retry(
        investor_fit_agent,
        context,
        "Investor Fit, Exit Strategy & Funding Narrative"
    )
    context["investor_fit_exit_strategy_funding"] = investor_fit_exit_strategy_funding

    final_recommendations_next_steps = generate_with_retry(
        recommendations_agent,
        context,
        "Final Recommendations & Next Steps"
    )
    context["final_recommendations_next_steps"] = final_recommendations_next_steps

    full_report = {
        "executive_summary_investment_rationale": executive_summary_investment_rationale,
        "market_opportunity_competitive_landscape": market_opportunity_competitive_landscape,
        "financial_performance_investment_readiness": financial_performance_investment_readiness,
        "go_to_market_strategy_customer_traction": go_to_market_strategy_customer_traction,
        "leadership_team": leadership_team,
        "investor_fit_exit_strategy_funding": investor_fit_exit_strategy_funding,
        "final_recommendations_next_steps": final_recommendations_next_steps,
    }

    # Simple status logging
    status_summary = {}
    for section_name, content in full_report.items():
        if "Error generating" in content:
            status_summary[section_name] = "failed"
        else:
            status_summary[section_name] = "generated"

    logger.info("Report generation completed. Section statuses: %s", status_summary)
    return full_report