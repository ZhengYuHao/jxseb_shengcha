from llm.get_llm_key import get_llm_key

from llm.send_request import send_async_request


async def detect_doc_type(text: str) -> str:
    prompt = f"""
    分析以下文本，判断是专利、论文还是其他：
    {text[:1000]}

    返回：专利、论文、其他,你只能返回专利、论文、其他
    """
    api_key = get_llm_key()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    data = {
        'model': "qwen-plus",
        'messages': [
            {"role": "system", "content": "你是一个文档分类专家"},
            {"role": "user", "content": prompt}
        ],
    }
    print(f"to info {headers} \n {url} \n {data}\n")
    response = await send_async_request(url, headers, data)
    # print("response", response['choices'][0]['message']['content'])
    return response['choices'][0]['message']['content'].strip()
