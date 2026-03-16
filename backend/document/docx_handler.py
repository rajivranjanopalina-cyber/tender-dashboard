import io
from docx import Document as DocxDocument
from docx.oxml.ns import qn

# The wps namespace is not registered in python-docx's nsmap, so use raw Clark notation
_WPS_TXBX = "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}txbx"
_W_P = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"


def fill_docx_template(template_bytes: bytes, placeholders: dict[str, str], output_path: str) -> None:
    """
    Replace {{placeholder}} occurrences in a DOCX template and save to output_path.
    Handles paragraphs, table cells, headers, footers, and text boxes.
    Missing placeholder values are left unreplaced.
    """
    doc = DocxDocument(io.BytesIO(template_bytes))

    # Paragraphs in body
    for para in doc.paragraphs:
        _replace_in_paragraph(para, placeholders)

    # Tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _replace_in_paragraph(para, placeholders)

    # Headers and footers
    for section in doc.sections:
        for para in section.header.paragraphs:
            _replace_in_paragraph(para, placeholders)
        for para in section.footer.paragraphs:
            _replace_in_paragraph(para, placeholders)

    # Text boxes (drawing elements in body XML)
    from docx.text.paragraph import Paragraph
    for shape in doc.element.body.iter(_WPS_TXBX):
        for para_elem in shape.iter(_W_P):
            para = Paragraph(para_elem, doc)
            _replace_in_paragraph(para, placeholders)

    doc.save(output_path)


def _replace_in_paragraph(paragraph, placeholders: dict[str, str]) -> None:
    """Replace placeholders in a paragraph, preserving runs."""
    full_text = paragraph.text
    if "{{" not in full_text:
        return

    # Build the replacement text
    new_text = full_text
    for key, value in placeholders.items():
        new_text = new_text.replace(f"{{{{{key}}}}}", value or "")

    # Clear existing runs and write replacement into the first run
    if paragraph.runs:
        paragraph.runs[0].text = new_text
        for run in paragraph.runs[1:]:
            run.text = ""
