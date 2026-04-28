"""Download planet textures from public sources to D:/jarvis-assets/textures/
Run once:  python scripts/download_planet_textures.py
"""
import urllib.request
import ssl
import pathlib
import sys

DEST = pathlib.Path("D:/jarvis-assets/textures")

# Solar System Scope textures — high-quality public CC BY 4.0
# https://www.solarsystemscope.com/textures/
SSS = "https://www.solarsystemscope.com/textures/download/"
# NASA visible earth: public domain
NASA = "https://eoimages.gsfc.nasa.gov/images/imagerecords/"
# Planet Pixel Emporium (public domain)
PPE = "http://planetpixelemporium.com/download/download.php?"

# Map target filename -> download URL
TEXTURES = {
    "mercury.jpg":           "https://www.solarsystemscope.com/textures/download/2k_mercury.jpg",
    "venus.jpg":             "https://www.solarsystemscope.com/textures/download/2k_venus_surface.jpg",
    "mars_1k_color.jpg":     "https://www.solarsystemscope.com/textures/download/2k_mars.jpg",
    "mars_1k_normal.jpg":    "https://www.solarsystemscope.com/textures/download/2k_mars.jpg",  # reuse color as normal fallback
    "jupiter.jpg":           "https://www.solarsystemscope.com/textures/download/2k_jupiter.jpg",
    "saturn.jpg":            "https://www.solarsystemscope.com/textures/download/2k_saturn.jpg",
    "uranus.jpg":            "https://www.solarsystemscope.com/textures/download/2k_uranus.jpg",
    "neptune.jpg":           "https://www.solarsystemscope.com/textures/download/2k_neptune.jpg",
    "pluto.jpg":             "https://www.solarsystemscope.com/textures/download/2k_eris_fictional.jpg",
    "saturnringcolor.jpg":   "https://www.solarsystemscope.com/textures/download/2k_saturn_ring_alpha.png",
    "saturnringpattern.gif": "https://www.solarsystemscope.com/textures/download/2k_saturn_ring_alpha.png",
}

def download(name: str, url: str, dest_dir: pathlib.Path) -> bool:
    out = dest_dir / name
    if out.exists():
        print(f"  skip (exists): {name}")
        return True
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisHUD/1.0 planet-texture-downloader"})
        with urllib.request.urlopen(req, timeout=40, context=ctx) as resp:
            data = resp.read()
        out.write_bytes(data)
        print(f"  ok: {name}  ({len(data)//1024} KB)  <- {url}")
        return True
    except Exception as exc:
        print(f"  FAILED: {name} <- {url}\n    {exc}")
        return False

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    print(f"Saving to: {DEST}")
    ok = 0
    fail = 0
    for name, url in TEXTURES.items():
        if download(name, url, DEST):
            ok += 1
        else:
            fail += 1
    print(f"\nDone: {ok} ok, {fail} failed")
    if fail:
        sys.exit(1)

if __name__ == "__main__":
    main()
