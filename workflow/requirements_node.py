"""
요구사항 분석 노드
- 사용자 입력 요구사항을 분석하여 구조화
"""
import json
from typing import Dict
from workflow.utils import llm_medium


def analyze_requirements_node(state) -> Dict[str, str]:
    """
    요구사항 분석 노드: 사용자 요구사항을 분석하여 구조화합니다.
    
    Args:
        state: AgentState (TypedDict)
            - raw_user_requirements: 원본 사용자 요구사항
            - job_info: 작업 관련 정보 (선택)
    
    Returns:
        Dict: 업데이트된 상태
            - analyzed_user_requirements: 분석된 사용자 요구사항
    
    Note:
        - 시스템 프롬프트는 prompts.py의 AGENT_SYSTEM_PROMPT를 사용
        - analyzed_system_requirements는 제거됨 (정적 프롬프트이므로)
    """
    print("--- 📋 Node: 요구사항 분석 중... ---")
    
    raw_user_requirements = state.get("raw_user_requirements", "")

    job_info_json = state.get("job_info", {}) # dictionary 형태의 데이터
    job_info = "(작업 정보 없음)"
    if job_info_json:
        job_info = json.dumps(job_info_json, ensure_ascii=False, indent=2)

    prompt = f"""당신은 사용자 요구사항 분석가입니다.
아래의 작업 정보와 사용자 요구사항을 종합하여 데이터 분석 에이전트가 활용할 수 있도록
명확하고 구체적인 요구사항 명세서를 작성해 주세요.

[작업 정보]
{job_info}

[사용자 요구사항]
{raw_user_requirements}

[작성 지침]
1. 사용자 요구사항의 핵심 목표를 명확히 파악하세요.
2. 분석 대상, 분석 범위, 기대 결과를 구체화하세요.
3. 에이전트가 어떤 데이터를 검색하고 분석해야 하는지 명시하세요.
4. 모호한 표현은 구체적인 표현으로 변환하세요.

[출력 형식]
마크다운 형식으로 작성하되, 다음 섹션을 포함하세요:
- ## 분석 목표
- ## 분석 대상
- ## 기대 결과
- ## 주요 질문
"""

    try:
        # LLM을 사용하여 요구사항 분석
        response = llm_medium.invoke(prompt)
        analyzed_user_requirements = str(response.content)
        
        print("  ✅ 요구사항 분석 완료")
        print(f"     - 사용자 요구사항: {len(analyzed_user_requirements)}자")
        
    except Exception as e:
        print(f"  ⚠️  요구사항 분석 중 오류 발생: {e}")
        print(f"     - 원본 사용자 요구사항을 그대로 사용합니다.")
        analyzed_user_requirements = raw_user_requirements or "정보유출 시나리오 분석"
    
    return {
        "analyzed_user_requirements": analyzed_user_requirements
    }
