import re
import requests

""" Parses TensorFlow releases and extracts relevant change information,
including the specific module associated with each change. """

url = "https://api.github.com/repos/tensorflow/tensorflow/releases"
response = requests.get(url)
data = response.json()

def parse_release(release: dict) -> dict:
    version = release['tag_name'].lstrip('v')
    body = release['body']
    changes = []

    # Sections to extract
    breaking_section = extract_section(body, r'### Breaking Changes')
    features_section = extract_section(body, r'### Major Features and Improvements')
    bugfixes_section = extract_section(body, r'### Bug Fixes and Other Changes')

    # Process breaking changes
    for item in extract_items_with_module(breaking_section):
        changes.append({'type': 'breaking', 'module': item['module'], 'description': item['description'], 'fix': ''})

    # Process features
    for item in extract_items_with_module(features_section):
        changes.append({'type': 'feature', 'module': item['module'], 'description': item['description'], 'fix': ''})

    # Process bug fixes
    for item in extract_items_with_module(bugfixes_section):
        changes.append({'type': 'bugfix', 'module': item['module'], 'description': item['description'], 'fix': ''})

    return {'version': version, 'changes': changes}

def extract_section(body: str, section_pattern: str) -> str:
    """Extracts the content of a specific section."""
    match = re.search(section_pattern + r'(.*?)(?=^##|\Z)', body, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""

def extract_items_with_module(section: str) -> list:
    """Extracts items with their associated module (e.g., tf.lite)."""
    items = []
    lines = section.split('\n')
    current_module = ""

    for line in lines:
        # Detect top-level bullet (module)
        if line.startswith('* ') and '`' in line:
            match = re.search(r'`([^`]+)`', line)
            if match:
                current_module = match.group(1)
        # Detect sub-bullet (item under a module)
        elif line.startswith('    * '):
            description = line[6:].strip().replace('\xa0', ' ')
            if description:
                items.append({'module': current_module, 'description': description})
        # Detect bullet without module (breaking changes with no sub-items)
        elif line.startswith('* ') and '`' not in line:
            description = line[2:].strip().replace('\xa0', ' ')
            if description:
                items.append({'module': "", 'description': description})

    return items

parsed_releases = [parse_release(release) for release in data if '-rc' not in release['tag_name'].lower()][:5]
print(parsed_releases)
""" for release in parsed_releases:
    print(f"Version: {release['version']}")
    for change in release['changes']:
        print(f"  - Type: {change['type']}, Module: {change['module']}")
        print(f"    Description: {change['description']}") """