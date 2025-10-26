import json
import base64
from pathlib import Path
import re
# 读取响应。__保留__1__
with open("response.json", "r") as f:
    data = json.load(f)
#从图像字段中提取图像
images = data["output"]["images"]
#创建作品目录
output_dir = Path("extracted_images")
output_dir.mkdir(exist_ok=True)
# 将每个图像保存为PNG
for idx, b64img in enumerate(images):
    b64img = re.sub("^data:image/.+;base64,", "", b64img)
    img_bytes = base64.b64decode(b64img)
    out_path = output_dir / f"image_{idx+1:03d}.png"
    with open(out_path, "wb") as f:
        f.write(img_bytes)
    print(f"Saved: {out_path}")

print(f"Saved {len(images)} images to {output_dir}")
