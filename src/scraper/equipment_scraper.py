"""
CRRI Equipment Scraper v2 - Smart Equipment Extraction

A redesigned scraper that correctly identifies and extracts only actual R&D 
testing equipment from CRRI website, eliminating false positives.

Key improvements:
- Two-phase scraping: Extract URLs from division pages, then validate
- Strict validation: Only yield pages with Working Principles or Applications
- Clean metadata: Proper categorization and division attribution
"""

import scrapy
import re
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class CrriEquipmentSpider(scrapy.Spider):
    name = 'crri_equipment'
    allowed_domains = ['crridom.gov.in']
    
    # The 7 R&D divisions that actually have equipment
    DIVISION_URLS = {
        'Bridge Engineering and Structures': 'https://crridom.gov.in/bridge-engineering-and-structures-division',
        'Geotechnical Engineering': 'https://crridom.gov.in/geotechnical-engineering-division',
        'Flexible Pavements': 'https://crridom.gov.in/flexible-pavements-division',
        'Pavement Evaluation': 'https://crridom.gov.in/pavement-evaluationdivision',
        'Rigid Pavements': 'https://crridom.gov.in/rigid-pavements-division',
        'Traffic Engineering and Safety': 'https://crridom.gov.in/traffic-engineering-and-safety-divsion',
        'Transport Planning': 'https://crridom.gov.in/transport-planning-division',
    }
    
    # Pages to explicitly skip (known non-equipment)
    SKIP_SLUGS = {
        'site-map', 'help', 'linking-policy', 'disclaimer', 'privacy-policy',
        'copyright', 'upcoming-events', 'feedback', 'web-information-manager',
        'recruitment', 'acsir', 'faculty', 'preamble', 'internship', 'human-resource',
        'articles', 'sexual-harassment', 'creche', 'guest-house', 'canteen',
        'right-to-information', 'rajbhasha', 'vigilance', 'personnel-cell',
        'main-stores', 'patents', 'about', 'contact', 'news', 'events', 'gallery',
        'division', 'staff', 'node', 'user', 'admin', 'past-directors', 'directors',
        'publications', 'facilities/', 'r-and-d', 'tender', 'crri-hq', 'organization'
    }
    
    # Track scraped URLs to prevent duplicates
    scraped_urls = set()
    
    def start_requests(self):
        """Phase 1: Start with all division pages to extract equipment links"""
        for division_name, url in self.DIVISION_URLS.items():
            yield scrapy.Request(
                url,
                callback=self.parse_division_page,
                meta={'division_name': division_name}
            )
    
    def parse_division_page(self, response):
        """Parse division page to extract numbered equipment links"""
        division_name = response.meta['division_name']
        
        # Extract all links from the main content area
        content = response.css('div.content, div.field-item, div.block-content')
        equipment_urls = set()
        
        # Method 1: Find numbered lists with equipment links
        # Pattern: [Equipment Name](https://crridom.gov.in/equipment-slug)
        for link in content.css('a'):
            href = link.css('::attr(href)').get()
            text = link.css('::text').get()
            
            if not href or not text:
                continue
            
            # Skip external links and known non-equipment pages
            if not href.startswith('/') and 'crridom.gov.in' not in href:
                continue
            
            # Get the slug from the URL
            full_url = response.urljoin(href)
            slug = urlparse(full_url).path.strip('/').lower()
            
            # Skip if slug contains known non-equipment patterns
            if any(skip in slug for skip in self.SKIP_SLUGS):
                continue
            
            # Skip division pages themselves
            if slug.endswith('-division') or slug.endswith('-divsion'):
                continue
            
            # This looks like a potential equipment page
            equipment_urls.add((full_url, text.strip()))
        
        self.logger.info(f"Found {len(equipment_urls)} potential equipment URLs in {division_name}")
        
        # Phase 2: Follow each equipment link and validate
        for url, title in equipment_urls:
            # Skip if already scraped (deduplication)
            if url in self.scraped_urls:
                continue
            self.scraped_urls.add(url)
            
            yield scrapy.Request(
                url,
                callback=self.parse_equipment_page,
                meta={
                    'division_name': division_name,
                    'expected_name': title
                }
            )
    
    def parse_equipment_page(self, response):
        """Parse and validate individual equipment pages"""
        division_name = response.meta['division_name']
        expected_name = response.meta.get('expected_name', '')
        
        # Get the page title/name
        equipment_name = response.css('h1.title::text').get()
        if not equipment_name:
            equipment_name = response.css('h1::text').get()
        if not equipment_name:
            equipment_name = expected_name
        
        equipment_name = equipment_name.strip() if equipment_name else 'Unknown'
        
        # Get full page HTML for h2 section detection
        # Use body or full response since div.content doesn't always contain the field content
        full_html = response.text
        
        # STRICT VALIDATION: Check for actual h2 section headers
        # Equipment pages have "Working Principles" and "Applications" as h2 headers
        has_working_principles = '<h2>Working Principles</h2>' in full_html
        has_applications = '<h2>Applications</h2>' in full_html
        
        # Must have at least Working Principles OR Applications as section header
        is_valid_equipment = has_working_principles or has_applications
        
        if not is_valid_equipment:
            self.logger.info(f"Skipping non-equipment page: {equipment_name} ({response.url})")
            return
        
        # Extract proper division from breadcrumb
        # Breadcrumb format: R&D Facilities > Flexible Pavements Division >
        breadcrumb_links = response.css('#breadcrumb .breadcrumb a::text').getall()
        actual_division = division_name  # Fallback to meta
        for bc in breadcrumb_links:
            bc_clean = bc.strip()
            # Check if this is a division name (contains 'Division' or is in our list)
            if 'Division' in bc_clean or bc_clean in [
                'Bridge Engineering and Structures', 'Geotechnical Engineering',
                'Flexible Pavements', 'Pavement Evaluation', 'Rigid Pavements',
                'Traffic Engineering and Safety', 'Transport Planning'
            ]:
                actual_division = bc_clean.replace(' Division', '')
                break
        
        self.logger.info(f"Valid equipment found: {equipment_name} ({actual_division})")
        
        # Extract detailed information
        content = response.css('div.field-item, div.content')
        
        # Extract sections
        working_principles = self.extract_section(response, 'Working Principles')
        applications = self.extract_section(response, 'Applications')
        user_instructions = self.extract_section(response, 'User Instructions')
        contact_details = self.extract_contact_details(response)
        instrument_details = self.extract_instrument_details(response)
        usage_charges = self.extract_usage_charges(response)
        images = self.extract_images(response)
        
        # Generate URL slug for deduplication
        url_slug = urlparse(response.url).path.strip('/')
        
        yield {
            'page_type': 'equipment',
            'equipment_name': equipment_name,
            'equipment_slug': url_slug,
            'division': actual_division,
            'url': response.url,
            
            # Content sections
            'working_principles': working_principles,
            'applications': applications,
            'user_instructions': user_instructions,
            'contact_details': contact_details,
            'instrument_details': instrument_details,
            'usage_charges': usage_charges,
            'images': images,
            
            # Validation metadata
            'has_working_principles': bool(working_principles),
            'has_applications': bool(applications),
            'has_user_instructions': bool(user_instructions),
            'has_usage_charges': bool(usage_charges),
            
            'scraped_at': datetime.utcnow().isoformat()
        }
    
    def extract_section(self, response, section_name):
        """Extract content from a named section (h2 heading)"""
        content_parts = []
        
        # Use full page HTML since div.content doesn't always contain equipment details
        full_html = response.text
        soup = BeautifulSoup(full_html, 'html.parser')
        
        # Find h2 with section name
        for h2 in soup.find_all(['h2', 'h3']):
            if section_name.lower() in h2.get_text().lower():
                # Get following content until next section
                next_elem = h2.find_next_sibling()
                while next_elem:
                    # Stop at next section header
                    if next_elem.name in ['h2', 'h3']:
                        break
                    
                    # Get text from paragraphs, divs, spans
                    if next_elem.name in ['p', 'div', 'span']:
                        text = next_elem.get_text(strip=True)
                        if text and len(text) > 5:  # Skip very short fragments
                            content_parts.append(text)
                    
                    # Also get list items
                    for li in next_elem.find_all('li'):
                        li_text = li.get_text(strip=True)
                        if li_text and li_text not in content_parts:
                            content_parts.append(f"• {li_text}")
                    
                    next_elem = next_elem.find_next_sibling()
                break
        
        return '\n'.join(content_parts) if content_parts else None
    
    def extract_instrument_details(self, response):
        """Extract Make, Model, Specification"""
        details = {}
        page_text = ' '.join(response.css('div.content ::text').getall())
        
        patterns = {
            'make': r'Make\s*[:\-]?\s*([^\n\r,]+)',
            'model': r'Model\s*[:\-]?\s*([^\n\r,]+)',
            'specification': r'Specification\s*[:\-]?\s*([^\n\r]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value and len(value) > 2:
                    details[key] = value
        
        return details if details else None
    
    def extract_contact_details(self, response):
        """Extract structured contact information"""
        contact = {}
        page_text = ' '.join(response.css('div.content ::text').getall())
        
        # Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', page_text)
        if email_match:
            contact['email'] = email_match.group(0)
        
        # Phone
        phone_match = re.search(r'(?:Tel|Phone|Telephone)[:\s]*([0-9\-\+\s]+)', page_text, re.I)
        if phone_match:
            contact['phone'] = phone_match.group(1).strip()
        else:
            # Try to find phone numbers directly
            phone_match = re.search(r'\+91[\-\s]?\d{2}[\-\s]?\d{8}', page_text)
            if phone_match:
                contact['phone'] = phone_match.group(0)
        
        # Address - common CRRI address
        if 'delhi-mathura road' in page_text.lower() or 'crri' in page_text.lower():
            contact['address'] = 'CSIR-CRRI, Delhi-Mathura Road, New Delhi-110025'
        
        return contact if contact else None
    
    def extract_usage_charges(self, response):
        """Extract usage charges table if present"""
        charges = []
        
        # Look for tables with pricing keywords
        for table in response.css('table'):
            table_text = ' '.join(table.css('::text').getall()).lower()
            
            if any(kw in table_text for kw in ['industry', 'university', 'charges', 'per test', 'per day', 'r&d']):
                rows = table.css('tr')
                headers = []
                
                for i, row in enumerate(rows):
                    cells = row.css('td::text, th::text').getall()
                    cells = [c.strip() for c in cells if c.strip()]
                    
                    if i == 0 and cells:
                        headers = cells
                    elif cells and len(cells) >= 2:
                        if headers:
                            row_data = dict(zip(headers, cells))
                        else:
                            row_data = {'category': cells[0], 'charges': cells[1]}
                        charges.append(row_data)
                
                if charges:
                    break
        
        return charges if charges else None
    
    def extract_images(self, response):
        """Extract equipment images"""
        images = []
        
        for img in response.css('div.content img'):
            src = img.css('::attr(src)').get()
            if src and not any(skip in src.lower() for skip in ['logo', 'icon', 'banner', 'flag']):
                images.append({
                    'url': response.urljoin(src),
                    'alt': img.css('::attr(alt)').get() or '',
                    'title': img.css('::attr(title)').get() or ''
                })
        
        return images if images else None
