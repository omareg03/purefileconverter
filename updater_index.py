index_code = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CleanFileConverter | Free Multi-Tool File Converter</title>
    <meta name="description" content="Free online document converter. Convert PDF, Word, Excel, CSV, JPG, and PNG online for free. No registration required.">
    <meta name="keywords" content="document online free, free online, convert pdf online free, pdf to word, word to pdf, csv to excel, online for free">
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
        <h1 class="text-4xl font-extrabold text-gray-900 mb-4 text-center">Every tool you need to work with files, in one place</h1>
        <p class="text-gray-600 mb-8 text-center max-w-2xl text-lg">Every tool you need to use PDFs, images, and documents, at your fingertips. All are 100% FREE and easy to use! Merge, split, compress, convert, rotate, unlock and watermark files with just a few clicks.</p>

        <!-- Google Ad Placeholder (Top) -->
        <div class="w-full max-w-4xl h-24 bg-gray-200 border border-gray-300 flex items-center justify-center text-gray-500 text-sm mb-12 rounded">
            [ Google AdSense Banner Placeholder ]
        </div>

        <!-- Tool Grid -->
        <div class="w-full max-w-6xl">
            <!-- Document Tools -->
            <h2 class="text-2xl font-bold text-blue-700 mb-6 border-b-2 border-blue-200 pb-2">Document Tools</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                <!-- Tool: PDF to Word -->
                <a href="/pdf-to-word" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
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

                <!-- Tool: CSV to Excel -->
                <a href="/csv-to-excel" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-file-csv"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">CSV to Excel</h3>
                    <p class="text-gray-500 text-sm">Convert CSV files to XLSX easily and accurately.</p>
                </a>

                <!-- Tool: Excel to PDF -->
                <a href="/excel-to-pdf" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-file-excel"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">Excel to PDF</h3>
                    <p class="text-gray-500 text-sm">Convert Excel spreadsheets to PDF format.</p>
                </a>
            </div>

            <!-- Image Tools -->
            <h2 class="text-2xl font-bold text-green-700 mb-6 border-b-2 border-green-200 pb-2">Image Tools</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                <!-- Tool: Image Converter -->
                <a href="/image-converter" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-image"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">Image Converter</h3>
                    <p class="text-gray-500 text-sm">Convert JPG, PNG, and WebP images to your desired format.</p>
                </a>

                <!-- Tool: Image to PDF -->
                <a href="/image-to-pdf" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-file-image"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">Image to PDF</h3>
                    <p class="text-gray-500 text-sm">Convert images into PDF documents.</p>
                </a>

                <!-- Tool: Image Resizer -->
                <a href="/image-resizer" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-down-left-and-up-right-to-center"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">Image Resizer</h3>
                    <p class="text-gray-500 text-sm">Resize your images to specific dimensions.</p>
                </a>

                <!-- Tool: Compress Image -->
                <a href="/compress-image" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-compress"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">Compress Image</h3>
                    <p class="text-gray-500 text-sm">Compress images to reduce file size.</p>
                </a>
            </div>

            <!-- Media Tools -->
            <h2 class="text-2xl font-bold text-purple-700 mb-6 border-b-2 border-purple-200 pb-2">Media Tools</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <!-- Tool: MP4 to MP3 -->
                <a href="/mp4-to-mp3" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-file-audio"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">MP4 to MP3</h3>
                    <p class="text-gray-500 text-sm">Extract audio from MP4 video files and save as MP3.</p>
                </a>

                <!-- Tool: WAV to MP3 -->
                <a href="/wav-to-mp3" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-music"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">WAV to MP3</h3>
                    <p class="text-gray-500 text-sm">Convert WAV audio files to MP3 format.</p>
                </a>

                <!-- Tool: AVI to MP4 -->
                <a href="/avi-to-mp4" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-file-video"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">AVI to MP4</h3>
                    <p class="text-gray-500 text-sm">Convert AVI video files to MP4 format.</p>
                </a>

                <!-- Tool: MP3 to MP4 -->
                <a href="/mp3-to-mp4" class="tool-card bg-white p-6 rounded-xl shadow-sm hover:shadow-md border border-gray-100 transition flex flex-col items-center text-center block">
                    <div class="tool-icon w-16 h-16 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-2xl mb-4 transition duration-300">
                        <i class="fa-solid fa-film"></i>
                    </div>
                    <h3 class="font-bold text-gray-800 text-lg mb-2">MP3 to MP4</h3>
                    <p class="text-gray-500 text-sm">Create a static video from an MP3 audio file.</p>
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

with open("C:/Users/oegar/OneDrive/Documents/Free_File_Converter/index.html", "w", encoding="utf-8") as f:
    f.write(index_code)
