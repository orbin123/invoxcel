"""Render bounded page images locally, including in browsers without a PDF viewer."""
from io import BytesIO
from threading import Lock

import pypdfium2 as pdfium

# PDFium calls must never run concurrently in a threaded Django development server.
PDF_LOCK = Lock()


def render_page(source, page_number):
    with PDF_LOCK, pdfium.PdfDocument(source) as document:
        if not 1 <= page_number <= len(document):
            raise ValueError("Unknown page")
        page = document[page_number - 1]
        try:
            width, height = page.get_size()
            if min(width, height) <= 0:
                raise ValueError("Invalid page dimensions")
            bitmap = page.render(scale=min(2, 1600 / max(width, height)))
            try:
                image = bitmap.to_pil()
                try:
                    output = BytesIO()
                    image.save(output, format="PNG")
                    return output.getvalue()
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            page.close()
