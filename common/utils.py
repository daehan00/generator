"""
유틸리티 함수 모듈

"""
import os
from typing import List
from common.test_backendclient import TestBackendClient
from common.models import ScenarioCreate

from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

from langchain.chat_models import init_chat_model

# LLM 초기화
llm_small = init_chat_model("google_genai:gemini-2.5-flash-lite", temperature=0)
llm_medium = init_chat_model("google_genai:gemini-2.5-flash", temperature=0)
llm_large = init_chat_model("google_genai:gemini-2.5-pro", temperature=0)

def load_artifacts(task_id: str) -> List[dict]:
    """아티팩트를 백엔드에서 로드"""
    backend_client = TestBackendClient()
    job_id = "test+job_id"
    return backend_client.load_artifacts(task_id, job_id)


def pretty_print_scenario(scenario: ScenarioCreate):
    """시나리오 객체를 받아 가독성 좋은 보고서 형태로 출력합니다."""
    
    print("="*80)
    print(f"📜 시나리오 분석 보고서: {scenario.name}")
    print("="*80)
    
    print("\n[ 보고서 개요 ]")
    print(f"  - {scenario.description}")
    
    print("\n[ 식별 정보 ]")
    print(f"  - Job ID: {scenario.job_id}")
    print(f"  - Task ID: {scenario.task_id}")
    
    print("\n[ 재구성된 공격 단계 (Timeline) ]")
    print("-" * 80)
    
    if not scenario.steps:
        print("  (분석된 단계가 없습니다.)")
    else:
        # 시간 순서대로 정렬 (이미 정렬되어 있지만 안전장치)
        sorted_steps = sorted(scenario.steps, key=lambda s: s.order_no)
        
        for step in sorted_steps:
            # datetime 객체를 보기 좋은 문자열로 포맷팅
            timestamp_str = step.timestamp.strftime('%Y-%m-%d %H:%M:%S') if step.timestamp else ""
            
            # 아티팩트 ID 리스트를 콤마로 구분된 문자열로 변환
            artifacts_str = ", ".join(step.artifact_ids)
            
            print(f"\n▶ Step {step.order_no}: [{timestamp_str}]")
            print(f"  - 내용: {step.description}")
            print(f"  - 연관 아티팩트: [{artifacts_str}]")
    
    print("\n" + "="*80)


