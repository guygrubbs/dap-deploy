import logging
import time
from app.ai.agents import ExecutiveSummaryAgent, MarketAnalysisAgent, RecommendationsAgent

logger = logging.getLogger(__name__)

def generate_with_retry(agent, context: dict, section_name: str, max_attempts: int = 3, delay: int = 2) -> str:
    """
    Attempt to generate a report section with retries.

    Args:
        agent: An AI agent instance with a generate_section method.
        context (dict): A dictionary containing context parameters for report generation.
        section_name (str): The name of the section being generated (for logging purposes).
        max_attempts (int): Maximum number of attempts to try generating the section.
        delay (int): Delay in seconds between retry attempts.

    Returns:
        str: The generated section text, or an error message if all attempts fail.
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            logger.info("Attempt %s for generating %s section.", attempt + 1, section_name)
            result = agent.generate_section(context)
            logger.info("%s section generated successfully on attempt %s.", section_name, attempt + 1)
            return result
        except Exception as e:
            attempt += 1
            logger.error("Attempt %s failed for %s section: %s", attempt, section_name, str(e), exc_info=True)
            if attempt < max_attempts:
                logger.info("Retrying %s section generation in %s seconds...", section_name, delay)
                time.sleep(delay)
    logger.error("All %s attempts failed for %s section. Marking as failed.", max_attempts, section_name)
    return f"Error generating {section_name}."

def generate_report(request_params: dict) -> dict:
    """
    Generate a full report by sequentially calling AI agents for each report section.

    Args:
        request_params (dict): A dictionary containing context and parameters for the report generation.
            Expected keys include:
              - industry
              - company
              - key_findings
              - market_trends
              - competitors
              - performance
              - improvements

    Returns:
        dict: A dictionary containing the generated report content, structured by sections.
              Example:
              {
                  "executive_summary": "...",
                  "market_analysis": "...",
                  "recommendations": "..."
              }
    """
    # Log the context (excluding sensitive data if applicable)
    logger.info("Starting report generation with context: %s", 
                {k: request_params.get(k) for k in request_params if k != "sensitive"})

    # Initialize AI agents for each report section.
    exec_summary_agent = ExecutiveSummaryAgent()
    market_analysis_agent = MarketAnalysisAgent()
    recommendations_agent = RecommendationsAgent()

    # Use a common context from request_params.
    context = request_params.copy()

    # Generate the Executive Summary section with retry logic.
    executive_summary = generate_with_retry(exec_summary_agent, context, "Executive Summary")
    context["executive_summary"] = executive_summary  # Optionally include in context for subsequent sections.

    # Generate the Market Analysis section with retry logic.
    market_analysis = generate_with_retry(market_analysis_agent, context, "Market Analysis")
    context["market_analysis"] = market_analysis

    # Generate the Recommendations section with retry logic.
    recommendations = generate_with_retry(recommendations_agent, context, "Recommendations")

    full_report = {
        "executive_summary": executive_summary,
        "market_analysis": market_analysis,
        "recommendations": recommendations,
    }

    # Log the final status of each section.
    status_summary = {section: "generated" if "Error" not in content else "failed"
                      for section, content in full_report.items()}
    logger.info("Report generation completed with the following section statuses: %s", status_summary)

    return full_report
