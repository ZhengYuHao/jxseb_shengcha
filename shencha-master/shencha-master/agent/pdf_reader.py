import base64
import os

import aiofiles
import fitz
import pdfplumber

from llm.get_llm_key import get_llm_key
from llm.send_request import send_async_request


async def pdf_text_reader(temp_file_path: str) -> str:
    """
    Asynchronously extracts and returns all text content from a PDF file at the specified path.
    
    If the file is not found, the exception is raised. Returns an empty string if text extraction fails for other reasons.
    """
    print(f"处理中: {temp_file_path}")

    # 提取 PDF 文本内容
    try:
        with pdfplumber.open(temp_file_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:  # Only append if text was extracted
                    all_text += text + "\n"
        return all_text
    except FileNotFoundError as e:
        print(f"PDF文件未找到: {e}")
        raise
    except Exception as e:
        print(f"PDF解析失败: {e}")
        return ""

async def image_to_base64(image_path: str) -> str:
    """
    Asynchronously converts an image file to a Base64-encoded string.
    
    Parameters:
        image_path (str): Path to the image file to be encoded.
    
    Returns:
        str: The Base64-encoded representation of the image.
    """
    async with aiofiles.open(image_path, "rb") as f:
        image_data = await f.read()
        base64_image = base64.b64encode(image_data).decode("utf-8")
        return base64_image


async def extract_text_from_images(image_paths: list) -> str:
    """
    Extracts text from a list of image files using a GPT-based OCR API.
    
    Each image is converted to Base64 and sent to a GPT-4.1 OCR endpoint, which returns the recognized text. All extracted text is concatenated and returned as a single string.
    
    Parameters:
        image_paths (list): List of file paths to images for OCR processing.
    
    Returns:
        str: Concatenated text extracted from all provided images.
    """
    all_text = ""
    api_key = get_llm_key()
    url = "https://api.rcouyi.com/v1/chat/completions"
    for image_path in image_paths:
        base64_image = await image_to_base64(image_path)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
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
    Asynchronously extracts text from a PDF file by converting each page to an image and performing OCR using a GPT-based model.
    
    Parameters:
        temp_file_path (str): Path to the PDF file to be processed.
    
    Returns:
        str: The extracted text content, or a failure message if extraction is unsuccessful.
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
    finally:
        pdf_document.close()
    

    # 使用 GPT 模型对图片进行 OCR 识别
    try:
        all_text = await extract_text_from_images(image_paths)
        return all_text
    except FileNotFoundError as e:
        print(f"图片文件未找到: {e}")
        return "OCR 识别失败，无法提取文本内容。"
    except PermissionError as e:
        print(f"权限不足，无法访问图片文件: {e}")
        return "OCR 识别失败，无法提取文本内容。"