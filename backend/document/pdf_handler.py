import io
from pypdf import PdfReader, PdfWriter


class NoAcroFormFieldsError(Exception):
    """Raised when a PDF has no AcroForm fillable fields."""
    pass


def fill_pdf_template(template_bytes: bytes, placeholders: dict[str, str], output_path: str) -> None:
    """
    Fill AcroForm fields in a PDF template using placeholder names as field names.
    Raises NoAcroFormFieldsError if the PDF has no form fields.
    Saves filled PDF to output_path.
    """
    reader = PdfReader(io.BytesIO(template_bytes))
    fields = reader.get_fields()

    if not fields:
        raise NoAcroFormFieldsError(
            "PDF has no fillable form fields. Use a PDF with AcroForm fields, or upload a DOCX template instead."
        )

    writer = PdfWriter()
    writer.append(reader)

    # Fill fields across all pages (AcroForm fields can appear on any page)
    field_values = {name: placeholders.get(name, "") for name in fields}
    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values)

    with open(output_path, "wb") as f:
        writer.write(f)
