import json
import base64
from pathlib import Path
import re

# Read response.json
with open("response.json", "r") as f:
    data = json.load(f)

# Extract images from the images field
images = data["output"]["images"]

# Create output directory
output_dir = Path("extracted_images")
output_dir.mkdir(exist_ok=True)

# Save each image as PNG
for idx, b64img in enumerate(images):
    b64img = re.sub("^data:image/.+;base64,", "", b64img)
    img_bytes = base64.b64decode(b64img)
    out_path = output_dir / f"image_{idx+1:03d}.png"
    with open(out_path, "wb") as f:
        f.write(img_bytes)
    print(f"Saved: {out_path}")

print(f"Saved {len(images)} images to {output_dir}")
