from workflow.classes import AgentState, ChunkAnalysisResult, FilterResult
from workflow.prompts import FILTER_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from common.utils import llm_small, chunk_artifacts

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, cast
import json
import time


def recursive_filter_node(state: AgentState):
    """
    LangGraph 조건부 엣지와 함께 사용하는 재귀 필터링 노드.
    목표 개수에 도달할 때까지 필터링 강도를 높여가며 반복.
    
    Args:
        state: AgentState
    
    Returns:
        업데이트된 state
    """
    
    # 초기화 또는 기존 상태 읽기
    filter_iteration = state.get("filter_iteration", 0)
    target_count = state.get("target_artifact_count", 10000)  # 🆕 V2: 10,000개로 상향
    
    # 필터링 강도 레벨 정의 (V2: 3단계만 사용)
    strictness_levels = [
        ("very_strict", 0.015),   # 1.5%
        ("strict", 0.025),         # 2.5%
        ("moderate", 0.06),        # 6%
    ]
    
    # 최대 반복 횟수 체크 (V2: 3회로 제한)
    max_iterations = 3  # 🆕 V2: 5회 → 3회
    if filter_iteration >= max_iterations:
        print(f"⚠️  최대 반복 횟수({max_iterations}) 도달")
        return state
    
    # 현재 반복의 강도와 비율
    strictness, target_ratio = strictness_levels[filter_iteration]
    
    # 🔄 1차 반복: 원본 artifact_chunks 사용
    # 🔄 2차 이상: 이전 필터링 결과(intermediate_results) 사용
    if filter_iteration == 0:
        # 첫 번째 반복: 원본 사용
        artifact_chunks_input = state.get("artifact_chunks", [])
        all_artifacts = []
        for chunk in artifact_chunks_input:
            all_artifacts.extend(chunk)
    else:
        # 두 번째 이상: 이전 필터링 결과 사용
        intermediate_results = state.get("intermediate_results", [])
        all_artifacts = []
        for result in intermediate_results:
            all_artifacts.extend(result.important_artifacts)
    
    total_artifacts = len(all_artifacts)
    
    print(f"\n{'='*70}")
    print(f"🔄 필터링 반복 {filter_iteration + 1}/{max_iterations}: {strictness.upper()}")
    print(f"{'='*70}")
    if filter_iteration == 0:
        print(f"  - 입력: 원본 아티팩트")
    else:
        print(f"  - 입력: {filter_iteration}차 필터링 결과")
    print(f"  - 현재 아티팩트: {total_artifacts:,}개")
    print(f"  - 필터링 강도: {strictness}")
    print(f"  - 목표 비율: {target_ratio*100:.1f}%")
    print(f"  - 목표 개수: {target_count:,}개")
    
    # 청크 분할 및 배치 설정 (TPM 최적화 - Tier 1)
    chunk_size = 300  # 아티팩트 300개/청크
    
    # TPM 기반 배치 설정 (Tier 1 유료)
    # - gemini-2.5-flash-lite Tier 1: ~4M TPM, ~1,000 RPM
    # - 예상 토큰/요청: ~10K tokens (300개 아티팩트 요약)
    # - 안전 마진: 50% → 실제 목표 ~2M TPM, ~500 RPM
    # - 배치당 요청: 20개 (동시 처리)
    # - 배치 간격: 30초
    batch_size = 20  # 배치당 청크 수
    max_workers_per_batch = 5  # 배치 내 동시 실행
    batch_delay = 30.0  # 배치 간 대기 시간 (초)
    
    artifact_chunks = chunk_artifacts(all_artifacts, chunk_size=chunk_size)
    total_chunks = len(artifact_chunks)
    print(f"  - 총 청크 수: {total_chunks}개")
    
    # 배치 단위 필터링
    all_results = []
    num_batches = (total_chunks + batch_size - 1) // batch_size
    
    print(f"\n📦 총 {num_batches}개 배치로 처리\n")
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_chunks)
        batch_chunks = artifact_chunks[start_idx:end_idx]
        
        print(f"📦 배치 {batch_num + 1}/{num_batches} (청크 {start_idx + 1}-{end_idx})...")
        
        batch_results = []
        
        with ThreadPoolExecutor(max_workers=max_workers_per_batch) as executor:
            future_to_idx = {}
            for offset, chunk in enumerate(batch_chunks):
                chunk_idx = start_idx + offset
                future = executor.submit(
                    analyze_chunk_simple,
                    chunk,
                    chunk_idx,
                    target_ratio
                )
                future_to_idx[future] = chunk_idx
            
            for future in as_completed(future_to_idx):
                chunk_idx = future_to_idx[future]
                try:
                    chunk_result = future.result(timeout=120)
                    batch_results.append((chunk_idx, chunk_result))
                except TimeoutError:
                    print(f"⏱️  청크 {chunk_idx + 1}: 타임아웃")
                    batch_results.append((chunk_idx, ChunkAnalysisResult(
                        important_artifacts=[],
                        chunk_summary="타임아웃"
                    )))
                except Exception as e:
                    print(f"❌ 청크 {chunk_idx + 1}: {type(e).__name__}")
                    batch_results.append((chunk_idx, ChunkAnalysisResult(
                        important_artifacts=[],
                        chunk_summary=f"오류: {type(e).__name__}"
                    )))
        
        batch_results.sort(key=lambda x: x[0])
        all_results.extend([r for _, r in batch_results])
        
        batch_artifacts = sum(len(r.important_artifacts) for _, r in batch_results)
        print(f"  ✅ 배치 {batch_num + 1} 완료: {batch_artifacts}개 발견")
        
        if batch_num < num_batches - 1:
            time.sleep(batch_delay)
    
    # 결과 분석
    total_filtered = sum(len(r.important_artifacts) for r in all_results)
    
    print(f"\n📊 반복 {filter_iteration + 1} 결과:")
    print(f"  - 필터링된 개수: {total_filtered:,}개")
    print(f"  - 목표 대비: {total_filtered}/{target_count} ({total_filtered/target_count*100:.1f}%)")
    
    # 다음 반복을 위한 상태 업데이트
    next_iteration = filter_iteration + 1
    next_strictness_idx = min(next_iteration, len(strictness_levels) - 1)
    next_strictness = strictness_levels[next_strictness_idx][0]
    
    return {
        "intermediate_results": all_results,
        "filter_iteration": next_iteration,
        "current_strictness": next_strictness,
        "target_artifact_count": target_count,
        "job_id": state.get("job_id"),
        "task_id": state.get("task_id"),
        "artifact_chunks": state.get("artifact_chunks"),  # 원본 유지
    }


def should_continue_filtering(state: AgentState) -> str:
    """
    필터링을 계속할지 결정하는 조건 함수.
    (V2: 목표 10,000개, 최대 3회 반복)
    
    Args:
        state: AgentState
    
    Returns:
        "continue": 필터링 반복
        "synthesize": 다음 단계로 진행
    """
    target_count = state.get("target_artifact_count", 10000)  # 🆕 V2: 10,000개
    filter_iteration = state.get("filter_iteration", 0)
    intermediate_results = state.get("intermediate_results", [])
    
    total_filtered = sum(len(r.important_artifacts) for r in intermediate_results)
    
    max_iterations = 3  # 🆕 V2: 3회
    
    # 목표 달성 여부 확인
    if total_filtered <= target_count:
        print(f"\n✅ 목표 달성! ({total_filtered:,}개 >= {target_count:,.0f}개)")
        print(f"{'='*70}\n")
        return "synthesize"
    
    # 최대 반복 도달
    if filter_iteration >= max_iterations:
        print(f"\n⚠️  최대 반복 횟수 도달. 현재 결과({total_filtered:,}개)로 진행")
        print(f"{'='*70}\n")
        return "synthesize"
    
    # 계속 필터링
    print(f"\n🔄 목표 미달. 필터링 강도를 높여 재시도...\n")
    return "continue"


def analyze_chunk_simple(
    chunk: List[dict], 
    chunk_idx: int, 
    target_ratio: float = 0.05,
    max_retries: int = 1
):
    """
    점수 없이 단순 필터링만 수행 (빠르고 안정적).
    LLM 응답 오류 시 자동 재시도.
    
    Args:
        chunk: 분석할 아티팩트 리스트
        chunk_idx: 청크 인덱스
        strictness: 필터링 강도 (현재는 사용되지 않음)
        target_ratio: 목표 선택 비율 (0.05 = 5%)
        max_retries: 최대 재시도 횟수 (기본 2회)
    
    Returns:
        ChunkAnalysisResult (점수 없음)
    """
    # 아티팩트를 간략하게 포맷
    artifacts_summary = []
    for idx, artifact in enumerate(chunk):
        artifact_type = artifact.get('artifact_type', 'N/A')
        artifact_id = artifact.get('id', 'N/A')
        
        data = artifact.get('data', {})
        data_summary = {}
        for key, value in data.items():
            if not value:
                continue
            if hasattr(value, 'isoformat'):
                data_summary[key] = value.isoformat()
            else:
                data_summary[key] = str(value)
        
        artifacts_summary.append({
            "index": idx,
            "type": artifact_type,
            "key_data": data_summary,
            "id": artifact_id
        })
    
    artifacts_text = json.dumps(artifacts_summary, ensure_ascii=False, indent=2)
    
    # 🆕 통합된 단일 프롬프트 (필터링 강도와 무관하게 일관된 기준 적용)
    target_count = max(5, int(len(chunk) * target_ratio))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", FILTER_PROMPT),
        ("human", "아티팩트 목록:\n{artifacts_text}\n\n청크 크기: {chunk_size}개")
    ])
    
    structured_llm = llm_small.with_structured_output(FilterResult)
    filter_chain = prompt | structured_llm
    
    chunk_size = len(chunk)
    
    # 재시도 로직 (최대 max_retries회 시도)
    for attempt in range(max_retries + 1):
        try:
            filter_result = filter_chain.invoke({
                "artifacts_text": artifacts_text,
                "chunk_size": chunk_size,
                "target_ratio_percent": target_ratio * 100,
                "target_count": target_count
            })
            
            # 응답 검증
            if filter_result is None or not hasattr(filter_result, 'important_indices'):
                if attempt < max_retries:
                    print(f"⚠️  청크 {chunk_idx + 1}: LLM 응답 오류 (재시도 {attempt + 1}/{max_retries})...")
                    time.sleep(1)
                    continue
                else:
                    print(f"❌ 청크 {chunk_idx + 1}: 최대 재시도 횟수 도달 - 빈 결과 반환")
                    return ChunkAnalysisResult(
                        important_artifacts=[],
                        chunk_summary="분석 실패 (최대 재시도 초과)"
                    )
                
            filter_result = cast(FilterResult, filter_result)

            # 선택된 아티팩트의 원본 데이터 추출
            important_artifacts = [
                chunk[idx] for idx in filter_result.important_indices 
                if 0 <= idx < len(chunk)
            ]
            
            if not important_artifacts:
                print(f"✅ 청크 {chunk_idx + 1}: 유의미한 데이터 없음")
                chunk_summary = "관련성 없는 데이터"
            else:
                chunk_summary = filter_result.chunk_summary
                if attempt > 0:
                    print(f"✅ 청크 {chunk_idx + 1}: {len(important_artifacts)}개 발견 (재시도 {attempt}회 후 성공)")
                else:
                    print(f"✅ 청크 {chunk_idx + 1}: {len(important_artifacts)}개 발견")
            
            return ChunkAnalysisResult(
                important_artifacts=important_artifacts,
                chunk_summary=chunk_summary
            )
        
        except Exception as e:
            if attempt < max_retries:
                print(f"⚠️  청크 {chunk_idx + 1}: {type(e).__name__} (재시도 {attempt + 1}/{max_retries})...")
                time.sleep(1)
                continue
            else:
                print(f"❌ 청크 {chunk_idx + 1}: 최대 재시도 후 실패 - {str(e)}")
                return ChunkAnalysisResult(
                    important_artifacts=[],
                    chunk_summary=f"오류: {type(e).__name__}"
                )
