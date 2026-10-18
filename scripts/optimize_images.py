import os
from PIL import Image

SOURCE_DIR = r"C:\Users\chaud\.gemini\antigravity\brain\771587c8-afb6-48a8-8480-a47b24ce653f\.user_uploaded"
DEST_DIR = r"c:\Users\chaud\Developer\SabhaGachi\frontend\public\images"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPING = [
    {
        "source": "media_1792133859370_bd1bca0f.jpg",
        "basename": "hero-mandap",
        "widths": [480, 768, 1024],
    },
    {
        "source": "media_1792133859370_163e798a.jpg",
        "basename": "hastamelap-union",
        "widths": [480, 768, 1024],
    },
    {
        "source": "media_1792133859370_23d57578.jpg",
        "basename": "saptapadi-kalash",
        "widths": [480, 682], # vertical image, max width is 682
    },
    {
        "source": "media_1792133859370_6b128c59.jpg",
        "basename": "sacred-havan-fire",
        "widths": [480, 768, 1024],
    },
]

for item in IMAGE_MAPPING:
    src_path = os.path.join(SOURCE_DIR, item["source"])
    if not os.path.exists(src_path):
        print(f"Error: {src_path} does not exist")
        continue

    img = Image.open(src_path)
    # Convert RGBA/P to RGB if necessary
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    orig_w, orig_h = img.size
    print(f"\nProcessing {item['basename']} (Original: {orig_w}x{orig_h})...")

    # Generate webp variants for each width
    for w in item["widths"]:
        if w > orig_w:
            w = orig_w
        ratio = w / orig_w
        h = round(orig_h * ratio)
        resized = img.resize((w, h), Image.Resampling.LANCZOS)
        
        webp_out = os.path.join(DEST_DIR, f"{item['basename']}-{w}w.webp")
        resized.save(webp_out, "WEBP", quality=84, method=6)
        size_kb = os.path.getsize(webp_out) / 1024
        print(f"  Created {os.path.basename(webp_out)}: {w}x{h} ({size_kb:.1f} KB)")

    # Also save standard default webp and optimized jpg fallback
    default_webp = os.path.join(DEST_DIR, f"{item['basename']}.webp")
    img.save(default_webp, "WEBP", quality=85, method=6)
    print(f"  Created default {os.path.basename(default_webp)} ({os.path.getsize(default_webp)/1024:.1f} KB)")

    default_jpg = os.path.join(DEST_DIR, f"{item['basename']}.jpg")
    img.save(default_jpg, "JPEG", quality=85, optimize=True)
    print(f"  Created fallback {os.path.basename(default_jpg)} ({os.path.getsize(default_jpg)/1024:.1f} KB)")

print("\nImage processing complete!")
