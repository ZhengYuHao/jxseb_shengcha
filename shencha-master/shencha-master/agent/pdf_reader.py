import base64
import os

import aiofiles
import fitz
import pdfplumber

from llm.get_llm_key import get_llm_key
from llm.send_request import send_async_request


async def pdf_text_reader(temp_file_path: str) -> str:
    """
    异步处理 PDF 文件，提取文本内容。

    Args:
        temp_file_path (str): 临时文件路径。

    Returns:
        str: 提取的文本内容。
    """
    print(f"处理中: {temp_file_path}")

    # 提取 PDF 文本内容
    try:
        with pdfplumber.open(temp_file_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                text0 = page.extract_text()
                all_text += text0 + "\n"
        return all_text
    except Exception as e:
        print(f"PDF解析失败: {e}")
        return ""


async def image_to_base64(image_path: str) -> str:
    """
    将图片转换为 Base64 编码。

    Args:
        image_path (str): 图片路径。

    Returns:
        str: Base64 编码的图片。
    """
    async with aiofiles.open(image_path, "rb") as f:
        image_data = await f.read()
        base64_image = base64.b64encode(image_data).decode("utf-8")
        return base64_image


async def extract_text_from_images(image_paths: list) -> str:
    """
    使用 GPT 模型对图片进行 OCR 识别并提取文本。

    Args:
        image_paths (list): 图片路径列表。

    Returns:
        str: 提取的文本内容。
    """
    all_text = ""
    for image_path in image_paths:
        base64_image = await image_to_base64(image_path)
        api_key = get_llm_key()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        url = "https://api.rcouyi.com/v1/chat/completions"
        data = {
            'model': "gpt-4.1",
            'messages': [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请给出图片中的文字(数字、中文、英文等）,不要给出任何解释",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
        }
        try:
            response = await send_async_request(url, headers, data)

            page_text = response['choices'][0]['message']['content']
            # print(f"提取文本内容: {page_text}")
            all_text += page_text + "\n"
        except Exception as e:
            print(f"图片 OCR 识别失败: {e}")
    return all_text


async def pdf_pic_reader(temp_file_path: str) -> str:
    """
    异步处理 PDF 文件，转图片后使用 GPT 模型进行 OCR 识别并提取文本内容。

    Args:
        temp_file_path (str): PDF 文件路径。

    Returns:
        str: 提取的文本内容。
    """
    print(f"处理中: {temp_file_path}")

    # 获取 PDF 文件所在目录
    pdf_dir = os.path.dirname(temp_file_path)
    pdf_name = os.path.splitext(os.path.basename(temp_file_path))[0]  # 获取 PDF 文件名（无扩展名）

    # 转换 PDF 为图片
    image_paths = []
    try:
        pdf_document = fitz.open(temp_file_path)
        for page_number in range(len(pdf_document)):
            page = pdf_document.load_page(page_number)
            zoom = 0.5  # 缩放比例，1表示原始分辨率，0.5表示降低分辨率，2表示提高分辨率
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)  # 应用缩放矩阵

            # 图片保存路径：与 PDF 文件同目录，文件名为 PDF 文件名加页码
            image_path = os.path.join(pdf_dir, f"{pdf_name}_page_{page_number + 1}.png")
            # print(f"保存图片路径: {image_path}")
            pix.save(image_path)
            image_paths.append(image_path)

        if not image_paths:
            print("PDF 转图片失败，无法提取文本内容。")
            return "PDF 转图片失败，无法提取文本内容。"
    except Exception as e:
        print(f"PDF 转图片失败: {e}")
        return "PDF 转图片失败，无法提取文本内容。"

    # 使用 GPT 模型对图片进行 OCR 识别
    try:
        all_text = await extract_text_from_images(image_paths)
        return all_text
    except Exception as e:
        print(f"OCR 识别失败: {e}")
        return "OCR 识别失败，无法提取文本内容。"
