import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict, Optional
from app.services.llm_utils import get_llm
from app.services.pgp_verifier import verify_onion_pgp
import re

logger = logging.getLogger(__name__)


async def generate_findings_summary(
    query: str,
    findings: List[Dict],
    model_choice: str = None,  # Made optional to use default
    pgp_verify: bool = False  # Add PGP verification flag
) -> Optional[Dict]:
    """
    Generate an LLM-based summary of dark web findings with intelligence artifacts and insights.
    
    Args:
        query: Original search query
        findings: List of finding dictionaries with URL and content
        model_choice: LLM model to use (defaults to gemini-2.5-flash)
        pgp_verify: Whether to verify .onion site legitimacy via PGP
        
    Returns:
        Dictionary with summary, artifacts, insights, pgp_verification, and next steps
    """
    if not findings:
        logger.warning("No findings provided for summary generation")
        return None
    
    if not model_choice:
        model_choice = "gemini-2.5-flash"
    
    try:
        llm = get_llm(model_choice)
        
        # Format findings content for LLM analysis
        content_chunks = []
        source_links = []
        onion_urls = []
        
        for finding in findings[:15]:  # Limit to top 15 findings to avoid token limits
            url = finding.get("url", "")
            title = finding.get("title", "")
            text_excerpt = finding.get("text_excerpt", "")
            risk_level = finding.get("risk_level", "unknown")
            threat_indicators = finding.get("threat_indicators", [])
            
            source_links.append(url)
            
            if ".onion" in url:
                onion_urls.append(url)
            
            chunk = f"""
URL: {url}
Title: {title}
Risk Level: {risk_level}
Threat Indicators: {', '.join(threat_indicators) if threat_indicators else 'None'}
Content: {text_excerpt[:500]}
---"""
            content_chunks.append(chunk)
        
        combined_content = "\n".join(content_chunks)
        
        system_prompt = """You are an expert Cybercrime Threat Intelligence Analyst. Your task is to analyze dark web OSINT search results and provide actionable intelligence.

CRITICAL RULES:
1. Analyze ONLY the provided data - do not make assumptions
2. Extract concrete indicators: names, emails, phone numbers, crypto addresses, domains, forum usernames, threat actor IDs, malware names
3. Output Source Links: ALL URLs you referenced for analysis
4. Generate 3-5 KEY INSIGHTS that are specific, evidence-based, and actionable
5. Each insight must cite data from the findings
6. Identify TTPs (Tactics, Techniques, Procedures) if visible
7. Suggest next investigation steps and follow-up search queries
8. Flag illegal content explicitly - do NOT analyze illegal marketplaces or services in detail
9. Be objective and analytical

OUTPUT FORMAT:
---
**Input Query:** [query here]

**Source Links Referenced for Analysis:**
[List all URLs analyzed]

**Investigation Artifacts:**
[Extract and categorize all indicators found]

**Key Insights:**
[Numbered insights with evidence]

**Threat Assessment Summary:**
[1-2 paragraph technical assessment]

**Recommended Next Steps:**
[Specific follow-up queries and investigation paths]
---"""

        prompt_template = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", f"Query: {query}\n\nFindings Data:\n{combined_content}")
        ])
        
        chain = prompt_template | llm | StrOutputParser()
        summary_text = chain.invoke({})
        
        logger.info(f"Successfully generated summary for query: {query}")
        
        pgp_results = None
        if pgp_verify and onion_urls:
            logger.info(f"Running PGP verification for {len(onion_urls)} .onion URLs")
            pgp_results = []
            for onion_url in onion_urls[:5]:  # Limit to 5 for performance
                try:
                    # Extract clean onion address
                    onion_match = re.search(r'([a-z0-9]{16,}\.onion)', onion_url)
                    if onion_match:
                        result = await verify_onion_pgp(onion_match.group(0))
                        pgp_results.append(result)
                except Exception as e:
                    logger.warning(f"PGP verification failed for {onion_url}: {str(e)}")
        
        return {
            "success": True,
            "query": query,
            "model_used": model_choice,
            "summary": summary_text,
            "findings_analyzed": len(findings),
            "source_links_count": len(source_links),
            "pgp_verification_results": pgp_results  # Include PGP results
        }
        
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }


async def generate_custom_summary(
    query: str,
    findings: List[Dict],
    custom_prompt: str,
    model_choice: str = None  # Made optional
) -> Optional[Dict]:
    """
    Generate a summary using a custom prompt template.
    
    Args:
        query: Original search query
        findings: List of finding dictionaries
        custom_prompt: Custom system prompt for the LLM
        model_choice: LLM model to use (defaults to gemini-2.5-flash)
        
    Returns:
        Dictionary with summary or error
    """
    if not findings:
        logger.warning("No findings provided for custom summary")
        return None
    
    if not model_choice:
        model_choice = "gemini-2.5-flash"
    
    try:
        llm = get_llm(model_choice)
        
        # Format findings
        content_chunks = []
        for finding in findings[:15]:
            chunk = f"""
URL: {finding.get("url", "")}
Title: {finding.get("title", "")}
Risk: {finding.get("risk_level", "")}
Content: {finding.get("text_excerpt", "")[:400]}
---"""
            content_chunks.append(chunk)
        
        combined_content = "\n".join(content_chunks)
        
        prompt_template = ChatPromptTemplate([
            ("system", custom_prompt),
            ("user", f"Query: {query}\n\nFindings:\n{combined_content}")
        ])
        
        chain = prompt_template | llm | StrOutputParser()
        summary_text = chain.invoke({})
        
        logger.info(f"Custom summary generated for query: {query}")
        
        return {
            "success": True,
            "query": query,
            "model_used": model_choice,
            "summary": summary_text,
            "findings_analyzed": len(findings)
        }
        
    except Exception as e:
        logger.error(f"Custom summary generation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
