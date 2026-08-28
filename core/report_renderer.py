"""Rendert Reports als Markdown und HTML."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.base_module import Report

_template_dir = Path(__file__).parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(["html"]),
)


def render_markdown(report: Report) -> str:
    """Report als Markdown rendern."""
    lines = [f"# {report.title}", f"*Generiert: {report.generated_at:%d.%m.%Y %H:%M}*\n"]

    if report.critical_items:
        lines.append("## 🚨 Kritisch\n")
        for item in report.critical_items:
            lines.append(f"### {item.title}")
            lines.append(f"{item.summary}")
            if item.source_url:
                lines.append(f"[→ Details]({item.source_url})\n")

    if report.important_items:
        lines.append("## ⚠️ Wichtig\n")
        for item in report.important_items:
            lines.append(f"### {item.title}")
            lines.append(f"{item.summary}")
            if item.source_url:
                lines.append(f"[→ Details]({item.source_url})\n")

    if report.info_items:
        lines.append("## ℹ️ Info\n")
        for item in report.info_items:
            lines.append(f"- **{item.title}**: {item.summary}")

    if not report.items:
        lines.append("*Keine neuen Ereignisse in dieser Periode.*")

    return "\n".join(lines)


def render_html(report: Report) -> str:
    """Report als HTML rendern (für E-Mail)."""
    template = _env.get_template("report_email.html")
    return template.render(report=report)
