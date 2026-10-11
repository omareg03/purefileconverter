import re
import os

def refactor_file(filename, has_style=False, has_script=False):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    main_match = re.search(r'<main[^>]*>(.*?)</main>', content, re.DOTALL)
    if not main_match:
        print(f"Skipped {filename} (no main)")
        return
    main_inner = main_match.group(1).strip()
    
    script_inner = ""
    if has_script:
        script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
        if script_match:
            script_inner = script_match.group(1).strip()

    style_inner = ""
    if has_style:
        style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
        if style_match:
            style_inner = style_match.group(1).strip()

    new_content = '{% extends "base.html" %}\n\n'
    
    if has_style and style_inner:
        new_content += '{% block head_extra %}\n<style>\n' + style_inner + '\n</style>\n{% endblock %}\n\n'
        
    new_content += '{% block content %}\n' + main_inner + '\n{% endblock %}\n'
    
    if has_script and script_inner:
        new_content += '\n{% block scripts %}\n<script>\n' + script_inner + '\n</script>\n{% endblock %}\n'

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Updated {filename}")

refactor_file("index.html", has_style=True)
refactor_file("tool.html", has_script=True)
refactor_file("download.html", has_script=True)
