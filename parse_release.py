import re
import requests

""" Archivo para parsear los releases de TensorFlow y extraer
la información relevante sobre los cambios, incluyendo el 
módulo específico asociado a cada cambio. """

url = "https://api.github.com/repos/tensorflow/tensorflow/releases"
response = requests.get(url)
data = response.json()

def parse_release(release: dict) -> dict:
    version = release['tag_name'].lstrip('v')
    body = release['body']
    changes = []

    # Secciones a extraer
    breaking_section = extract_section(body, r'### Breaking Changes')
    features_section = extract_section(body, r'### Major Features and Improvements')
    bugfixes_section = extract_section(body, r'### Bug Fixes and Other Changes')

    # Procesar breaking changes
    for item in extract_items_with_module(breaking_section):
        changes.append({'type': 'breaking', 'module': item['module'], 'description': item['description'], 'fix': ''})

    # Procesar features
    for item in extract_items_with_module(features_section):
        changes.append({'type': 'feature', 'module': item['module'], 'description': item['description'], 'fix': ''})

    # Procesar bug fixes
    for item in extract_items_with_module(bugfixes_section):
        changes.append({'type': 'bugfix', 'module': item['module'], 'description': item['description'], 'fix': ''})

    return {'version': version, 'changes': changes}

def extract_section(body: str, section_pattern: str) -> str:
    """Extrae el contenido de una sección específica."""
    match = re.search(section_pattern + r'(.*?)(?=^##|\Z)', body, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""

def extract_items_with_module(section: str) -> list:
    """Extrae los items con su módulo asociado (e.g., tf.lite)."""
    items = []
    lines = section.split('\n')
    current_module = ""

    for line in lines:
        # Detectar si es un bullet de primer nivel (módulo)
        if line.startswith('* ') and '`' in line:
            match = re.search(r'`([^`]+)`', line)
            if match:
                current_module = match.group(1)
        # Detectar si es un sub-bullet (item del módulo)
        elif line.startswith('    * '):
            description = line[6:].strip().replace('\xa0', ' ')
            if description:
                items.append({'module': current_module, 'description': description})
        # Detectar bullet sin módulo (breaking changes sin sub-items)
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