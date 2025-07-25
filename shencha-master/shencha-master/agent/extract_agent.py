import json
from typing import Dict, Any

from llm.get_llm_key import get_llm_key
from llm.send_request import send_async_request


# async def extract_info(text: str, doc_type: str) -> Dict[str, Any]:
#     if doc_type == '专利':
#         prompt = f"""
#         从以下专利文本中提取信息：
#         {text[:5000]}

#         请提取：
#         1. 专利号
#         2. 申请日期（YYYY-MM-DD）
#         3. 授权日期（如无则写N/A）
#         4. 发明人（逗号分隔）
#         5. 受让人（公司/机构）

#         返回 JSON 格式。
#         """
#     if doc_type == '论文':
#         prompt = f"""
#             请从以下论文文本中精确提取信息：
#             {text[:5000]}

#             要求返回严格JSON格式，包含以下字段：
#             1. 标题（必须提取）
#             2. 作者（分号分隔，如"张三; 李四; 王五"）
#             3. 期刊/会议名称（完整名称）
#             4. 发表年份（YYYY，必须从文本中提取）
#             5. DOI（完整格式，如"10.1002/ajh.27272"，若无则写N/A）
#             6. received_date（收稿日期，YYYY-MM-DD格式）
#             7. accepted_date（接受日期，YYYY-MM-DD格式）
#             8. published_date（出版日期，YYYY-MM-DD格式）

#             特别注意：
#             - 日期格式示例：Received:4December2023 → received_date: "2023-12-04"
#             - 必须包含所有8个字段，没有的字段写N/A
#             - 年份优先从出版日期提取，其次接受日期，最后收稿日期

#             示例格式：
#             {{
#               "标题": "Report of IRF2BP1 as a novel partner of RARA in variant acute promyelocytic leukemia",
#               "作者": "Jiang Bin; Zhang San; Li Si",
#               "期刊": "American Journal of Hematology",
#               "year": 2024,
#               "DOI": "10.1002/ajh.27272",
#               "received_date": "2023-12-04",
#               "accepted_date": "2024-02-18",
#               "published_date": "2024-03-01"
#             }}
#             """

#     role = "你是一个信息提取专家"
#     api_key = get_llm_key()
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {api_key}"
#     }
#     url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
#     data = {
#         'model': "qwen-plus",
#         'messages': [
#             {"role": "system", "content": "你是一个文档分类专家"},
#             {"role": "user", "content": prompt}
#         ],
#     }
#     try:
#         response = await send_async_request(url, headers, data)
#         if not response or 'choices' not in response:
#             raise ValueError("Invalid API response format")
            
#         content = response['choices'][0]['message']['content']
#         if content.startswith("```json"):
#             content = content.strip("```json").strip("```")
#         elif content.startswith("```"):
#             content = content.strip("```")
            
#         result = json.loads(content.strip())
#     except json.JSONDecodeError as e:
#         raise ValueError(f"Failed to parse API response as JSON: {e}")
#     except Exception as e:
#         raise RuntimeError(f"Error during information extraction: {e}")
#     # print("提取结果:", result)

#     # 确保所有字段存在
#     if doc_type == '论文':
#         required_fields = [
#             '标题', '作者', '期刊', 'year',
#             'DOI', 'received_date', 'accepted_date', 'published_date'
#         ]
#         for field in required_fields:
#             if field not in result:
#                 result[field] = "N/A"

#     return result

import json
from typing import Dict, Any
from aiohttp import ClientError  # 假设使用aiohttp实现send_async_request

async def extract_info(text: str, doc_type: str) -> Dict[str, Any]:
    """
    Asynchronously extracts structured information from a patent or academic paper text using an external LLM API.
    
    Parameters:
        text (str): The input document text to extract information from.
        doc_type (str): The type of document ("专利" for patent or "论文" for paper).
    
    Returns:
        Dict[str, Any]: A dictionary containing the extracted and validated information fields.
    
    Raises:
        ValueError: If the API response format is invalid or required fields are missing.
        ConnectionError: If there is a network error during the API call.
        RuntimeError: For other unexpected errors during extraction.
    """
    try:
        # 生成Prompt
        prompt = _generate_prompt(text, doc_type)
        
        # 配置参数（建议通过环境变量或配置文件注入）
        role = "你是一个信息提取专家"
        api_key = get_llm_key()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        data = {
            'model': "qwen-plus",
            'messages': [
                {"role": "system", "content": role},
                {"role": "user", "content": prompt}
            ],
        }

        try:
            response = await send_async_request(url, headers, data)
            if not response or 'choices' not in response:
                raise ValueError("Invalid API response format")
                
            content = response['choices'][0]['message']['content']
            if content.startswith("```json"):
                content = content.strip("```json").strip("```")
            elif content.startswith("```"):
                content = content.strip("```")
                
            result = json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse API response as JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"Error during information extraction: {e}")
        
        # 验证必填字段
        if doc_type == '论文':
            _validate_paper_fields(result)
        elif doc_type == '专利':
            _validate_patent_fields(result)
            
        return result
    except KeyError as e:
        # 处理响应结构异常
        raise ValueError("API响应结构异常") from e
    except json.JSONDecodeError as e:
        # 处理解析失败
        raise ValueError("JSON解析失败") from e
    except ClientError as e:
        # 处理网络异常
        raise ConnectionError(f"API调用失败: {str(e)}") from e
    except Exception as e:
        # 捕获其他未知异常
        raise RuntimeError(f"信息提取失败: {str(e)}") from e

def _generate_prompt(text: str, doc_type: str) -> str:
    """
    Generate a prompt string for the language model to extract structured information from a patent or academic paper text.
    
    Parameters:
        text (str): The input document text to extract information from.
        doc_type (str): The type of document ("专利" for patent or "论文" for paper).
    
    Returns:
        str: A prompt formatted for the specified document type, instructing the language model to extract required fields in JSON format.
    
    Raises:
        ValueError: If an unsupported document type is provided.
    """
    text_sample = text[:5000]
    if doc_type == '专利':
        return f"""
        从以下专利文本中提取信息：
        {text_sample}

        请提取：
        1. 专利号
        2. 申请日期（YYYY-MM-DD）
        3. 授权日期（如无则写N/A）
        4. 发明人（逗号分隔）
        5. 受让人（公司/机构）

        返回 JSON 格式。
        """
    elif doc_type == '论文':
        return f"""
        请从以下论文文本中精确提取信息：
        {text_sample}

        要求返回严格JSON格式，包含以下字段：
        1. 标题（必须提取）
        2. 作者（分号分隔，如"张三; 李四; 王五"）
        3. 期刊/会议名称（完整名称）
        4. 发表年份（YYYY，必须从文本中提取）
        5. DOI（完整格式，如"10.1002/ajh.27272"，若无则写N/A）
        6. received_date（收稿日期，YYYY-MM-DD格式）
        7. accepted_date（接受日期，YYYY-MM-DD格式）
        8. published_date（出版日期，YYYY-MM-DD格式）

        特别注意：
        - 日期格式示例：Received:4December2023 → received_date: "2023-12-04"
        - 必须包含所有8个字段，没有的字段写N/A
        - 年份优先从出版日期提取，其次接受日期，最后收稿日期

        示例格式：
        {{
          "标题": "Report of IRF2BP1 as a novel partner of RARA in variant acute promyelocytic leukemia",
          "作者": "Jiang Bin; Zhang San; Li Si",
          "期刊": "American Journal of Hematology",
          "year": 2024,
          "DOI": "10.1002/ajh.27272",
          "received_date": "2023-12-04",
          "accepted_date": "2024-02-18",
          "published_date": "2024-03-01"
        }}
        """
    else:
        raise ValueError(f"不支持的文档类型: {doc_type}")

def _validate_paper_fields(result: Dict[str, Any]) -> None:
    """
    Ensure all required fields for an academic paper are present in the result dictionary, adding missing fields with "N/A".
    """
    required_fields = [
        '标题', '作者', '期刊', 'year',
        'DOI', 'received_date', 'accepted_date', 'published_date'
    ]
    for field in required_fields:
        if field not in result:
            result[field] = "N/A"

def _validate_patent_fields(result: Dict[str, Any]) -> None:
    """
    Ensure all required patent fields are present in the result dictionary, adding missing fields with "N/A" as needed.
    
    Modifies the input dictionary in place to guarantee the presence of '专利号', '申请日期', '发明人', '受让人', and '授权日期' keys.
    """
    required_fields = ['专利号', '申请日期', '发明人', '受让人']
    for field in required_fields:
        if field not in result:
            result[field] = "N/A"
    if '授权日期' not in result:
        result['授权日期'] = "N/A"