import json
import sys
import os
from typing import Any, Callable
from functools import wraps

# 프로젝트 루트를 sys.path에 추가 (직접 실행 시)
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# 직접 실행 vs 모듈 임포트에 따라 다른 임포트 경로 사용
try:
    # 모듈로 임포트될 때 (from common.report_exporters import ...)
    from .report_prompts import (
        SYSTEM_PROMPT, PROMPT_0, PROMPT_1, PROMPT_2, PROMPT_3, PROMPT_4,
        PROMPT_5, PROMPT_6, PROMPT_7, PROMPT_8, PROMPT_9, PROMPT_10, PROMPT_11
    )
    from .utils import llm_medium, llm_large
except ImportError:
    # 직접 실행될 때 (python report_exporters.py)
    from common.report_prompts import (
        SYSTEM_PROMPT, PROMPT_0, PROMPT_1, PROMPT_2, PROMPT_3, PROMPT_4,
        PROMPT_5, PROMPT_6, PROMPT_7, PROMPT_8, PROMPT_9, PROMPT_10, PROMPT_11
    )
    from common.utils import llm_medium, llm_large


from langchain_core.prompts import ChatPromptTemplate


def _serialize_data(data: Any) -> str:
    """LLM 친화적 형식으로 데이터 직렬화"""
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(data)

def _validate_field(data: dict[str, Any], field: str) -> Any:
    """필수 필드 검증"""
    value = data.get(field)
    if value is None:
        raise ValueError(f"필수 데이터 누락: '{field}'")
    return value

def create_llm_exporter(
    prompt_template: str,
    required_fields: list[str],
    llm=llm_medium,
) -> Any:
    def exporter(data: dict[str, Any]) -> dict[str, Any]:
        field_values = {
            field: _serialize_data(_validate_field(data, field)) for field in required_fields
        }

        prompt = ChatPromptTemplate.from_messages([
            ('system', SYSTEM_PROMPT),
            ('human', prompt_template)
        ])

        formatted_prompt = prompt.format_messages(**field_values)

        response = llm.invoke(formatted_prompt)

        if not response.content or not response.content.strip(): # type: ignore
            print("LLM returned empty response for prompt")
            raise BrokenPipeError("LLM 응답이 비어있습니다")

        return {"content": response.content}
    return exporter


type Data = dict[str, Any]
type ReturnData = dict[str, Any]
type ExportFn = Callable[[Data], ReturnData]

exporters: dict[int, ExportFn] = {}

def register_exporters(index: int) -> Callable[[ExportFn], ExportFn]:
    def decorator(fn: ExportFn) -> ExportFn:
        @wraps(fn)
        def wrapper(data: Data) -> ReturnData:
            return fn(data)
        exporters[index] = wrapper
        return wrapper
    return decorator


@register_exporters(0)
def export_0(data: Data) -> ReturnData:
    """분석 목적 생성"""
    return {"content": PROMPT_0}


@register_exporters(1)
def export_1(data: Data) -> ReturnData:
    """데이터 수집 생성"""
    result = create_llm_exporter(PROMPT_1, ["job_info"])(data)
    return result


@register_exporters(2)
def export_2(data: Data) -> ReturnData:
    """분석 일정 생성"""
    result = create_llm_exporter(PROMPT_2, ["job_info"])(data)
    return result


@register_exporters(3)
def export_3(data: Data) -> ReturnData:
    """분석 방법 및 절차 -> 고정된 문장 그대로 리턴."""
    return {"content": PROMPT_3}


@register_exporters(4)
def export_4(data: Data) -> ReturnData:
    """분석 방법 및 절차 -> 고정된 문장 그대로 리턴."""
    return {"content": PROMPT_4}


@register_exporters(5)
def export_5(data: Data) -> ReturnData:
    """분석 요약"""
    result = create_llm_exporter(PROMPT_5, ["context"], llm=llm_large)(data)
    return result


@register_exporters(6)
def export_6(data: Data) -> ReturnData:
    """취득 행위"""
    result = create_llm_exporter(PROMPT_6, ["context"])(data)
    return result


@register_exporters(7)
def export_7(data: Data) -> ReturnData:
    """유출 행위"""
    result = create_llm_exporter(PROMPT_7, ["context"], llm=llm_large)(data)
    return result


@register_exporters(8)
def export_8(data: Data) -> ReturnData:
    """증거 인멸 행위"""
    result = create_llm_exporter(PROMPT_8, ["context"])(data)
    return result


@register_exporters(9)
def export_9(data: Data) -> ReturnData:
    """기타 의심 행위"""
    result = create_llm_exporter(PROMPT_9, ["context"])(data)
    if result["content"].lower() == "none":
        return {"content": None}
    return result


@register_exporters(10)
def export_10(data: Data) -> ReturnData:
    """결론 - 확인된 사실"""
    result = create_llm_exporter(PROMPT_10, ["context"])(data)
    return result


@register_exporters(11)
def export_11(data: Data) -> ReturnData:
    """결론 - 재구성, 종합 의견"""
    result = create_llm_exporter(PROMPT_11, ["context", "scenario"], llm=llm_large)(data)
    return result


def invoke_report_details(index: int, data: Data) -> Any:
    exporter = exporters.get(index)

    if exporter is None:
        raise ValueError(f"No exporter found for index: {index}")
    content = exporter(data).get("content")

    return content


if __name__ == "__main__":
    # 테스트 데이터 임포트
    try:
        from common.test.export_test import data
    except ImportError:
        from test.export_test import data

    # print(invoke_report_details(9, data))

    result = {
        "report": {
            "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
            "title": "정보 유출 진단 보고서",
            "summary": "[의뢰 회사 이름]",
            "pc_id": "WORK-PC-001", 
            "created_at": "2025년 9월 18일",
            "created_by": "Forensic Analysis AI Agent", 
            "link": None, 
            "task_id": "test_id"
        },
        "details": []
    }

    for i in range(12):
        content = invoke_report_details(i, data)
        print(content)
        detail = {
            "id": f"id_{i}",
            "section_type": i,
            "order_no": None,
            "content": content
        }
        result["details"].append(detail)
    
    print(result)
