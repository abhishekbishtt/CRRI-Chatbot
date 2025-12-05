import scrapy
from urllib.parse import urljoin, urlparse, parse_qs  #used for URL manipulations
from datetime import datetime #used for timestamps
import re #used for cleaning email addresses

class CrriStaffOrganizationalSpider(scrapy.Spider):
    name = 'crri_staff_org'
    allowed_domains = ['crridom.gov.in']


    #initializing the class constructor
    def __init__(self, *args, **kwargs):     #this is the constructor of  the class
        super().__init__(*args, **kwargs)    # used super to inherit the parent class constructor  
        self.staff_profiles_scraped = set()   # set so that to avoid duplicate profile scrapes
   
   
    #creating a method start_requests
    def start_requests(self):
        """Start with Staff and Organizational Information URLs"""
        urls = [
            'https://crridom.gov.in/about-us  ',
            'https://crridom.gov.in/director-crri  ', 
            'https://crridom.gov.in/vision-mission-objectives  ',
            'https://crridom.gov.in/csir-leadership  ',
            'https://crridom.gov.in/research-council  ',
            'https://crridom.gov.in/hod-list  ',
            'https://crridom.gov.in/staff-list  ',
            'https://crridom.gov.in/staff-list/scientific  ',
            'https://crridom.gov.in/staff-list/technical  ',
            'https://crridom.gov.in/staff-list/administrative  ',
            'https://crridom.gov.in/staff-list/division-wise  ',
            'https://crridom.gov.in/staff-list/tabular  ',
        ]
        
        for url in urls:
            yield scrapy.Request(url, callback=self.parse_main_page)
    
    #method to parse the main page
    def parse_main_page(self, response):
        """Main parser that detects page type and routes to appropriate handler"""
        
        # Detect page type from URL and content
        page_type = self.detect_page_type(response.url, response)
        
        base_data = {
            'url': response.url,
            'page_type': page_type,
            'title': response.css('h1.title::text').get(),
            'breadcrumb': response.css('#breadcrumb .breadcrumb ::text').getall(),
            'scraped_at': datetime.utcnow().isoformat()
        }
        
        # Route to appropriate parser based on page type
        if page_type == 'staff_list':
            yield from self.parse_staff_list_page(response, base_data)
        elif page_type == 'staff_profile':
            yield from self.parse_staff_profile_page(response, base_data)
        elif page_type == 'division_wise_staff':
            yield from self.parse_division_wise_staff(response, base_data)
        elif page_type == 'research_council':
            yield from self.parse_research_council_page(response, base_data)
        elif page_type == 'hod_list':
            yield from self.parse_hod_list_page(response, base_data)
        elif page_type == 'csir_leadership':
            yield from self.parse_csir_leadership_page(response, base_data)
        elif page_type == 'vision_mission':
            yield from self.parse_vision_mission_page(response, base_data)
        elif page_type == 'director_page':
            yield from self.parse_director_page(response, base_data)
        else:
            yield from self.parse_generic_about_page(response, base_data)
    
    def detect_page_type(self, url, response):
        """Detect page type from URL patterns and content"""
        
        url_lower = url.lower()
        
        # Staff-related pages
        if '/staff-list' in url_lower:
            if '/scientific' in url_lower:
                return 'staff_list'
            elif '/technical' in url_lower:
                return 'staff_list'
            elif '/administrative' in url_lower:
                return 'staff_list'
            elif '/division-wise' in url_lower:
                return 'division_wise_staff'
            elif '/tabular' in url_lower:
                return 'staff_list'
            elif url_lower.endswith('/staff-list'):
                return 'staff_list'  # Director tab
                
        # Individual staff profiles (node URLs)
        elif '/node/' in url_lower and response.css('div.field-name-field-staff-photo'):
            return 'staff_profile'
            
        # Specific page types
        elif '/director-crri' in url_lower:
            return 'director_page'
        elif '/vision-mission' in url_lower:
            return 'vision_mission'
        elif '/csir-leadership' in url_lower:
            return 'csir_leadership'
        elif '/research-council' in url_lower:
            return 'research_council'
        elif '/hod-list' in url_lower:
            return 'hod_list'
            
        return 'generic_about'
    
    def parse_staff_list_page(self, response, base_data):
        """Parse staff list pages (Director, Scientific, Technical, Administrative)"""
        
        staff_members = []
        
        # Extract staff from grid layout
        staff_boxes = response.css('div.staff-box')
        
        for staff_box in staff_boxes:
            staff_data = self.extract_staff_box_data(staff_box, response)
            if staff_data:
                staff_members.append(staff_data)
                
                # If staff has profile link, scrape it
                if staff_data.get('profile_url'):
                    profile_url = staff_data['profile_url']
                    if profile_url not in self.staff_profiles_scraped:
                        self.staff_profiles_scraped.add(profile_url)
                        yield scrapy.Request(
                            profile_url,
                            callback=self.parse_staff_profile_page,
                            meta={'staff_basic_info': staff_data}
                        )
        
        # Handle pagination
        next_page_links = response.css('li.pager-next a::attr(href)').getall()
        for next_link in next_page_links:
            next_url = response.urljoin(next_link)
            yield scrapy.Request(next_url, callback=self.parse_main_page)
        
        # Yield staff list summary
        base_data.update({
            'staff_category': self.extract_staff_category(response.url),
            'staff_count': len(staff_members),
            'staff_members': staff_members,
            'has_pagination': bool(next_page_links)
        })
        
        yield base_data
    
    def extract_staff_box_data(self, staff_box, response):
        """Extract data from individual staff box"""
        
        name_element = staff_box.css('div.staff-box-name')
        name = name_element.css('::text').get()
        profile_link = name_element.css('a::attr(href)').get()
        
        # Handle name with link vs plain text
        if not name and profile_link:
            name = name_element.css('a::text').get()
            
        if not name:
            return None
            
        return {
            'name': name.strip(),
            'designation': staff_box.css('div.staff-box-designation::text').get(),
            'division': staff_box.css('div.staff-box-division::text').get(),
            'photo_url': staff_box.css('div.staff-box-img img::attr(src)').get(),
            'profile_url': response.urljoin(profile_link) if profile_link else None
        }
    
    def parse_staff_profile_page(self, response, base_data=None):
        """Parse individual staff member profile pages"""
        
        staff_info = response.meta.get('staff_basic_info', {}) # default to empty dict if not provided and meta is used in scrapy request to pass data between requests
        
        # Extract detailed profile information
        profile_data = {
            'name': response.css('h1.title::text').get(),
            'photo_url': response.css('div.field-name-field-staff-photo img::attr(src)').get(),
            'designations': response.css('div.field-name-field-designation .field-item::text').getall(),
            'divisions': response.css('div.field-name-field-division .field-item::text').getall(),
        }
        
        # Extract biodata/CV links
        cv_links = []
        biodata_section = response.css('div.field-name-field-biodata')
        if biodata_section:
            cv_urls = biodata_section.css('a::attr(href)').getall()
            cv_links = [response.urljoin(url) for url in cv_urls if url.endswith('.pdf')]
        
        # Merge with basic info from staff list
        staff_info.update(profile_data)
        staff_info.update({
            'cv_links': cv_links,
            'scraped_at': datetime.utcnow().isoformat(),
            'page_type': 'staff_profile'
        })
        
        yield staff_info
    
    def parse_division_wise_staff(self, response, base_data):
        """Parse division-wise staff selection page and trigger division queries"""
        
        # Extract division options
        division_options = response.css('select#edit-tid option[value!="All"]')
        
        divisions = []
        for option in division_options:
            division_value = option.css('::attr(value)').get()
            division_name = option.css('::text').get()
            
            if division_value and division_name:
                divisions.append({
                    'value': division_value,
                    'name': division_name.strip()
                })
                
                # Create URL for this division
                division_url = f"{response.url}?tid={division_value}"
                yield scrapy.Request(
                    division_url,
                    callback=self.parse_division_staff_results,
                    meta={'division_info': {'value': division_value, 'name': division_name.strip()}}
                )
        
        base_data.update({
            'divisions_available': divisions,
            'total_divisions': len(divisions)
        })
        
        yield base_data
    
    def parse_division_staff_results(self, response, base_data=None):
        """Parse results when a specific division is selected"""
        
        division_info = response.meta.get('division_info', {})
        
        # Extract staff from this division (same as staff list parsing)
        staff_members = []
        staff_boxes = response.css('div.staff-box')
        
        for staff_box in staff_boxes:
            staff_data = self.extract_staff_box_data(staff_box, response)
            if staff_data:
                staff_data['source_division'] = division_info.get('name')
                staff_members.append(staff_data)
                
                # Follow profile links to get full details
                if staff_data.get('profile_url'):
                    profile_url = staff_data['profile_url']
                    if profile_url not in self.staff_profiles_scraped:
                        self.staff_profiles_scraped.add(profile_url)
                        yield scrapy.Request(
                            profile_url,
                            callback=self.parse_staff_profile_page,
                            meta={'staff_basic_info': staff_data}
                        )
        
        yield {
            'page_type': 'division_staff_results',
            'division': division_info,
            'staff_count': len(staff_members),
            'staff_members': staff_members,
            'scraped_at': datetime.utcnow().isoformat()
        }
    
    def parse_research_council_page(self, response, base_data):
        """Parse Research Council page with member table and PDF links"""
        
        # Extract member table
        members = []
        table_rows = response.css('table tbody tr')
        
        for row in table_rows:
            cells = row.css('td')
            if len(cells) >= 3:
                member_data = {
                    'serial_no': cells[0].css('::text').get(),
                    'name_address': ' '.join(cells[1].css('::text').getall()).strip(),
                    'post': cells[2].css('::text').get()
                }
                members.append(member_data)
        
        # Extract PDF links for meeting minutes
        pdf_links = []
        pdf_elements = response.css('span.file a[href$=".pdf"]')
        for pdf_link in pdf_elements:
            pdf_data = {
                'title': pdf_link.css('::text').get(),
                'url': response.urljoin(pdf_link.css('::attr(href)').get()),
                'size': pdf_link.xpath('following-sibling::text()').re_first(r'\(([\d\.]+ [A-Z]+)\)')
            }
            pdf_links.append(pdf_data)
        
        base_data.update({
            'council_composition': response.css('div.field-item p::text').get(),
            'members': members,
            'meeting_minutes_pdfs': pdf_links,
            'member_count': len(members),
            'pdf_count': len(pdf_links)
        })
        
        yield base_data
    
    def parse_hod_list_page(self, response, base_data):
        """Parse Head of Divisions/Sections table"""
        
        heads = []
        table_rows = response.css('table.views-table tbody tr')
        
        for row in table_rows:
            cells = row.css('td')
            if len(cells) >= 5:
                head_data = {
                    'serial_no': cells[0].css('::text').get(),
                    'name': cells[1].css('::text').get(),
                    'designation': cells[2].css('::text').get(),
                    'division': cells[3].css('::text').get(),
                    'email': self.clean_email(cells[4].css('::text').getall())
                }
                heads.append(head_data)
        
        base_data.update({
            'heads_of_divisions': heads,
            'head_count': len(heads)
        })
        
        yield base_data
    
    def clean_email(self, email_parts):
        """Clean obfuscated email addresses"""
        if not email_parts:
            return None
            
        email_text = ' '.join(email_parts)
        # Replace [dot] with . and [at] with @
        email_text = email_text.replace('[dot]', '.').replace('[at]', '@')
        # Extract clean email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email_text)
        return email_match.group() if email_match else email_text.strip()
    
    def parse_csir_leadership_page(self, response, base_data):
        """Parse CSIR Leadership table"""
        
        leaders = []
        table_rows = response.css('table tbody tr')
        
        for row in table_rows:
            leader_text = row.css('h3::text').get()
            description = row.css('p::text').get()
            image_url = row.css('img::attr(src)').get()
            
            if leader_text:
                leaders.append({
                    'position': leader_text.strip(),
                    'description': description.strip() if description else None,
                    'image_url': response.urljoin(image_url) if image_url else None
                })
        
        base_data.update({
            'leadership_hierarchy': leaders,
            'leader_count': len(leaders)
        })
        
        yield base_data
    
    def parse_vision_mission_page(self, response, base_data):
        """Parse Vision, Mission and Key Objectives page"""
        
        # Extract Vision
        vision_section = response.css('h3:contains("Vision")').xpath('following-sibling::p[1]').get()
        
        # Extract Mission points
        mission_points = response.css('h3:contains("Mission")').xpath('following-sibling::ul[1]/li::text').getall()
        
        # Extract PDF links
        pdf_links = []
        pdf_elements = response.css('span.file a[href$=".pdf"]')
        for pdf_link in pdf_elements:
            pdf_links.append({
                'title': pdf_link.css('::text').get(),
                'url': response.urljoin(pdf_link.css('::attr(href)').get())
            })
        
        base_data.update({
            'vision': vision_section,
            'mission_points': mission_points,
            'related_documents': pdf_links
        })
        
        yield base_data
    
    def parse_director_page(self, response, base_data):
        """Parse Director information page"""
        
        # Extract director biography
        bio_paragraphs = response.css('div.field-item p::text').getall()
        biography = '\n'.join(bio_paragraphs) if bio_paragraphs else None
        
        # Extract director image
        director_image = response.css('div.field-item img::attr(src)').get()
        
        # .update() is used to update the dictionary with new key-value pairs
        base_data.update({
            'director_name': base_data.get('title'),
            'biography': biography,
            'photo_url': response.urljoin(director_image) if director_image else None
        })
        
        yield base_data
    
    def parse_generic_about_page(self, response, base_data):
        """Parse other About Us pages"""
        
        # Extract main content
        content_paragraphs = response.css('div.field-item p::text').getall()
        content = '\n'.join(content_paragraphs) if content_paragraphs else None
        
        # Extract any tables
        tables = response.css('table').getall()
        
        # Extract PDF links
        pdf_links = response.css('a[href$=".pdf"]::attr(href)').getall()
        pdf_links = [response.urljoin(url) for url in pdf_links]
        
        base_data.update({
            'content': content,
            'tables_html': tables,
            'pdf_links': pdf_links,
            'has_tables': len(tables) > 0,
            'pdf_count': len(pdf_links)
        })
        
        yield base_data
    
    def extract_staff_category(self, url):
        """Extract staff category from URL"""
        if '/scientific' in url:
            return 'scientific'
        elif '/technical' in url:
            return 'technical' 
        elif '/administrative' in url:
            return 'administrative'
        elif url.endswith('/staff-list'):
            return 'director'
        else:
            return 'unknown'