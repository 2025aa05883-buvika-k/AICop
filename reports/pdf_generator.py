from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.config import settings


class PDFReportGenerator:
    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = Path(output_dir or settings.reports_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, case_id: str, content: str) -> str:
        output_path = self.output_dir / f"{case_id}.pdf"
        document = SimpleDocTemplate(str(output_path), pagesize=letter, rightMargin=0.75 * inch, leftMargin=0.75 * inch)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("AICop Investigation Report", styles["Title"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(content.replace("\n", "<br/>"), styles["BodyText"]))
        document.build(story)
        return str(output_path)
