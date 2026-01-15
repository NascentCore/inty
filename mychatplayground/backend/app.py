import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)

# 设置 Google Cloud 凭证
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "inty-backend-key.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

# 获取 project_id
PROJECT_ID = "alien-paratext-461204-i9"


def get_gemini_client():
    """获取 Gemini 客户端"""
    return genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="us-central1",
    )


@app.route("/api/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok"})


@app.route("/api/generate-image", methods=["POST"])
def generate_image():
    """使用 Gemini 生成图片"""
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        reference_images = data.get("reference_images", [])  # base64 图片列表

        if not prompt:
            return jsonify({"error": "prompt is required"}), 400

        client = get_gemini_client()
        model = "gemini-2.0-flash-exp"  # 支持图像生成的模型

        # 构建 parts 列表
        parts = []
        
        # 用于记录发送给模型的完整信息（可视化用）
        debug_parts = []
        
        # 参考图角色描述
        ref_descriptions = [
            "【参考图1 - AI角色外观】这是 AI 角色的外观参考图，请在生成的图片中保持这个角色的外貌特征（发型、五官、身材等）。",
            "【参考图2 - 用户外观】这是用户的外观参考图，如果 prompt 中提到用户出现在画面中，请参考这张图的外貌特征。"
        ]
        
        # 添加参考图（如果有）
        for i, ref_img in enumerate(reference_images):
            if ref_img:
                # 处理 base64 图片 (可能有 data:image/xxx;base64, 前缀)
                if "," in ref_img:
                    # 提取 MIME 类型和 base64 数据
                    header, base64_data = ref_img.split(",", 1)
                    mime_type = header.split(":")[1].split(";")[0] if ":" in header else "image/png"
                else:
                    base64_data = ref_img
                    mime_type = "image/png"
                
                image_bytes = base64.b64decode(base64_data)
                # 先添加描述文本，再添加图片
                if i < len(ref_descriptions):
                    parts.append(types.Part.from_text(text=ref_descriptions[i]))
                    debug_parts.append({"type": "text", "content": ref_descriptions[i]})
                parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
                debug_parts.append({"type": "image", "content": f"[图片数据 - {mime_type}]"})

        # 添加文本提示 - 明确要求生成图片
        image_generation_prompt = f"""
【图片生成任务】
请根据以下描述生成一张图片。

重要提示：
- 如果提供了参考图1（AI角色），生成的图片中该角色必须保持参考图1中的外貌特征
- 如果提供了参考图2（用户）并且描述中提到了用户，则用户角色必须保持参考图2中的外貌特征
- 两个角色应该有明显不同的外貌，不要混淆

【用户描述】
{prompt}

请立即生成图片，不要只输出文字描述。"""
        parts.append(types.Part.from_text(text=image_generation_prompt))
        debug_parts.append({"type": "text", "content": image_generation_prompt})

        contents = [
            types.Content(
                role="user",
                parts=parts,
            )
        ]

        # gemini-2.5-flash-image 只支持 1024x1024 固定尺寸，不支持自定义比例
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            max_output_tokens=8192,
            response_modalities=["TEXT", "IMAGE"],
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            ],
        )

        # 调用 Gemini API（非流式）
        print(f"Calling Gemini API with model: {model}")
        print(f"Prompt: {prompt[:200]}...")
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        print(f"Response received: {response}")

        # 处理响应，提取图片
        result_text = ""
        result_image = None

        if response.candidates:
            for candidate in response.candidates:
                print(f"Candidate: {candidate}")
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        print(f"Part type: {type(part)}, attrs: {dir(part)}")
                        if hasattr(part, "text") and part.text:
                            result_text += part.text
                            print(f"Found text: {part.text[:100]}...")
                        elif hasattr(part, "inline_data") and part.inline_data:
                            # 图片数据
                            print(f"Found inline_data!")
                            image_data = part.inline_data.data
                            mime_type = part.inline_data.mime_type or "image/png"
                            # 转换为 base64 data URL
                            if isinstance(image_data, bytes):
                                b64_data = base64.b64encode(image_data).decode("utf-8")
                            else:
                                b64_data = image_data
                            result_image = f"data:{mime_type};base64,{b64_data}"
                        # 检查是否有其他图片属性
                        if hasattr(part, "image"):
                            print(f"Found image attr: {part.image}")
        else:
            print(f"No candidates in response")

        if not result_image:
            # 如果只有文本没有图片，可能是内容安全策略拒绝了
            error_msg = "No image generated"
            if result_text:
                error_msg = f"模型返回了文本而非图片（可能被内容安全策略拦截）:\n\n{result_text[:1000]}"
            return jsonify({
                "error": error_msg,
                "text": result_text,
                "raw_response": str(response)[:2000],
            }), 500

        return jsonify({
            "success": True,
            "image": result_image,
            "text": result_text,
            "debug_request": debug_parts,  # 发送给模型的完整信息
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error generating image: {error_trace}")
        return jsonify({
            "error": str(e),
            "traceback": error_trace
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

