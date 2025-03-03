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

    # 1) Log context (excluding sensitive fields)
    safe_context = {k: request_params.get(k) for k in request_params if k != "sensitive"}
    logger.info("Starting report generation with context: %s", safe_context)

    # (Optional) Vector retrieval for context, if Vertex AI Matching Engine is configured
    user_query = request_params.get("report_query", "Investment readiness analysis")
    endpoint_resource_name = os.getenv("VERTEX_ENDPOINT_RESOURCE_NAME", "")
    deployed_index_id = os.getenv("VERTEX_DEPLOYED_INDEX_ID", "")  # e.g. 'my_vector_index_deployed'
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

    # 2) Initialize AI agents for each Tier-2 section
    executive_summary_agent = ExecutiveSummaryAgent()      # Section 1
    market_opportunity_agent = MarketAnalysisAgent()       # Section 2
    financial_performance_agent = FinancialPerformanceAgent()  # Section 3
    gtm_strategy_agent = GoToMarketAgent()                 # Section 4
    leadership_team_agent = LeadershipTeamAgent()          # Section 5
    investor_fit_agent = InvestorFitAgent()                # Section 6
    recommendations_agent = RecommendationsAgent()         # Section 7

    # 3) Copy request_params to a working context
    context = request_params.copy()
    # Insert the retrieved context into the `context` dictionary
    context["retrieved_context"] = context_snippets

    # 4) Generate each section with retry logic
    # 1) Executive Summary & Investment Rationale
    executive_summary_investment_rationale = generate_with_retry(
        executive_summary_agent,
        context,
        "Executive Summary & Investment Rationale"
    )
    context["executive_summary_investment_rationale"] = executive_summary_investment_rationale

    # 2) Market Opportunity & Competitive Landscape
    market_opportunity_competitive_landscape = generate_with_retry(
        market_opportunity_agent,
        context,
        "Market Opportunity & Competitive Landscape"
    )
    context["market_opportunity_competitive_landscape"] = market_opportunity_competitive_landscape

    # 3) Financial Performance & Investment Readiness
    financial_performance_investment_readiness = generate_with_retry(
        financial_performance_agent,
        context,
        "Financial Performance & Investment Readiness"
    )
    context["financial_performance_investment_readiness"] = financial_performance_investment_readiness

    # 4) Go-To-Market (GTM) Strategy & Customer Traction
    go_to_market_strategy_customer_traction = generate_with_retry(
        gtm_strategy_agent,
        context,
        "Go-To-Market (GTM) Strategy & Customer Traction"
    )
    context["go_to_market_strategy_customer_traction"] = go_to_market_strategy_customer_traction

    # 5) Leadership & Team
    leadership_team = generate_with_retry(
        leadership_team_agent,
        context,
        "Leadership & Team"
    )
    context["leadership_team"] = leadership_team

    # 6) Investor Fit, Exit Strategy & Funding Narrative
    investor_fit_exit_strategy_funding = generate_with_retry(
        investor_fit_agent,
        context,
        "Investor Fit, Exit Strategy & Funding Narrative"
    )
    context["investor_fit_exit_strategy_funding"] = investor_fit_exit_strategy_funding

    # 7) Final Recommendations & Next Steps
    final_recommendations_next_steps = generate_with_retry(
        recommendations_agent,
        context,
        "Final Recommendations & Next Steps"
    )
    context["final_recommendations_next_steps"] = final_recommendations_next_steps

    # 5) Construct the final report dict
    full_report = {
        "executive_summary_investment_rationale": executive_summary_investment_rationale,
        "market_opportunity_competitive_landscape": market_opportunity_competitive_landscape,
        "financial_performance_investment_readiness": financial_performance_investment_readiness,
        "go_to_market_strategy_customer_traction": go_to_market_strategy_customer_traction,
        "leadership_team": leadership_team,
        "investor_fit_exit_strategy_funding": investor_fit_exit_strategy_funding,
        "final_recommendations_next_steps": final_recommendations_next_steps,
    }

    # 6) Log status of each section (simple pass/fail check)
    status_summary = {}
    for section_name, content in full_report.items():
        if "Error generating" in content:
            status_summary[section_name] = "failed"
        else:
            status_summary[section_name] = "generated"

    logger.info("Report generation completed. Section statuses: %s", status_summary)

    return full_report
