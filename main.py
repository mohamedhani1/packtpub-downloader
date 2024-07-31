import requests
import configparser
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
import glob
import os
from zipfile import ZipFile
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import pytz
from uuid import uuid4
import sys


class Utils:
    def __init__(self):
        pass

    @staticmethod
    def remove_three_dot_tags(xml_string):
        pattern = r"(<[^>]*>)(.*?)(\.\.\.\s*.*?)(</[^>]*>)"  # Matches opening tag, content, "...", closing tag
        replacement = r"\1\2\4"  # Keeps opening and closing tags, removes "... content"
        return re.sub(pattern, replacement, xml_string, flags=re.DOTALL)


    @staticmethod
    def clean_text(text):
        ok = re.compile(r'[^\\/:*,?!"&’…– <>|_]')
        text = "".join(x if ok.match(x) else " " for x in text)
        text = re.sub(r"\.+$", "", text.strip())
        text = ' '.join([word for word in text.split(' ') if word != ''])
        return text

    
    @staticmethod
    def filter_attributes(xml_content):
        # Parse the XML content
        root = ET.fromstring(xml_content)
        
        # Define allowed attributes
        allowed_attributes = [
            "src",
            "about", "accesskey", "aria-activedescendant", "aria-atomic", 
            "aria-autocomplete", "aria-busy", "aria-checked", "aria-colcount", 
            "aria-colindex", "aria-colspan", "aria-controls", "aria-current", 
            "aria-describedby", "aria-description", "aria-details", 
            "aria-disabled", "aria-errormessage", "aria-expanded", 
            "aria-flowto", "aria-haspopup", "aria-hidden", "aria-invalid", 
            "aria-keyshortcuts", "aria-label", "aria-labelledby", "aria-level", 
            "aria-live", "aria-modal", "aria-multiline", "aria-multiselectable", 
            "aria-orientation", "aria-owns", "aria-posinset", "aria-pressed", 
            "aria-readonly", "aria-relevant", "aria-required", 
            "aria-roledescription", "aria-rowcount", "aria-rowindex", 
            "aria-rowspan", "aria-selected", "aria-setsize", "aria-sort", 
            "aria-valuemax", "aria-valuemin", "aria-valuenow", 
            "aria-valuetext", "autocapitalize", "autofocus", "class", "content", 
            "contenteditable", "datatype", "dir", "draggable", "enterkeyhint", 
            "epub:type", "hidden", "id", "inert", "inlist", "inputmode", "is", 
            "itemid", "itemprop", "itemref", "itemscope", "itemtype", "lang", 
            "nonce", "ns:alphabet", "ns:ph", "onauxclick", "onbeforeinput", 
            "onbeforematch", "onblur", "oncancel", "oncanplay", 
            "oncanplaythrough", "onchange", "onclick", "onclose", 
            "oncontextlost", "oncontextmenu", "oncontextrestored", "oncopy", 
            "oncuechange", "oncut", "ondblclick", "ondrag", "ondragend", 
            "ondragenter", "ondragleave", "ondragover", "ondragstart", "ondrop", 
            "ondurationchange", "onemptied", "onended", "onerror", "onfocus", 
            "onformdata", "ongotpointercapture", "oninput", "oninvalid", 
            "onkeydown", "onkeypress", "onkeyup", "onload", "onloadeddata", 
            "onloadedmetadata", "onloadstart", "onlostpointercapture", 
            "onmousedown", "onmouseenter", "onmouseleave", "onmousemove", 
            "onmouseout", "onmouseover", "onmouseup", "onpaste", "onpause", 
            "onplay", "onplaying", "onpointercancel", "onpointerdown", 
            "onpointerenter", "onpointerleave", "onpointermove", "onpointerout", 
            "onpointerover", "onpointerrawupdate", "onpointerup", "onprogress", 
            "onratechange", "onreset", "onresize", "onscroll", "onscrollend", 
            "onsecuritypolicyviolation", "onseeked", "onseeking", "onselect", 
            "onslotchange", "onstalled", "onsubmit", "onsuspend", "ontimeupdate", 
            "ontoggle", "onvolumechange", "onwaiting", "onwheel", "prefix", 
            "property", "rel", "resource", "rev", "role", "slot", "spellcheck", 
            "style", "tabindex", "title", "translate", "typeof", "vocab", 
            "xml:base", "xml:lang", "xml:space"
        ]
        
        # Iterate through all elements and attributes
        for elem in root.iter():
            # Store a list of attributes to delete
            attrs_to_delete = []
            for attr in elem.attrib:
                # If attribute is not in allowed list and not an essential attribute, mark it for deletion
                if attr not in allowed_attributes:
                    attrs_to_delete.append(attr)
            # Delete marked attributes
            for attr_to_delete in attrs_to_delete:
                del elem.attrib[attr_to_delete]
                
            # Fix unclosed <html:pre> tags
            if elem.tag == '{http://www.w3.org/1999/xhtml}pre':
                # Find the immediate parent tag of <html:pre>
                parent = None
                for e in root.iter():
                    for child in e:
                        if child == elem:
                            parent = e
                if parent is not None:
                    # Replace <html:pre> with its text content
                    if elem.text:
                        if parent.text is None:
                            parent.text = ''
                        parent.text += elem.text.replace('...', '')  # Remove "..."
                    # Append <html:pre>'s tail content to its parent's text
                    if elem.tail:
                        if parent.text is None:
                            parent.text = ''
                        parent.text += elem.tail.replace('...', '')  # Remove "..."
                    # Remove the <html:pre> element from its parent
                    parent.remove(elem)
        
        # Return the filtered XML content
        return ET.tostring(root, encoding="unicode")

    
    def disable_internal_hrefs(self, html_string, output_path, title):
        soup = BeautifulSoup(html_string, 'lxml')
        # Disable internal hrefs
        for a_tag in soup.find_all('a'):
            if a_tag.get('href'):
                href = a_tag['href']
                if not urlparse(href).netloc:  # Check if it's a relative URL
                    del a_tag['href']  # Remove href attribute for internal links
        
        # Download images and make them internal hrefs
        for img_tag in soup.find_all('img', src=True):
            src = img_tag['src']
            img_url = src
            if urlparse(src).netloc:  # Check if it's an external URL
                img_filename = src.split('/')[-1]
                image_final_name = os.path.join(output_path, img_filename)
                if not os.path.exists(image_final_name):
                    img_response = requests.get(img_url)
                    if img_response.status_code == 200:
                        img_data = img_response.content
                        with open(image_final_name, 'wb') as img_file:
                            img_file.write(img_data)

                img_tag['src'] = '../Images/' + img_filename  # Change src to internal href
                        
        soup.html["xmlns"] = "http://www.w3.org/1999/xhtml"
        soup.html["xmlns:epub"] = "http://www.idpf.org/2007/ops"
        head_tag = soup.new_tag("head")
        title_tag = soup.new_tag("title")
        title_tag.string = soup.find('h1').get_text() if soup.find('h1') else title
        head_tag.append(title_tag)
        soup.html.insert(0, head_tag)
        soup = soup.prettify()
        soup_str = str(soup).replace('<?xml encoding="utf-8" ?>', '<?xml version="1.0" encoding="utf-8"?>\n').replace(' type="square"', '').replace(' type="disc"', '').replace(' type="bullet"', '')
        soup_str = self.remove_three_dot_tags(self.filter_attributes(soup_str))
        return soup_str


class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

    def create_config(self):
        self.config['Credentials'] = {
            'email': '',
            'password': '',
            'access_token': '',
            'refresh_token': ''
        }
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def get_credentials(self):
        if 'Credentials' in self.config:
            return self.config['Credentials']
        else:
            return None

    def update_credentials(self, email=None, password=None, access_token=None, refresh_token=None):
        if email:
            self.config['Credentials']['email'] = email
        if password:
            self.config['Credentials']['password'] = password
        if access_token:
            self.config['Credentials']['access_token'] = access_token
        if refresh_token:
            self.config['Credentials']['refresh_token'] = refresh_token

        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def delete_config(self):
        self.config.remove_section('Credentials')
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)


class PacktPub:

    HEADERS = {
        'Host': 'subscription.packtpub.com',
        'Accept': 'application/json, text/plain, */*',
        'Mobile-Api-Token': '374b30ba603eeef8fa2d89e6502db4f49ad5e29ac4e1b2340368a55ee7a79ad2',
        'Authorization': 'Bearer',
        'Content-Type': 'application/json',
        'User-Agent': 'okhttp/4.9.2'
        }
    
    COOKIES = {
        'packt_session': 'xwjjR2q6frLW6237fZrHdF2bG44KUnPpZ98SOSmP',
    }

    REFRESH_TOKENS_API = 'https://services.packtpub.com/auth-v1/users/me/tokens'
    
    DOMAIN = 'https://subscription.packtpub.com'
    LOGIN_API = f'{DOMAIN}/api/mobile/auth/login'
    PRODUCT_API = f'{DOMAIN}/api/mobile/product/{{}}'
    
    
    def __init__(self, email=None, pwd=None):
        self.config = ConfigManager('config/config.ini')
        self._email = email
        self._pwd = pwd
        self._access_token = None
        self._refresh_token = None
        self._user_id = None

        self.session = requests.session()
        self.session.headers.update(self.HEADERS)
        self.session.cookies.update(self.COOKIES)

        self.__check_credentials()
        if not self._access_token or not self._refresh_token:
            self.login()
            self.HEADERS['Authorization'] = f'Bearer {self._access_token}'
            self.session.headers.update(self.HEADERS)
        else:
            self.refresh_token()

    def __check_credentials(self):
        credentials = self.config.get_credentials()
        if not credentials:
            self.config.create_config()
            credentials = self.config.get_credentials()

        if not credentials['email']:
            self._email = input('Add your email: ') if not self._email else self._email
            self.config.update_credentials(email=self._email)

        if not credentials['password']:
            self._pwd = input('Add your password: ') if not self._pwd else self._pwd
            self.config.update_credentials(password=self._pwd)

        self._email = credentials['email']
        self._pwd = credentials['password']
        self._access_token = credentials['access_token']
        self._refresh_token = credentials['refresh_token']

    def login(self):

        json_data = {
            'username': self._email,
            'password': self._pwd,
            'error': False,
            'loading': False,
            'message': 'There is some technical issue please try again.',
        }

        response = self.session.post(
            self.LOGIN_API,
            json=json_data
        )
        response_json = response.json()
        message = response_json.get('message').lower()
        data = response_json.get('data')
        if message == 'success':
            print('Valid Token.')
            tokens = data.get('tokens')
            self._access_token = tokens.get('access')
            self._refresh_token = tokens.get('refresh')
            self.config.update_credentials(access_token=self._access_token)
            self.config.update_credentials(refresh_token=self._refresh_token)
        else:
            print('Invalid Login!')
            sys.exit(input(message))


    # REFRESH TOKEN
    def refresh_token(self):
        headers = self.HEADERS.copy()
        headers['Host'] = 'services.packtpub.com'
        json_data = {
            'refresh': self._refresh_token,
        }
        response = requests.post(
            self.REFRESH_TOKENS_API,
            json=json_data,
            headers=headers,
            cookies=self.COOKIES
        )
        
        response_json = response.json()
        if response_json.get('status') == 200:
            data = response_json.get('data')
            self._access_token = data.get('access')
            self._refresh_token = data.get('refresh')
        else:
            self.login()
        

    def get_product(self, product_id):
        response = self.session.get(
            self.PRODUCT_API.format(product_id),
        )
        return response.json()



    def get_book_chapters(self, product_id, chapter_num, chapter_name):
        headers = {
            "Host": "subscription.packtpub.com",
            "accept": "application/json, text/plain, */*",
            "mobile-api-token": "374b30ba603eeef8fa2d89e6502db4f49ad5e29ac4e1b2340368a55ee7a79ad2",
            "authorization": "Bearer " + self._access_token,
            "accept-encoding": "gzip",
            "cookie": "packt_session=" + self.COOKIES['packt_session'],
            "user-agent": "okhttp/4.9.2",
            "if-modified-since": "Sat, 20 Apr 2024 10:46:29 GMT"
        }

        url = f"https://subscription.packtpub.com/api/mobile/product/book/{product_id}/{chapter_num}/{chapter_name}"

        response = requests.get(url, headers=headers)
        '''response = requests.get(
            self.PRODUCT_API.format(f'book/{product_id}/{chapter_num}/{chapter_name}'),
            headers=self.HEADERS,
            cookies=self.COOKIES
        )'''
        return response.json()

    def get_toc(self, product_id):
        headers = {
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://account.packtpub.com/',
            'sec-ch-ua-mobile': '?0',
            'Authorization': "Bearer " + self._access_token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
        }
        return requests.get(f'https://static.packt-cdn.com/products/{product_id}/toc', headers=headers).json()


class EPUB:
    EPUB_DIR = 'temp'
    
    def __init__(self, name, author, description):
        self.name = name
        self.author = author
        self.description = description
        self.cover_ext = None
        self.output_path = self.name + '.epub'
        self.book_uuid = uuid4()
        self.main_dir = os.path.join(self.EPUB_DIR, name)
        self.meta_info_path = os.path.join(self.main_dir, 'META-INF')
        self.OEBPS_path = os.path.join(self.main_dir, 'OEBPS')
        self.images_path = os.path.join(self.OEBPS_path, 'Images')
        self.styles_path = os.path.join(self.OEBPS_path, 'Styles')
        self.text_path = os.path.join(self.OEBPS_path, 'Text')
        self.create_folders()

        self.toc_content = ''
        self.manifest = ''
        self.spine = ''
        self.ncx_content = ''
        self.css_path = None
        self.manifest += '<item id="cover" href="Text/cover.xhtml" media-type="application/xhtml+xml"/>\n'
        self.manifest += '<item id="toc.xhtml" href="Text/toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
        self.spine += '<itemref idref="cover" linear="no"/>\n'
        self.spine += '<itemref idref="toc.xhtml"/>\n'

    def create_folders(self):
        for folder in [self.EPUB_DIR, self.meta_info_path,self.OEBPS_path,self.images_path,self.styles_path,self.text_path]:
            
            os.makedirs(folder, exist_ok=True)

    def create_mimetype(self):
        with open(os.path.join(self.main_dir, 'mimetype'), 'w') as f:
            f.write('application/epub+zip')

    def create_container_xml(self):
        container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
      <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
      </rootfiles>
    </container>'''
        with open(os.path.join(self.main_dir, 'META-INF', 'container.xml'), 'w') as f:
            f.write(container_xml)

    def create_content_opf(self):
        now = datetime.now(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        # Add the Table of Contents (TOC) file to the manifest
        manifest_with_toc = self.manifest + '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        content_opf = f'''<?xml version="1.0" encoding="utf-8"?>
    <package version="3.0" unique-identifier="bookid" prefix="ibooks: http://vocabulary.itunes.apple.com/rdf/ibooks/vocabulary-extensions-1.0/" xmlns="http://www.idpf.org/2007/opf">
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
            <dc:title>{self.name}</dc:title>
            <dc:identifier id="bookid">urn:uuid:{self.book_uuid}</dc:identifier>
            <dc:language>en-US</dc:language>
            <dc:date>{now}</dc:date>
            <dc:creator id="author">{self.author}</dc:creator>
            <meta refines="#author" property="role" scheme="marc:relators">aut</meta>
            <dc:publisher>PacktPub</dc:publisher>
            <dc:rights>Public domain</dc:rights>
            <dc:description>{self.description}</dc:description>
            <meta name="cover" content="cover.{self.cover_ext}" />
            <!-- Add the modified date here -->
            <meta property="dcterms:modified">{now}</meta>
        </metadata>
        <manifest>
        {manifest_with_toc} <!-- Use the manifest with TOC added -->
        </manifest>
        <spine toc="ncx">
        {self.spine}
        </spine>
        <guide>
            <reference type="cover" title="Cover" href="Text/cover.xhtml"/>
        </guide>
    </package>'''

        with open(os.path.join(self.main_dir, 'OEBPS', 'content.opf'), 'w', encoding='utf-8') as f:
            f.write(content_opf)

    def add_xhtml_to_manifest_spine(self, i, file_name):
        if file_name != 'toc' and file_name != 'cover':
            file_id = f'text_{i}'
            file_path = f'Text/{file_name}.xhtml'
            self.manifest += f'<item id="{file_id}" href="{file_path}" media-type="application/xhtml+xml"/>\n'
            self.spine += f'<itemref idref="{file_id}"/>\n'
        '''
        if self.css_path:
            css_file_name = f'Styles/{css_path}'
            manifest += f'<item id="css" href="{css_file_name}" media-type="text/css"/>\n'
        '''

    def add_images_to_manifest_spine(self, images):
        for i, file_name in enumerate(images, start=1):
            if file_name != f'cover.{self.cover_ext}':
                file_id = f'image_{i}'
                img_ext = file_name.split('.')[-1]
                file_path = f'Images/{file_name}'
                if img_ext == 'jpg':
                    img_ext = 'jpeg'
                self.manifest += f'<item id="{file_id}" href="{file_path}" media-type="image/{img_ext}"/>\n'

    def add_cover_to_manifest_spine(self):
        media_type = 'jpeg' if self.cover_ext == 'jpg' else self.cover_ext
        self.manifest += f'<item id="cover.{self.cover_ext}" href="Images/cover.{self.cover_ext}" media-type="image/{media_type}" properties="cover-image"/>\n'

    def create_toc_ncx(self):
        toc_ncx = f'''<?xml version="1.0" encoding="UTF-8"?>
    <ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
      <head>
        <meta name="dtb:uid" content="urn:uuid:{self.book_uuid}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
      </head>
      <docTitle>
        <text>Table of Contents</text>
      </docTitle>
      <navMap>
        {self.ncx_content}
      </navMap>
    </ncx>'''

        with open(os.path.join(self.main_dir, 'OEBPS', 'toc.ncx'), 'w', encoding='utf-8') as f:
            f.write(toc_ncx)

    def add_to_ncx_content(self, i, path, title):
        self.ncx_content += f'''<navPoint id="navpoint-{i}" playOrder="{i}">
          <navLabel>
            <text>{title}</text>
          </navLabel>
          <content src="Text/{path}.xhtml"/>
        </navPoint>\n'''

    def create_toc_xhtml(self):
        toc_xhtml = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>

<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Table of Contents</title>
</head>
<body>
        <nav epub:type="toc" id="toc">
            <h2 class="Heading-1-Heading-1--PACKT-">Contents</h2>
            <ol class="toc">
                {self.toc_content}
            </ol>
        </nav>
        <nav epub:type="landmarks" id="landmarks" hidden="">
            <h1>Landmarks</h1>
            <ol>
              <li class="noNumber">
                <a epub:type="cover" href="../Text/cover.xhtml">Cover</a>
              </li>
            </ol>
        </nav>
</body>
</html>'''
        with open(os.path.join(self.text_path, 'toc.xhtml'), 'w', encoding='utf-8') as f:
            f.write(toc_xhtml)


    def add_item_to_toc(self, i, path, title):
        if path != 'toc':
            self.toc_content += f'<li value="{i}"><a href="{path}.xhtml">{title}</a></li>\n'
            
    def generate_cover_content(self):
        return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>

<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
		<title>cover</title>
	</head>
	<body>
		<div style="text-align:center;" epub:type="cover">
			<img src="../Images/cover.{self.cover_ext}" alt="cover.{self.cover_ext}" style="max-width:100%;"/>
		</div>
</body>
</html>'''
        

    def create_cover_xhtml(self):
        cover_content = self.generate_cover_content()
        with open(f'{self.text_path}/cover.xhtml', 'w', encoding='utf-8') as f:
            f.write(cover_content)

    def create_epub(self):
        self.create_mimetype()
        self.create_cover_xhtml()
        self.create_container_xml()
        self.create_toc_xhtml()
        self.create_toc_ncx()
        self.create_content_opf()
        
        with ZipFile(self.output_path, 'w') as epub:
            for root, _, files in os.walk(self.main_dir):
                for file in files:
                    arcname = os.path.relpath(os.path.join(root, file), self.main_dir)
                    epub.write(os.path.join(root, file), arcname=arcname)

class Book(EPUB):
    
    def __init__(self, packt, book_id):
        
        self.packt = packt
        self.book_id = book_id
        self.data = self.packt.get_product(self.book_id).get('data')
        self.info = self.data.get('info')
        self.chapters = self.data.get('data').get('chapters')
        super().__init__(self.title, self.authors, self.about)


    def download_chapters(self):
        print(f'\n\n{self.title}')

        for chapter_num, chapter in self.chapters.items():
            print(f'\r[Downloading] {chapter_num}|{len(self.chapters)}', end='\r')
            chapter_name = list(chapter.keys())[0]
            for sec_name, sec in chapter.items():
                title = Utils.clean_text(sec['title'])
                file_path = f'{self.text_path}/{sec_name}.xhtml'
                
                response = self.packt.get_book_chapters(self.book_id, chapter_num, sec_name)
                for key, value in response.get('data').items():
                    #print(value.get(sec_name).get('isTruncatedContent'))
                        
                    content = value.get(sec_name).get('content')
                    if str(content).lower().find('join the book&rsquo;s discord') < 0 and str(content).lower().find('follow these simple steps to get the benefits') < 0:
                        content = Utils().disable_internal_hrefs(content, self.images_path, title)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                            
        toc_response = self.packt.get_toc(self.book_id)
        preface = toc_response.get('prefaces')
        chapters = toc_response.get('chapters')
        chapters_toc_content = ''
        i = 1
        for chapter_toc in chapters:
            chapter_form = '''<li><a href="{chapter_filename}.xhtml">{chapter_title}</a>
        <ol style="list-style-type: none;">
          {sections_content}
        </ol>
      </li>'''
            chapter_number = int(chapter_toc.get('id'))
            chapter_title = chapter_toc.get('title')

            sections_content = ''
            for section in chapter_toc.get('sections'):
                section_title = section.get('title')
                section_file_name = section.get('id')
                if f'{section_file_name}.xhtml' in os.listdir(self.text_path):
                    self.add_xhtml_to_manifest_spine(i, section_file_name)
                    self.add_to_ncx_content(i, section_file_name, section_title); i+=1
                    sections_content += f'<li style="list-style-type: none;"><a href="{section_file_name}.xhtml">{section_title}</a></li>\n'

            if f'{chapter_toc.get("sections")[0].get("id")}.xhtml' in os.listdir(self.text_path):
                chapter_form = chapter_form.format(chapter_filename=chapter_toc.get('sections')[0].get('id'), chapter_title=chapter_title, sections_content=sections_content)
                chapters_toc_content += chapter_form+'\n'

        self.toc_content = chapters_toc_content
        self.cover_ext = self.download_cover().split('.')[-1]
        self.add_cover_to_manifest_spine()
        image_files = [f for f in os.listdir(self.images_path) if not f.startswith('.')]
        self.add_images_to_manifest_spine(image_files)
        print("All chapters downloaded.\n\n")

    def download_cover(self):
        cover_image = self.cover_image
        ext = cover_image.split('.')[-1]
        content = requests.get(cover_image).content
        cover_path = f'{self.images_path}/cover.{ext}'
        with open(cover_path, 'wb') as f:
            f.write(content)
        print("Cover downloaded.")
        return cover_path

    @property
    def title(self):
        return Utils.clean_text(self.info.get('title'))

    @property
    def cover_image(self):
        return self.info.get('coverImage').replace('small', 'large')

    @property
    def category(self):
        return self.info.get('category')

    @property
    def authors(self):
        authors = self.info.get('authors')
        if isinstance(authors, list):
            return Utils.clean_text(', '.join(authors))
        else:
            return Utils.clean_text(authors)

    @property
    def pages_number(self):
        return self.info.get('pages')

    @property
    def about(self):
        return  Utils.clean_text(self.info.get('about'))

    @property
    def one_liner(self):
        return self.info.get('oneLiner')

    @property
    def primary_product_id(self):
        return self.cover_image.split('/')[-2]

def extract_id_from_url(url):
    for book_id in url.split('/'):
        book_id = re.findall(r'\b\d+\b', book_id)
        if book_id:
            book_id = book_id[0]
            if book_id.isdigit() and len(book_id) == 13:
                return book_id
            else:
                print(f'Invalid ID >> {url}')


def hello():
    os.system("cls" if os.name == "nt" else "echo -e \\\\033c")
    os.system("title " + "[•] PackTpub Downloader BY: @Caliginous_0")
    print('''
                                            ╔══════════════════════════════╗
                                            ║    PackTpub - @Caliginous_0  ║
                                            ╚══════════════════════════════╝
    ''')
    print('\n')
    
def main():
    hello()
    input_data = input('Add (txt OR id OR url): ')
    ids = []
    if input_data.endswith('.txt'):
        for url in open(input_data, 'r', encoding='utf-8').read().splitlines():
            book_id = extract_id_from_url(url)
            if book_id:
                ids.append(book_id)

    elif input_data.isdigit() and len(input_data) == 13:
        ids.append(input_data)

    elif 'http' in input_data:
        book_id = extract_id_from_url(input_data)
        if book_id:
            ids.append(book_id)

    for book_id in ids:
        packt = PacktPub(book_id)
        book = Book(packt, book_id)
        book.download_chapters()
        book.create_epub()
        

main()
