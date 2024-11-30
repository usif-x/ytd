import os
from flask import Flask, request, render_template_string
import yt_dlp

app = Flask(__name__)

def get_m3u8(link):
    try:
        ydl_opts = {
            'format': 'best',
            'noplaylist': True,
            'quiet': True
            'cookiefile': './cookies.txt'  # Pass cookies to yt-dlp
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info without downloading
            info_dict = ydl.extract_info(link, download=False)

            # Check if 'formats' is in the extracted information
            if 'formats' in info_dict:
                for format in info_dict['formats']:
                    # Check if the format URL contains '.m3u8'
                    if 'url' in format and '.m3u8' in format['url']:
                        return format['url']

            # If no m3u8 URL is found in formats, check if it's available directly
            if 'manifest_url' in info_dict:
                return info_dict['manifest_url']

    except Exception as e:
        print(f"Error: {e}")
        return None

# HTML template with embedded Plyr and Hls.js libraries
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Video Player</title>
    <link rel="stylesheet" href="https://unpkg.com/plyr@3/dist/plyr.css">
    <style>
        .container {
            margin: 100px auto;
            width: 70%;
        }
        video {
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <video controls crossorigin playsinline></video>
    </div>
    <script src="https://cdn.rawgit.com/video-dev/hls.js/18bb552/dist/hls.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/core-js/3.22.8/minified.js"></script>
    <script src="https://unpkg.com/plyr@3"></script>
    <script>
        document.addEventListener("DOMContentLoaded", () => {
            const source = "{{ m3u8_source }}";
            const video = document.querySelector("video");

            const defaultOptions = {};

            if (!Hls.isSupported()) {
                video.src = source;
                var player = new Plyr(video, defaultOptions);
            } else {
                const hls = new Hls();
                hls.loadSource(source);

                hls.on(Hls.Events.MANIFEST_PARSED, function(event, data) {
                    const availableQualities = hls.levels.map((l) => l.height);
                    availableQualities.unshift(0);

                    defaultOptions.quality = {
                        default: 0,
                        options: availableQualities,
                        forced: true,
                        onChange: (e) => updateQuality(e),
                    };
                    defaultOptions.i18n = {
                        qualityLabel: {
                            0: "Auto",
                        },
                    };

                    hls.on(Hls.Events.LEVEL_SWITCHED, function(event, data) {
                        var span = document.querySelector(
                            ".plyr__menu__container [data-plyr='quality'][value='0'] span"
                        );
                        if (hls.autoLevelEnabled) {
                            span.innerHTML = `AUTO (${hls.levels[data.level].height}p)`;
                        } else {
                            span.innerHTML = `AUTO`;
                        }
                    });

                    var player = new Plyr(video, defaultOptions);
                });

                hls.attachMedia(video);
                window.hls = hls;
            }

            function updateQuality(newQuality) {
                if (newQuality === 0) {
                    window.hls.currentLevel = -1;
                } else {
                    window.hls.levels.forEach((level, levelIndex) => {
                        if (level.height === newQuality) {
                            console.log("Found quality match with " + newQuality);
                            window.hls.currentLevel = levelIndex;
                        }
                    });
                }
            }
        });
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def index():
    url = request.args.get('url')
    if not url:
        return "Please provide a URL parameter", 400
    
    m3u8_url = get_m3u8(url)
    if not m3u8_url:
        return "Could not find M3U8 URL", 404
    
    return render_template_string(HTML_TEMPLATE, m3u8_source=m3u8_url)

if __name__ == '__main__':
    app.run(debug=True)
