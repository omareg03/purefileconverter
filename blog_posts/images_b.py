"""Image size guides: compressing JPGs, resizing images, HEIC to JPG."""
from blog_posts import C, H, IMG, L, O, P, SUB

ARTICLES = [
    {
        "slug": "how-to-compress-jpg-images",
        "category": "Image Guides",
        "icon": "fa-compress",
        "title": "How to Compress JPG Images for Faster Loading — Free Guide",
        "description": "Make JPG photos much smaller without visible quality loss. Which quality setting to use, "
                       "why resizing matters more, and how to hit an exact upload limit.",
        "tool_name": "Image Compressor",
        "tool_link": "/compress-image",
        "date_published": "2026-10-11",
        "date_modified": "2026-10-26",
        "content_blocks": [
            P("A modern phone photo is often 3 to 6 MB. That is fine in your camera roll, but it is too heavy for a "
              "fast website, an online application form with a size cap, or an email with a dozen attachments. "
              "Compressing JPGs is the quickest fix, and if you choose the right settings, nobody can tell the "
              "difference by looking."),
            IMG("/static/compress-jpg-image-tool.svg",
                "JPG image compressor showing file size reduction with a compression slider"),
            H("How JPG compression works"),
            P("JPG divides a picture into small blocks and stores a simplified description of each one. The quality "
              "setting decides how much fine detail is kept. At high settings, almost everything is preserved. At "
              "lower settings, subtle texture in skies, skin and shadows is smoothed away, and at very low settings "
              "you start to see blocky squares and smudged edges."),
            P("The quality number is not a percentage of the original image, and the same number can produce "
              "different results in different programs. Treat it as a dial: lower means smaller and softer, higher "
              "means larger and sharper."),
            H("Which quality setting should you use?"),
            L("85 to 90: photography portfolios and images where every detail matters. Files are still noticeably "
              "smaller than camera originals.",
              "70 to 80: the sweet spot for websites, blogs, online stores and email. Most people can't tell these "
              "apart from the original at normal size.",
              "50 to 65: thumbnails and previews, or when you must hit a strict size limit.",
              "Below 50: emergency use only. Compression artifacts become obvious, especially around text."),
            H("Compress a JPG online"),
            O("Open the free Compress Image tool.",
              "Upload a JPG or WebP image.",
              "Set the quality. Start at 75 if you're not sure.",
              "Download the result and compare it with the original at 100 percent zoom."),
            P("The file keeps its format and its pixel dimensions; only the way the detail is stored changes. For "
              "JPGs, the encoder also optimizes its internal tables, which trims a few extra kilobytes at no cost "
              "to quality."),
            H("Resize first: it usually matters more"),
            P("Compression and resizing work best together, and resizing is often the bigger win. A 4000 x 3000 "
              "pixel photo contains 12 million pixels, while a typical Full HD laptop screen shows about 2 million. "
              "Reducing that photo to 1600 pixels wide removes about 84 percent of the pixels before compression "
              "even starts, and it will still look sharp on any web page."),
            C("Order of operations: resize to the size you actually need, then compress. Doing it the other way "
              "around means compressing pixels you are about to throw away."),
            H("Hitting an exact size limit"),
            P("Forms often state limits such as \"maximum 200 KB\" or \"under 1 MB\". A reliable approach:"),
            O("Resize the image so its longest side is about 1200 to 1600 pixels.",
              "Compress at quality 75 and check the file size of the download.",
              "Still too large? Lower the quality in steps of 10 and try again.",
              "If quality drops below about 50 and it still doesn't fit, resize smaller instead of compressing "
              "harder."),
            H("Avoid compressing the same file repeatedly"),
            P("Every time a JPG is opened, edited and saved again, it goes through compression again and loses a "
              "little more detail. Photographers call this generation loss. Keep your original photo untouched, and "
              "always create compressed copies from that original rather than from a previous copy."),
            H("Tips for website owners"),
            L("Serve images at the size they display. A 300-pixel-wide thumbnail should not be a 3000-pixel file "
              "scaled down by the browser.",
              "Consider WebP for your site. It is typically 25 to 34 percent smaller than JPG at similar quality and "
              "is supported by all current major browsers.",
              "Add loading=\"lazy\" to images further down the page, so the browser only downloads them when the "
              "visitor scrolls near them.",
              "Always set width and height attributes on images to prevent the layout from jumping while pages "
              "load."),
            SUB("What about PNG files?"),
            P("PNG is lossless, so it has no quality dial to turn down. If a PNG is a photograph, convert it to JPG "
              "or WebP first; that alone usually shrinks it several times over. If it is a logo or screenshot, keep "
              "it as PNG and reduce its dimensions instead."),
            P("With a sensible quality setting and the right dimensions, most photos can drop from several megabytes "
              "to a few hundred kilobytes, with faster pages and fewer rejected uploads as the reward."),
            H("Common questions"),
            SUB("What is a good file size for a website image?"),
            P("For most images inside an article or product page, a few hundred kilobytes or less is a "
              "reasonable target. Large full-width banners may reach 300 to 500 KB, while thumbnails should be "
              "tens of kilobytes. Smaller is better, as long as the picture still looks sharp."),
            SUB("Can I compress a JPG without losing any quality?"),
            P("Lossless optimizers can remove metadata and rewrite a JPG more efficiently, usually saving only "
              "a few percent. Real savings always involve a small quality trade-off, which at settings between "
              "70 and 80 is very hard to see."),
            SUB("Why does the sky in my compressed photo look blotchy?"),
            P("Smooth gradients such as skies, walls and studio backgrounds show compression first, as visible "
              "bands or blocks. Raise the quality by about 10, or reduce the image's dimensions instead of "
              "compressing it harder."),
            SUB("Is WebP better than a compressed JPG?"),
            P("For websites, usually yes: at the same visual quality, WebP files are typically a quarter to a "
              "third smaller. Keep JPG where compatibility matters, such as email attachments and upload forms."),
        ],
    },
    {
        "slug": "how-to-resize-images-online",
        "category": "Image Guides",
        "icon": "fa-image",
        "title": "How to Resize Images Online Without Losing Quality — Free Guide",
        "description": "Resize photos to exact pixel dimensions for websites, social media, email and printing, "
                       "without stretching or blurring. Includes common sizes and the math for aspect ratios.",
        "tool_name": "Image Resizer",
        "tool_link": "/image-resizer",
        "date_published": "2026-10-11",
        "date_modified": "2026-10-26",
        "content_blocks": [
            P("Resizing sounds simple, yet it causes a surprising number of stretched faces, blurry banners and "
              "rejected uploads. Most problems come from three misunderstandings: confusing pixels with file size, "
              "ignoring the aspect ratio, and trying to make small images bigger. Get those right and resizing "
              "becomes a ten-second job."),
            IMG("/static/image-resizer-tool.svg", "Online image resizer showing a photo being scaled to new pixel dimensions"),
            H("Pixels, file size and DPI are three different things"),
            L("Pixel dimensions, such as 1920 x 1080, describe how much detail an image contains. This is what "
              "resizing changes.",
              "File size, such as 850 KB, is how much storage the image takes. Smaller dimensions usually mean a "
              "smaller file, but compression also plays a big role.",
              "DPI (dots per inch) only matters when printing. Changing the DPI number alone doesn't add or remove a "
              "single pixel."),
            H("Keep the aspect ratio to avoid stretching"),
            P("The aspect ratio is the relationship between width and height. If you change one without changing "
              "the other proportionally, people look taller or wider than they are. To keep proportions, calculate "
              "the new height like this: new height = new width x original height / original width."),
            P("Example: a 4032 x 3024 phone photo resized to 1200 pixels wide should be 1200 x 3024 / 4032 = 900 "
              "pixels tall. If the target size has a different shape, such as a square, crop the photo to that shape "
              "first and then resize it, rather than squeezing it."),
            H("Resize an image online"),
            O("Open the free Image Resizer.",
              "Upload a JPG, PNG or WebP image (up to 10 MB).",
              "Type the new width and height in pixels, anywhere from 1 to 8000.",
              "Download the resized image, which keeps its original format."),
            P("The resizer uses Lanczos resampling, one of the sharpest methods for shrinking photographs, and it "
              "turns phone photos the right way up first, so the width and height you type match what you see on "
              "screen."),
            H("Common sizes worth remembering"),
            L("Instagram square post: 1080 x 1080. Portrait post: 1080 x 1350.",
              "Facebook or LinkedIn link preview image: 1200 x 630.",
              "YouTube thumbnail: 1280 x 720.",
              "X (Twitter) header: 1500 x 500. LinkedIn personal banner: 1584 x 396.",
              "Full HD slide or wallpaper: 1920 x 1080.",
              "Photos for email or a blog: about 1600 pixels on the longest side.",
              "Online store product photos: check your platform; many recommend square images of 1000 to 2000 "
              "pixels so zoom works well."),
            C("Platforms change their recommended sizes from time to time. If an upload looks cropped, check the "
              "platform's current help page and match its aspect ratio first; the exact pixel count matters less."),
            H("Resizing for print"),
            P("For prints, multiply the print size in inches by the resolution. Photo labs typically want 300 DPI, so "
              "a 4 x 6 inch print needs 1200 x 1800 pixels, and an 8 x 10 needs 2400 x 3000. Most modern phone "
              "photos have more than enough pixels for standard print sizes, so for printing you rarely need to "
              "resize at all; just choose the matching crop."),
            H("Why making images bigger doesn't add detail"),
            P("Shrinking an image throws away pixels you don't need, which looks clean. Enlarging has to invent new "
              "pixels from the existing ones, so the result looks soft, and edges can turn blurry. Doubling the size "
              "of a small logo will never look as sharp as the original vector artwork. Always start from the largest "
              "version of an image you have, and resize down."),
            SUB("Built-in alternatives"),
            L("Windows Photos: open the picture, click the three-dot menu and choose Resize image.",
              "Windows Paint: press Ctrl+W, choose Pixels and keep Maintain aspect ratio ticked.",
              "Mac Preview: use Tools > Adjust Size and make sure Scale proportionally is selected.",
              "iPhone: the Photos app crops but doesn't set exact pixel sizes, so an online resizer is the easiest "
              "route."),
            H("Resize, then compress"),
            P("Resizing reduces the number of pixels; compression reduces how much space each pixel takes. For "
              "the smallest files, do both: resize to the dimensions you need, then run the image through a "
              "compressor at a quality around 75. That combination turns most multi-megabyte photos into files of a "
              "few hundred kilobytes that still look crisp."),
            H("Common questions"),
            SUB("Does resizing reduce the file size?"),
            P("Making an image smaller in pixels almost always makes the file smaller too, often dramatically, "
              "because there is less detail to store. Halving the width and height leaves only a quarter of the "
              "pixels. Making an image larger increases the file size without adding real detail."),
            SUB("How do I make an image exactly 500 KB or 1 MB?"),
            P("Pixel dimensions don't map directly to file size, because compression depends on what the "
              "picture contains. Resize first to a sensible size, then use an image compressor and adjust the "
              "quality until the file is under your target."),
            SUB("What DPI should I use for web images?"),
            P("It doesn't matter. Browsers ignore the DPI value and display images by their pixel dimensions, "
              "so a 1200-pixel-wide image looks the same at 72 or 300 DPI on a website. DPI only matters when "
              "you print."),
            SUB("Can I resize many images at once?"),
            P("The online resizer handles one image per upload. For batches on Windows, Microsoft's free "
              "PowerToys includes an Image Resizer that adds a resize option to the right-click menu for any "
              "number of files. On a Mac, select several images in Preview's sidebar and use Tools > Adjust "
              "Size to resize them all in one step."),
        ],
    },
    {
        "slug": "how-to-convert-heic-to-jpg",
        "category": "Image Guides",
        "icon": "fa-mobile-screen-button",
        "title": "How to Convert iPhone HEIC Photos to JPG (Windows, Mac and Online)",
        "description": "Why iPhones save photos as HEIC, how to convert them to JPG for free on any device, and the "
                       "iPhone settings that stop the problem from happening again.",
        "tool_name": "HEIC to JPG Converter",
        "tool_link": "/heic-to-jpg",
        "date_published": "2026-10-13",
        "date_modified": "2026-10-26",
        "content_blocks": [
            P("You copy photos from your iPhone to a Windows PC, or try to upload one to a job application, and "
              "the file ends in .heic and won't open. This is one of the most common file problems iPhone owners "
              "run into. The photos are fine; they are simply saved in a format that much of the world's software "
              "still doesn't handle well."),
            IMG("/static/heic-to-jpg-converter-tool.svg",
                "HEIC to JPG converter showing an iPhone photo format converting to JPG"),
            H("What is HEIC, and why does my iPhone use it?"),
            P("HEIC is Apple's name for photos stored in HEIF, the High Efficiency Image File Format, using the "
              "same advanced compression as modern HEVC video. Apple made it the default camera format in iOS 11 in "
              "2017. The benefit is size: a HEIC photo typically takes about half the space of a JPG of similar "
              "quality, which means more photos fit on your phone and in iCloud."),
            P("HEIF can also hold extra information alongside the picture, which Apple uses for features such as "
              "Live Photos and the depth data behind Portrait mode. The drawback is compatibility. Many Windows "
              "programs, older Android phones, websites and online forms don't accept HEIC files."),
            H("Convert HEIC to JPG online"),
            O("Open the free HEIC to JPG converter.",
              "Upload a .heic or .heif photo (up to 10 MB).",
              "Download the JPG and use it anywhere."),
            P("The JPG is saved at quality 92 and at the photo's full original resolution, so it stays sharp for "
              "viewing, sharing and printing. It is also rotated correctly, so pictures taken sideways don't arrive "
              "on their side. If the photo was a Live Photo, you get the still image."),
            H("Convert on Windows"),
            P("Windows 10 and 11 can display HEIC photos once two extensions are installed from the Microsoft Store: "
              "HEIF Image Extensions, which is free, and HEVC Video Extensions, which usually costs a small fee. Some "
              "computers come with HEVC support preinstalled. Once both are installed, you can open a photo in the "
              "Photos app or Paint and save a copy as JPG. Viewing becomes easy, but the files are still HEIC, so "
              "uploads to websites may still fail until you convert them."),
            H("Convert on a Mac"),
            P("Macs open HEIC natively. Open the photo in Preview, choose File > Export, set Format to JPEG and "
              "save. To convert several at once, open them together in Preview, select them all in the sidebar and "
              "choose File > Export Selected Images. In the Photos app, File > Export > Export Photos with the JPEG "
              "option does the same job."),
            H("Stop the problem at the source"),
            SUB("Shoot JPG instead of HEIC"),
            P("On your iPhone, go to Settings > Camera > Formats and choose Most Compatible. From then on, the camera "
              "saves new photos as JPG. The files will be larger, so it is a trade-off between storage space and "
              "convenience."),
            SUB("Convert automatically when copying to a computer"),
            P("Go to Settings > Photos and, under Transfer to Mac or PC, choose Automatic. When you copy photos to a "
              "computer with a cable, the iPhone converts them to JPG on the way. This keeps the space savings on "
              "the phone and gives you compatible files on the computer."),
            C("Sharing tip: when you send photos through Mail or many messaging apps, iOS often converts them to "
              "JPG automatically. The problem mostly appears when you copy original files with a cable, a cloud "
              "folder or a file manager."),
            H("Will converting reduce quality?"),
            P("Converting from one compressed format to another always involves re-encoding, but at a high quality "
              "setting the difference is not visible in normal viewing, printing or sharing. The JPG will be larger "
              "than the HEIC file, often around twice the size, because JPG compression is less efficient. Keep the "
              "original HEIC files if you want the smallest archive, and convert copies whenever you need to share "
              "them."),
            H("Quick troubleshooting"),
            L("\"The file is too large\": very high-resolution photos can exceed upload limits. Convert to JPG, then "
              "reduce the dimensions with an image resizer.",
              "\"The converted photo is sideways\": use a converter that applies the orientation data, as "
              "PureFileConverter does, or rotate it once in any photo app.",
              "\"I have hundreds of photos\": use the iPhone's Automatic transfer setting or a Mac's batch export "
              "rather than converting one by one.",
              "\"It's a .mov file, not a photo\": that is the video part of a Live Photo. Use the matching .heic "
              "file for the still image."),
            P("HEIC is a good format held back by compatibility. Converting the photos you need to share, and "
              "adjusting two iPhone settings, takes the frustration out of it for good."),
            H("Common questions"),
            SUB("Will the JPG keep the date and location of the photo?"),
            P("No. The converter copies the picture but not the photo's metadata, so the date taken, camera "
              "details and GPS location are not included in the JPG. That is good for privacy when you share "
              "photos. If you are archiving photos and want dates preserved, use the iPhone's Automatic "
              "transfer setting or a Mac's export instead."),
            SUB("Can I convert HEIC to PNG instead?"),
            P("You can, but there is little reason to. HEIC photos are photographs, so JPG is the natural "
              "match; PNG would make the files many times larger without improving how they look."),
            SUB("Do Android phones use HEIC?"),
            P("Some Android phones offer HEIF or HEIC as an optional camera format, but most save JPG by "
              "default. If someone sends you a .heic file from any phone, the same conversion methods apply."),
        ],
    },
]
