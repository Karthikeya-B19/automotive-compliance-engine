from __future__ import annotations

from pathlib import Path

from fpdf import FPDF


PROJECT_ROOT = Path(__file__).resolve().parent
STANDARDS_DIR = PROJECT_ROOT / "data" / "standards"
PDF_PATH = STANDARDS_DIR / "MISRA_C_Mock_Standard.pdf"


class MisraMockPdf(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "MISRA C:2012 Mock Standard", ln=True, align="C")
        self.ln(2)

    def chapter_title(self, title: str) -> None:
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, title, ln=True, fill=True)
        self.ln(1)

    def chapter_body(self, body: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, body)
        self.ln(2)


def build_mock_misra_pdf(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = MisraMockPdf()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.chapter_title("1. Scope")
    pdf.chapter_body(
        "This mock document is a synthetic MISRA-style reference for local ingestion testing. "
        "It is intentionally simplified and should not be treated as an authoritative standard."
    )

    pdf.chapter_title("2. Example Rule Set")
    pdf.chapter_body(
        "Rule 1: Avoid unreachable code paths.\n"
        "Rule 2: Use explicit type conversions when narrowing values.\n"
        "Rule 3: Prefer static allocation for safety-critical embedded modules.\n"
        "Rule 4: Validate every external input before use.\n"
        "Rule 5: Document deviations with a traceable justification."
    )

    pdf.chapter_title("3. Review Notes")
    pdf.chapter_body(
        "The ingestion pipeline should be able to extract these sections, chunk the text, "
        "and store them in the local vector database for retrieval experiments."
    )

    pdf.output(str(output_path))
    return output_path


def main() -> None:
    generated_path = build_mock_misra_pdf(PDF_PATH)
    print(f"Created mock MISRA C PDF at: {generated_path}")


if __name__ == "__main__":
    main()