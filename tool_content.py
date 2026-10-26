"""Long-form help text for every tool page (v1.4).

Each entry is written for that tool only: how to use it, what actually happens to the file, and the
honest limits. server.py attaches it to TOOLS_CONFIG and tool.html renders it under the converter.
"article" links the tool page to its in-depth blog guide (None when there is no dedicated guide).
"""

TOOL_GUIDES = {
    # ------------------------------------------------------------------ Document tools
    "pdf-to-word": {
        "steps": [
            "Click the upload area and choose a PDF, or drag the file onto it.",
            "Wait while the converter rebuilds the pages as a Word document. Long or image-heavy PDFs take a little longer.",
            "Download the .docx file and open it in Microsoft Word, Google Docs or LibreOffice Writer to edit it.",
        ],
        "body": [
            "The converter reads the text, fonts, tables and images inside your PDF and rebuilds them as real Word "
            "paragraphs and tables, so you can change a sentence instead of retyping the whole page. It works best "
            "on PDFs that were created digitally, such as files exported from Word, invoices from accounting software "
            "or forms downloaded from a website.",
            "A quick way to check your file first: open the PDF and try to highlight a sentence with your mouse. If "
            "the text highlights, it will convert into editable text. If the whole page highlights like a photo, the "
            "PDF is a scan, and a scan is only a picture of words. This tool does not run OCR (text recognition), so "
            "scanned pages arrive in Word as images.",
            "Expect very simple documents to come out almost identical. Pages built from many columns, floating text "
            "boxes or decorative layouts can shift a little, because Word and PDF position content differently. After "
            "converting, scroll through the document once and fix any line breaks before you send it on.",
            "Large PDFs take longer because every page is analyzed separately. If you only need to edit a few "
            "pages of a long report, pull those pages out with Split PDF first and convert just that part. It's "
            "faster, and you get a shorter Word document that is easier to work with.",
        ],
        "article": "how-to-convert-pdf-to-word",
    },
    "word-to-pdf": {
        "steps": [
            "Upload a Word document in .docx format or the older .doc format.",
            "The file is converted with LibreOffice, the open-source office suite, on the server.",
            "Download the PDF. It looks the same on phones, Macs, Windows PCs and printers.",
        ],
        "body": [
            "Sending a PDF instead of a Word file is the safest way to make sure the reader sees exactly what you see. "
            "Fonts, page breaks and spacing are locked in place, and nobody can accidentally edit the content. That is "
            "why job applications, invoices, school assignments and contracts are usually requested as PDF.",
            "The one thing to watch is fonts. Documents set in Arial, Calibri, Cambria, Times New Roman or Courier "
            "New match closely, because the server has those fonts or exact-width equivalents. A rare or custom "
            "font that is not installed is replaced with a similar one, which can change line lengths slightly. For a résumé or "
            "any document where layout matters, stick to standard fonts, or check the PDF before you send it.",
            "Both .doc and .docx files up to the size limit are accepted, including documents with pictures, tables, "
            "headers and footers. Page size and margins come from the document's own page setup, so a Letter-size "
            "document stays Letter and an A4 document stays A4. Password-protected documents need to be unlocked in "
            "Word first, because the converter can't open them.",
        ],
        "article": "how-to-convert-word-to-pdf",
    },
    "csv-to-excel": {
        "steps": [
            "Upload a .csv file that uses commas to separate its columns.",
            "The first row is read as column headings, and every following row becomes a row in the spreadsheet.",
            "Download the .xlsx workbook and open it in Excel, Google Sheets or LibreOffice Calc.",
        ],
        "body": [
            "CSV is the plain-text format that banks, online stores, email tools and databases use when you click "
            "\"export\". It has no formatting, no formulas and no sheets, and opening it directly in Excel sometimes "
            "scrambles accented characters. Converting it to a real Excel workbook gives you a file you can sort, "
            "filter, chart and share without those surprises.",
            "Text is read as UTF-8 first and then as Latin-1, which covers exports from most US and European "
            "software. Two details are worth knowing before you convert. Columns that look like numbers are stored "
            "as numbers, so a ZIP code like 02134 or a product code with leading zeros loses those zeros. And files "
            "that separate values with semicolons, which is common in Europe, will land in a single column; change "
            "the separator to commas first, or open the file with Excel's import wizard instead.",
            "Dates are kept exactly as they appear in the CSV, so you can apply your own date format in Excel "
            "afterwards. Empty CSV files are rejected with a clear message rather than producing a blank workbook.",
        ],
        "article": "how-to-convert-csv-to-excel",
    },
    "excel-to-pdf": {
        "steps": [
            "Upload an Excel workbook (.xlsx or .xls) or a CSV file.",
            "Each sheet is laid out on pages using the sheet's own print settings.",
            "Download the PDF to email, print or attach to a report.",
        ],
        "body": [
            "Spreadsheets are hard to read when they are shared as Excel files: columns get cut off on phones, "
            "formulas can be changed by accident, and the recipient may not have Excel at all. A PDF freezes the "
            "numbers exactly as they are and opens anywhere, which is why quotes, timesheets, price lists and "
            "budgets are usually sent that way.",
            "The conversion follows the print setup saved in your workbook, just as if you printed it. That means "
            "wide sheets can spill onto extra pages. For a tidy one-page-wide result, open the file in Excel first, "
            "go to Page Layout, set the orientation to Landscape and choose \"Fit All Columns on One Page\" under "
            "Scaling, then save and upload. Setting a print area also stops empty rows and helper columns from "
            "appearing in the PDF.",
            "Charts, cell colors, borders and number formats are carried over. If your workbook pulls data from "
            "other files or online sources, refresh it and save before converting, because the PDF shows the last "
            "values stored in the file. Every sheet in the workbook is included, in the order of the sheet tabs, so "
            "remove any sheet you don't want to share before uploading.",
        ],
        "article": None,
    },
    "pdf-to-jpg": {
        "steps": [
            "Upload a PDF of up to 50 pages.",
            "Every page is rendered as an image at 150 DPI using PDFium, the PDF engine built into Google Chrome.",
            "Download one JPG for a single-page PDF, or a ZIP file with one JPG per page for longer documents.",
        ],
        "body": [
            "Turning PDF pages into pictures is useful whenever the place you're posting to only accepts images: a "
            "social media post, a slide in a presentation, a chat message, an online form that asks for a photo of a "
            "document, or a thumbnail preview on a website. Each image keeps the page's exact look, including fonts "
            "and vector graphics that might otherwise display differently.",
            "At 150 DPI a standard Letter or A4 page becomes an image of roughly 1275 x 1650 pixels, which is sharp "
            "on screens and fine for normal printing, while keeping each file reasonably small. Pages are named "
            "page-1.jpg, page-2.jpg and so on inside the ZIP, so they stay in order when you unzip them.",
            "Extremely large pages, such as engineering drawings or posters, are rendered at a lower resolution so "
            "the image stays under 25 megapixels. PDFs with more than 50 pages are rejected rather than half "
            "converted; split them first with the Split PDF tool and convert the parts you need.",
            "Need just one page as an image? Pull that page out with Split PDF first, then convert it here to get "
            "a single JPG instead of a ZIP. If you need large prints, such as a poster, use a desktop PDF program "
            "that can export at 300 DPI, because 150 DPI is designed for screens and everyday printing.",
        ],
        "article": None,
    },
    # ------------------------------------------------------------------ PDF tools
    "merge-pdf": {
        "steps": [
            "Select between 2 and 10 PDF files at once. Hold Ctrl (or Cmd on a Mac) to pick several files.",
            "The files are joined in the order you selected them.",
            "Download a single combined PDF that contains every page.",
        ],
        "body": [
            "Merging is the quickest way to send one tidy file instead of a pile of attachments: scanned receipts "
            "for an expense report, a cover letter plus résumé plus references, monthly statements for a loan "
            "application, or chapters that were exported separately. The pages are copied as they are, so text "
            "stays searchable and nothing is re-compressed.",
            "Order is the part people most often get wrong. File pickers usually sort by name, so the simplest trick "
            "is to rename the files 1, 2, 3 (or 01, 02, 03 when there are more than nine) before you upload them. "
            "If a page ends up in the wrong place, you can fix it afterwards with Split PDF and merge again.",
            "Together the files must fit within the upload limit, and the merged document can have up to 200 pages. "
            "PDFs that "
            "are protected with a password can't be opened by the server, so remove the password in your PDF reader "
            "first. Pages keep their original size and orientation; if one is sideways, run the merged file through "
            "Rotate PDF.",
            "Pages keep their original size, so mixing Letter and A4 pages, or portrait and landscape ones, works "
            "fine; PDF viewers simply show each page at its own size. If the files contain fillable forms, fill "
            "them in and save or flatten them before merging, because fields with the same name in different "
            "files can clash.",
        ],
        "article": None,
    },
    "split-pdf": {
        "steps": [
            "Upload the PDF you want to split.",
            "Leave the page box empty to save every page as its own PDF, or type the pages you want, such as 1-3, 7.",
            "Download a ZIP of single-page PDFs, or one new PDF that contains only the pages you typed.",
        ],
        "body": [
            "Splitting solves two everyday problems. The first is sending only part of a document: one signed page "
            "of a contract, the two pages of a statement a landlord asked for, or a single chapter of a manual. The "
            "second is breaking a big scan into separate files, such as one PDF per receipt or per form.",
            "The page box accepts single pages, ranges and mixes separated by commas. \"2\" keeps one page, \"4-9\" "
            "keeps a range, and \"1-3, 7, 10-12\" builds a new document from all of those pages in exactly the order "
            "you typed them. That last trick also lets you reorder pages, because typing \"3, 1, 2\" produces a PDF "
            "with page 3 first.",
            "Pages are copied without re-rendering, so quality, links and searchable text are unchanged. Documents "
            "can have up to 200 pages. If you type a page number that doesn't exist, the tool tells you instead of "
            "silently skipping it.",
            "Splitting never changes the original file on your device, so you can experiment freely. Bookmarks "
            "and fillable form fields may not carry over into the new files, because they often point to pages "
            "that are no longer included, but the text, images and links on each page are kept.",
        ],
        "article": None,
    },
    "compress-pdf": {
        "steps": [
            "Upload the PDF that is too big to email or upload.",
            "Large photos and scans inside it are resized and recompressed, and duplicate data is removed.",
            "Download the smaller PDF. If it can't be made smaller, you get the original back unchanged.",
        ],
        "body": [
            "Most oversized PDFs are big because of pictures, not text. A phone scan or a photo exported at full "
            "camera resolution can weigh several megabytes per page. The compressor finds those images and scales "
            "any that are larger than about 1600 pixels on their longest side, which is roughly 150 DPI on a Letter "
            "or A4 page, and saves them as JPEG at quality 70. That is plenty for reading on screen and for normal "
            "office printing.",
            "Text, vector drawings and fonts are not converted to pictures, so the words stay sharp and you can "
            "still search and copy them. Images with transparency or masks are left alone, because recompressing "
            "them could change how the page looks. The page streams are also compressed and repeated objects, such "
            "as a logo stored on every page, are stored once.",
            "Results depend on what is inside the file. Scanned and photo-heavy PDFs often shrink by more than half. "
            "PDFs that are already mostly text change very little, because there is nothing heavy left to remove.",
            "If the compressed file is still too big for an email, two more steps usually help. Split the PDF "
            "into smaller parts with Split PDF and send them separately, or check whether the recipient accepts a "
            "download link instead. Most email services cap attachments at about 20 to 25 MB, and many online "
            "forms allow far less.",
        ],
        "article": "how-to-compress-pdf-files",
    },
    "rotate-pdf": {
        "steps": [
            "Upload a PDF that opens sideways or upside down.",
            "Choose 90° clockwise, 180° or 270° (which is the same as 90° counter-clockwise).",
            "Download the fixed PDF. The new orientation is saved permanently.",
        ],
        "body": [
            "Sideways PDFs usually come from scanners and phone scanning apps that guess the page direction wrong, "
            "or from landscape pages added to a portrait document. Rotating the view in your PDF reader only fixes "
            "it on your screen. This tool saves the rotation into the file itself, so it opens the right way up for "
            "everyone you send it to, and on printers too.",
            "The rotation is stored as a page setting rather than by redrawing the page, so nothing is re-compressed "
            "and the quality is exactly the same as before. Text remains searchable and links keep working.",
            "This tool turns every page in the document by the same amount. If only one page is wrong, split it out "
            "with Split PDF, rotate that single page here, and then put the pieces back together with Merge PDF. A "
            "quick way to pick the angle: if the top of the page points left, choose 90°; if it points right, choose "
            "270°; if the page is upside down, choose 180°.",
            "Rotating is safe to repeat. If you pick the wrong angle, upload the result and rotate it again; "
            "because the pages are never re-compressed, nothing is lost no matter how many times you do it. Your "
            "original file stays untouched on your own device either way.",
        ],
        "article": None,
    },
    # ------------------------------------------------------------------ Image tools
    "image-converter": {
        "steps": [
            "Choose the format you want: JPG, PNG or WebP.",
            "Upload a JPG, PNG or WebP image.",
            "Download the converted picture, already turned the right way up.",
        ],
        "body": [
            "Each of the three formats has a job. JPG is the universal choice for photos and works on every device "
            "and website. PNG is lossless and supports transparency, which makes it right for logos, screenshots "
            "and graphics with sharp edges or text. WebP is the modern web format, usually 25 to 35 percent smaller "
            "than a JPG of similar quality, and it supports transparency too.",
            "Phone cameras often store photos sideways and add a note telling viewers to rotate them. Some apps "
            "ignore that note, which is why pictures sometimes appear on their side after you upload them somewhere. "
            "The converter applies the rotation for you, so the result displays correctly everywhere.",
            "Converting a transparent PNG or WebP to JPG fills the see-through areas with white, because the JPG "
            "format cannot store transparency. Converting a JPG to PNG won't make it look better: the detail that JPG "
            "compression removed doesn't come back, and the PNG will usually be larger. Pick PNG only when you need "
            "lossless editing or transparency.",
            "A quick rule of thumb: photos you share or post should be JPG or WebP. Anything with text, sharp "
            "lines or a transparent background, such as a logo, a chart or a screenshot, is better as PNG or "
            "WebP. If a website rejects your upload, JPG is the safest choice, because every system accepts it.",
        ],
        "article": "jpg-vs-png-vs-webp-guide",
    },
    "image-to-pdf": {
        "steps": [
            "Upload a JPG, PNG or WebP picture, such as a photo of a document or a scanned page.",
            "The image is placed on a single PDF page that matches its shape.",
            "Download the PDF to email, upload to a form or archive.",
        ],
        "body": [
            "Many online forms, schools and offices accept documents only as PDF, even when all you have is a photo "
            "taken with your phone. This tool wraps the picture in a standard PDF file so it can be uploaded anywhere "
            "a PDF is required, without installing an app.",
            "The page takes the exact proportions of your image, so a portrait photo becomes a portrait page and a "
            "wide screenshot becomes a wide page. Phone photos are turned the right way up first, and transparent "
            "areas in PNG or WebP files are filled with white. When you print the PDF, choose \"Fit to page\" in the "
            "print dialog so the picture fills the paper.",
            "For the cleanest result when photographing paperwork, place the page on a dark, flat surface, shoot "
            "from directly above in good light, and crop away the background before converting. Each upload creates "
            "a one-page PDF; to combine several pages into one document, convert each photo and then join the files "
            "with Merge PDF.",
            "Image to PDF is also the easiest way to send a picture to someone who has to print it at an office "
            "or library. A PDF prints the same on every printer, while photo apps often crop or stretch pictures "
            "to fit the paper. Keep the original photo as well, because a PDF is harder to edit later.",
        ],
        "article": None,
    },
    "image-resizer": {
        "steps": [
            "Upload a JPG, PNG or WebP image.",
            "Enter the new width and height in pixels, anywhere from 1 to 8000.",
            "Download the resized image in its original format.",
        ],
        "body": [
            "Websites, marketplaces and social networks often ask for images at specific sizes, and huge phone "
            "photos (often 4000 pixels wide or more) are slow to upload and email. Resizing to the size you actually "
            "need makes the file smaller and the page faster, without visible loss on screen.",
            "The image is resized to exactly the width and height you type, so keep the original proportions to "
            "avoid stretching. The math is simple: new height = new width × original height ÷ original width. For "
            "example, a 4000 × 3000 photo resized to 1200 pixels wide should be 900 pixels tall. Resampling uses "
            "the Lanczos filter, one of the sharpest methods for shrinking photos.",
            "Making an image bigger than the original can't add detail that wasn't captured, so large upscales will "
            "look soft. For the best quality, start from the largest version of the picture you have and resize "
            "down, not up. Phone photos are rotated the right way up before resizing, so the width and height you "
            "enter match what you see.",
            "Some common sizes to start from: 1080 x 1080 for a square Instagram post, 1200 x 630 for a link "
            "preview image on Facebook or LinkedIn, 1920 x 1080 for a full HD wallpaper or presentation slide, "
            "and about 1600 pixels on the longest side for photos you plan to email.",
        ],
        "article": "how-to-resize-images-online",
    },
    "compress-image": {
        "steps": [
            "Upload a JPG or WebP image.",
            "Pick a quality value between 1 and 100. Lower numbers make smaller files.",
            "Download the compressed image and compare it with the original.",
        ],
        "body": [
            "Compression lowers the file size by storing fine detail more efficiently. For photos, a quality "
            "setting between 60 and 80 usually cuts the size by half or more while looking the same at normal "
            "viewing size. That's the range most websites use. Below about 50, you will start to see blocky areas "
            "and smudged edges, especially around text and in skies.",
            "The original format is kept, so a JPG stays a JPG and a WebP stays a WebP. For JPG files the encoder also "
            "optimizes its internal tables, which trims a few more kilobytes without changing the picture. PNG "
            "files aren't accepted here, because PNG is lossless and doesn't have a quality setting; convert a PNG "
            "photo to WebP or JPG with the Image Converter first, which often shrinks it dramatically on its own.",
            "Avoid compressing the same JPG again and again. Every save throws away a little more detail, so always "
            "start from the best original you have. If you need a smaller file and the quality is already low, "
            "reduce the dimensions with the Image Resizer instead.",
            "If you need to hit a specific limit, such as a 200 KB maximum on an online application form, start "
            "at quality 75 and check the size of the download. Lower the number in steps of 10 until the file "
            "fits, and shrink the dimensions instead if the quality has to go below about 50.",
        ],
        "article": "how-to-compress-jpg-images",
    },
    "heic-to-jpg": {
        "steps": [
            "Upload a .heic or .heif photo from an iPhone or iPad.",
            "The photo is decoded and saved as a high-quality JPG at its full resolution.",
            "Download the JPG and use it on Windows, Android, websites or any app.",
        ],
        "body": [
            "Since iOS 11, iPhones save photos in HEIC (High Efficiency Image Coding) by default. It keeps good "
            "quality at about half the size of a JPG, but many Windows PCs, older Android phones, websites and "
            "online forms still can't open it. Converting to JPG is the simplest way to make a photo work "
            "everywhere.",
            "The JPG is saved at quality 92 with the original pixel dimensions, and it is rotated the right way up, "
            "so it looks the same as on your phone. If a Live Photo was exported as HEIC, you get the still image; "
            "the short video part isn't included.",
            "If you convert photos often, two iPhone settings save time. Settings > Camera > Formats > Most "
            "Compatible makes the camera shoot JPG instead of HEIC from now on. Settings > Photos > Transfer to Mac "
            "or PC > Automatic makes the iPhone convert photos to JPG when you copy them to a computer with a cable. "
            "Photos you already took stay in HEIC, which is where this tool comes in.",
            "On Windows 10 and 11 you can sometimes view HEIC files after installing the HEIF and HEVC extensions "
            "from the Microsoft Store, but the HEVC extension may cost money, and the photos still won't upload "
            "to many websites and forms. Converting to JPG once avoids both problems.",
        ],
        "article": "how-to-convert-heic-to-jpg",
    },
    "remove-background": {
        "steps": [
            "Choose a JPG, PNG or WebP photo with a clear main subject.",
            "Wait while the AI separates the subject from the background. The first run downloads the AI model.",
            "Download the transparent PNG and place it on any background you like.",
        ],
        "body": [
            "This tool runs an open-source AI segmentation model directly in your browser using WebAssembly. Your "
            "photo is never uploaded to a server, which makes it a good choice for personal pictures, ID-style "
            "portraits and unreleased product shots. The model is about 44 MB and is downloaded once, then cached "
            "by your browser, so later photos are much faster.",
            "It works best when the subject stands out clearly: a person, a pet, a product, a car or a logo against "
            "a background of a different color or brightness. Fine details such as loose hair, fur, glass and thin "
            "cables are the hardest parts for any background remover, so check the edges by zooming in before you "
            "use the image in print.",
            "The result is a PNG with real transparency, up to 2048 pixels on its longest side. If a marketplace "
            "requires a pure white background, as Amazon does for main product images, place the PNG on white in "
            "any editor. Photos up to 25 MB can be used, and very large ones are scaled down before processing to "
            "keep your browser responsive.",
        ],
        "article": None,
    },
    "qr-code-generator": {
        "steps": [
            "Type or paste a link, text, email address, phone number or Wi-Fi details (up to 1000 characters).",
            "Click Generate to create the QR code.",
            "Download the PNG and test it with your phone camera before you print it.",
        ],
        "body": [
            "The QR codes made here are static: your link or text is stored directly in the pattern of squares. "
            "There's no redirect service in the middle, no tracking and no expiry date, so the code keeps working "
            "for as long as the link it points to exists. Many \"free\" QR sites create dynamic codes that stop "
            "working when a trial ends; that can't happen with a static code.",
            "The image is about 1000 by 1000 pixels with a white quiet zone around it and medium error correction, "
            "which lets phones read the code even if around 15 percent of it is scratched or covered. For print, "
            "keep the code at least 2 cm (about 0.8 inch) wide, dark on a light background, and test it from the "
            "distance people will actually scan it.",
            "Shorter content makes a simpler code that scans faster, so use a short link when you can. For Wi-Fi, "
            "type WIFI:T:WPA;S:YourNetwork;P:YourPassword;; and most phones will offer to join the network when they "
            "scan it. Because a static code can't be edited later, double-check the link before printing menus, "
            "flyers or business cards.",
        ],
        "article": None,
    },
    # ------------------------------------------------------------------ Media tools
    "mp4-to-mp3": {
        "steps": [
            "Upload an MP4 video that has sound.",
            "The audio track is extracted from the video and encoded as MP3.",
            "Download the MP3 and play it on any phone, car stereo or music app.",
        ],
        "body": [
            "Pulling the sound out of a video is handy for lectures, recorded meetings, interviews, sermons and "
            "music practice: you get a much smaller file that plays in the background or offline, without the video "
            "draining your battery. MP3 is the most widely supported audio format there is, from old car stereos to "
            "smart speakers.",
            "Only audio that already exists in the video can be extracted. Some MP4 files, such as many screen "
            "recordings and clips exported without sound, have no audio track at all; in that case the converter "
            "shows a clear \"no audio track\" message instead of returning a silent file.",
            "Because the upload limit applies to the video, this tool is best for short clips. A minute of HD phone "
            "video is often 60 MB or more, while screen recordings, voice memos saved as video and low-resolution "
            "clips are much smaller. To get audio from a long recording, trim the video first on your phone, or "
            "lower its resolution, and then upload it.",
            "The MP3 is saved at 128 kbps and 44.1 kHz, which is clear for speech and fine for casual music "
            "listening. The file keeps the video's name, so lecture-week-3.mp4 downloads as lecture-week-3.mp3, "
            "which makes a series of recordings easy to keep in order.",
        ],
        "article": "how-to-extract-audio-from-mp4",
    },
    "wav-to-mp3": {
        "steps": [
            "Upload a .wav audio file.",
            "The audio is compressed into the MP3 format.",
            "Download the MP3, which is usually about a tenth of the original size.",
        ],
        "body": [
            "WAV files are uncompressed, which is why recorders, studio software and voice-memo apps produce them, "
            "but it also makes them huge. CD-quality stereo WAV uses about 10 MB per minute. The same minute as an "
            "MP3 at a common bitrate of 128 kbps is roughly 1 MB, small enough to email, upload or keep on a phone.",
            "MP3 is a lossy format: it removes sounds that people are least likely to hear. For speech, podcasts "
            "and everyday listening the difference is very hard to notice. Keep the original WAV if you plan to "
            "edit, mix or master the audio later, because each round of lossy compression loses a little more "
            "detail.",
            "Since WAV is so large, the upload limit fits about one minute of CD-quality stereo audio, and longer "
            "for mono recordings or lower sample rates such as voice notes. For a longer recording, split it into "
            "parts in an audio editor first, or export it from your recording app at a lower sample rate.",
            "The MP3 is encoded at 128 kbps and 44.1 kHz, the settings many podcasts and streaming services use, "
            "which keeps voices clear and music pleasant on phones, laptops and car speakers. The file keeps its "
            "name, so interview-01.wav downloads as interview-01.mp3.",
        ],
        "article": "how-to-convert-wav-to-mp3",
    },
    "avi-to-mp4": {
        "steps": [
            "Upload an .avi video.",
            "The video is re-encoded to H.264 with AAC audio inside an MP4 file.",
            "Download the MP4 and play it on phones, smart TVs, browsers and editing apps.",
        ],
        "body": [
            "AVI is a container format from the 1990s that is still produced by older camcorders, dash cams, "
            "security systems and screen recorders. The problem is that an AVI file can hold many different codecs, "
            "and phones, browsers and smart TVs often refuse to play them. MP4 with H.264 video and AAC audio is the "
            "combination that plays almost everywhere.",
            "This is a full conversion, not just a rename, so the video is re-encoded frame by frame. Short clips "
            "finish in seconds; longer ones can take a minute or two depending on resolution and how busy the "
            "server is. Keep the page open until the download button appears.",
            "H.264 is usually far more efficient than the older codecs found in AVI files, so the MP4 is often "
            "smaller than the original at similar quality. Because of the upload limit, this tool suits short clips "
            "such as dash cam events, family videos and screen recordings. If your AVI is larger, trim it first or "
            "convert it in parts.",
            "If the converted video has no sound, the original AVI probably has no audio track, or uses an "
            "unusual audio format; play the AVI in VLC to check. If the picture looks blocky, the source was most "
            "likely recorded at a low bitrate, and re-encoding can't restore detail the camera never captured.",
        ],
        "article": "how-to-convert-avi-to-mp4",
    },
    "mp3-to-mp4": {
        "steps": [
            "Upload an MP3 audio file.",
            "The audio is combined with a plain black 640 x 480 picture to make a video.",
            "Download the MP4 and upload it to any site that only accepts video.",
        ],
        "body": [
            "Some platforms, such as video sites and many social apps, accept only video files, even when all you "
            "want to share is a podcast episode, a song demo, a sermon or a voice message. Wrapping the MP3 in an MP4 "
            "solves that without any video editing.",
            "The picture is a simple black frame that stays on screen for the whole length of the audio. It is "
            "encoded at one frame per second, which keeps the video file only slightly larger than the MP3 itself, "
            "so it uploads quickly. The sound is re-encoded as AAC, the standard audio format for MP4, at a bitrate "
            "similar to a typical MP3, so it sounds the same for normal listening.",
            "Custom cover art and waveforms are not supported yet. If you need a picture on screen, make the MP4 "
            "here and add an image in a free editor such as Clipchamp or iMovie, or use the platform's own thumbnail "
            "option after uploading.",
            "Before uploading the video, check the platform's rules. Most video sites require that you own the "
            "rights to the music or speech you upload, and they may mute or block videos that use copyrighted "
            "songs. Podcasts, lectures, sermons and your own recordings are the safest fit for this tool.",
        ],
        "article": None,
    },
    "mp4-to-gif": {
        "steps": [
            "Upload a short MP4, MOV or WebM clip.",
            "The first 15 seconds are turned into a looping GIF at 12 frames per second.",
            "Download the GIF and drop it into chats, emails, slides or documentation.",
        ],
        "body": [
            "GIFs play automatically, loop forever and work in places that don't support video, such as many email "
            "clients, forums, wikis, README files and older chat apps. That makes them ideal for reactions, short "
            "product demos and step-by-step screen captures.",
            "To keep the file reasonable, the clip is limited to its first 15 seconds, 12 frames per second, and a "
            "maximum size of 480 pixels in width or height. The converter builds a custom 256-color palette from "
            "your clip in two passes, which gives noticeably cleaner colors than a generic palette.",
            "GIF is an old format and is much less efficient than video: a few seconds of GIF can be larger than "
            "the original MP4. For the smallest file, trim the clip to the exact moment you need before uploading, "
            "and choose scenes with less motion and fewer colors. If the place you're posting to accepts video, an "
            "MP4 will usually look better at a fraction of the size.",
            "For screen recordings and tutorials, crop the video to the area that matters before converting. A "
            "smaller frame keeps text readable at 480 pixels and makes the GIF much lighter. Clips with a still "
            "background also compress better, because the encoder can skip the parts of each frame that don't "
            "change.",
        ],
        "article": None,
    },
    "gif-to-mp4": {
        "steps": [
            "Upload an animated .gif file.",
            "The animation is encoded as an H.264 MP4 video at its original frame rate.",
            "Download the MP4, which is usually far smaller and smoother than the GIF.",
        ],
        "body": [
            "Large GIFs are slow to load, often fail to upload to social networks and messaging apps, and look "
            "grainy because GIF can show only 256 colors per frame. Converting to MP4 typically makes the file 5 to "
            "10 times smaller, keeps colors smoother and plays smoothly on Instagram, TikTok, X, WhatsApp and in "
            "PowerPoint.",
            "The video keeps your GIF's original frame rate and covers the first 30 seconds, scaled so the longest "
            "side is at most 720 pixels. H.264 is the most widely supported video format, so the result plays on "
            "practically every phone, browser and computer without extra apps.",
            "A few things change by design. MP4 can't store transparency, so see-through areas become a solid "
            "background. Videos don't loop on their own the way GIFs do, but most social apps and players loop short "
            "clips automatically, and PowerPoint lets you tick \"Loop until stopped\".",
            "Converting also helps websites. A page that loads slowly because of a heavy GIF banner or tutorial "
            "animation usually becomes noticeably faster when the GIF is replaced by a short MP4 set to autoplay, "
            "loop and stay muted, which modern browsers allow without a click.",
        ],
        "article": None,
    },
}
