"""
유틸리티 함수 모듈
- 아티팩트 로딩 및 청크 분할
- 보고서 출력
- 청크 사이즈 최적화
"""

from typing import List
from common.test_backendclient import TestBackendClient
from common.models import ScenarioCreate
from langchain.chat_models import init_chat_model


from dotenv import load_dotenv
load_dotenv("../.env")

# LLM 초기화
llm_small = init_chat_model("google_genai:gemini-2.5-flash-lite", temperature=0)
llm_medium = init_chat_model("google_genai:gemini-2.5-flash", temperature=0)
llm_large = init_chat_model("google_genai:gemini-2.5-pro", temperature=0)

def load_artifacts(task_id: str) -> List[dict]:
    """아티팩트를 백엔드에서 로드"""
    backend_client = TestBackendClient()
    job_id = "test+job_id"
    return backend_client.load_artifacts(task_id, job_id)


def chunk_artifacts(artifacts: List[dict], chunk_size: int = 50) -> List[List[dict]]:
    """아티팩트를 청크로 분할"""
    return [artifacts[i:i+chunk_size] for i in range(0, len(artifacts), chunk_size)]


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


def calculate_optimal_chunk_size(total_artifacts: int, target_chunks: int = 100) -> int:
    """
    아티팩트 총 개수에 따라 최적의 청크 사이즈 계산
    
    Args:
        total_artifacts: 전체 아티팩트 개수
        target_chunks: 목표 청크 개수 (기본 100개)
        
    Returns:
        최적화된 청크 사이즈
    """
    # 목표 청크 개수로 나눈 값
    calculated_size = total_artifacts // target_chunks
    
    # 최소/최대 제한 설정
    min_chunk_size = 500   # 너무 작으면 비효율
    max_chunk_size = 2000  # 너무 크면 토큰 초과 위험
    
    # 범위 내로 조정
    optimal_size = max(min_chunk_size, min(calculated_size, max_chunk_size))
    
    # 실제 청크 개수 계산
    actual_chunks = (total_artifacts + optimal_size - 1) // optimal_size
    
    print(f"📊 청크 사이즈 최적화 결과:")
    print(f"  - 전체 아티팩트: {total_artifacts:,}개")
    print(f"  - 청크 사이즈: {optimal_size}개")
    print(f"  - 예상 청크 개수: {actual_chunks}개")
    print(f"  - Map 단계 LLM 호출: {actual_chunks}번")
    print(f"  - 예상 처리 시간: ~{actual_chunks * 2.5:.0f}초 (약 {actual_chunks * 2.5 / 60:.1f}분)")
    
    return optimal_size
