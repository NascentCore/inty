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


def get_text_parts(texts: list[str]) -> list[types.Part]:
    """
    返回文本列表的 Part 对象列表，作为 GenAI client 输入的一部分。
    """
    return [get_text_part(text) for text in texts]


def get_jpeg_url_and_text_mixed_parts(contents: list[str]) -> list[types.Part]:
    parts = []
    for content in contents:
        # 如果是 jpeg url，则转换为 Part.from_uri
        if content.startswith("http") and (
            content.endswith(".jpeg") or content.endswith(".jpg")
        ):
            parts.append(
                types.Part.from_uri(file_uri=content, mime_type="image/jpeg")
            )
        else:
            parts.append(types.Part.from_text(text=content))
    return parts
