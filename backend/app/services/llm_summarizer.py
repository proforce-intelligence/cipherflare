import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict, Optional
from app.services.llm_utils import get_llm
from app.services.pgp_verifier import verify_onion_pgp
import re

logger = logging.getLogger(__name__)


async def refine_query(
    query: str,
    model_choice: str = "gemini-2.5-flash"
) -> str:
    """
    Refine user query for better dark web search results.
    """
    try:
        llm = get_llm(model_choice)
        
        system_prompt = """
        You are a Cybercrime Threat Intelligence Expert. Your task is to refine the provided user query that needs to be sent to darkweb search engines. 
        
        Rules:
        1. Analyze the user query and think about how it can be improved to use as search engine query
        2. Refine the user query by adding or removing words so that it returns the best result from dark web search engines
        3. Don't use any logical operators (AND, OR, etc.)
        4. Keep the final refined query limited to 5 words or less
        5. Output just the user query and nothing else
        """
        
        prompt_template = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", "{query}")
        ])
        
        chain = prompt_template | llm | StrOutputParser()
        refined = chain.invoke({"query": query})
        
        # Clean up the output (sometimes LLMs add quotes or extra spaces)
        refined = refined.strip().strip('"').strip("'")
        # Ensure it's not too long
        words = refined.split()
        if len(words) > 6:
            refined = " ".join(words[:6])
            
        logger.info(f"Refined query: '{query}' -> '{refined}'")
        return refined
    except Exception as e:
        logger.error(f"Query refinement failed: {e}")
        return query


async def filter_results(
    query: str,
    results: List[Dict],
    model_choice: str = "gemini-2.5-flash",
    top_k: int = 50
) -> List[Dict]:
    """
    Use LLM to select the most relevant search results.
    """
    if not results:
        return []
    
    try:
        llm = get_llm(model_choice)
        
        system_prompt = f"""
        You are a Cybercrime Threat Intelligence Expert. You are given a dark web search query and a list of search results in the form of ID, URL, Title, and Snippet. 
        Your task is to select the Top {top_k} relevant results that best match the search query. 
        Focus on relevance: if a user is searching for "guns in Togo", prioritize results mentioning Togo, firearms, weapons, or regional security.
        
        Rules:
        1. Output ONLY a comma-separated list of IDs (e.g., 1, 5, 12) that best match the input query.
        2. Do not include any other text.
        3. Select at most {top_k} IDs.
        """
        
        # Format results for LLM
        formatted_results = []
        for i, res in enumerate(results):
            url = res.get("url", "")
            title = res.get("title", "No Title")
            snippet = res.get("snippet", "") or res.get("description", "")
            # Truncate to save tokens
            title = (title[:60] + "..") if len(title) > 60 else title
            snippet = (snippet[:160] + "..") if len(snippet) > 160 else snippet
            formatted_results.append(f"ID: {i+1} | Title: {title} | Snippet: {snippet} | URL: {url}")
            
        results_str = "\n".join(formatted_results)
        
        prompt_template = ChatPromptTemplate([
            ("system", system_prompt.format(top_k=top_k)),
            ("user", "Search Query: {query}\n\nSearch Results:\n{results}")
        ])
        
        chain = prompt_template | llm | StrOutputParser()
        response = chain.invoke({"query": query, "results": results_str})
        
        # Parse IDs from response
        import re
        ids = [int(x) for x in re.findall(r"\d+", response)]
        
        filtered = []
        seen_ids = set()
        for idx in ids:
            if 1 <= idx <= len(results) and idx not in seen_ids:
                filtered.append(results[idx-1])
                seen_ids.add(idx)
                if len(filtered) >= top_k:
                    break
        
        if not filtered:
            logger.warning("LLM filtering returned no results or failed to parse. Using top_k fallback.")
            return results[:top_k]
            
        logger.info(f"Filtered {len(results)} results down to {len(filtered)}")
        return filtered
        
    except Exception as e:
        logger.error(f"Result filtering failed: {e}")
        return results[:top_k]


PRESET_PROMPTS = {
    "threat_intel": """
    You are an Cybercrime Threat Intelligence Expert tasked with generating context-based technical investigative insights from dark web osint search engine results.

    Rules:
    1. Analyze the Darkweb OSINT data provided using links and their raw text.
    2. Output the Source Links referenced for the analysis.
    3. Provide a detailed, contextual, evidence-based technical analysis of the data.
    4. Provide intelligence artifacts along with their context visible in the data.
    5. The artifacts can include indicators like name, email, phone, cryptocurrency addresses, domains, darkweb markets, forum names, threat actor information, malware names, TTPs, etc.
    6. Generate 3-5 key insights based on the data.
    7. Each insight should be specific, actionable, context-based, and data-driven.
    8. Include suggested next steps and queries for investigating more on the topic.
    9. Be objective and analytical in your assessment.
    10. Ignore not safe for work texts from the analysis

    Output Format:
    ---
    **Input Query:** {query}

    **Source Links Referenced for Analysis:**
    [List all source links used]

    **Investigation Artifacts:**
    [Detailed list of identified artifacts with context]

    **Key Insights:**
    [3-5 numbered insights]

    **Next Steps:**
    [Investigative recommendations and follow-up queries]
    ---
    """,
    "ransomware_malware": """
    You are a Malware and Ransomware Intelligence Expert tasked with analyzing dark web data for malware-related threats.

    Rules:
    1. Analyze the Darkweb OSINT data provided using links and their raw text.
    2. Output the Source Links referenced for the analysis.
    3. Focus specifically on ransomware groups, malware families, exploit kits, and attack infrastructure.
    4. Identify malware indicators: file hashes, C2 domains/IPs, staging URLs, payload names, and obfuscation techniques.
    5. Map TTPs to MITRE ATT&CK where possible.
    6. Identify victim organizations, sectors, or geographies mentioned.
    7. Generate 3-5 key insights focused on threat actor behavior and malware evolution.
    8. Include suggested next steps for containment, detection, and further hunting.
    9. Be objective and analytical.

    Output Format:
    ---
    **Input Query:** {query}

    **Source Links Referenced for Analysis:**
    [List links]

    **Malware / Ransomware Indicators:**
    [hashes, C2s, payload names, TTPs]

    **Threat Actor Profile:**
    [group name, aliases, known victims, sector targeting]

    **Key Insights:**
    [3-5 insights]

    **Next Steps:**
    [hunting queries, detection rules, further investigation]
    ---
    """,
}

async def generate_findings_summary(
    query: str,
    findings: List[Dict],
    model_choice: str = None,
    pgp_verify: bool = False,
    preset: str = "threat_intel"
) -> Optional[Dict]:
    """
    Generate an LLM-based summary of dark web findings with intelligence artifacts and insights.
    """
    if not findings:
        logger.warning("No findings provided for summary generation")
        return None
    
    if not model_choice:
        model_choice = "gemini-2.5-flash"
    
    try:
        logger.info(f"Generating summary for query '{query}' using {model_choice}...")
        llm = get_llm(model_choice)
        
        # Format findings content for LLM analysis
        content_chunks = []
        source_links = []
        onion_urls = []
        
        for finding in findings[:15]:
            url = finding.get("url", "")
            title = finding.get("title", "")
            # Use OCR text if available, fallback to excerpt
            text_content = finding.get("ocr_text", "")
            if finding.get("text_excerpt"):
                text_content += "\n" + finding.get("text_excerpt")
            
            risk_level = finding.get("risk_level", "unknown")
            threat_indicators = finding.get("threat_indicators", [])
            
            source_links.append(url)
            if ".onion" in url:
                onion_urls.append(url)
            
            chunk = f"URL: {url}\nTitle: {title}\nRisk: {risk_level}\nIndicators: {', '.join(threat_indicators)}\nContent: {text_content[:2500]}\n---"
            content_chunks.append(chunk)
        
        combined_content = "\n".join(content_chunks)
        
        system_prompt_text = PRESET_PROMPTS.get(preset, PRESET_PROMPTS["threat_intel"])

        prompt_template = ChatPromptTemplate([
            ("system", system_prompt_text),
            ("user", "Findings Data:\n{combined_content}")
        ])
        
        chain = prompt_template | llm | StrOutputParser()
        
        try:
            summary_text = await chain.ainvoke({
                "query": query,
                "combined_content": combined_content
            })
        except Exception as e:
            if "gemini-2.5" in model_choice:
                logger.warning(f"Gemini 2.5 failed, falling back to 1.5: {e}")
                # Fallback to 1.5-flash if 2.5 is not available
                llm_fallback = get_llm("gemini-1.5-flash")
                chain_fallback = prompt_template | llm_fallback | StrOutputParser()
                summary_text = await chain_fallback.ainvoke({
                    "query": query,
                    "combined_content": combined_content
                })
            else:
                raise e
        
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
