import os
import asyncio
from io import BytesIO
from typing import List, Dict, Any
from fastapi import UploadFile, File
from pydantic import BaseModel, Field
import json

from app import process_files, check_documents_validity, parse_date

# 定义目录路径
DOCS_DIR = "test/文档示例"
OUTPUT_DIR = "test/output"
UPLOAD_RESULTS_FILE = os.path.join(OUTPUT_DIR, "上传结果.json")  # Changed to JSON for easier parsing
VALIDITY_RESULTS_FILE = os.path.join(OUTPUT_DIR, "有效时间检查结果.txt")


def create_output_dir():
    """确保输出目录存在"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

import os
import logging
import asyncio
from typing import List
from io import BytesIO
from fastapi import UploadFile
import aiofiles

# 假设 DOCS_DIR 已在外部定义
# DOCS_DIR = "your_directory_path"

async def generate_test_files() -> List[UploadFile]:
    """生成测试用的UploadFile列表"""
    try:
        # 检查 DOCS_DIR 是否存在且为目录
        if not os.path.isdir(DOCS_DIR):
            logging.warning(f"目录 {DOCS_DIR} 不存在或不是目录。")
            return []

        # 获取所有文件路径
        files = [
            full_path
            for f in os.listdir(DOCS_DIR)
            if (full_path := os.path.join(DOCS_DIR, f)) and os.path.isfile(full_path)
        ]

        if not files:
            logging.warning(f"目录 {DOCS_DIR} 中没有文件。")
            return []

        upload_files = []
        for file_path in files:
            try:
                async with aiofiles.open(file_path, "rb") as f:
                    file_content = await f.read()
                # 过滤空文件
                if not file_content:
                    logging.warning(f"文件 {file_path} 为空，已跳过。")
                    continue
                file_like = BytesIO(file_content)
                upload_files.append(
                    UploadFile(
                        filename=os.path.basename(file_path),
                        file=file_like
                    )
                )
            except (OSError, IOError, MemoryError) as e:
                logging.error(f"读取文件 {file_path} 时发生错误: {e}")
                continue

        return upload_files

    except Exception as e:
        logging.error(f"生成测试文件时发生错误: {e}")
        return []


class ValidityCheckRequest(BaseModel):
    start_date: str = Field(..., description="起始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    docs: Dict[str, Dict[str, Dict[str, Any]]] = Field(
        ...,
        description="已提取的文档结构化信息，包括专利和论文"
    )


async def test_process_files(files: List[UploadFile] = File(...)) -> Dict[str, Dict[str, Any]]:
    """测试process_files函数并返回结构化数据"""
    create_output_dir()

    if not files:
        print("没有提供测试文件")
        return {}

    # 调用原函数
    response = await process_files(files)

    # 验证响应
    assert response.results is not None, "Results should not be None"
    assert response.data is not None, "Data should not be None"
    assert len(response.results) == len(files), f"Expected {len(files)} results, got {len(response.results)}"

    # 保存结果为JSON格式以便后续使用
    result_data = {
        "results": response.results,
        "data": response.data
    }

    with open(UPLOAD_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"上传结果已保存到 {UPLOAD_RESULTS_FILE}")
    print(f"✅ 成功处理 {len(response.results)} 个文件")
    return response.data  # 返回结构化数据供后续测试使用
async def load_structured_data() -> Dict[str, Dict[str, Any]]:
    """从保存的文件中加载结构化数据"""
    if not os.path.exists(UPLOAD_RESULTS_FILE):
        print(f"文件 {UPLOAD_RESULTS_FILE} 不存在")
        return {}

    with open(UPLOAD_RESULTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("data", {})


async def test_check_validity(request: ValidityCheckRequest):
    """测试check_documents_validity函数"""
    create_output_dir()

    # 调用原函数
    response = await check_documents_validity(request)

    # 保存结果
    with open(VALIDITY_RESULTS_FILE, "w", encoding="utf-8") as f:
        f.write(f"有效时间范围: {response.time_range}\n\n")
        f.write("有效专利:\n")
        for patent in response.valid_patents:
            f.write(f"{patent}\n")
        f.write("\n有效论文:\n")
        for paper in response.valid_papers:
            f.write(f"{paper}\n")
        f.write("\n统计信息:\n")
        f.write(f"{response.comparison_stats}\n")

    print(f"有效性检查结果已保存到 {VALIDITY_RESULTS_FILE}")


import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def main():
    """主测试函数"""
    # 1. 测试文件上传处理并获取结构化数据
    test_files = await generate_test_files()
    if not test_files:
        return

    structured_data = await test_process_files(test_files)
    if not structured_data:
        logging.error("未能获取结构化数据")
        return

    # 2. 准备有效性检查请求
    logging.info("\n准备有效性检查...")

    # 获取并验证日期输入
    try:
        start_date = input("请输入起始时间 (格式: YYYY-MM-DD): ").strip()
        end_date = input("请输入结束时间 (格式: YYYY-MM-DD): ").strip()
        start_dt = parse_date(start_date)
        end_dt = parse_date(end_date)

        if start_dt > end_dt:
            raise ValueError("起始日期不能晚于结束日期")
    except ValueError as e:
        logging.error(f"日期输入错误: {e}")
        return
    except Exception as e:
        logging.error(f"未知错误: {e}")
        return

    # 3. 创建请求对象
    try:
        request = ValidityCheckRequest(
            start_date=start_date,
            end_date=end_date,
            docs={
                "patentData": structured_data,
                "paperData": structured_data
            }
        )
    except Exception as e:
        logging.error(f"请求对象创建失败: {e}")
        return

    # 4. 测试有效性检查
    try:
        await test_check_validity(request)
    except Exception as e:
        logging.error(f"有效性检查失败: {e}")
        return

def parse_date(date_str: str) -> datetime:
    """解析日期字符串为 datetime 对象"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"日期格式错误: {date_str}") from e


if __name__ == "__main__":

    asyncio.run(main())
