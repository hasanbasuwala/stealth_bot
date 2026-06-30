"""
Stealth Bot v13 Downloader Layer

Central export registry for all downloader engines.

Purpose:
- Keep worker imports clean
- Standardize downloader interfaces
- Allow future engine expansion without changing worker code

Pipeline Engines:
1. aria2      -> direct file downloads (.mp4, static links)
2. mediago    -> m3u8/HLS segmented downloads
3. ytdlp      -> adaptive yt-dlp engine with fingerprint rotation
4. playwright -> HTTP/browser extraction resolver
5. fpoxxx     -> custom domain-specific extractor
"""

# Direct file downloader (fast static links)
from .aria2 import download_aria2c

# HLS / M3U8 segmented stream downloader
from .mediago import download_mediago

# URL resolver + extraction engine
from .playwright import run_custom_workflow

# Adaptive yt-dlp fallback downloader
from .ytdlp import download_with_ytdlp

# Domain specific extractor
from .fpoxxx import extract_fpoxxx_video


# Public export map
__all__ = [

    # Download engines
    "download_aria2c",
    "download_mediago",
    "download_with_ytdlp",

    # Resolver engines
    "run_custom_workflow",
    "extract_fpoxxx_video",
]