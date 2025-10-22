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
        self._generate_pdf_report(report_saved)

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

        def _generate_pdf_report(self, data: dict[str, Any]):
            """
            보고서 데이터를 PDF로 변환하고 S3에 업로드
            
            Args:
                data: save_report()에서 반환된 보고서 전체 데이터
                    - report: 보고서 메타데이터 (id, pc_id, created_at 등)
                    - details: 보고서 섹션 리스트
            
            Returns:
                str: S3 업로드된 PDF URL (성공시), None (실패시)
            """
            try:
                # PDF Export 모듈 임포트
                from pdf_export import PDFReportExporter
                
                print("\n" + "=" * 60)
                print("📄 보고서 PDF 변환 프로세스 시작")
                print("=" * 60)
                
                # PDFReportExporter 인스턴스 생성
                exporter = PDFReportExporter()
                
                # 커스텀 파일명 생성
                report_id = data.get('report', {}).get('id', 'unknown')
                pc_id = data.get('report', {}).get('pc_id', 'unknown')
                custom_filename = f"forensic_report_{pc_id}_{report_id[:8]}"
                
                print(f"📋 보고서 ID: {report_id}")
                print(f"💻 PC ID: {pc_id}")
                print(f"📝 파일명: {custom_filename}.pdf")
                
                # PDF 생성 및 S3 업로드
                pdf_url = exporter.generate_and_upload(
                    report_data=data,
                    delete_local=True,  # 임시 파일 자동 삭제
                    custom_filename=custom_filename
                )
                
                if pdf_url:
                    print("\n" + "=" * 60)
                    print("✅ 보고서 PDF 처리 완료!")
                    print(f"🌐 PDF URL: {pdf_url}")
                    print("=" * 60 + "\n")
                    return pdf_url
                else:
                    print("\n" + "=" * 60)
                    print("❌ PDF 생성 또는 업로드 실패")
                    print("=" * 60 + "\n")
                    return None
                    
            except ImportError as e:
                print(f"❌ PDF Export 모듈을 찾을 수 없습니다: {e}")
                print("💡 pdf_export 패키지가 설치되어 있는지 확인하세요.")
                return None
                
            except Exception as e:
                print("\n" + "=" * 60)
                print(f"❌ PDF 생성 중 예상치 못한 오류 발생")
                print(f"🔍 오류 내용: {e}")
                print("=" * 60 + "\n")
                return None