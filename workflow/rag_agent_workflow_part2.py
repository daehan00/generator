"""
워크플로우 Part 2: 에이전트 분석 및 보고서 생성
- 요구사항 분석
- 에이전트 자율 추론 및 도구 사용
- 최종 시나리오 보고서 생성
"""

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from workflow.classes import AgentState
from workflow.requirements_node import analyze_requirements_node
from workflow.tools import agent_tools
from workflow.rag_agent_workflow import (
    agent_reasoner,
    scenario_generator,
    classify_data,
    router
)


# --------------------------------------------------------------------------
# 그래프 구성 및 컴파일
# --------------------------------------------------------------------------

# 도구 노드 생성
tool_node = ToolNode(agent_tools)

# 그래프 워크플로우 정의
workflow_part2 = StateGraph(AgentState)

# 노드 추가
workflow_part2.add_node("analyze_requirements", analyze_requirements_node)
workflow_part2.add_node("agent_reasoner", agent_reasoner)
workflow_part2.add_node("execute_tools", tool_node)
workflow_part2.add_node("generate_scenario", scenario_generator)
workflow_part2.add_node("classify_results", classify_data)

# 엣지(연결 흐름) 설정
workflow_part2.set_entry_point("analyze_requirements")

workflow_part2.add_edge("analyze_requirements", "agent_reasoner")

workflow_part2.add_conditional_edges(
    "agent_reasoner",
    router,
    {
        "tools": "execute_tools",
        "generate_scenario": "generate_scenario",
        "continue": "agent_reasoner",
    }
)

workflow_part2.add_edge("execute_tools", "agent_reasoner")
workflow_part2.add_edge("generate_scenario", "classify_results")
workflow_part2.add_edge("classify_results", END)

# 그래프 컴파일
app_part2 = workflow_part2.compile()

print("✅ Part 2 Graph compiled successfully (에이전트 분석 및 보고서 생성)!")


# --------------------------------------------------------------------------
# 테스트 실행
# --------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Part 2 워크플로우 테스트 실행")
    print("="*60 + "\n")
    
    # 초기 상태 (Part 1 완료 후 상태를 가정)
    initial_state = {
        "job_id": "test_job_001",
        "task_id": "test_task_001",
        "job_info": {
            "description": "정보유출 의심 사례 분석",
            "pc_username": "조민하",
            "pc_userrank": "직원",
            "pc_usercompany": "프리렌서"
        },
        "collection_name": "artifacts_collection",
        "db_config": None,
        "filtered_artifacts": [],  # Part 1에서 필터링된 아티팩트 (실제로는 데이터 있음)
        "data_save_status": "success",
        "raw_user_requirements": """프리렌서입니다. 주로 문서 작업을 하고 코드를 작성하는 프로젝트를 진행합니다. 내부 유출, 이직 정황에 대해서 파악해주세요. 단순 이직 의사를 넘어서 실질적으로 이직을 시도했는지 알고 싶습니다.
 따라서 기존 업무의 특성을 고려하여 정보를 수집해 주세요."""
    }
    
    print("📝 초기 상태:")
    print(f"  - Job ID: {initial_state['job_id']}")
    print(f"  - Task ID: {initial_state['task_id']}")
    print(f"  - 사용자 요구사항: {initial_state['raw_user_requirements']}")
    print(f"  - 컬렉션: {initial_state['collection_name']}")
    print()
    
    try:
        # 워크플로우 실행
        print("🚀 워크플로우 실행 시작...\n")
        final_state = app_part2.invoke(
            initial_state, # type: ignore
            config={"recursion_limit": 50}  # 재귀 제한 증가
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
        else:
            print("⚠️  최종 보고서가 생성되지 않았습니다.")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
