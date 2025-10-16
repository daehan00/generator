# agentic ai code implement
from typing import List
from common.models import SectionTypeEnum, ReportBase, ReportDetailBase, ReportDetailCreate, ReportCreate, ScenarioCreate, ScenarioStepCreate


def invoke_scenarios_test(artifacts, task_id: str, job_id: str) -> ScenarioCreate:
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

    return result

def invoke_report_details_test(sectiontype: SectionTypeEnum, job_info: dict) -> List[ReportDetailCreate]:
    result = []

    is_one = True
    content=""
    match sectiontype:
        case SectionTypeEnum.analysis_objective:
            content="""본 보고서는 특정 사용자 PC에서 발생한 의심스러운 행위들을 윈도우 아티팩트를 기반으로 분석하여, 내부 정보 유출 가능성을 진단하는 것을 목적으로 한다. 이를 통해 기업 자산의 보안 위협 수준을 평가하고, 향후 대응 방안을 마련하는 데 참고 자료로 활용한다."""
        case SectionTypeEnum.data_collection_method:
            content="""Agent 프로그램을 통해 대상 PC에서 아래에 해당하는 정보 수집
수집 대상 정보:
Prefetch 파일 (실행 이력)
LNK 파일 (최근 문서/폴더 접근 기록)
브라우저 아티팩트 (History, Cookie, Cache)
USB 연결 이력 (SetupAPI, Registry)
메신저 로그 (WhatsApp, KakaoTalk PC 버전 등)"""
        case SectionTypeEnum.data_collection_period:
            content="""2025년 8월 20일 ~ 2025년 8월 25일"""
        case SectionTypeEnum.analysis_schedule:
            content="""분석 시작: 2025년 9월 17일 10:00 (KST)
분석 종료: 2025년 9월 17일 10:10 (KST)"""
        case SectionTypeEnum.analysis_method:
            content="""수집된 아티팩트 정리 및 무결성 검증(SHA256 해시 확인)
실행 이력(Prefetch) 및 접근 기록(LNK)을 기반으로 사용자 활동 재구성
브라우저 및 메신저 로그 분석을 통한 외부 전송 여부 확인
USB 저장장치 연결 흔적 검토
행위별 타임라인 작성 및 유출 시나리오 평가"""
        case SectionTypeEnum.analysis_procedure:
            content=""""""
        case SectionTypeEnum.analysis_limitation:
            content="""본 분석은 정보유출 징후가 의심되는 사용자 PC에 남아 있는 정보유출 가능 경로로 한정하여, 본 보고서에 명시된 절차에 따라 수행되었습니다.

분석 범위는 해당 장치에서 직접 확인하거나 수집 가능한 디지털 정보에 국한되며, 외부 저장매체, 네트워크 기록, 서버 로그 등은 포함되지 않았습니다.

보고서에 기술된 일부 사항은 디지털 흔적과 정황 분석을 통한 합리적 추정으로, 명백한 사실로 단정할 수 없는 사안에 대해서는 별도 표시하였습니다.

이러한 추정 사항은 현재로서는 객관적 증거력이 충분하지 않으므로, 향후 법률 자문을 거치고 보완 증거를 확보한 후 활용하시기 바랍니다.

중요한 의사결정이나 법적 조치 이전에는 반드시 추가 검증을 실시하고, 필요시 공인된 디지털포렌식 전문기관의 재검토를 권장합니다."""
        case SectionTypeEnum.key_findings:
            content="""8월 22일, 외부 USB 저장장치 연결 후 특정 기밀 문서 접근 정황 확인

같은 날, 크롬 브라우저를 통해 특정 외부 웹메일 서비스 접속 흔적 발견

메신저 로그에서 문서명과 동일한 파일 전송 시도 정황 식별

일련의 행위를 종합했을 때, 기업 내부 문서 유출 가능성이 존재함"""
        case SectionTypeEnum.detailed_analysis:
            content="""상세 분석 내용 ~~~"""
        case SectionTypeEnum.Scenario_synthesis:
            content=""""""
        case SectionTypeEnum.result:
            contents=[
                """3.1 종합 요약

사용자 PC에서 기밀 문서 열람 → USB 연결 → 웹메일 접속의 순차적 행위가 확인됨.

일부 메신저 대화에서 해당 문서 전송 시도가 발견됨.

외부 유출 가능성은 높으나, 확정적 증거 확보는 제한됨.""",
                """3.2 평가
유출로 의심되는 정황이 존재합니다. 다만 이러한 추정 사항은 현재로서는 객관적 증거력이 충분하지 않으므로, 향후 법률 자문을 거치고 보완 증거를 확보한 후 활용하시기 바랍니다.

중요한 의사결정이나 법적 조치 이전에는 반드시 추가 검증을 실시하고, 필요시 공인된 디지털포렌식 전문기관의 재검토를 권장합니다."""
            ]
            is_one = False

            for i, item in enumerate(contents, 1):
                report_detail = ReportDetailCreate(
                    section_type=sectiontype,
                    content=item,
                    order_no=i
                )
                result.append(report_detail)

    if is_one:
        report_detail = ReportDetailCreate(
            section_type=sectiontype,
            content=content,
            order_no=None
        )
        result.append(report_detail)
    
    return result