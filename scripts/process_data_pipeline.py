"""
Data Processing Pipeline for CRRI Chatbot
Processes raw scraped data into clean, deduplicated chunks ready for embedding.
"""

import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set
from collections import defaultdict
import hashlib

# Configuration
RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
CHUNK_SIZE_THRESHOLD = 1000

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROCESSED_DATA_DIR / "pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataProcessor:
    """Main data processing class with modular methods for each data type."""
    
    def __init__(self):
        self.processed_chunks = []
        self.seen_content_hashes = set()
        self.stats = defaultdict(int)
    
    def standardize_text(self, text: str) -> str:
        """Clean and standardize text."""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def create_chunk(self, content: str, metadata: dict) -> dict:
        """Create a standardized chunk with content hash for deduplication."""
        content = self.standardize_text(content)
        content_hash = hash(content)
        
        if content_hash in self.seen_content_hashes:
            self.stats['duplicates_skipped'] += 1
            return None
        
        self.seen_content_hashes.add(content_hash)
        
        return {
            "page_content": content,
            "metadata": metadata
        }
    
    def process_staff_profiles(self, records: List[Dict]) -> None:
        """
        Process staff profile records.
        Creates ONE comprehensive chunk per staff member.
        """
        logger.info(f"Processing {len(records)} staff profile records...")
        
        staff_data = {}
        
        for record in records:
            name = self.standardize_text(record.get('name', ''))
            if not name:
                continue
            
            division = record.get('division', '')
            if not division:
                divisions = record.get('divisions', [])
                division = divisions[0] if divisions else 'Unknown'
            
            division = self.standardize_text(division)
            
            key = (name.lower(), division.lower())
            
            if key not in staff_data:
                staff_data[key] = record
            else:
                existing = staff_data[key]
                if len(str(record)) > len(str(existing)):
                    staff_data[key] = record
        
        for (name_key, div_key), record in staff_data.items():
            name = self.standardize_text(record.get('name', ''))
            title = self.standardize_text(record.get('title', ''))
            
            designations = record.get('designations', [])
            if not designations and record.get('designation'):
                designations = [record.get('designation')]
            designations = [self.standardize_text(d) for d in designations if d]
            
            divisions = record.get('divisions', [])
            if not divisions and record.get('division'):
                divisions = [record.get('division')]
            divisions = [self.standardize_text(d) for d in divisions if d]
            
            primary_division = divisions[0] if divisions else 'Unknown'
            
            cv_links = record.get('cv_links', [])
            
            text_parts = [
                f"Staff Member: {name}",
                f"Title: {title}" if title else None,
                f"Designations: {', '.join(designations)}" if designations else None,
                f"Primary Division: {primary_division}",
                f"All Divisions: {', '.join(divisions)}" if len(divisions) > 1 else None,
                f"CV Available: {', '.join(cv_links)}" if cv_links else None
            ]
            
            text = ". ".join([p for p in text_parts if p]) + "."
            
            metadata = {
                'source_type': 'staff',
                'page_type': 'staff_profile',
                'name': name,
                'title': title,
                'designations': designations,
                'divisions': divisions,
                'primary_division': primary_division,
                'cv_available': bool(cv_links),
                'cv_links': cv_links,
                'source_url': record.get('profile_url', record.get('url', 'unknown')),
                'scraped_at': record.get('scraped_at', datetime.utcnow().isoformat())
            }
            
            chunk = self.create_chunk(text, metadata)
            if chunk:
                self.processed_chunks.append(chunk)
                self.stats['staff_profiles'] += 1
    
    def extract_deadline_from_text(self, text: str) -> datetime:
        """Attempt to extract a deadline date from text."""
        if not text:
            return None
            
        patterns = [
            r'(?:deadline|last date).*?(\d{1,2}\s*(?:st|nd|rd|th)?\s+[a-zA-Z]+\s+\d{4})',
            r'(?:deadline|last date).*?(\d{1,2}[-/]\d{1,2}[-/]\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                dt = self.parse_deadline(date_str)
                if dt:
                    return dt
        return None

    def process_news(self, records: List[Dict]) -> None:
        """Process news records."""
        logger.info(f"Processing {len(records)} news records...")
        
        active_news_count = 0
        expired_news_count = 0
        current_time = datetime.now()
        
        for record in records:
            headline = self.standardize_text(record.get('headline', ''))
            if not headline:
                continue
            
            summary = self.standardize_text(record.get('brief_summary', ''))
            full_content = self.standardize_text(record.get('full_content', ''))
            
            content = full_content if full_content else summary
            
            if not content:
                continue
                
            if "expression of interest" in headline.lower() or "eoi" in headline.lower() or "tender" in headline.lower():
                deadline_dt = self.extract_deadline_from_text(content)
                if deadline_dt and deadline_dt < current_time:
                    logger.info(f"Skipping expired News/EOI: {headline} (Deadline: {deadline_dt.strftime('%Y-%m-%d')})")
                    expired_news_count += 1
                    continue
            
            text = f"News: {headline}. {content}"
            
            metadata = {
                'source_type': 'news',
                'page_type': 'news_detail',
                'headline': headline,
                'has_full_content': bool(full_content),
                'source_url': record.get('source_url', record.get('url', 'unknown')),
                'scraped_at': record.get('scraped_at', datetime.utcnow().isoformat())
            }
            
            chunk = self.create_chunk(text, metadata)
            if chunk:
                self.processed_chunks.append(chunk)
                self.stats['news'] += 1
                active_news_count += 1
                
        logger.info(f"News processed: {active_news_count} active, {expired_news_count} expired/skipped.")
    
    def process_equipment(self, records: List[Dict]) -> None:
        """Process equipment records with full details."""
        logger.info(f"Processing {len(records)} equipment records...")
        
        for record in records:
            name = self.standardize_text(record.get('equipment_name', ''))
            if not name:
                continue
            
            division = self.standardize_text(record.get('division', 'Unknown'))
            make = self.standardize_text(record.get('make', ''))
            model = self.standardize_text(record.get('model', ''))
            spec = self.standardize_text(record.get('specification', ''))
            
            working_principles = record.get('working_principles', '')
            if isinstance(working_principles, list):
                working_principles = ' '.join(str(x) for x in working_principles if x)
            working_principles = self.standardize_text(working_principles)
            
            applications = record.get('applications', '')
            if isinstance(applications, list):
                applications = ' '.join(str(x) for x in applications if x)
            applications = self.standardize_text(applications)
            
            usage_charges = self.standardize_text(str(record.get('usage_charges', '')))
            contact = self.standardize_text(str(record.get('contact_details', '')))
            
            text_parts = [
                f"Equipment: {name}",
                f"Division: {division}",
                f"Make: {make}" if make else None,
                f"Model: {model}" if model else None,
                f"Specification: {spec}" if spec else None,
                f"Working Principles: {working_principles}" if working_principles else None,
                f"Applications: {applications}" if applications else None,
                f"Usage Charges: {usage_charges}" if usage_charges else None,
                f"Contact: {contact}" if contact else None
            ]
            
            text = ". ".join([p for p in text_parts if p]) + "."
            
            metadata = {
                'source_type': 'equipment',
                'page_type': 'equipment_detail',
                'equipment_name': name,
                'division': division,
                'make': make,
                'model': model,
                'specification': spec,
                'working_principles': working_principles,
                'applications': applications,
                'usage_charges': usage_charges,
                'contact_details': contact,
                'source_url': record.get('source_url', record.get('url', 'unknown')),
                'scraped_at': record.get('scraped_at', datetime.utcnow().isoformat())
            }
            
            chunk = self.create_chunk(text, metadata)
            if chunk:
                self.processed_chunks.append(chunk)
                self.stats['equipment'] += 1
    
    def parse_deadline(self, date_str: str) -> datetime:
        """Parse tender deadline string into datetime object."""
        if not date_str or date_str.lower() == 'not specified':
            return None
        
        clean_str = re.sub(r'(\d+)\s*(st|nd|rd|th)', r'\1', date_str)
        clean_str = re.sub(r'\s+', ' ', clean_str).strip()
        
        formats = [
            "%d %b %Y - %I:%M%p",
            "%d %B %Y - %I:%M%p",
            "%d %B %Y",
            "%d %b %Y",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(clean_str, fmt)
            except ValueError:
                continue
        
        return None

    def process_tenders(self, records: List[Dict]) -> None:
        """Process tender records."""
        logger.info(f"Processing {len(records)} tender records...")
        
        active_tenders_count = 0
        expired_tenders_count = 0
        
        current_time = datetime.now()
        
        for record in records:
            title = self.standardize_text(record.get('tender_title', ''))
            if not title:
                continue
            
            ref_no = self.standardize_text(record.get('reference_no', ''))
            description = self.standardize_text(record.get('description', ''))
            deadline_str = self.standardize_text(record.get('bid_submission_deadline', 'Not specified'))
            
            deadline_dt = self.parse_deadline(deadline_str)
            if deadline_dt and deadline_dt < current_time:
                logger.info(f"Skipping expired tender: {title} (Deadline: {deadline_str})")
                expired_tenders_count += 1
                continue
            
            pdf_files = record.get('pdf_files', [])
            pdf_text_parts = []
            for pdf in pdf_files:
                p_title = self.standardize_text(pdf.get('title', 'Document'))
                p_url = pdf.get('url', '')
                if p_url:
                    pdf_text_parts.append(f"[{p_title}]({p_url})")
            
            pdf_section = "Documents: " + ", ".join(pdf_text_parts) if pdf_text_parts else ""
            
            text = f"Tender: {title}. Reference: {ref_no}. Deadline: {deadline_str}. {description}. {pdf_section}"
            
            metadata = {
                'source_type': 'tender',
                'page_type': 'tender_detail',
                'tender_title': title,
                'reference_no': ref_no,
                'bid_submission_deadline': deadline_str,
                'pdf_files': pdf_files,
                'source_url': record.get('source_url', record.get('url', 'unknown')),
                'scraped_at': record.get('scraped_at', datetime.utcnow().isoformat())
            }
            
            chunk = self.create_chunk(text, metadata)
            if chunk:
                self.processed_chunks.append(chunk)
                self.stats['tenders'] += 1
                active_tenders_count += 1
                
        logger.info(f"Tenders processed: {active_tenders_count} active, {expired_tenders_count} expired/skipped.")
    
    def process_events(self, records: List[Dict]) -> None:
        """Process event records."""
        logger.info(f"Processing {len(records)} event records...")
        
        for record in records:
            title = self.standardize_text(record.get('event_title', ''))
            if not title:
                continue
            
            description = self.standardize_text(record.get('description', ''))
            date = self.standardize_text(record.get('event_date', ''))
            
            text = f"Event: {title}. Date: {date}. {description}"
            
            metadata = {
                'source_type': 'event',
                'page_type': 'event_detail',
                'event_title': title,
                'event_date': date,
                'source_url': record.get('source_url', record.get('url', 'unknown')),
                'scraped_at': record.get('scraped_at', datetime.utcnow().isoformat())
            }
            
            chunk = self.create_chunk(text, metadata)
            if chunk:
                self.processed_chunks.append(chunk)
                self.stats['events'] += 1
    
    def load_and_process_file(self, filepath: Path) -> None:
        """Load a raw JSON file and process it based on its type."""
        logger.info(f"Loading file: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                logger.warning(f"Empty file: {filepath}")
                return
            
            filename = filepath.name.lower()
            
            if 'staff' in filename:
                staff_records = [r for r in data if r.get('page_type') == 'staff_profile']
                self.process_staff_profiles(staff_records)
            elif 'news' in filename:
                self.process_news(data)
            elif 'equipment' in filename:
                self.process_equipment(data)
            elif 'tender' in filename:
                self.process_tenders(data)
            elif 'event' in filename:
                self.process_events(data)
            else:
                logger.warning(f"Unknown file type: {filepath}")
        
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
    
    def save_processed_data(self, output_file: Path) -> None:
        """Save processed chunks to JSONL file."""
        logger.info(f"Saving {len(self.processed_chunks)} chunks to {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for chunk in self.processed_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        
        logger.info(f"✓ Saved {len(self.processed_chunks)} chunks")
        logger.info(f"Statistics: {dict(self.stats)}")


def main():
    """Main pipeline execution."""
    logger.info("=" * 80)
    logger.info("Starting CRRI Data Processing Pipeline")
    logger.info("=" * 80)
    
    # STEP 1: Process contacts.pdf first
    logger.info("STEP 1: Processing contacts.pdf...")
    pdf_processor_script = Path(__file__).parent / "clean_pdf_contacts.py"
    if pdf_processor_script.exists():
        import subprocess
        try:
            result = subprocess.run(
                ["python", str(pdf_processor_script)],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("✓ PDF processing completed")
            if result.stdout:
                logger.info(f"PDF processor output:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ PDF processing failed: {e}")
            logger.error(f"Error output: {e.stderr}")
    else:
        logger.warning(f"PDF processor script not found at {pdf_processor_script}")
    
    # STEP 2: Process raw JSON files
    logger.info("STEP 2: Processing raw JSON files...")
    processor = DataProcessor()
    
    raw_files = list(RAW_DATA_DIR.glob("*.json"))
    logger.info(f"Found {len(raw_files)} raw data files")
    
    for raw_file in raw_files:
        processor.load_and_process_file(raw_file)
    
    # STEP 3: Merge with processed PDF contacts
    logger.info("STEP 3: Merging with processed PDF contacts...")
    pdf_contacts_files = list(PROCESSED_DATA_DIR.glob("processed_pdf_contacts_*.jsonl"))
    if pdf_contacts_files:
        latest_pdf_contacts = max(pdf_contacts_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Found PDF contacts file: {latest_pdf_contacts.name}")
        
        try:
            with open(latest_pdf_contacts, 'r', encoding='utf-8') as f:
                for line in f:
                    chunk = json.loads(line.strip())
                    content_hash = hashlib.md5(chunk['page_content'].encode()).hexdigest()
                    if content_hash not in processor.seen_content_hashes:
                        processor.processed_chunks.append(chunk)
                        processor.seen_content_hashes.add(content_hash)
                        processor.stats['pdf_contacts'] += 1
            logger.info(f"✓ Merged {processor.stats['pdf_contacts']} PDF contact chunks")
        except Exception as e:
            logger.error(f"✗ Failed to merge PDF contacts: {e}")
    else:
        logger.warning("No processed PDF contacts file found")
    
    # STEP 4: Save final knowledge base
    logger.info("STEP 4: Saving final knowledge base...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = PROCESSED_DATA_DIR / f"knowledge_base_{timestamp}.jsonl"
    processor.save_processed_data(output_file)
    
    logger.info("=" * 80)
    logger.info("Pipeline completed successfully!")
    logger.info(f"Output: {output_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
