from typing import Any, List
from common.test_backendclient import TestBackendClient as BackendClient
from common.agent import invoke_report_details_test, invoke_scenarios_test
from common.agent import invoke_scenarios
from common.report_exporters import invoke_report_details
from common.models import SectionTypeEnum, ReportCreate, ReportDetailCreate
from common.models import ScenarioCreate
from common.sample import sample_create_data
from pdf_export import PDFReportExporter
from pdf_export.pdf_generator import transform_flat_to_hierarchical
import logging


class Generator:
    def __init__(self) -> None:
        self.scenario: ScenarioCreate
        self.report: ReportCreate
        self.logger = logging.getLogger(__name__)

    def generate_no_data_report(self, task_id: str, job_id: str, job_info: dict, backend_client: BackendClient):
        pass

    def generate_report(self, task_id: str, job_id: str, artifacts: List[dict], job_info: dict, backend_client: BackendClient):
        # 1. artifacts를 분석하고, 시나리오 생성
        self.logger.info(f"Starting report generation for task_id: {task_id}, job_id: {job_id}")
        self._generate_scenarios(artifacts, task_id, job_id, job_info)

        # 2. 생성된 시나리오 데이터베이스에 저장
        self.logger.debug("Saving scenario to database")
        scenario_saved = backend_client.save_scenario(self.scenario)
        
        if not scenario_saved:
            self.logger.error(f"Failed to save scenario for task {task_id}. Report generation aborted.")
            raise RuntimeError(f"Failed to save scenario for task {task_id}. Report generation aborted.")
        
        self.logger.info("Scenario saved successfully")

        # 3. 생성된 시나리오들 기반으로 보고서 내용 생성
        # 4. 위 내용들 정리하면서 보고서 나머지 항목들 생성
        self.logger.debug("Generating report details")
        self._generate_report_details(job_info, task_id)

        # 5. 보고서 항목들 데이터베이스에 저장
        user_id = job_info.get("user_id", "system")
        self.logger.debug(f"Saving report to database for user_id: {user_id}")
        report_saved = backend_client.save_report(self.report, user_id, job_id)
        
        if not report_saved:
            self.logger.error(f"Failed to save report for task {task_id}. Report generation failed.")
            raise RuntimeError(f"Failed to save report for task {task_id}. Report generation failed.")
        
        self.logger.info("Report saved successfully")
        
        # 6. 보고서 pdf 처리
        self.logger.debug("Starting PDF generation")
        self._generate_pdf_report(report_saved)
        self.logger.info("Report generation completed successfully")

    def _generate_scenarios(self, artifacts, task_id: str, job_id: str, job_info: dict[str, Any]) -> None:
        # 1. llm service를 호출해서 시나리오 생성
        self.logger.debug(f"Invoking LLM service to generate scenarios for task_id: {task_id}")
        result, context = invoke_scenarios(artifacts, task_id, job_id, job_info)
        self.scenario = result
        self.context = context
        self.logger.info(f"Scenarios generated successfully for task_id: {task_id}")

    def _generate_report_details(self, job_info: dict, task_id: str):
        self.logger.debug("Initializing report structure")
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
        self.logger.debug("Generating report details for each section type")
        for sectiontype in SectionTypeEnum:
            self.logger.debug(f"Processing section: {sectiontype.value}")
            content = invoke_report_details(sectiontype, data)
            
            if not content:
                self.logger.warning(f"No detail data generated for section: {sectiontype.value}")
                continue

            self.report.details.append(ReportDetailCreate(
                section_type=sectiontype,
                content=content,
                order_no=None
            ))
            self.logger.debug(f"Section {sectiontype.value} added successfully")
        
        self.logger.info(f"Report details generation completed. Total sections: {len(self.report.details)}")

    def _generate_pdf_report(self, data: dict[str, Any]):
        try:
            self.logger.info("📄 보고서 PDF 변환 프로세스 시작")
            # 🔍 입력 데이터 확인
            report_info = data.get('report', {})
            details = data.get('details', [])
            
            self.logger.info("📋 보고서 정보:")
            self.logger.info(f"  - ID: {report_info.get('id')}")
            self.logger.info(f"  - Title: {report_info.get('title')}")
            self.logger.info(f"  - Summary: {report_info.get('summary')}")
            self.logger.info(f"  - PC ID: {report_info.get('pc_id')}")
            self.logger.info(f"  - Created At: {report_info.get('created_at')}")
            self.logger.info(f"  - Details Count: {len(details)}")
            
            # 🔧 평면 구조를 계층 구조로 변환
            self.logger.debug("🔧 데이터 구조 변환 중...")
            transformed_details = transform_flat_to_hierarchical(details)
            
            # 변환된 데이터 구조 생성
            transformed_data = {
                'report': report_info,
                'details': transformed_details
            }
            
            self.logger.info("✅ 데이터 변환 완료:")
            self.logger.info(f"  - 원본 Details: {len(details)}개")
            self.logger.info(f"  - 변환된 Main Sections: {len(transformed_details)}개")
            for section in transformed_details:
                self.logger.debug(f"    • {section['main_order']}. {section['main_title']} ({len(section['sections'])}개 하위 섹션)")
            
            # PDFReportExporter 인스턴스 생성
            self.logger.debug("PDFReportExporter 인스턴스 생성 중...")
            exporter = PDFReportExporter()
            
            # 커스텀 파일명 생성
            report_id = report_info.get('id', 'unknown')
            custom_filename = f"{report_id}.pdf"

            self.logger.info(f"📝 생성할 파일명: {custom_filename}")
            
            # PDF 생성 및 S3 업로드
            self.logger.debug("PDF 생성 및 S3 업로드 시작...")
            pdf_url = exporter.generate_and_upload(
                report_data=transformed_data,
                delete_local=True,
                custom_filename=custom_filename
            )
            
            if pdf_url:
                self.logger.info(" 보고서 PDF 처리 완료!")
                self.logger.info(f" PDF URL: {pdf_url}")
                return pdf_url
            else:
                self.logger.error("❌ PDF 생성 또는 업로드 실패")
                return None
                
        except ImportError as e:
            self.logger.error(f"❌ PDF Export 모듈을 찾을 수 없습니다: {e}")
            self.logger.error("💡 pdf_export 패키지가 설치되어 있는지 확인하세요.")
            return None
            
        except Exception as e:
            import traceback
            self.logger.error("❌ PDF 생성 중 예상치 못한 오류 발생")
            self.logger.error(f"🔍 오류 내용: {e}")
            self.logger.error("🔍 상세 스택 트레이스:")
            self.logger.error(traceback.format_exc())
            return None

    ### pdf 생성 테스트용 코드
    def _test_pdf_create(self, backend_client: BackendClient):
        self.logger.info("PDF 생성 테스트 시작")
        task_id = "test_task_id"
        job_id = "test_job_id"
        
        self.logger.debug(f"Loading job info for task_id: {task_id}, job_id: {job_id}")
        job_info = backend_client.load_job_info(task_id, job_id)
        
        user_id = job_info.get("user_id", "system")
        self.logger.debug(f"Creating test report for user_id: {user_id}")
        report_create_data = ReportCreate(**sample_create_data)
        report_response = backend_client.save_report(report_create_data, user_id, job_id)

        self.logger.debug("Generating PDF report for test")
        self._generate_pdf_report(report_response)
        self.logger.info("PDF 생성 테스트 완료")