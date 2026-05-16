import re
from bs4 import BeautifulSoup
import minify_html


def mangle_html_classes(html_content):
    """
    Parses HTML to rename class names across HTML structure, 
    internal CSS, and basic JavaScript selector strings.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    class_map = {}
    current_char_code = 97  # Starts at ASCII 97 ('a')

    def get_short_name(long_name):
        """Generates sequential short names: a-z, then aa, ab, etc."""
        nonlocal current_char_code
        if long_name not in class_map:
            if current_char_code <= 122:
                class_map[long_name] = chr(current_char_code)
            else:
                offset = current_char_code - 123
                prefix = chr(97 + (offset // 26))
                suffix = chr(97 + (offset % 26))
                class_map[long_name] = f"{prefix}{suffix}"
            current_char_code += 1
        return class_map[long_name]

    # 1. Process HTML Class Attributes
    for element in soup.find_all(class_=True):
        mangled_classes = [get_short_name(c) for c in element["class"]]
        element["class"] = mangled_classes

    # 2. Process CSS Stylesheets (<style> tags)
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            css_text = style_tag.string
            for long_class, short_class in class_map.items():
                css_text = re.sub(rf'\.{long_class}(?=[ \.\,{{\:\n])', f'.{short_class}', css_text)
            style_tag.string = css_text

    # 3. Process JavaScript Code Strings (<script> tags)
    for script_tag in soup.find_all("script"):
        if script_tag.string:
            js_text = script_tag.string
            for long_class, short_class in class_map.items():
                # Raw strings
                js_text = js_text.replace(f"'{long_class}'", f"'{short_class}'")
                js_text = js_text.replace(f'"{long_class}"', f'"{short_class}"')
                js_text = js_text.replace(f"`{long_class}`", f"`{short_class}`")
                # Dot-notation strings
                js_text = js_text.replace(f"'.{long_class}'", f"'.{short_class}'")
                js_text = js_text.replace(f'".{long_class}"', f'".{short_class}"')
                js_text = js_text.replace(f"`.{long_class}`", f"`.{short_class}`")
            script_tag.string = js_text

    return str(soup)


# =====================================================================
# YOUR FILE PIPELINE (INTEGRATED)
# =====================================================================
def optimize_file(base_path):
    # 1. Read your raw template file
    with open(f'{base_path}', 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 2. Mangle the structural class names
    mangled_content = mangle_html_classes(html_content)

    # 3. Perform final heavy minification (removes spaces, squashes assets)
    minified = minify_html.minify(mangled_content, minify_css=True, minify_js=True)

    # 4. Save to your output file
    with open(f'{base_path}', 'w', encoding='utf-8') as f:
        f.write(minified)

    print("Optimization complete! Check template.min.html")
