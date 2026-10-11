import os

BASE_DIR = r"c:\Users\oegar\OneDrive\Documents\Free_File_Converter"
server_path = os.path.join(BASE_DIR, "server.py")

with open(server_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    'templates.TemplateResponse("tool.html", {"request": request, "tool": tool})',
    'templates.TemplateResponse(request=request, name="tool.html", context={"request": request, "tool": tool})'
)

with open(server_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done patching.")
