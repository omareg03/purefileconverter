"""Office and PDF-size guides: Word to PDF, CSV to Excel, compressing PDFs."""
from blog_posts import AFF, C, H, IMG, L, O, P, SUB

ARTICLES = [
    {
        "slug": "how-to-convert-word-to-pdf",
        "category": "Document Guides",
        "icon": "fa-file-word",
        "title": "How to Convert Word Documents to PDF — Free Online Guide",
        "description": "Turn DOC and DOCX files into PDFs that look the same everywhere: the free online method, "
                       "the built-in options in Word and Google Docs, and fixes for font and layout surprises.",
        "tool_name": "Word to PDF Converter",
        "tool_link": "/word-to-pdf",
        "date_published": "2026-10-11",
        "date_modified": "2026-10-26",
        "content_blocks": [
            P("Job portals, schools, landlords and government forms keep asking for the same thing: \"Please upload "
              "a PDF.\" The reason is simple. A Word file can look different on every computer depending on the "
              "installed fonts, the version of Word and even the printer, while a PDF freezes the layout exactly as "
              "you saw it. It is also much harder to change by accident."),
            P("Converting takes a few seconds once you know your options. Here are four free ways, plus the font "
              "issue that causes most of the surprises."),
            IMG("/static/word-to-pdf-converter-tool.svg",
                "Word to PDF converter showing a DOCX document converting to a print-ready PDF file"),
            H("Option 1: Convert online in your browser"),
            O("Open the free Word to PDF converter on PureFileConverter.",
              "Upload a .docx file or an older .doc file (up to 10 MB).",
              "Wait a few seconds while LibreOffice, the open-source office suite, lays out the pages.",
              "Download the PDF and open it once to check it before you send it."),
            P("This is the easiest route on a phone, a Chromebook or a computer without Microsoft Office. The "
              "uploaded document is deleted as soon as the PDF is created, and the PDF is deleted after you download "
              "it."),
            H("Option 2: Save as PDF from Microsoft Word"),
            P("If you have Word, you don't need anything else. On Windows, choose File > Save As, pick a folder and "
              "set Save as type to PDF. The Optimize for setting offers Standard, which is best for printing, or "
              "Minimum size, which is best for email and web uploads. On a Mac, use File > Save As and choose PDF as "
              "the file format."),
            P("Word's own export keeps clickable links and can create PDF bookmarks from your headings when you open "
              "Options before saving. That is worth doing for long reports and manuals."),
            H("Option 3: Download as PDF from Google Docs"),
            P("If you write in Google Docs, or you open a Word file there, use File > Download > PDF Document (.pdf). "
              "Google renders the document with its own fonts, so check the page count and line breaks against the "
              "original if the document came from Word."),
            H("Option 4: Print to PDF"),
            P("Windows 10 and 11 include a virtual printer called Microsoft Print to PDF, and every Mac has a PDF "
              "button in the print dialog. These work from almost any program, but printing produces a flat copy, so "
              "links usually stop being clickable and you can't add bookmarks. Use it as a fallback rather than the "
              "first choice."),
            H("Why fonts cause most problems"),
            P("A PDF made on your own computer embeds the fonts you used, so it looks right everywhere. Problems "
              "happen when a document is converted on a different machine that doesn't have those fonts. The "
              "software then substitutes the closest font it has, and if the substitute has different letter widths, "
              "lines wrap differently, a one-page résumé can spill onto a second page, and tables can shift."),
            L("Fonts that convert reliably online: Arial, Calibri, Cambria, Times New Roman and Courier New, because "
              "free fonts with identical letter widths exist for all of them.",
              "Fonts that may shift: Aptos (the newer Microsoft 365 default), Georgia, Segoe UI and most decorative "
              "fonts.",
              "Custom brand fonts: convert on the computer where the font is installed, using Word's own Save As "
              "PDF."),
            C("Résumé tip: if your one-page résumé becomes two pages after converting, switch the body text to Calibri "
              "or Arial and convert again. Recruiters' systems read those fonts reliably too."),
            H("Checklist before you send the PDF"),
            L("Page count matches the Word document.",
              "Headers, footers and page numbers appear on every page they should.",
              "Images are sharp, and none are cut off at page edges.",
              "Links work, if your PDF needs them.",
              "The file name is clear, for example Jane-Doe-Resume.pdf rather than Document1.pdf.",
              "The file size fits the upload form; if it doesn't, run it through the Compress PDF tool."),
            H("Need to edit the PDF later?"),
            P("Keep the original .docx. Editing a PDF is always harder than editing the source, and converting a PDF "
              "back into Word is possible but rarely perfect. Treat the PDF as the printed copy and the Word document "
              "as the master you update."),
            AFF("Microsoft 365 — Word with built-in PDF export",
                "If you create documents every week, Word's own Save As PDF keeps links and bookmarks and works "
                "offline.", "microsoft+365"),
            P("For a quick one-off conversion, the online converter is the fastest path. For documents you will "
              "revise again and again, saving directly from Word or Google Docs keeps everything in one place."),
            H("Common questions"),
            SUB("Can someone edit my PDF after I convert it?"),
            P("PDFs can be edited with dedicated software, so think of a PDF as hard to change rather than "
              "impossible to change. For contracts and official paperwork, a digital signature or your PDF "
              "software's protection features give a much stronger guarantee."),
            SUB("Why aren't my links clickable in the PDF?"),
            P("Printing to PDF usually flattens links into plain text. Use Save As PDF in Word, or a converter "
              "that exports the document directly, and links stay active."),
            SUB("How do I convert a document with tracked changes and comments?"),
            P("Accept or reject the changes and delete comments first, so the PDF shows only the final text. In "
              "Word, use Review > Accept > Accept All Changes, then Review > Delete > Delete All Comments in "
              "Document, save, and convert."),
            SUB("Can I convert several Word files at once?"),
            P("The online tool converts one document per upload. To combine several documents into a single "
              "PDF, convert each one and then join them in the right order with Merge PDF."),
            SUB("Will my PDF work with screen readers?"),
            P("Use Word's own Save As PDF, open Options, and keep Document structure tags for accessibility "
              "ticked. That creates a tagged PDF that screen readers can navigate by headings. Using Word's "
              "Heading styles in the document makes the biggest difference of all."),
        ],
    },
    {
        "slug": "how-to-convert-csv-to-excel",
        "category": "Document Guides",
        "icon": "fa-file-csv",
        "title": "How to Convert CSV Files to Excel (XLSX) — Free Guide",
        "description": "Turn a CSV export into a real Excel workbook without scrambled characters or lost zeros. "
                       "Free online method, Excel's import tools, and fixes for common CSV problems.",
        "tool_name": "CSV to Excel Converter",
        "tool_link": "/csv-to-excel",
        "date_published": "2026-10-11",
        "date_modified": "2026-10-26",
        "content_blocks": [
            P("CSV stands for comma-separated values. It is the plain-text format almost every system uses for "
              "exports: bank transactions, online store orders, email subscriber lists, survey results and database "
              "reports. Each line is a row, and commas separate the columns. That simplicity is why CSV works "
              "everywhere, and also why it causes so much frustration once you open it in a spreadsheet."),
            P("Converting the file into a real Excel workbook (.xlsx) gives you a file you can format, filter, chart "
              "and share safely. Here is how to do it, and how to avoid the classic CSV traps."),
            IMG("/static/csv-to-excel-converter-tool.svg",
                "CSV to Excel converter showing raw data transforming into a formatted spreadsheet"),
            H("CSV versus XLSX in one minute"),
            L("A CSV file holds only text: no formatting, no formulas, no column widths and only one sheet.",
              "An XLSX file is a full workbook: multiple sheets, number formats, formulas, charts, filters and "
              "frozen header rows.",
              "CSV files are tiny and universal, which makes them perfect for moving data between systems.",
              "XLSX files are what people expect when you share data with a colleague or a client."),
            H("Convert a CSV to Excel online"),
            O("Open the free CSV to Excel converter.",
              "Upload your .csv file. The first row should contain the column names.",
              "Download the .xlsx workbook. The first row becomes the column headings and every other line becomes "
              "a row of data.",
              "Open it in Excel, Google Sheets or LibreOffice Calc and apply any formatting you like."),
            P("The converter reads the file as UTF-8, the modern standard, and falls back to Latin-1 for older "
              "exports, so names with accents like José or Müller come through correctly instead of turning into "
              "garbled symbols."),
            H("The three CSV traps to know about"),
            SUB("1. Leading zeros disappear"),
            P("Spreadsheet software treats anything that looks like a number as a number, and numbers don't have "
              "leading zeros. ZIP codes such as 02134, phone numbers, employee IDs and product codes can lose their "
              "first digits. This happens when Excel opens a CSV directly and also in most automated conversions, "
              "including this one. If those columns matter, import the CSV into Excel with Data > From Text/CSV, "
              "click Transform Data, and set those columns to Text before loading."),
            SUB("2. Long numbers turn into scientific notation"),
            P("Excel stores numbers with 15 digits of precision. Credit card numbers, tracking numbers and other "
              "long identifiers can be displayed as 4.12E+15 or have their last digits replaced by zeros. Treat such "
              "columns as text, exactly like ZIP codes, rather than numbers."),
            SUB("3. Semicolons instead of commas"),
            P("In many European countries the comma is the decimal separator, so exports use semicolons between "
              "columns instead. If a converted file shows everything in column A, that is the reason. Open the file "
              "in a text editor, check the separator, and either re-export it with commas or use Excel's import "
              "wizard, which lets you choose the delimiter."),
            C("Dates stay exactly as they were written in the CSV. After converting, select the date column and use "
              "Format Cells to choose how dates should appear, or use Data > Text to Columns to turn text dates into "
              "real Excel dates."),
            H("Making the workbook pleasant to use"),
            L("Freeze the header row with View > Freeze Panes > Freeze Top Row, so column names stay visible while "
              "you scroll.",
              "Turn the data into a table with Ctrl+T. You get filters, banded rows and formulas that extend "
              "automatically.",
              "Double-click the border between column letters to fit each column to its contents.",
              "Use Data > Remove Duplicates before analyzing exports that may contain repeated rows.",
              "Save as .xlsx, not .csv, or all formatting will be lost when you close the file."),
            H("Going the other way"),
            P("Many upload forms, such as email marketing tools and online stores, only accept CSV. To create one "
              "from a workbook, use File > Save As in Excel and choose CSV UTF-8 (Comma delimited). The UTF-8 "
              "version keeps accented characters intact. Only the active sheet is saved, and formulas are replaced by "
              "their values."),
            AFF("Microsoft 365 Personal — Excel and Word",
                "The full desktop Excel includes Power Query for importing large CSV files with exact control over "
                "every column.", "microsoft+365+personal"),
            H("Large files and privacy"),
            P("Online conversion is ideal for everyday exports of up to 10 MB, which is tens of thousands of rows. "
              "Very large datasets are better imported directly in Excel or Google Sheets on your own computer. If "
              "your CSV contains customer or financial details, remember that any online upload leaves your device; "
              "PureFileConverter deletes the file right after conversion and the workbook after download."),
            H("Common questions"),
            SUB("Why do accented letters look wrong when I open a CSV directly in Excel?"),
            P("Excel sometimes guesses the wrong text encoding for CSV files, turning é into Ã©. Converting "
              "with a tool that reads UTF-8 correctly avoids it, and so does importing with Data > From "
              "Text/CSV and choosing 65001: Unicode (UTF-8) as the file origin."),
            SUB("Is there a limit on rows?"),
            P("An Excel worksheet holds up to 1,048,576 rows and 16,384 columns. Online, the 10 MB upload limit "
              "is usually reached long before that, so very large exports are best opened with Excel's import "
              "tools on your own computer."),
            SUB("Will formulas work after converting?"),
            P("A CSV file only contains values, never formulas, so there is nothing to carry over. Add totals "
              "and calculations in Excel after converting, ideally after turning the data into a table so new "
              "formulas fill down automatically."),
            SUB("Can I open the converted file in Google Sheets?"),
            P("Yes. Upload the XLSX to Google Drive and open it with Google Sheets, or use File > Import inside "
              "an existing spreadsheet to add it as a new sheet."),
        ],
    },
    {
        "slug": "how-to-compress-pdf-files",
        "category": "Document Guides",
        "icon": "fa-file-zipper",
        "title": "How to Compress a PDF (and Why Some PDFs Barely Shrink)",
        "description": "Find out what makes a PDF large, how to shrink it for email and upload limits, and what to "
                       "do when compression doesn't make it small enough.",
        "tool_name": "Compress PDF",
        "tool_link": "/compress-pdf",
        "date_published": "2026-10-13",
        "date_modified": "2026-10-26",
        "content_blocks": [
            P("An upload form that stops at 2 MB, an email that bounces because the attachment is too big, a "
              "portal that refuses your application packet: oversized PDFs cause a lot of last-minute stress. The "
              "good news is that most large PDFs can be shrunk dramatically. The key is understanding what is "
              "actually taking up the space."),
            IMG("/static/compress-pdf-files-guide.svg",
                "Compress PDF files showing file size reduction from large to small"),
            H("What makes a PDF big?"),
            P("Text is tiny. A hundred pages of plain text can fit in a few hundred kilobytes. What makes a PDF "
              "heavy is almost always pictures, and especially pictures stored at a much higher resolution than "
              "anyone needs."),
            L("Scanned pages: every page is a full photograph, often saved at 300 to 600 DPI.",
              "Phone photos inserted into a document: a single modern phone photo can be several megabytes.",
              "Embedded fonts: usually small, but documents with many complete fonts add up.",
              "Duplicated content: a logo or background image stored separately on every page.",
              "Exports from design software: print-ready files keep images at full print quality."),
            H("How to compress a PDF online"),
            O("Open the free Compress PDF tool.",
              "Upload the PDF (up to 10 MB).",
              "Wait while the images are resized and the file structure is optimized.",
              "Download the smaller file and compare the size and the look with the original."),
            P("Here is what the compressor actually does. Any photo larger than about 1600 pixels on its longest "
              "side, which is roughly 150 DPI on a Letter or A4 page, is scaled down and saved as a JPEG at quality "
              "70. That level is sharp on screens and fine for office printing. Page content is compressed, and "
              "objects repeated across pages are stored only once. Text, fonts and vector drawings are left "
              "untouched, so words stay crisp and searchable. If compression can't make the file smaller, you get "
              "the original back instead of a bigger file."),
            C("Expect big savings on scans and photo-heavy PDFs, often more than half. PDFs that are mostly text "
              "were already compact, so they barely change."),
            H("Built-in options you may already have"),
            SUB("Microsoft Word"),
            P("If the PDF started as a Word document, export it again with File > Save As, choose PDF, and select "
              "Minimum size (publishing online). Word compresses images during export. You can also shrink pictures "
              "in the document first with Picture Format > Compress Pictures and a lower resolution."),
            SUB("Mac Preview"),
            P("Open the PDF in Preview, choose File > Export, and pick the Reduce File Size Quartz filter. It is "
              "aggressive and can make photos blurry, so check the result, but it is fast and free."),
            SUB("Scanning apps"),
            P("When you control the scan, prevention beats compression. Scan documents at 200 to 300 DPI in "
              "grayscale or black and white instead of full color. A black-and-white text page can be ten times "
              "smaller than the same page scanned in color."),
            H("When compression isn't enough"),
            L("Split the document. Use Split PDF to send the pages in two or three parts, or to remove pages the "
              "recipient doesn't need, such as blank backs of scanned sheets.",
              "Check for oversized pages. One huge photo page can be responsible for most of the size. Remove or "
              "replace that page and merge the rest again with Merge PDF.",
              "Share a link. Most email services cap attachments at about 20 to 25 MB. For larger files, upload to "
              "a cloud drive and send a link.",
              "Ask about the limit. Some portals accept several smaller files instead of one large packet."),
            H("Quality checklist after compressing"),
            P("Zoom to 100 percent and read a paragraph of small print, look at any signatures and stamps, and check "
              "photos for blocky areas. If something matters for legal or official reasons, such as a signed form or "
              "an ID scan, keep the uncompressed original as well and send the compressed copy only when the "
              "recipient's limits require it."),
            AFF("Adobe Acrobat Pro — advanced PDF optimization",
                "Paid software that lets you choose exact image resolution and audit what uses space in a PDF. "
                "Useful for people who prepare large PDFs every day.", "adobe+acrobat+pro"),
            P("For most everyday cases, one pass through a compressor that targets images is all you need. Knowing "
              "that pictures are the real weight helps you predict results and choose the next step when a file "
              "still won't fit."),
            H("Common questions"),
            SUB("Does compressing a PDF make the text blurry?"),
            P("No. Text, fonts and vector graphics are kept exactly as they are; only large photos and scans "
              "are resized and recompressed. Body text looks the same as before, even when you zoom in."),
            SUB("Why did my PDF barely get smaller?"),
            P("Most of its size is probably text, fonts or vector artwork, which are already compact, or its "
              "images were compressed when the PDF was created. In that case the file is close to as small as "
              "it can get without removing content, and splitting it is the better option."),
            SUB("Is it safe to compress signed documents?"),
            P("Compression keeps everything visible on the page, including scanned signatures. A PDF with a "
              "digital signature, the cryptographic kind that shows a signature panel in your reader, will lose "
              "its validity when the file is changed in any way, so send the original for anything that must "
              "stay verifiably signed."),
            SUB("Can I compress a password-protected PDF?"),
            P("Not directly. Open the PDF in your reader, remove the password, compress the unlocked copy, and "
              "add protection again afterwards if you still need it. The tool tells you when a file is "
              "password-protected instead of failing silently."),
            SUB("Can I choose how much to compress?"),
            P("The online tool uses one balanced setting designed to keep documents readable and printable. "
              "Desktop software such as Adobe Acrobat lets you pick exact image resolutions when you need finer "
              "control, for example for high-quality print files."),
        ],
    },
]
