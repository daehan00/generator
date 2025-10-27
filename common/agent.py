# agentic ai code implement
from typing import Any, List, cast
from common.models import SectionTypeEnum, ReportBase, ReportDetailBase, ReportDetailCreate, ReportCreate, ScenarioCreate, ScenarioStepCreate
from workflow.rag_agent_workflow import app, AgentState
from workflow.classes import create_initial_state
from workflow.prompts import RAW_REQUIREMENTS

def invoke_scenarios(artifacts, task_id, job_id, job_info) -> tuple[ScenarioCreate, str, List]:
    initial_state = create_initial_state(
        job_id=job_id,
        task_id=task_id,
        job_info=job_info,
        artifact_chunks=[artifacts],
        intermediate_results=[],
        filter_iteration=0,
        target_artifact_count=100_000,
        current_strictness="very_strict",
        raw_user_requirements=RAW_REQUIREMENTS
    )

    initial_state = cast(AgentState, initial_state)
    final_state = app.invoke(initial_state, config={"recursion_limit": 80})
    return final_state["final_report"], final_state["context"], final_state["messages"]

def invoke_scenarios_test(artifacts, task_id: str, job_id: str, job_info: dict[str, Any]) -> tuple[ScenarioCreate, str]:
    print(f"Count of artifacts: {len(artifacts)}")
    result = ScenarioCreate(
        job_id= job_id,
        task_id= task_id,
        name= "내부 기밀 문서 유출",
        description= """
위 행위들을 종합적으로 분석하면, 사용자가 기밀 문서(Strategy2025.docx)를 열람 후 USB 저장장치에 복사했을 가능성이 높으며, 이어 외부 웹메일 접속까지 이루어진 정황이 확인된다. 또한, 메신저 로그 일부에서 동일한 문서명 언급이 발견되어, 전송 시도가 있었음을 강하게 시사한다.
다만, 실제 첨부/전송 여부는 네트워크 트래픽 캡처 부재로 인해 직접 확인되지 않았다.        
""",
        report_detail_id= None,
        steps=[
            ScenarioStepCreate(
                order_no=1,
                timestamp=None,
                description="특정 기밀 문서 접근 정황",
                artifact_ids=[]
            ),
            ScenarioStepCreate(
                order_no=2,
                timestamp=None,
                description="8월 22일, 외부 USB 저장장치 연결",
                artifact_ids=[]
            ),
            ScenarioStepCreate(
                order_no=3,
                timestamp=None,
                description="크롬 브라우저를 통해 특정 외부 웹메일 서비스 접속 흔적 발견",
                artifact_ids=[]
            ),
            ScenarioStepCreate(
                order_no=4,
                timestamp=None,
                description="메신저 로그에서 문서명과 동일한 파일 전송 시도 정황 식별",
                artifact_ids=[]
            ),
        ]
    )
    context = ""
    return result, context

def invoke_report_details_test(sectiontype: SectionTypeEnum, job_info: dict) -> str:
    return f"This is test content from sectiontype {sectiontype}."    