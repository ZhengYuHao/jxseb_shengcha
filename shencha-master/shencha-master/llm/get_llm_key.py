import ast
import json
import os
import random


def get_llm_key():
    """
    从环境变量里读取 API Key 列表，然后随机返回一个。支持三种格式：
      1. Python 列表风格（单引号）："['key1','key2','key3']"
      2. JSON 列表风格（双引号）：'["key1","key2","key3"]'
      3. 如果没有 OPENAI_KEY_LIST，则读取单个 OPENAI_KEY
    """
    try:
        key_list_str = os.getenv("OPENAI_KEY_LIST")
        # 如果没设置或者为空，直接退回到读取单个 OPENAI_KEY
        if not key_list_str:
            raise ValueError("环境变量 OPENAI_KEY_LIST 未设置或为空。")

        # 尝试用 json.loads 解析（针对 JSON 格式的列表）
        try:
            key_list = json.loads(key_list_str)
        except json.JSONDecodeError:
            # 如果 JSON 解析失败，尝试用 ast.literal_eval（支持 Python 列表风格）
            try:
                key_list = ast.literal_eval(key_list_str)
            except (ValueError, SyntaxError):
                # 都失败的话，就当做普通的逗号分隔字符串
                key_list = [k.strip() for k in key_list_str.split(",") if k.strip()]

        # 检验解析出来的 key_list 必须是可迭代并且非空
        if not isinstance(key_list, (list, tuple)) or not key_list:
            raise ValueError("解析后未能获取到有效的 API Key 列表。")

        # 随机选一个返回
        return random.choice(key_list)

    except Exception as e:
        # 打印错误并回退到单个 OPENAI_KEY
        print(f"获取 OpenAI API Key 时出错：{e}")
        return os.getenv("OPENAI_KEY")

# =========================
# 测试示例（可选）：
# =========================
# if __name__ == "__main__":
#     # 下面几行注释掉的 export 只是举例：你可以在终端里直接 export 再跑脚本
#     #
#     # 情况1：Python 风格的列表（单引号）
#     # export OPENAI_KEY_LIST="['sk-xxx1','sk-yyy2','sk-zzz3']"
#     #
#     # 情况2：JSON 风格的列表（双引号）
#     # export OPENAI_KEY_LIST='["sk-aaa1","sk-bbb2","sk-ccc3"]'
#     #
#     # 情况3：逗号分隔单行字符串
#     # export OPENAI_KEY_LIST="sk-1111,sk-2222,sk-3333"
#     #
#     # 如果以上都没设置，再定义一个单个 key 作为回退：
#     # export OPENAI_KEY="sk-default-0000"
#
#     key = get_llm_key()
#     if key:
#         print("随机选到的 API Key：", key)
#     else:
#         print("未能获取到有效的 API Key")
