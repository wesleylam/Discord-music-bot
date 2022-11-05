# TODO: REWRITE README FOR DJ2.0
# Discord mini music bot
Built using Python 3.7.7 with AWS DynamoDB

## Required modules
- boto3
- discord.py
- discord_components
- discord.py[voice] (pycparser, cffi, six, PyNaCl)
- youtube-dl
- ffmpeg
- opus (Not required in windows environment: https://discordpy.readthedocs.io/en/latest/api.html#discord.opus.load_opus)
- pytz (timezone)

## Packages install
- discord (async-timeout, chardet, typing-extensions, multidict, attrs, idna, yarl, aiohttp, discord.py, discord)
- discord.py[voice] (six, pycparser, cffi, PyNaCl)
- discord_components
- youtube-dl
- ffmpeg
- pytz
- requests (charset-normalizer, urllib3, certifi, requests)
- boto3 (jmespath, botocore, s3transfer, boto3)

## Configurations
- Configure AWS connection `aws configure`
    - Require key pair (ID, secret key)
- `config.py`: access keys and file directories
    - `TOKEN`: Your Discord bot access token. Create through [Discord Developer Portal] (https://discord.com/developers/applications)
    - `yt_API_key`: Your Youtube API key, for video/song search
    - `opus_dir`: opus module library path, used with ffmpeg to play audio
    - `dynamodb_table`: table name of dynamodb for song info
    - `dynamodb_hist_table`: table name of dynamodb for played histories
- `options.py`: (Optional, defaulted) Options for ytdl, ffmpeg and other default in-app settings. Change to customise your settings.
    - `cookiefile` options within ytdl options can be added to access premium content


## fixed bug
/home/wesleylam/.local/lib/python3.7/site-packages/youtube_dl/extractor/youtube.py
refer to this fix: https://github.com/ytdl-org/youtube-dl/pull/30366/files  
```
    #  r'\bm=(?P<sig>[a-zA-Z0-9$]{2})\(decodeURIComponent\(h\.s\)\)',
    #  r'\bc&&\(c=(?P<sig>[a-zA-Z0-9$]{2})\(decodeURIComponent\(c\)\)',
    #  r'(?:\b|[^a-zA-Z0-9$])(?P<sig>[a-zA-Z0-9$]{2})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\);[a-zA-Z0-9$]{2}\.[a-zA-Z0-9$]{2}\(a,\d+\)',
    #  r'(?:\b|[^a-zA-Z0-9$])(?P<sig>[a-zA-Z0-9$]{2})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',

    # replaced with below 4 lines, fixing function signature bug
      r'\bm=(?P<sig>[a-zA-Z0-9$]{2,})\(decodeURIComponent\(h\.s\)\)',
      r'\bc&&\(c=(?P<sig>[a-zA-Z0-9$]{2,})\(decodeURIComponent\(c\)\)',
      r'(?:\b|[^a-zA-Z0-9$])(?P<sig>[a-zA-Z0-9$]{2,})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\);[a-zA-Z0-9$]{2}\.[a-zA-Z0-9$]{2}\(a,\d+\)',
      r'(?:\b|[^a-zA-Z0-9$])(?P<sig>[a-zA-Z0-9$]{2,})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',
```