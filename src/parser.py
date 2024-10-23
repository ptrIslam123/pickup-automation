import re

from typing import Optional
from bs4 import BeautifulSoup

def extract_images(div) -> list:
    image_list = list()
    pattern = re.compile('.*')
    if div.find('section', class_=pattern):
        images = div.find_all('img')
        if images:
            for image in images:
                image_list.append(image)  # you have to extract real href from image element
    return image_list

def extract_profile_text(sections) -> Optional[str]:
    last_section = None
    for section in sections:
        last_section = section

    if last_section:
        pattern = r'\s*\d+:\d+:\d+'
        return re.sub(pattern, '', last_section.text)
    else:
        return None

def parse_info(page_content: str) -> Optional[tuple[list, str]]:
    soup = BeautifulSoup(page_content, 'html.parser')
    bubbles_inner_pattern = re.compile(r'^bubbles-inner.*')
    content = soup.find_all('div', class_=bubbles_inner_pattern)
    if content:
        for div in content:
            pattern = re.compile('.*')
            sections = div.find('section', class_=pattern)
            if sections:
                profile_text = extract_profile_text(sections)
                image_list = extract_images(div)
                return image_list, profile_text
    else:
        return None