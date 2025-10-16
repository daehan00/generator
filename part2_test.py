from typing import cast
from workflow.rag_agent_workflow_part2 import app_part2, AgentState

initial_state = {
    "job_id": "test_job_001",
    "task_id": "test_task_001",
    "job_info": {
        "description": "정보유출 의심 사례 분석",
        "pc_username": "이정호",
        "pc_userrank": "주임",
        "pc_usercompany": "한국정보보호산업협회"
    },
    "collection_name": "artifacts_collection",
    "db_config": None,
    "filtered_artifacts": [],  # Part 1에서 필터링된 아티팩트 (실제로는 데이터 있음)
    "data_save_status": "success",
    "raw_user_requirements": """
사내에서 활용되는 교육생 개인정보유출 의심 활동을 분석해주세요. 추가로, 이직 정황에 대해서 파악해주세요. 단순 이직 의사를 넘어서 실질적으로 이직을 시도했는지 알고 싶습니다.
이정호 주임은 한국정보보호산업협회에서 교육프로그램 운영 실무자로, 보안 전문가 육성 관련 프로그램을 기획하고 진행하는 업무를 합니다. 따라서 기존 업무의 특성을 고려하여 정보를 수집해 주세요."""
}


print("📝 초기 상태:")
print(f"  - Job ID: {initial_state['job_id']}")
print(f"  - Task ID: {initial_state['task_id']}")
print(f"  - 사용자 요구사항: {initial_state['raw_user_requirements']}")
print(f"  - 컬렉션: {initial_state['collection_name']}")

try:
    initial_state = cast(AgentState, initial_state)
    # 워크플로우 실행
    print("🚀 워크플로우 실행 시작...\n")
    final_state = app_part2.invoke(
        initial_state,
        config={"recursion_limit": 80}  # 재귀 제한 증가
    )  # type: ignore
    
    print("\n" + "="*60)
    print("✅ 워크플로우 실행 완료!")
    print("="*60 + "\n")
        
        # 결과 출력
    final_report = final_state.get("final_report")
    if final_report:
        print("📊 최종 보고서:")
        print(f"  - 제목: {final_report.name}")
        print(f"  - 설명: {final_report.description}")
        print(f"  - 단계 수: {len(final_report.steps)}개")
        print(f"  - Job ID: {final_report.job_id}")
        print(f"  - Task ID: {final_report.task_id}")
        
        if final_report.steps:
            print("\n  📝 시나리오 단계:")
            for step in final_report.steps:
                print(f"    {step.order_no}. {step.description}")
                print(step.artifact_ids)
    else:
        print("⚠️  최종 보고서가 생성되지 않았습니다.")
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
