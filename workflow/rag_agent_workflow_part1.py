"""
워크플로우 Part 1: 데이터 로딩 및 저장
- 아티팩트 필터링
- 필터링된 아티팩트 추출
- 벡터 DB 및 아티팩트 저장소에 저장
"""

from langgraph.graph import StateGraph, END

from workflow.filter_node import (
    recursive_filter_node,
    should_continue_filtering
)
from workflow.classes import AgentState
from workflow.database import save_data_node
from workflow.rag_agent_workflow import extract_filtered_artifacts, check_save_status



# --------------------------------------------------------------------------
# 그래프 구성 및 컴파일
# --------------------------------------------------------------------------

# 그래프 워크플로우 정의
workflow_part1 = StateGraph(AgentState)

# 노드 추가
workflow_part1.add_node("recursive_filter", recursive_filter_node)
workflow_part1.add_node("extract_artifacts", extract_filtered_artifacts)
workflow_part1.add_node("save_data", save_data_node)

# 엣지(연결 흐름) 설정
workflow_part1.set_entry_point("recursive_filter")

# 재귀 필터링 조건부 엣지
workflow_part1.add_conditional_edges(
    "recursive_filter",
    should_continue_filtering,
    {
        "continue": "recursive_filter",  # 필터링 반복
        "synthesize": "extract_artifacts"  # 다음 단계로
    }
)

workflow_part1.add_edge("extract_artifacts", "save_data")
workflow_part1.add_edge("save_data", END)

# # 데이터 저장 후 종료
# workflow_part1.add_conditional_edges(
#     "save_data",
#     check_save_status,
#     {
#         "success": END,  # 성공 시 종료
#         "failure": END   # 실패 시도 종료
#     }
# )

# 그래프 컴파일
app_part1 = workflow_part1.compile()

print("✅ Part 1 Graph compiled successfully (데이터 로딩 및 저장)!")
