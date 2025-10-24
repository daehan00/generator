from typing import Any, Dict

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode


# 🆕 V2: workflow_v2의 필터링 로직 및 클래스 import
from workflow.filter_node import (
    recursive_filter_node,
    should_continue_filtering
)
from workflow.classes import AgentState, ScenarioCreate
from workflow.database import save_data_node
from workflow.requirements_node import analyze_requirements_node
from workflow.tools import agent_tools, ToolContext, get_metadata_info, format_metadata_section
from workflow.prompts import AGENT_SYSTEM_PROMPT, SCENARIO_GENERATOR_SYSTEM_PROMPT, CLASSIFY_PROMPT
from workflow.utils import llm_large, llm_small

# --------------------------------------------------------------------------
# LLM 및 도구 설정
# --------------------------------------------------------------------------
llm_with_tools = llm_large.bind_tools(agent_tools)

# --------------------------------------------------------------------------
# 그래프 노드(Nodes) 정의
# --------------------------------------------------------------------------

def extract_filtered_artifacts(state: AgentState) -> Dict:
    """
    재귀 필터링 완료 후, intermediate_results에서 filtered_artifacts를 추출하고
    메모리 최적화를 위해 불필요한 원본 데이터를 정리합니다.
    """
    print("--- 📦 Node: 필터링 결과 추출 및 메모리 정리 중... ---")
    
    # 1. 필터링된 아티팩트 추출
    filtered = []
    for result in state.get("intermediate_results", []):
        filtered.extend(result.important_artifacts)
    
    print(f"  ✅ 총 {len(filtered)}개 아티팩트 추출")
    
    # 2. 메모리 최적화: 더 이상 필요 없는 대용량 데이터 정리
    # - artifact_chunks: 원본 아티팩트 청크 (필터링 완료 후 불필요)
    # - intermediate_results: 중간 결과 (이미 filtered_artifacts로 추출)
    
    chunks_count = sum(len(chunk) for chunk in state.get("artifact_chunks", []))
    
    print(f"  🗑️  메모리 정리:")
    print(f"     - artifact_chunks 제거: {chunks_count:,}개")
    print(f"     - intermediate_results 제거: {len(state.get('intermediate_results', []))}개 청크")
    
    print(f"--- ✅ Node: 메모리 정리 완료 (필터링된 {len(filtered)}개만 유지) ---")
    
    return {
        "filtered_artifacts": filtered,
        # 메모리 최적화: 불필요한 데이터 명시적으로 제거
        "artifact_chunks": [],
        "intermediate_results": [],
    }

def agent_reasoner(state: AgentState) -> Dict:
    """
    (워크플로우 3단계) 에이전트의 자율적 추론 및 행동 결정
    
    역할:
    - 요구사항을 분석하여 필요한 정보 수집 계획 수립
    - 도구를 자율적으로 선택하여 실행 (query_planner, artifact_search, web_search)
    - 도구 결과를 분석하여 추가 조사 필요 여부 판단
    - 충분한 정보 수집 시 최종 보고서 생성 결정
    
    흐름:
    1. 시스템 프롬프트(AGENT_SYSTEM_PROMPT) + 사용자 요구사항 로드
    2. LLM이 다음 행동 결정 (도구 호출 또는 보고서 생성)
    3. 메시지를 state에 추가 (다음 노드로 전달)
    """
    print("--- 🤔 Agent: 추론 및 행동 결정 중... ---")
    
    # 0. 도구 컨텍스트 설정 (도구가 State 정보에 접근 가능하도록)
    collection_name = state.get("collection_name") or "artifacts_collection"
    db_config = state.get("db_config")
    ToolContext.set_context(collection_name, db_config)
    
    # 1. 메시지 구성
    existing_messages = state.get("messages", [])
    messages_to_invoke = list(existing_messages) # type: ignore

    if not messages_to_invoke:
        # 첫 실행: 시스템 메시지 + 사용자 메시지 생성
        user_requirements = state.get("analyzed_user_requirements", "일반적인 정보유출 분석을 진행해 주세요.")

        metadata_info = get_metadata_info(collection_name, db_config)
        context_info = format_metadata_section(metadata_info)

        messages_to_invoke = [
            SystemMessage(content=AGENT_SYSTEM_PROMPT.format(context_info=context_info)),
            HumanMessage(content=user_requirements or "정보유출 시나리오 분석")
        ]


    else:
        # 이후 실행: 기존 히스토리만 사용
        last_message = messages_to_invoke[-1]

        # ToolMessage 이후에는 continuation_prompt를 추가하지 않음
        # (도구 결과가 이미 메시지에 포함되어 있으므로 LLM이 자동으로 분석함)
        if isinstance(last_message, AIMessage) and not last_message.tool_calls:
            continuation_prompt = "분석을 바탕으로 다음 단계를 진행하세요. 모든 정보가 수집되었다고 판단되면 최종 보고서를 생성하겠다고 명확히 언급해주세요."
            messages_to_invoke.append(HumanMessage(content=continuation_prompt))

    # 2. LLM 호출
    print(f"  📨 메시지 개수: {len(messages_to_invoke)}개")
    
    try:
        response = llm_with_tools.invoke(messages_to_invoke)

        # 3. 응답 분석 및 로깅
        tool_calls = getattr(response, 'tool_calls', None)
        if tool_calls:
            print(f"  🔧 도구 호출: {len(tool_calls)}개")
            for tool_call in tool_calls:
                print(f"     - {tool_call.get('name', 'unknown')}")
        else:
            content = getattr(response, 'content', '')
            if content:
                # 첫 100자만 출력 (간결하게)
                preview = content[:100] + "..." if len(content) > 100 else content
                print(f"  💭 추론: {preview}")
            else:
                print(f"  ⚠️  경고: LLM 응답이 비어있습니다!")
            
            # 종료 조건 확인
            if "충분한 정보를 수집했습니다" in content or "최종 보고서를 생성하겠습니다" in content:
                print("  ✅ 정보 수집 완료 → 보고서 생성 단계로 이동")
        
        print("--- ✅ Agent: 추론 완료 ---")
        if len(messages_to_invoke) == 2:
            return {"messages": messages_to_invoke + [response]}
        return {"messages": [response]}
        
    except Exception as e:
        print(f"  ❌ 에이전트 추론 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        # 오류 발생 시 "충분한 정보" 키워드를 포함하지 않음 (가짜 보고서 생성 방지)
        error_response = AIMessage(
            content=f"오류가 발생했습니다: {str(e)}\n데이터베이스 접근 또는 LLM 호출에 문제가 발생했습니다."
        )
        return {"messages": [error_response], "analysis_failed": True}

def scenario_generator(state: AgentState) -> Dict:
    """
    (워크플로우 4단계) 누적된 모든 정보(History, 검색 결과)를 바탕으로 최종 보고서를 생성합니다.
    
    역할:
    - 대화 히스토리에서 수집된 모든 정보 분석
    - 정보유출 시나리오를 시간순으로 재구성
    - ScenarioCreate 객체로 구조화된 보고서 생성
    
    출력:
    - name: 시나리오 제목
    - description: 시나리오 요약
    - steps: 5-10개의 단계별 행위 설명 (시간순)
    """
    print("--- 📝 Node: 최종 보고서 생성 중 ---")
    
    # 1. 메시지 히스토리 가져오기
    messages = state.get("messages") or []
    job_id = state.get("job_id", "unknown")
    task_id = state.get("task_id", "unknown")
    analysis_failed = state.get("analysis_failed", False)
    
    print(f"  📊 분석 대상: {len(messages)}개 메시지")
    
    # 2. 오류 상태 확인 (가짜 보고서 생성 방지)
    if analysis_failed:
        print("  ⚠️  분석 실패 상태 - 오류 보고서 생성")
        error_report = ScenarioCreate(
            name="데이터 분석 실패",
            description=(
                "데이터베이스 접근 또는 LLM 호출 중 오류가 발생하여 "
                "정보유출 시나리오를 생성할 수 없습니다. "
                "시스템 로그를 확인해주세요."
            ),
            job_id=job_id,
            task_id=task_id,
            report_detail_id="analysis_failed",
            steps=[]
        )
        return {"final_report": error_report}
    
    # 3. 도구 실행 검증 (최소 검색 횟수 확인)
    tool_messages = [m for m in messages if hasattr(m, 'name') and getattr(m, 'name', None)]
    if len(tool_messages) == 0:
        print("  ⚠️  도구 실행 없음 - 데이터 부족 보고서 생성")
        no_search_report = ScenarioCreate(
            name="검색 결과 없음",
            description=(
                "데이터 검색이 수행되지 않았습니다. "
                "벡터 데이터베이스가 비어있거나 접근 권한이 없을 수 있습니다."
            ),
            job_id=job_id,
            task_id=task_id,
            report_detail_id="no_search",
            steps=[]
        )
        return {"final_report": no_search_report}
    
    print(f"  🔍 도구 실행 횟수: {len(tool_messages)}개")
    
    # 4. LLM 호출 (structured output)
    try:
        structured_llm = llm_large.with_structured_output(ScenarioCreate)
        
        # 시나리오 생성 메시지 구성
        scenario_messages = [
            SystemMessage(content=SCENARIO_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(content=f"대화 히스토리를 바탕으로 정보유출 시나리오를 생성하세요.\n\n도구 실행 횟수: {len(tool_messages)}개"),
            *messages  # 전체 대화 히스토리 포함
        ]
        
        result = structured_llm.invoke(scenario_messages)
        
        # Pydantic 모델로 변환 (dict로 반환될 수 있음)
        report: ScenarioCreate
        if isinstance(result, dict):
            report = ScenarioCreate(**result)
        else:
            report = result  # type: ignore
        
        # job_id, task_id 업데이트
        report = report.model_copy(update={"job_id": job_id, "task_id": task_id})
        
        print(f"  ✅ 보고서 생성 완료:")
        print(f"     - 제목: {report.name}")
        print(f"     - 단계 수: {len(report.steps)}개")
        
        return {"final_report": report}
        
    except Exception as e:
        print(f"  ❌ 보고서 생성 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        # 오류 시 기본 보고서 반환
        fallback_report = ScenarioCreate(
            name="보고서 생성 실패",
            description=f"LLM 호출 중 오류 발생: {str(e)}",
            job_id=job_id,
            task_id=task_id,
            report_detail_id="llm_error",
            steps=[]
        )
        return {"final_report": fallback_report}

def classify_data(state: AgentState) -> Dict:
    """
    (워크플로우 4단계) 누적된 메시지 정보들을 바탕으로 나온 마지막 결론을 행위 기준으로 분류합니다.
    """
    print("--- 📝 Node: 데이터 분류 중 ---")
    messages = state.get("messages") or []
    analysis_failed = state.get("analysis_failed", False)

    if analysis_failed:
        context = ""
        return {"context": context}
    
    try:
        response = llm_large.invoke([HumanMessage(content=CLASSIFY_PROMPT), *messages])
        context = response.content
        return {"context": context}
    except Exception as e:
        print(f"  ❌ 분류 데이터 생성 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        context = ""
        return {"context": context}


# --------------------------------------------------------------------------
# 5. 제어 흐름(Router) 정의
# --------------------------------------------------------------------------

# 데이터 저장 결과에 따라 분기할 라우터
def check_save_status(state: AgentState) -> str:
    """data_save_status 필드의 값을 확인하여 'success' 또는 'failure'를 반환합니다."""
    status = state.get("data_save_status")
    return status if status else "failure"

def router(state: AgentState) -> str:
    """에이전트의 마지막 메시지를 보고 다음에 실행할 노드를 결정합니다."""
    messages = state.get("messages", [])
    if not messages:
        return "continue"
    
    # 오류 상태 확인 (agent_reasoner에서 설정)
    if state.get("analysis_failed"):
        print("  ⚠️  분석 실패 상태 감지 - 오류 보고서 생성")
        return "generate_scenario"
    
    # 무한 루프 방지: 최대 반복 횟수 체크
    ai_messages = [m for m in messages if isinstance(m, AIMessage)]
    max_iterations = 20
    if len(ai_messages) >= max_iterations:
        print(f"  ⚠️  최대 반복 횟수({max_iterations}) 도달 - 보고서 생성")
        return "generate_scenario"
    
    last_message = messages[-1]
    
    # AIMessage에 tool_calls가 있으면 도구 실행
    tool_calls = getattr(last_message, 'tool_calls', None)
    if tool_calls:
        return "tools"
    
    # AIMessage의 content를 보고 최종 보고서 생성 여부 판단
    content = getattr(last_message, "content", "") or ""
    if not content:
        return "continue"

    prompt_text = (
        "아래 ai message를 보고 최종 보고서 생성이 완료되었는지 True or False로 판단하세요.\n"
        "[ai_message]\n"
        f"{content}\n\n"
        "응답은 반드시 True 또는 False만 반환하세요."
    )

    structured_llm = llm_small.with_structured_output(bool)
    result = structured_llm.invoke([HumanMessage(content=prompt_text)])

    if check_is_done(result):
        return "generate_scenario"
    
    # 기본적으로 계속 생각
    return "continue"

def check_is_done(result: bool | dict | Any) -> bool:
    is_done = False
    if isinstance(result, bool):
        is_done = result
    elif isinstance(result, dict):
        bool_vals = [v for v in result.values() if isinstance(v, bool)]
        if bool_vals:
            is_done = bool_vals[0]
        else:
            is_done = str(result).strip().lower() in ("true", "yes", "1")
    else:
        is_done = str(result).strip().lower() in ("true", "yes", "1")
    return is_done

# --------------------------------------------------------------------------
# 그래프 구성 및 컴파일
# --------------------------------------------------------------------------

# 도구 노드 생성 (agent_tools는 tools.py에서 import됨)
tool_node = ToolNode(agent_tools)

# 그래프 워크플로우 정의
workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node("filter_artifacts", recursive_filter_node)  # 아티팩트 필터링
workflow.add_node("extract_results", extract_filtered_artifacts)  # 필터링 결과 추출
workflow.add_node("save_data", save_data_node)  # 데이터 저장
workflow.add_node("analyze_requirements", analyze_requirements_node)  # 요구사항 분석
workflow.add_node("agent_reasoner", agent_reasoner)  # 에이전트 추론
workflow.add_node("execute_tools", tool_node)  # 도구 실행
workflow.add_node("generate_scenario", scenario_generator)  # 시나리오 생성
workflow.add_node("classify_results", classify_data)  # 결과 분류

# 엣지(연결 흐름) 설정
workflow.set_entry_point("filter_artifacts")

# 🆕 재귀 필터링 조건부 엣지
workflow.add_conditional_edges(
    "filter_artifacts",
    should_continue_filtering,
    {
        "continue": "filter_artifacts",  # 필터링 반복
        "synthesize": "extract_results"  # 다음 단계로
    }
)

workflow.add_edge("extract_results", "save_data")  # 아티팩트 추출 후 데이터 저장

# [수정] 데이터 저장 후, 결과에 따라 분기하는 조건부 엣지 추가
workflow.add_conditional_edges(
    "save_data",
    check_save_status,
    {
        "success": "analyze_requirements",  # 성공 시 요구사항 분석
        "failure": END                      # 실패 시 워크플로우 즉시 종료
    }
)

workflow.add_edge("analyze_requirements", "agent_reasoner")  # 요구사항 분석 후 에이전트 시작

workflow.add_conditional_edges(
    "agent_reasoner",
    router,
    {
        "tools": "execute_tools",
        "generate_scenario": "generate_scenario",
        "continue": "agent_reasoner", # 계속 생각
    }
)
workflow.add_edge("execute_tools", "agent_reasoner") # 도구 사용 후 다시 생각
workflow.add_edge("generate_scenario", "classify_results") 
workflow.add_edge("classify_results", END) 

# 그래프 컴파일
app = workflow.compile()

print("✅ Graph compiled successfully!")