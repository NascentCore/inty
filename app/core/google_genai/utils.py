from google.genai import types


def get_jpeg_part(jpeg_path: str) -> types.Part:
    """
    返回 JPEG 图片的 Part 对象，作为 GenAI client 输入的一部分。
    """
    with open(jpeg_path, "rb") as f:
        raw_bytes = f.read()
    return types.Part.from_bytes(
        data=raw_bytes,
        mime_type="image/jpeg",
    )


def get_text_part(text: str) -> types.Part:
    """
    返回文本的 Part 对象，作为 GenAI client 输入的一部分。
    """
    return types.Part.from_text(text=text)
