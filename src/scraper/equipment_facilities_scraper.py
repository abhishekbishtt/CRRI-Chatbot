import scrapy
from urllib.parse import urljoin
import re
from datetime import datetime
from bs4 import BeautifulSoup

class CrriEquipmentFacilitiesSpider(scrapy.Spider):
    name = 'crri_equipment_facilities'
    allowed_domains = ['crridom.gov.in']
    
    def start_requests(self):
        """Start with R&D Facilities main page and division pages"""
        base_urls = [
            'https://crridom.gov.in/r-and-d-facilities  ',
            'https://crridom.gov.in/bridge-engineering-and-structures-division  ',
            'https://crridom.gov.in/geotechnical-engineering-division  ', 
            'https://crridom.gov.in/flexible-pavements-division  ',
            'https://crridom.gov.in/pavement-evaluationdivision  ',
            'https://crridom.gov.in/rigid-pavements-division  ',
            'https://crridom.gov.in/traffic-engineering-and-safety-divsion  ',
            'https://crridom.gov.in/transport-planning-division  '
        ]
        
        for url in base_urls:
            yield scrapy.Request(url, callback=self.parse_division_page)
    
    def parse_division_page(self, response):
        """Parse division pages to find equipment links"""
        
        # Extract division info
        division_name = response.css('h1.title::text').get()
        breadcrumb = response.css('#breadcrumb .breadcrumb ::text').getall()
        
        # Find all equipment/facility links in grid layout
        facility_links = []
        
        # Look for facility cards/boxes
        facility_boxes = response.css('div.views-row, div.facility-box, div.equipment-box')
        for box in facility_boxes:
            link = box.css('a::attr(href)').get()
            title = box.css('a::text, h3::text, .title::text').get()
            image = box.css('img::attr(src)').get()
            
            if link and not any(skip in link.lower() for skip in ['staff', 'node']):
                facility_links.append({
                    'url': response.urljoin(link),
                    'title': title.strip() if title else None,
                    'preview_image': response.urljoin(image) if image else None
                })
        
        # Also look for direct links in content - IMPROVED DETECTION
        # Get all links from the main content area
        content_links = response.css('div.content a::attr(href)').getall()
        
        # Define patterns that indicate this is likely an equipment/facility page
        # Include common equipment-related keywords
        equipment_keywords = [
            'tester', 'machine', 'equipment', 'apparatus', 'system', 
            'test', 'instrument', 'device', 'analyzer', 'meter',
            'capo', 'pit', 'utm', 'pundit', 'strain', 'pull-out',
            'foaming', 'moisture', 'pneumatic', 'modulus', 'abrasion',
            'skid', 'ultrasonic', 'pile', 'structural'
        ]
        
        # Patterns to exclude (non-equipment pages)
        exclude_patterns = [
            'staff', 'node/', 'user/', 'admin/', 'login',
            'contact-us', 'about', 'home', 'news', 'events',
            'gallery', 'publication', 'tender', 'career',
            'linkedin.com', 'facebook.com', 'twitter.com', 'youtube.com',
            'javascript:', 'mailto:', '#'
        ]
        
        for link in content_links:
            link_lower = link.lower()
            
            # Skip if matches exclude patterns
            if any(exclude in link_lower for exclude in exclude_patterns):
                continue
            
            # Include if matches equipment keywords OR if it's a relative link to a specific page
            # (relative links from division pages are usually equipment pages)
            is_equipment_keyword = any(keyword in link_lower for keyword in equipment_keywords)
            is_relative_equipment_link = link.startswith('/') and len(link) > 1 and not link.startswith('//')
            
            if is_equipment_keyword or is_relative_equipment_link:
                full_url = response.urljoin(link)
                # Avoid duplicates
                if not any(f['url'] == full_url for f in facility_links):
                    facility_links.append({'url': full_url})
        
        # Yield division summary
        yield {
            'page_type': 'facilities_division',
            'division_name': division_name,
            'breadcrumb': breadcrumb,
            'url': response.url,
            'facility_count': len(facility_links),
            'facilities_overview': facility_links,
            'scraped_at': datetime.utcnow().isoformat()
        }
        
        # Follow each facility link
        for facility in facility_links:
            yield scrapy.Request(
                facility['url'], 
                callback=self.parse_facility_detail,
                meta={'division': division_name}
            )
        
        # Handle pagination
        next_page = response.css('li.pager-next a::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_division_page)
    
    def parse_facility_detail(self, response):
        """Parse individual equipment/facility pages with full details"""
        
        division = response.meta.get('division')
        breadcrumb = response.css('#breadcrumb .breadcrumb ::text').getall()
        
        base_data = {
            'page_type': 'facility_detail',
            'equipment_name': response.css('h1.title::text').get(),
            'division': division,
            'breadcrumb': breadcrumb,
            'url': response.url,
            'scraped_at': datetime.utcnow().isoformat()
        }
        
        # Extract all structured sections
        content = response.css('div.field-item')
        
        # 1. Instrument Details
        instrument_details = self.extract_instrument_details(content)
        
        # 2. Working Principles
        working_principles = self.extract_section_content(content, 'Working Principles')
        
        # 3. Applications
        applications = self.extract_list_content(content, 'Applications')
        
        # 4. User Instructions
        user_instructions = self.extract_list_content(content, 'User Instructions')
        
        # 5. Contact Details
        contact_details = self.extract_contact_details(content)
        
        # 6. Usage Charges Table
        usage_charges = self.extract_usage_charges_table(response)
        
        # 7. Images
        images = self.extract_images(response)
        
        # 8. Language
        language = response.css('div.form-item:contains("Language") ::text').re_first(r'(?i)english|hindi|both')
        
        # Combine all data
        base_data.update({
            'instrument_details': instrument_details,
            'working_principles': working_principles,
            'applications': applications,
            'user_instructions': user_instructions,
            'contact_details': contact_details,
            'usage_charges': usage_charges,
            'images': images,
            'language': language
        })
        
        yield base_data
    
    def extract_instrument_details(self, content):
        """Extract Make, Model, Specification from instrument details section"""
        details = {}
        
        # Look for patterns like "Make : Value" or "Model : Value"
        text_content = ' '.join(content.css('::text').getall())
        
        patterns = {
            'make': r'Make\s*:?\s*([^\n\r]+)',
            'model': r'Model\s*:?\s*([^\n\r]+)', 
            'specification': r'Specification\s*:?\s*([^\n\r]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                details[key] = match.group(1).strip()
        
        return details
    
    def extract_section_content(self, content, section_name):
        """Extract content from a specific section like Working Principles"""
        section_text = []
        
        # Find section header and extract following content
        for element in content:
            html_content = element.get()
            if section_name.lower() in html_content.lower():
                # Parse with BeautifulSoup for better handling
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find the section header
                header = soup.find(string=re.compile(section_name, re.IGNORECASE))
                if header:
                    # Get parent element and find following content
                    parent = header.parent
                    if parent:
                        # Extract text from following paragraphs
                        for sibling in parent.find_next_siblings(['p', 'div']):
                            text = sibling.get_text(strip=True)
                            if text and not any(stop in text.lower() for stop in ['applications', 'contact', 'user instructions']):
                                section_text.append(text)
        
        return '\n'.join(section_text) if section_text else None
    
    def extract_list_content(self, content, section_name):
        """Extract bulleted or numbered lists from sections like Applications"""
        items = []
        
        for element in content:
            html_content = element.get()
            if section_name.lower() in html_content.lower():
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find lists after section header
                lists = soup.find_all(['ul', 'ol'])
                for lst in lists:
                    for li in lst.find_all('li'):
                        text = li.get_text(strip=True)
                        if text:
                            items.append(text)
        
        return items if items else None
    
    def extract_contact_details(self, content):
        """Extract structured contact information"""
        contact_info = {}
        
        for element in content:
            html_content = element.get()
            if 'contact' in html_content.lower():
                soup = BeautifulSoup(html_content, 'html.parser')
                text = soup.get_text()
                
                # Extract phone numbers
                phone_match = re.search(r'(?i)telephone?:?\s*([0-9\-\+\s]+)', text)
                if phone_match:
                    contact_info['telephone'] = phone_match.group(1).strip()
                
                # Extract emails (handle obfuscation)
                email_match = re.search(r'(?i)email?:?\s*([^\n\r]+)', text)
                if email_match:
                    email = email_match.group(1).strip()
                    # Clean email obfuscation
                    email = email.replace('[dot]', '.').replace('[at]', '@')
                    contact_info['email'] = email
                
                # Extract address
                if 'delhi-mathura road' in text.lower():
                    contact_info['address'] = 'CSIR-Central Road Research Institute, Delhi-Mathura Road, P.O: CRRI, New Delhi-110025'
                
                # Extract department
                dept_match = re.search(r'(?i)head,?\s*([^\n\r]+)', text)
                if dept_match:
                    contact_info['department'] = dept_match.group(1).strip()
        
        return contact_info if contact_info else None
    
    def extract_usage_charges_table(self, response):
        """Extract the instrument usage charges pricing table"""
        charges = []
        
        # Find the charges table
        table = response.css('table:contains("Industry"), table:contains("University")')
        if table:
            # Extract headers
            headers = table.css('th::text, thead td::text').getall()
            headers = [h.strip() for h in headers if h.strip()]
            
            # Extract rows
            rows = table.css('tbody tr')
            for row in rows:
                cells = row.css('td::text').getall()
                cells = [c.strip() for c in cells]
                
                if len(cells) >= len(headers):
                    row_data = dict(zip(headers, cells))
                    charges.append(row_data)
        
        return charges if charges else None
    
    def extract_images(self, response):
        """Extract all equipment images with descriptions"""
        images = []
        
        img_elements = response.css('div.content img')
        for img in img_elements:
            src = img.css('::attr(src)').get()
            alt = img.css('::attr(alt)').get()
            title = img.css('::attr(title)').get()
            
            if src:
                images.append({
                    'url': response.urljoin(src),
                    'alt_text': alt,
                    'title': title,
                    'description': alt or title
                })
        
        return images if images else None