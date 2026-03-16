# tests/test_document.py
import io
import os
import pytest
from docx import Document as DocxDocument


def make_docx_with_placeholders(text: str) -> bytes:
    doc = DocxDocument()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_docx_replaces_placeholder_in_paragraph(tmp_path):
    from backend.document.docx_handler import fill_docx_template
    content = make_docx_with_placeholders("Dear Team, re: {{tender_title}} by {{tender_deadline}}")
    placeholders = {"tender_title": "IT Infrastructure", "tender_deadline": "2026-04-30"}
    out_path = str(tmp_path / "output.docx")
    fill_docx_template(content, placeholders, out_path)
    doc = DocxDocument(out_path)
    full_text = " ".join(p.text for p in doc.paragraphs)
    assert "IT Infrastructure" in full_text
    assert "2026-04-30" in full_text
    assert "{{" not in full_text


def test_docx_replaces_placeholder_in_table(tmp_path):
    from backend.document.docx_handler import fill_docx_template
    doc = DocxDocument()
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Tender"
    table.cell(0, 1).text = "{{tender_title}}"
    buf = io.BytesIO()
    doc.save(buf)
    placeholders = {"tender_title": "Cloud Migration"}
    out_path = str(tmp_path / "output.docx")
    fill_docx_template(buf.getvalue(), placeholders, out_path)
    doc2 = DocxDocument(out_path)
    cell_text = doc2.tables[0].cell(0, 1).text
    assert cell_text == "Cloud Migration"


def test_docx_ignores_missing_placeholders(tmp_path):
    from backend.document.docx_handler import fill_docx_template
    content = make_docx_with_placeholders("Value: {{tender_estimated_value}}")
    out_path = str(tmp_path / "output.docx")
    fill_docx_template(content, {}, out_path)  # No placeholders provided
    doc = DocxDocument(out_path)
    # Unreplaced placeholders left as-is
    assert "{{tender_estimated_value}}" in doc.paragraphs[0].text


def test_pdf_fills_acroform_field(tmp_path):
    from unittest.mock import patch, MagicMock
    from backend.document.pdf_handler import fill_pdf_template

    out_path = str(tmp_path / "output.pdf")

    with patch("backend.document.pdf_handler.PdfReader") as MockReader, \
         patch("backend.document.pdf_handler.PdfWriter") as MockWriter:

        mock_reader = MagicMock()
        mock_reader.get_fields.return_value = {"tender_title": MagicMock()}
        MockReader.return_value = mock_reader

        mock_writer = MagicMock()
        mock_writer.pages = [MagicMock()]
        MockWriter.return_value = mock_writer

        def write_bytes(f):
            f.write(b"%PDF-1.4 filled")
        mock_writer.write.side_effect = write_bytes

        fill_pdf_template(b"fake pdf", {"tender_title": "IT Infrastructure"}, out_path)

    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 0


def test_pdf_has_no_fields_raises(tmp_path):
    from unittest.mock import patch, MagicMock
    from backend.document.pdf_handler import fill_pdf_template, NoAcroFormFieldsError

    out_path = str(tmp_path / "output.pdf")

    with patch("backend.document.pdf_handler.PdfReader") as MockReader:
        mock_reader = MagicMock()
        mock_reader.get_fields.return_value = {}  # no fields
        MockReader.return_value = mock_reader

        with pytest.raises(NoAcroFormFieldsError):
            fill_pdf_template(b"fake pdf", {"tender_title": "Test"}, out_path)
