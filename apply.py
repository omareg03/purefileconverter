import os

BASE_DIR = r"c:\Users\oegar\OneDrive\Documents\Free_File_Converter"

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CleanConvert | Free Multi-Tool File Converter</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .tool-card:hover .tool-icon {
            transform: scale(1.1);
        }
    </style>
</head>
<body class="bg-gray-50 flex flex-col min-h-screen">
    <!-- Navbar -->
    <nav class="bg-white shadow-sm py-4">
        <div class="max-w-6xl mx-auto px-4 flex justify-between items-center">
            <a href="/" class="font-bold text-2xl text-blue-600"><i class="fa-solid fa-arrows-rotate mr-2"></i>CleanConvert</a>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-grow flex flex-col items-center pt-12 px-4 pb-12">
        <h1 class="text-4xl font-extrabold text-gray-900 mb-4 text-center">Every tool you need to work with files, in one place</h1>
        <p class="text-gray-600 mb-8 text-center max-w-2xl text-lg">Every tool you need to use PDFs, images, and documents, at your fingertips. All are 100% FREE and easy to use! Merge, split, compress, convert, rotate, unlock and watermark files with just a few clicks.</p>

        <!-- Google Ad Placeholder (Top) -->
        <div class="w-full max-w-4xl h-24 bg-gray-200 border border-gray-300 flex items-center justify-center text-gray-500 text-sm mb-12 rounded">
            [ Google AdSense Banner Placeholder ]
        </div>

        <!-- Tool Grid -->
        <div class="w-full max-w-6xl">
            <h2 class="text-2xl font-bold text-gray-800 mb-6">Document Tools</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                
                <!-- Tool: CSV to Excel -->
                <a href="/csv-to-excel" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-file-csv"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">CSV to Excel</h3>
                    <p class="text-gray-500 text-sm">Convert CSV files to XLSX easily and accurately.</p>
                </a>

                <!-- Tool: PDF to Word -->
                <a href="/pdf-to-word" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-file-pdf"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">PDF to Word</h3>
                    <p class="text-gray-500 text-sm">Easily convert your PDF files into easy to edit DOCX documents.</p>
                </a>

                <!-- Tool: Word to PDF -->
                <a href="/word-to-pdf" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-file-word"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">Word to PDF</h3>
                    <p class="text-gray-500 text-sm">Make DOC and DOCX files easy to read by converting them to PDF.</p>
                </a>

            </div>

            <h2 class="text-2xl font-bold text-gray-800 mb-6">Image Tools</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <!-- Tool: Image Converter -->
                <a href="/image-converter" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-yellow-100 text-yellow-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-image"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">Image Converter</h3>
                    <p class="text-gray-500 text-sm">Convert JPG, PNG, and WebP images to your desired format.</p>
                </a>
            </div>
        </div>

    </main>

    <footer class="bg-white text-center py-6 text-gray-500 text-sm border-t mt-auto">
        &copy; 2026 CleanConvert. Built for fast, free utility.
    </footer>
</body>
</html>
"""

TOOL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ tool.title }} | CleanConvert</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-50 flex flex-col min-h-screen">
    <!-- Navbar -->
    <nav class="bg-white shadow-sm py-4">
        <div class="max-w-6xl mx-auto px-4 flex justify-between items-center">
            <a href="/" class="font-bold text-2xl text-blue-600"><i class="fa-solid fa-arrows-rotate mr-2"></i>CleanConvert</a>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-grow flex flex-col items-center pt-12 px-4 pb-12">
        <div class="w-full max-w-3xl">
            <a href="/" class="text-blue-600 hover:underline mb-6 inline-block"><i class="fa-solid fa-arrow-left mr-2"></i>Back to Tools</a>
            
            <div class="bg-white rounded-xl shadow-lg p-8 relative">
                <div class="text-center mb-8">
                    <div class="w-20 h-20 bg-{{ tool.color }}-100 text-{{ tool.color }}-600 rounded-full flex items-center justify-center text-4xl mb-4 mx-auto">
                        <i class="fa-solid {{ tool.icon }}"></i>
                    </div>
                    <h1 class="text-3xl font-bold text-gray-800 mb-2">{{ tool.title }}</h1>
                    <p class="text-gray-600 text-lg">{{ tool.description }}</p>
                </div>
                
                <div id="dropzone" class="border-2 border-dashed border-blue-300 rounded-lg p-16 text-center hover:bg-blue-50 transition cursor-pointer mb-6">
                    <div class="text-5xl text-blue-500 mb-4"><i class="fa-solid fa-cloud-arrow-up"></i></div>
                    <p class="text-gray-600 font-medium text-xl">Drag & Drop your file here</p>
                    <p class="text-gray-400 text-base mt-2">or <span class="text-blue-600 underline">Select File</span></p>
                    <input type="file" id="fileInput" class="hidden" accept="{{ tool.accept }}">
                </div>

                {% if tool.has_format_selector %}
                <div id="imageFormatSelector" class="mb-6 flex justify-center items-center gap-3">
                    <label class="text-sm text-gray-600 font-medium">Convert to:</label>
                    <select id="formatSelect" class="border border-gray-300 rounded p-2 text-sm font-bold text-gray-700 focus:ring-blue-500">
                        <option value="jpg">JPG</option>
                        <option value="png">PNG</option>
                        <option value="webp">WebP</option>
                    </select>
                </div>
                {% endif %}

                <div id="loadingIndicator" class="hidden text-center py-12">
                    <div class="inline-block animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mb-4"></div>
                    <p class="text-gray-600 font-medium text-lg">Processing your file...</p>
                </div>

                <div id="errorMsg" class="hidden bg-red-50 text-red-600 p-4 rounded-lg text-center mb-4 text-sm font-medium border border-red-200"></div>

            </div>
            
            <!-- Google Ad Placeholder (Bottom) -->
            <div class="w-full h-24 bg-gray-200 border border-gray-300 flex items-center justify-center text-gray-500 text-sm mt-12 rounded">
                [ Google AdSense Banner Placeholder ]
            </div>
        </div>
    </main>

    <footer class="bg-white text-center py-6 text-gray-500 text-sm border-t mt-auto">
        &copy; 2026 CleanConvert. Built for fast, free utility.
    </footer>

    <script>
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const errorMsg = document.getElementById('errorMsg');
        
        // Drag and drop visuals
        dropzone.addEventListener('click', () => fileInput.click());
        
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('bg-blue-50', 'border-blue-500');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('bg-blue-50', 'border-blue-500');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('bg-blue-50', 'border-blue-500');
            if (e.dataTransfer.files.length) {
                processFile(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                processFile(e.target.files[0]);
            }
        });

        async function processFile(file) {
            errorMsg.classList.add('hidden');
            dropzone.classList.add('hidden');
            {% if tool.has_format_selector %}
            document.getElementById('imageFormatSelector').classList.add('hidden');
            {% endif %}
            loadingIndicator.classList.remove('hidden');

            const formData = new FormData();
            formData.append('file', file);
            
            {% if tool.has_format_selector %}
            formData.append('format', document.getElementById('formatSelect').value);
            {% endif %}

            try {
                const response = await fetch('{{ tool.endpoint }}', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok) {
                    window.location.href = `/download-page?file_id=${result.file_id}&filename=${encodeURIComponent(result.filename)}`;
                } else {
                    throw new Error(result.detail || 'Conversion failed');
                }
            } catch (err) {
                errorMsg.textContent = err.message;
                errorMsg.classList.remove('hidden');
                dropzone.classList.remove('hidden');
                {% if tool.has_format_selector %}
                document.getElementById('imageFormatSelector').classList.remove('hidden');
                {% endif %}
                loadingIndicator.classList.add('hidden');
                
                // Clear input
                fileInput.value = '';
            }
        }
    </script>
</body>
</html>
"""

SERVER_ADDITION = """
TOOLS_CONFIG = {
    "csv-to-excel": {
        "title": "CSV to Excel",
        "accept": ".csv",
        "description": "Convert CSV files to XLSX easily and accurately.",
        "endpoint": "/api/convert/csv-to-excel",
        "has_format_selector": False,
        "icon": "fa-file-csv",
        "color": "green"
    },
    "pdf-to-word": {
        "title": "PDF to Word",
        "accept": ".pdf",
        "description": "Easily convert your PDF files into easy to edit DOCX documents.",
        "endpoint": "/api/convert/pdf-to-word",
        "has_format_selector": False,
        "icon": "fa-file-pdf",
        "color": "red"
    },
    "word-to-pdf": {
        "title": "Word to PDF",
        "accept": ".doc,.docx",
        "description": "Make DOC and DOCX files easy to read by converting them to PDF.",
        "endpoint": "/api/convert/word-to-pdf",
        "has_format_selector": False,
        "icon": "fa-file-word",
        "color": "blue"
    },
    "image-converter": {
        "title": "Image Converter",
        "accept": "image/png, image/jpeg, image/webp",
        "description": "Convert JPG, PNG, and WebP images to your desired format.",
        "endpoint": "/api/convert/image",
        "has_format_selector": True,
        "icon": "fa-image",
        "color": "yellow"
    }
}

@app.get("/{tool_slug}", response_class=HTMLResponse)
async def tool_page(request: Request, tool_slug: str):
    if tool_slug not in TOOLS_CONFIG:
        raise HTTPException(status_code=404, detail="Page not found")
    tool = TOOLS_CONFIG[tool_slug]
    return templates.TemplateResponse("tool.html", {"request": request, "tool": tool})
"""

with open(os.path.join(BASE_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(INDEX_HTML)

with open(os.path.join(BASE_DIR, "tool.html"), "w", encoding="utf-8") as f:
    f.write(TOOL_HTML)

with open(os.path.join(BASE_DIR, "server.py"), "a", encoding="utf-8") as f:
    f.write(SERVER_ADDITION)

print("Done")
