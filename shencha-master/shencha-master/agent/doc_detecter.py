from llm.get_llm_key import get_llm_key

from llm.send_request import send_async_request
import os

async def detect_doc_type(text: str) -> str:
    """
    Classifies the type of a given text as "专利" (patent), "论文" (paper), or "其他" (other) using a language model API.
    
    Parameters:
        text (str): The input text to classify. Must not be empty or whitespace only.
    
    Returns:
        str: The detected document type—one of "专利", "论文", or "其他". Returns "其他" if classification fails or the result is unexpected.
    
    Raises:
        ValueError: If the input text is empty or contains only whitespace.
    """
    if not text or not text.strip():
        raise ValueError("Input text cannot be empty")
    
    prompt = f"""
    分析以下文本，判断是专利、论文还是其他类型文档：
    {text[:1000].strip()}

    请严格按照以下格式返回分类结果，只能返回以下三个选项之一：
    - 专利
    - 论文  
    - 其他
    """    
    api_key = get_llm_key()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    url = os.getenv(
        "LLM_API_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )   
    data = {
        'model': "qwen-plus",
        'messages': [
            {"role": "system", "content": "你是一个文档分类专家"},
            {"role": "user", "content": prompt}
        ],
    }
    print(f"to info {headers} \n {url} \n {data}\n")
    try:
        response = await send_async_request(url, headers, data)
        if not response or 'choices' not in response:
            raise ValueError("Invalid API response format")
        
        content = response['choices'][0]['message']['content'].strip()
        if content not in ['专利', '论文', '其他']:
            # Fallback to 其他 for unexpected responses
            return '其他'
        return content
    except Exception as e:
        # Log the error and return a default classification
        print(f"Error in document type detection: {e}")
        return '其他'