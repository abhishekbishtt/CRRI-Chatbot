# scripts/clean_pdf_contacts.py
"""
Script to extract, clean, and process staff contact data from the local contacts.pdf file.

This script reads the 'contacts.pdf' file from data/raw/, extracts the table using pdfplumber,
handles multi-page tables (headers only on first page), cleans the extracted data
(standardizes text, fixes email format), converts it into chunks (page_content + metadata),
and saves the result to data/processed/.
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
PDF_FILENAME = "contacts.pdf" # The name of the PDF file in data/raw/
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
    """Standardize text by removing extra whitespace, fixing common issues."""
    if not text or not isinstance(text, str):
        return ""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fix_email_format(email: str) -> str:
    """Fix common email obfuscations like [dot] and [at]."""
    if not email:
        return ""
    # Replace [dot] with . and [at] with @
    email = email.replace('[dot]', '.').replace('[at]', '@').replace('[DOT]', '.').replace('[AT]', '@')
    # Remove common artifacts like "Id: "
    email = email.replace('Id:', '').replace('Id: ', '')
    # Remove spaces around @ and .
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
    Returns the index if found, otherwise -1.
    """
    headers_lower = [standardize_text(h).lower() for h in headers]
    for name in possible_names:
        name_lower = standardize_text(name).lower()
        for i, header in enumerate(headers_lower):
            if name_lower in header or header in name_lower: # Check if name is part of header or vice-versa
                logger.debug(f"  Mapped column '{name}' to index {i} ('{headers[i]}')")
                return i
    return -1

def extract_and_clean_pdf_data(pdf_path: Path):
    """Extract table from PDF, clean data, and create chunks."""
    logger.info(f"Starting extraction and cleaning from PDF: {pdf_path}")

    all_chunks = []
    headers = [] # Store headers found on the first page
    email_col_index = -1 # Store email column index found on the first page
    mobile_col_index = -1 # Store mobile column index found on the first page

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

                        if page_num == 0: # Only process headers on the first page
                            headers = table[0] if table else []
                            if not headers:
                                logger.error(f"    No headers found in the first table on page 1, cannot process multi-page table.")
                                return [] # Cannot proceed without headers

                            logger.debug(f"    Raw headers from first page: {headers}")
                            # Standardize headers for easier lookup
                            standardized_headers = [standardize_text(h) for h in headers]
                            logger.debug(f"    Standardized headers: {standardized_headers}")

                            # Find column indices for Email and Mobile based on first page headers
                            email_col_index = find_column_index(standardized_headers, ['Email Id', 'Email', 'Email Id(gov/nic)'])
                            mobile_col_index = find_column_index(standardized_headers, ['Mobile', 'Mobile(preferably Linked with Aadhar)', 'Phone'])

                            logger.info(f"    Identified Email column index: {email_col_index}")
                            logger.info(f"    Identified Mobile column index: {mobile_col_index}")

                            if email_col_index == -1:
                                logger.warning(f"    Could not find Email column header in the first table.")
                            if mobile_col_index == -1:
                                logger.warning(f"    Could not find Mobile column header in the first table.")

                            # Data rows start from index 1 on the first page
                            data_rows = table[1:] if len(table) > 1 else []

                        else: # For pages other than the first
                            # Assume the structure (headers) is the same as the first page
                            # Just take the data rows
                            data_rows = table # All rows on subsequent pages are data rows

                        for row_num, row in enumerate(data_rows):
                            # Create a dictionary for the row data using standardized headers found on the first page
                            # Handle potential mismatch in row length and headers
                            row_dict = {}
                            for i, header_standardized in enumerate(standardized_headers):
                                # Use 'Col{i}' if header is missing or empty after standardization (shouldn't happen if headers are consistent)
                                key = header_standardized if header_standardized else f"Col{i}"
                                # Use empty string if row value is missing for this column
                                value = row[i] if i < len(row) else ""
                                row_dict[key] = standardize_text(str(value)) # Ensure it's a string

                            # --- Clean and map fields using indices found on the FIRST page ---
                            # Use indices to get Name, Designation, Email, Mobile directly from the row list
                            s_no_index = 0 # Assume S. No. is the first column (index 0)
                            name_index = 1  # Assume Name is the second column (index 1)
                            designation_index = 2 # Assume Designation is the third column (index 2)

                            s_no = row[s_no_index] if 0 <= s_no_index < len(row) else ''
                            name = row[name_index] if 0 <= name_index < len(row) else ''
                            designation = row[designation_index] if 0 <= designation_index < len(row) else ''

                            # Use the indices found on page 1
                            raw_email = row[email_col_index] if 0 <= email_col_index < len(row) else ''
                            raw_mobile = row[mobile_col_index] if 0 <= mobile_col_index < len(row) else ''

                            # Clean email and mobile
                            email = fix_email_format(raw_email)
                            mobile = standardize_text(raw_mobile)

                            # Validate name (basic check)
                            if not name:
                                logger.debug(f"    Row {row_num + 1} (on page {page_num + 1}, table {table_index + 1}) has no name, skipping.")
                                continue # Skip rows without a name

                            # --- Create descriptive text content ---
                            text_parts = [f"Staff Member: {name}"]
                            if designation:
                                text_parts.append(f"Designation: {designation}")
                            if email:
                                text_parts.append(f"Email: {email}")
                            if mobile:
                                text_parts.append(f"Mobile: {mobile}")

                            text_content = ". ".join(text_parts) + "."

                            # --- Create metadata ---
                            # Calculate the overall row number considering previous pages
                            # This is an approximation, as the exact row number across the whole table isn't directly available from pdfplumber per page
                            # But we can keep track of the row number *on the current page* for reference.
                            metadata = {
                                'source_type': 'staff_directory_pdf',
                                'source_file': pdf_path.name,
                                'page_number': page_num + 1,
                                'table_index_on_page': table_index,
                                'row_number_on_page': row_num + 1, # Row number *on this specific page*
                                's_no': standardize_text(str(s_no)),
                                'name': standardize_text(str(name)),
                                'designation': standardize_text(str(designation)),
                                'email': email, # This should now contain the cleaned email from the correct column
                                'mobile': mobile, # This should now contain the cleaned mobile from the correct column
                                'scraped_at': datetime.utcnow().isoformat(), # Use UTC time for consistency
                                # Keep the indices found on the first page for reference
                                'email_col_index_used': email_col_index,
                                'mobile_col_index_used': mobile_col_index,
                                'headers_on_first_page': standardized_headers # Log the headers used
                            }

                            # Create and append the chunk
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