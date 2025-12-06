# scripts/clean_pdf_contacts.py
"""
Script to extract, clean, and process staff contact data from the local contacts.pdf file.
"""

import pdfplumber
import pandas as pd
import json
import os
from pathlib import Path
import logging
import re
from datetime import datetime

# --- Configuration ---
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PDF_FILENAME = "contacts.pdf"
OUTPUT_FILENAME = f"processed_pdf_contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

# Ensure processed directory exists
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROCESSED_DIR / "pdf_cleaning.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def standardize_text(text: str) -> str:
    """Standardize text by removing extra whitespace."""
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fix_email_format(email: str) -> str:
    """Fix common email obfuscations like [dot] and [at]."""
    if not email:
        return ""
    email = email.replace('[dot]', '.').replace('[at]', '@').replace('[DOT]', '.').replace('[AT]', '@')
    email = email.replace('Id:', '').replace('Id: ', '')
    email = re.sub(r'\s*@\s*', '@', email)
    email = re.sub(r'\s*\.\s*', '.', email)
    return email.strip()

def create_chunk(text: str, metadata: dict) -> dict:
    """Create a standardized chunk."""
    return {
        "page_content": text,
        "metadata": metadata
    }

def find_column_index(headers: list, possible_names: list) -> int:
    """
    Find the index of a column based on a list of possible names (case-insensitive, partial match).
    """
    headers_lower = [standardize_text(h).lower() for h in headers]
    for name in possible_names:
        name_lower = standardize_text(name).lower()
        for i, header in enumerate(headers_lower):
            if name_lower in header or header in name_lower:
                logger.debug(f"  Mapped column '{name}' to index {i} ('{headers[i]}')")
                return i
    return -1

def extract_and_clean_pdf_data(pdf_path: Path):
    """Extract table from PDF, clean data, and create chunks."""
    logger.info(f"Starting extraction and cleaning from PDF: {pdf_path}")

    all_chunks = []
    headers = []
    email_col_index = -1
    mobile_col_index = -1

    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            logger.info(f"PDF has {num_pages} pages.")

            for page_num, page in enumerate(pdf.pages):
                logger.info(f"Processing page {page_num + 1}")
                tables = page.extract_tables()

                for table_index, table in enumerate(tables):
                    if table:
                        logger.info(f"  Found table {table_index + 1} on page {page_num + 1} with {len(table)} rows.")

                        if page_num == 0:
                            headers = table[0] if table else []
                            if not headers:
                                logger.error(f"    No headers found in the first table on page 1.")
                                return []

                            logger.debug(f"    Raw headers from first page: {headers}")
                            standardized_headers = [standardize_text(h) for h in headers]
                            logger.debug(f"    Standardized headers: {standardized_headers}")

                            email_col_index = find_column_index(standardized_headers, ['Email Id', 'Email', 'Email Id(gov/nic)'])
                            mobile_col_index = find_column_index(standardized_headers, ['Mobile', 'Mobile(preferably Linked with Aadhar)', 'Phone'])

                            logger.info(f"    Identified Email column index: {email_col_index}")
                            logger.info(f"    Identified Mobile column index: {mobile_col_index}")

                            if email_col_index == -1:
                                logger.warning(f"    Could not find Email column header in the first table.")
                            if mobile_col_index == -1:
                                logger.warning(f"    Could not find Mobile column header in the first table.")

                            data_rows = table[1:] if len(table) > 1 else []

                        else:
                            data_rows = table

                        for row_num, row in enumerate(data_rows):
                            row_dict = {}
                            for i, header_standardized in enumerate(standardized_headers):
                                key = header_standardized if header_standardized else f"Col{i}"
                                value = row[i] if i < len(row) else ""
                                row_dict[key] = standardize_text(str(value))

                            s_no_index = 0
                            name_index = 1
                            designation_index = 2

                            s_no = row[s_no_index] if 0 <= s_no_index < len(row) else ''
                            name = row[name_index] if 0 <= name_index < len(row) else ''
                            designation = row[designation_index] if 0 <= designation_index < len(row) else ''

                            raw_email = row[email_col_index] if 0 <= email_col_index < len(row) else ''
                            raw_mobile = row[mobile_col_index] if 0 <= mobile_col_index < len(row) else ''

                            email = fix_email_format(raw_email)
                            mobile = standardize_text(raw_mobile)

                            if not name:
                                logger.debug(f"    Row {row_num + 1} has no name, skipping.")
                                continue

                            text_parts = [f"Staff Member: {name}"]
                            if designation:
                                text_parts.append(f"Designation: {designation}")
                            if email:
                                text_parts.append(f"Email: {email}")
                            if mobile:
                                text_parts.append(f"Mobile: {mobile}")

                            text_content = ". ".join(text_parts) + "."

                            metadata = {
                                'source_type': 'staff_directory_pdf',
                                'source_file': pdf_path.name,
                                'page_number': page_num + 1,
                                'table_index_on_page': table_index,
                                'row_number_on_page': row_num + 1,
                                's_no': standardize_text(str(s_no)),
                                'name': standardize_text(str(name)),
                                'designation': standardize_text(str(designation)),
                                'email': email,
                                'mobile': mobile,
                                'scraped_at': datetime.utcnow().isoformat(),
                                'email_col_index_used': email_col_index,
                                'mobile_col_index_used': mobile_col_index,
                                'headers_on_first_page': standardized_headers
                            }

                            chunk = create_chunk(text_content, metadata)
                            all_chunks.append(chunk)

    except Exception as e:
        logger.error(f"Error processing PDF {pdf_path}: {e}")
        return []

    logger.info(f"Successfully processed PDF across {num_pages} pages. Created {len(all_chunks)} chunks.")
    return all_chunks

def save_chunks(chunks: list, output_path: Path):
    """Save the list of chunks to a JSONL file."""
    logger.info(f"Saving {len(chunks)} chunks to {output_path}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        logger.info("Chunks saved successfully.")
    except Exception as e:
        logger.error(f"Error saving chunks to {output_path}: {e}")

def main():
    """Main execution function."""
    pdf_path = RAW_DIR / PDF_FILENAME

    if not pdf_path.exists():
        logger.error(f"PDF file not found at {pdf_path}")
        return

    logger.info("Starting PDF contact cleaning process...")
    chunks = extract_and_clean_pdf_data(pdf_path)

    if chunks:
        output_path = PROCESSED_DIR / OUTPUT_FILENAME
        save_chunks(chunks, output_path)
        logger.info(f"PDF cleaning process completed. Output saved to {output_path}")
    else:
        logger.warning("No chunks were created from the PDF. Check the PDF content and the log for errors.")

if __name__ == "__main__":
    main()