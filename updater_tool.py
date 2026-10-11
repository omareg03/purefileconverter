tool_code = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ tool.title }} - Free Online | CleanFileConverter</title>
    <meta name="description" content="Free online {{ tool.title }} converter. {{ tool.description }} Convert your document online for free.">
    <meta name="keywords" content="{{ tool.title }}, document online free, free online, convert online for free">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-50 flex flex-col min-h-screen">
    <!-- Navbar -->
    <nav class="bg-white shadow-sm py-4">
        <div class="max-w-6xl mx-auto px-4 flex justify-between items-center">
            <a href="/" class="font-bold text-2xl flex items-center gap-2">
                <svg width="32" height="32" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                  <!-- Recycle/convert arrow motif -->
                  <path d="M50 15 A35 35 0 0 1 85 50 L95 50 L80 70 L65 50 L75 50 A25 25 0 0 0 50 25 Z" fill="#2563eb" /> <!-- Blue -->
                  <path d="M50 85 A35 35 0 0 1 15 50 L5 50 L20 30 L35 50 L25 50 A25 25 0 0 0 50 75 Z" fill="#16a34a" /> <!-- Green -->
                </svg>
                <span class="text-blue-600">CleanFile<span class="text-green-600">Converter</span></span>
            </a>
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

                {% if tool.has_resize_inputs %}
                <div id="resizeInputs" class="mb-6 flex justify-center items-center gap-3">
                    <label class="text-sm text-gray-600 font-medium">Width:</label>
                    <input type="number" id="resizeWidth" value="800" class="border border-gray-300 rounded p-2 text-sm focus:ring-blue-500 w-24">
                    <label class="text-sm text-gray-600 font-medium">Height:</label>
                    <input type="number" id="resizeHeight" value="600" class="border border-gray-300 rounded p-2 text-sm focus:ring-blue-500 w-24">
                </div>
                {% endif %}

                {% if tool.has_quality_input %}
                <div id="qualityInput" class="mb-6 flex justify-center items-center gap-3">
                    <label class="text-sm text-gray-600 font-medium">Quality (1-100):</label>
                    <input type="number" id="qualityValue" value="50" min="1" max="100" class="border border-gray-300 rounded p-2 text-sm focus:ring-blue-500 w-24">
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
            if (document.getElementById('imageFormatSelector')) {
                document.getElementById('imageFormatSelector').classList.add('hidden');
            }
            {% endif %}
            {% if tool.has_resize_inputs %}
            if (document.getElementById('resizeInputs')) {
                document.getElementById('resizeInputs').classList.add('hidden');
            }
            {% endif %}
            {% if tool.has_quality_input %}
            if (document.getElementById('qualityInput')) {
                document.getElementById('qualityInput').classList.add('hidden');
            }
            {% endif %}
            loadingIndicator.classList.remove('hidden');

            const formData = new FormData();
            formData.append('file', file);
            
            {% if tool.has_format_selector %}
            if (document.getElementById('formatSelect')) {
                formData.append('format', document.getElementById('formatSelect').value);
            }
            {% endif %}

            {% if tool.has_resize_inputs %}
            if (document.getElementById('resizeWidth') && document.getElementById('resizeHeight')) {
                formData.append('width', document.getElementById('resizeWidth').value);
                formData.append('height', document.getElementById('resizeHeight').value);
            }
            {% endif %}

            {% if tool.has_quality_input %}
            if (document.getElementById('qualityValue')) {
                formData.append('quality', document.getElementById('qualityValue').value);
            }
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
                if (document.getElementById('imageFormatSelector')) {
                    document.getElementById('imageFormatSelector').classList.remove('hidden');
                }
                {% endif %}
                {% if tool.has_resize_inputs %}
                if (document.getElementById('resizeInputs')) {
                    document.getElementById('resizeInputs').classList.remove('hidden');
                }
                {% endif %}
                {% if tool.has_quality_input %}
                if (document.getElementById('qualityInput')) {
                    document.getElementById('qualityInput').classList.remove('hidden');
                }
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

with open("C:/Users/oegar/OneDrive/Documents/Free_File_Converter/tool.html", "w", encoding="utf-8") as f:
    f.write(tool_code)
