from workflow.rag_agent_workflow_part1 import app_part1, AgentState
from workflow.classes import create_initial_state
from test.test_data_loader import test_data_loader_v1

import time
from typing import cast


task_id = "session-20251002-052932-151e52e9" # 10만개 데이터
# task_id = "session-20251002-040520-28a9dc6c" # 정호주임 pc
# task_id = "session-20250930-133411-99e3becc"
# task_id = "session-20251001-151642-1ff9e24a"
job_id = "test+job_id"

print("🔄 아티팩트 생성 중...")
# artifacts = make_test_artifacts(task_id, limit=100)
# artifacts = make_test_artifacts(task_id)
artifacts = test_data_loader_v1(task_id, months=12)

print(f"\n✅ 총 {len(artifacts):,}개 아티팩트 로드 완료")

print(f"\n🚀 분석 시작...")

initial_state = create_initial_state(
    job_id=job_id,
    task_id=task_id,
    job_info={},
    artifact_chunks=[artifacts],
    intermediate_results=[],
    filter_iteration=0,
    target_artifact_count=100_000,
    current_strictness="very_strict",
    raw_user_requirements=""
)

start_time = time.time()

initial_state = cast(AgentState, initial_state)
final_state = app_part1.invoke(initial_state)
elapsed_time = time.time() - start_time

print(f"\n⏱️  총 처리 시간: {elapsed_time:.1f}초 ({elapsed_time/60:.1f}분)")
print(f"🔍 필터링된 중요 아티팩트: {sum(len(r.important_artifacts) for r in final_state['intermediate_results'])}개")
