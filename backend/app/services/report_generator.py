# app/services/report_generator.py
"""
Renders reports as PDF using WeasyPrint + Jinja2 templates
"""

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime
import os
import uuid as uuid_lib

from app.models.report import Report, ReportType


# Setup Jinja2 environment (point to your templates folder)
templates_dir = os.path.join(os.path.dirname(__file__), "../templates/reports")
env = Environment(loader=FileSystemLoader(templates_dir))


async def generate_pdf_report(
    report: Report,
    content: str,               # ← LLM-generated markdown/text content
    findings: list = None,      # optional: raw findings for metadata/stats
    user_stats: dict = None     # optional: extra stats
) -> tuple[str, str]:
    """
    Generate a PDF report from LLM-generated content.

    Args:
        report: The Report database object (has title, type, etc.)
        content: Pre-generated report text (from report_llm)
        findings: Optional list of raw findings (used for stats)
        user_stats: Optional dict of user-level stats

    Returns:
        (filepath: str, size_mb: str)  e.g. ("static/reports/RPT-ABC123.pdf", "2.4")
    """
    try:
        # Choose template based on report type
        template_map = {
            ReportType.COMPREHENSIVE: "comprehensive.html",
            ReportType.EXECUTIVE:     "executive.html",
            ReportType.TECHNICAL:     "technical.html",
        }

        template_name = template_map.get(report.report_type)
        if not template_name:
            raise ValueError(f"Unknown report type: {report.report_type}")

        template = env.get_template(template_name)

        # Prepare context for Jinja2
        context = {
            "report": report,
            "content": content,                     # main LLM-generated text
            "generated_at": datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC"),
        }

        # Optional stats (used in template if needed)
        if findings:
            context["total_threats"] = len([
                f for f in findings
                if f.get("risk_level", "").lower() in ["high", "critical"]
            ])
            context["total_indicators"] = sum(
                len(f.get("indicators", [])) for f in findings
            )
        else:
            context["total_threats"] = 0
            context["total_indicators"] = 0

        if user_stats:
            context["user_stats"] = user_stats

        # Render HTML
        html_content = template.render(**context)

        # Save PDF
        os.makedirs("static/reports", exist_ok=True)
        filename = f"RPT-{str(uuid_lib.uuid4())[:8].upper()}.pdf"
        filepath = os.path.join("static/reports", filename)

        HTML(string=html_content).write_pdf(filepath)

        # Calculate size
        file_size_bytes = os.path.getsize(filepath)
        file_size_mb = round(file_size_bytes / (1024 * 1024), 1)

        return filepath, f"{file_size_mb}"

    except Exception as e:
        logger.exception("Failed to generate PDF report")
        raise RuntimeError(f"PDF generation failed: {str(e)}")