# app/services/report_llm.py
"""
Dedicated LLM service for generating threat intelligence reports
Using local OpenAI-compatible server at http://127.0.0.1:1234/v1
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Use OpenAI client — compatible with LM Studio, Ollama WebUI, etc.
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# Your local server endpoint
LOCAL_LLM_BASE_URL = "http://127.0.0.1:1234/v1"
LOCAL_LLM_API_KEY = "lm-studio"  # dummy key — most local servers accept anything

# ────────────────────────────────────────────────
#               Report-specific prompts
# ────────────────────────────────────────────────

# (your existing prompts here - unchanged)
EXECUTIVE_SUMMARY_PROMPT = PromptTemplate.from_template(
    """You are a senior threat intelligence analyst preparing an executive summary for stakeholders.

Report title: {title}
Date: {generated_date}
Total findings across jobs: {total_findings}
Jobs included: {jobs_count}
Time period: {time_period}

Key instructions:
- Write in clear, concise, professional language — no technical jargon unless necessary
- Focus on business impact, major threats, trends, and high-level recommendations
- Structure: 
  1. Overview of threat landscape
  2. Key findings & risk highlights
  3. Strategic implications
  4. Top 3–5 recommended actions

Findings summary (for context):
{findings_summary}

Generate the executive summary now:"""
)

TECHNICAL_ANALYSIS_PROMPT = PromptTemplate.from_template(
    """You are a senior threat intelligence analyst creating a technical report section.

Report title: {title}
Date: {generated_date}
Total findings: {total_findings}
Jobs included: {jobs_count}

Generate a detailed **Technical Analysis** section including:
- Extracted Indicators of Compromise (IOCs): IPs, domains, hashes, emails, URLs, etc.
- Observed Tactics, Techniques, and Procedures (TTPs)
- Technical patterns and behaviors
- Group findings by severity (critical/high/medium/low)
- Use tables or structured lists when appropriate

Findings to analyze:
{findings_text}

Output only the technical analysis content (no introduction or conclusion):"""
)

COMPREHENSIVE_REPORT_PROMPT = PromptTemplate.from_template(
    """You are an expert threat intelligence report writer.

Report title: {title}
Date: {generated_date}
Total findings: {total_findings}
Jobs included: {jobs_count}
Time period: {time_period}

Create a **comprehensive threat intelligence report** with the following sections:

1. Executive Summary (high-level overview, key risks, business impact)
2. Threat Landscape Overview
3. Detailed Findings (grouped by severity)
4. Indicators of Compromise (IOCs) — list clearly
5. Tactics, Techniques, and Procedures (TTPs)
6. Risk Assessment
7. Recommendations and Mitigation Steps

Use professional language. Include tables/lists for IOCs and findings where appropriate.

Findings to base the report on:
{findings_text}

Output the full report content now:"""
)

# ────────────────────────────────────────────────
#               Helper functions (unchanged)
# ────────────────────────────────────────────────

def prepare_findings_context(findings: List[Dict]) -> Dict[str, Any]:
    if not findings:
        return {
            "total_findings": 0,
            "findings_summary": "No findings available.",
            "findings_text": "No data.",
            "critical_count": 0,
            "high_count": 0
        }

    critical = sum(1 for f in findings if f.get("risk_level", "").lower() in ["critical"])
    high = sum(1 for f in findings if f.get("risk_level", "").lower() in ["high"])
    text_summary = "\n".join(
        f"- {f.get('title', 'Untitled')} ({f.get('risk_level', 'unknown')}) — {f.get('source_url', 'no url')}"
        for f in findings[:30]
    )

    return {
        "total_findings": len(findings),
        "critical_count": critical,
        "high_count": high,
        "findings_summary": f"{len(findings)} findings • {critical} critical • {high} high",
        "findings_text": text_summary or "No detailed findings available."
    }


def get_report_prompt(report_type: str):
    prompts = {
        "executive": EXECUTIVE_SUMMARY_PROMPT,
        "technical": TECHNICAL_ANALYSIS_PROMPT,
        "comprehensive": COMPREHENSIVE_REPORT_PROMPT,
    }
    return prompts.get(report_type.lower(), COMPREHENSIVE_REPORT_PROMPT)


# ────────────────────────────────────────────────
#               Main report generation function (Ollama-compatible server)
# ────────────────────────────────────────────────

async def generate_report_content(
    report_type: str,
    title: str,
    findings: List[Dict],
    jobs_count: int = 0,
    time_period: str = "N/A",
    model_choice: str = "llama3.1",           # change to your loaded model name
    max_findings_for_prompt: int = 50,
) -> str:
    """
    Generate full report text using local Ollama-compatible server
    """
    try:
        logger.info(f"Connecting to local LLM at {LOCAL_LLM_BASE_URL} with model: {model_choice}")

        llm = ChatOpenAI(
            base_url=LOCAL_LLM_BASE_URL,
            api_key=LOCAL_LLM_API_KEY,          # dummy key
            model=model_choice,
            temperature=0.3,
            max_tokens=4096,
            timeout=300,                        # generous timeout for long reports
        )

        context = prepare_findings_context(findings[:max_findings_for_prompt])
        generated_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        prompt_template = get_report_prompt(report_type)

        chain = (
            {
                "title": lambda x: title,
                "generated_date": lambda x: generated_date,
                "total_findings": lambda x: context["total_findings"],
                "jobs_count": lambda x: jobs_count,
                "time_period": lambda x: time_period,
                "findings_summary": lambda x: context["findings_summary"],
                "findings_text": lambda x: context["findings_text"],
            }
            | prompt_template
            | llm
            | StrOutputParser()
        )

        logger.info(f"Generating {report_type} report: '{title}' using model {model_choice}")

        report_text = await chain.ainvoke({})

        return report_text.strip()

    except Exception as e:
        logger.exception(f"Failed to generate {report_type} report content")
        raise RuntimeError(f"Report generation failed: {str(e)}")


__all__ = [
    "generate_report_content",
    "ReportType",
    "prepare_findings_context",
]