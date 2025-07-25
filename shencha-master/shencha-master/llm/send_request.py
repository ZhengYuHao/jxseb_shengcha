import aiohttp

# 异步发送 POST 请求
async def send_async_request(url, headers, data):
    """
    Send an asynchronous POST request to the specified URL with given headers and JSON data.
    
    If the response status is 200, returns the parsed JSON response. Otherwise, prints an error message and returns None.
    
    Parameters:
        url (str): The endpoint to which the POST request is sent.
        headers (dict): HTTP headers to include in the request.
        data (dict): JSON-serializable data to send in the request body.
    
    Returns:
        dict or None: Parsed JSON response if successful; otherwise, None.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                print(f"请求失败，状态码: {response.status}")
                print(await response.text())
                return None