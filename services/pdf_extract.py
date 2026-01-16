"""PDF text extraction service using pdfplumber."""

import pdfplumber
import re


def extract_pdf_text(file) -> str:
    """
    Extract text from a PDF file using pdfplumber.
    
    Args:
        file: File-like object (e.g., from Streamlit file uploader)
        
    Returns:
        Extracted text as string
        
    Raises:
        ValueError: If extraction fails or text is too short (< 500 chars)
    """
    try:
        text_parts = []
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        if not text_parts:
            raise ValueError(
                "Could not extract text from PDF. "
                "Please ensure the PDF is not scanned or image-based. "
                "Try using a text-based PDF."
            )
        
        raw_text = "\n".join(text_parts)
        
        # Basic cleaning: normalize whitespace
        text = re.sub(r'\s+', ' ', raw_text)  # Normalize spaces
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove repeated blank lines
        text = text.strip()
        
        # Validate minimum length
        if len(text) < 500:
            raise ValueError(
                f"Extracted text is too short ({len(text)} characters). "
                "Please ensure the PDF contains sufficient text content. "
                "Scanned PDFs or image-based PDFs are not supported. "
                "Minimum required: 500 characters."
            )
        
        return text
        
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(
            f"Failed to extract text from PDF: {str(e)}. "
            "Please ensure the file is a valid, text-based PDF."
        )
