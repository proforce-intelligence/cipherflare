# app/services/report_generator.py
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime
import os
import uuid as uuid_lib

# Import logger
import logging
logger = logging.getLogger(__name__)

# Your templates path (this should now work)
templates_dir = os.path.join(os.path.dirname(__file__), "../templates/reports")
env = Environment(loader=FileSystemLoader(templates_dir))

async def generate_pdf_report(
    report: 'Report',  # forward ref or import Report if needed
    content: str,
    findings: list = None,
    user_stats: dict = None
) -> tuple[str, str]:
    try:
        template_map = {
            'comprehensive': "comprehensive.html",
            'executive':     "executive.html",
            'technical':     "technical.html",
        }

        template_name = template_map.get(report.report_type.value)
        if not template_name:
            raise ValueError(f"Unknown report type: {report.report_type}")

        template = env.get_template(template_name)

        context = {
            "report": report,
            "content": content,
            "generated_at": datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC"),
        }

        if findings:
            context["total_threats"] = len([
                f for f in findings
                if f.get("risk_level", "").lower() in ["high", "critical"]
            ])
            context["total_indicators"] = sum(
                len(f.get("indicators", [])) for f in findings
            )

        html_content = template.render(**context)

        os.makedirs("static/reports", exist_ok=True)
        filename = f"RPT-{str(uuid_lib.uuid4())[:8].upper()}.pdf"
        filepath = os.path.join("static/reports", filename)

        HTML(string=html_content).write_pdf(filepath)

        file_size_bytes = os.path.getsize(filepath)
        file_size_mb = round(file_size_bytes / (1024 * 1024), 1)

        return filepath, f"{file_size_mb}"

    except Exception as e:
        logger.exception("Failed to generate PDF report")  # ← now logger exists
        raise RuntimeError(f"PDF generation failed: {str(e)}")