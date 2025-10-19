from typing import Any, List
from common.test_backendclient import TestBackendClient as BackendClient
from common.agent import invoke_report_details_test, invoke_scenarios_test
from common.agent import invoke_scenarios
from common.report_exporters import invoke_report_details
from common.models import SectionTypeEnum, ReportCreate, ReportDetailCreate
from common.models import ScenarioCreate

class Generator:
    def __init__(self) -> None:
        self.scenario: ScenarioCreate
        self.report: ReportCreate

    def generate_no_data_report(self, task_id: str, job_id: str, job_info: dict, backend_client: BackendClient):
        pass

    def generate_report(self, task_id: str, job_id: str, artifacts: List[dict], job_info: dict, backend_client: BackendClient):
        # 1. artifacts를 분석하고, 시나리오 생성
        self._generate_scenarios(artifacts, task_id, job_id, job_info)

        # 2. 생성된 시나리오 데이터베이스에 저장
        scenario_saved = backend_client.save_scenario(self.scenario)
        
        if not scenario_saved:
            raise RuntimeError(f"Failed to save scenario for task {task_id}. Report generation aborted.")

        # 3. 생성된 시나리오들 기반으로 보고서 내용 생성
        # 4. 위 내용들 정리하면서 보고서 나머지 항목들 생성
        self._generate_report_details(job_info, task_id)

        # 5. 보고서 항목들 데이터베이스에 저장
        user_id = job_info.get("user_id", "system")  # job_info에서 user_id 추출, 없으면 "system" 기본값
        report_saved = backend_client.save_report(self.report, user_id, job_id)  # user_id 전달
        if not report_saved:
            raise RuntimeError(f"Failed to save report for task {task_id}. Report generation failed.")
        
        # 6. 보고서 pdf 처리
        self._generate_pdf_report()

    def _generate_scenarios(self, artifacts, task_id: str, job_id: str, job_info: dict[str, Any]) -> None:
        # 1. llm service를 호출해서 시나리오 생성
        result, context = invoke_scenarios(artifacts, task_id, job_id, job_info)
        self.scenario = result
        self.context = context

    def _generate_report_details(self, job_info: dict, task_id: str):
        self.report = ReportCreate(
            title="윈도우 아티팩트 기반 정보 유출 진단 보고서",
            summary="내부 기밀 문서 유출 가능성 존재함",
            pc_id=job_info["pc_info"]["pc_id"],
            task_id=task_id,
            details=[]
        )

        data = {
            "job_info": job_info,
            "context": self.context,
            "scenario": self.scenario
        }
        # 내용 생성 -> self.report_details에 업데이트
        for sectiontype in SectionTypeEnum:
            content = invoke_report_details(sectiontype, data)
            if not content:
                print(f"There is no detail data in section {sectiontype.value}")
                continue

            self.report.details.append(ReportDetailCreate(
                section_type=sectiontype,
                content=content,
                order_no=None
            ))

    def _generate_pdf_report(self):
        pass