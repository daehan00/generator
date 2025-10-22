import logging
import uuid
from typing import Any, Optional, List, Dict
import datetime
from unknown_data.test import TestHelper
from unknown_data.loader.base import Config_db
from common.models import ReportCreate, ScenarioCreate

logger = logging.getLogger(__name__)


class TestBackendClient:
    def __init__(self, settings: Any = None):
        """
        테스트용 BackendClient 초기화.
        settings 객체는 필요하지 않지만, 기존 코드와의 호환성을 위해 인자로 받습니다.
        """
        self.set_database_settings()
        logger.info("Initialized TestBackendClient")

    def set_database_settings(self) -> None:
        """ 헬퍼는 현재 테스트용으로 적용됨. 배포용으로 변경해야 함. """
        db_config = Config_db(
            dbms="postgresql",
            username="forensic_agent",
            password="0814",
            ip="13.124.25.47",
            port=5432,
            database_name="forensic_agent"
        )
        
        self.helper = TestHelper(db_config)

    def send_completion_callback(
        self, task_id: str, success: bool = True, error_message: Optional[str] = None
    ) -> bool:
        """
        작업 완료/실패 콜백을 시뮬레이션합니다.
        성공 시 항상 True를 반환합니다.
        """
        logger.info(f"[Test] send_completion_callback called for task {task_id} with success={success}")
        if not success and not error_message:
            logger.error("[Test] error_message is required when success is False.")
            return False
        return True

    def load_job_info(self, task_id: str, job_id: str) -> dict:
        """
        작업 정보 로드를 시뮬레이션합니다.
        """
        logger.info(f"[Test] load_job_info called for task {task_id}, job {job_id}")
        response =  {
            "success": True,
            "data": {
                "job_id": "73c94dcd-d1a1-41c4-9636-dd24816dfd9a",
                "job_type": "full_scan",
                "job_status": "completed",
                "job_started_at": "2025-09-23T04:55:43",
                "job_ended_at": "2025-09-23T04:56:20",
                "pc_info": {
                    "pc_id": "MAC_00-0C-29-EB-B3-7B",
                    "pc_name": "DESKTOP-4L4O6MI",
                    "status": None,
                    "os": "Windows 11 Version 24H2",
                    "ip": "192.168.74.135",
                    "pc_username": "이정호",
                    "pc_userrank": "주임",
                    "pc_userbusinessnum": "2025031689",
                    "pc_userdepartment": "교육운영팀",
                    "pc_usercompanyname": "한국정보보호산업협회"
                },
                "tasks": [
                    {
                        "id": "218df7d9-dd19-4777-bdd8-0863d8d776e6",
                        "type": "generate",
                        "status": "running",
                        "started_at": "2025-09-23T04:56:19",
                        "ended_at": "",
                        "retry_count": 0,
                        "error_message": None
                    },
                    {
                        "id": "21c44cb1-938e-4273-827d-feb6d4d69e39",
                        "type": "analyze",
                        "status": "completed",
                        "started_at": "2025-09-23T04:55:59",
                        "ended_at": "2025-09-23T04:56:18",
                        "retry_count": 0,
                        "error_message": None
                    },
                    {
                        "id": "2e720078-381d-433c-8e9b-43ab7b317e6c",
                        "type": "collect",
                        "status": "completed",
                        "started_at": "2025-09-23T04:55:44",
                        "ended_at": "2025-09-23T04:55:55",
                        "retry_count": 0,
                        "error_message": None
                    }
                ],
                "data_collection_period": {
                    "started_at": "2025-09-23T04:55:44",
                    "ended_at": "2025-09-23T04:55:55"
                },
                "analysis_schedule": {
                    "analyze_started_at": "2025-09-23T04:55:59",
                    "generate_ended_at": "2025-09-23T04:56:19"
                },
                "user_id": "e133aded-a617-4fc8-83f0-6cd05cd4464b",
                "created_at": "2025-09-23T04:55:42",
                "updated_at": "2025-09-23T04:56:19"
            },
            "message": "Report generation info retrieved successfully"
        }
        return response["data"]

    def load_artifacts(self, task_id: str, job_id: str) -> List[dict]:
        """
        아티팩트 로드를 시뮬레이션합니다.
        항상 빈 리스트를 반환합니다.
        """
        logger.info(f"[Test] load_artifacts called for task {task_id}, job {job_id}")
        example_artifacts = [
            {
                "artifact_type": "usb_mobile",
                "source": "USB Mobile Device - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "device_id": "USB\\VID_04E8&PID_6860\\SM_G975F",
                    "vendor_id": "04E8",
                    "product_id": "6860",
                    "device_name": "Samsung Galaxy S10",
                    "drive_letter": "F:",
                    "serial_number": "SM_G975F",
                    "last_connection": "2025-09-23T04:56:14.703294",
                    "first_connection": "2025-09-23T04:56:14.703294"
                },
                "summary": "Mobile device USB connection detected",
                "collected_at": "2025-09-23T04:56:15",
                "hash_value": "fd0623a278f429bcc5a5ab6a77ae849a",
                "id": "2beeda5a-6953-424f-90aa-1688bec3d88a"
            },
            {
                "artifact_type": "usb_device",
                "source": "USB Device Registry - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "device_id": "USB\\VID_1234&PID_5678\\9876543210",
                    "vendor_id": "1234",
                    "product_id": "5678",
                    "device_name": "USB Storage Device",
                    "drive_letter": "E:",
                    "serial_number": "9876543210",
                    "last_connection": "2025-09-23T04:56:14.703294",
                    "first_connection": "2025-09-23T04:56:14.703294"
                },
                "summary": "USB storage device connection detected",
                "collected_at": "2025-09-23T04:56:15",
                "hash_value": "facb558310b10663bb369f79f6be8f24",
                "id": "d2694f9c-a4c6-4326-b25f-4e23485a726c"
            },
            {
                "artifact_type": "prefetch_file",
                "source": "Windows Prefetch - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "file_name": "MALICIOUS_APP.EXE-A1B2C3D4.pf",
                    "file_size": 15420,
                    "run_count": 3,
                    "last_run_time": "2025-09-23T04:56:11.626404",
                    "prefetch_hash": "A1B2C3D4",
                    "executable_name": "malicious_app.exe"
                },
                "summary": "Execution of potentially malicious application detected",
                "collected_at": "2025-09-23T04:56:12",
                "hash_value": "34b8412a762bc17934cbc9afcfdb4389",
                "id": "f2e5010f-ded1-4614-9236-6bcf3c840738"
            },
            {
                "artifact_type": "prefetch_system",
                "source": "System Tool Prefetch - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "file_name": "POWERSHELL.EXE-B5C6D7E8.pf",
                    "file_size": 22840,
                    "run_count": 15,
                    "last_run_time": "2025-09-23T04:56:11.626404",
                    "prefetch_hash": "B5C6D7E8",
                    "executable_name": "powershell.exe"
                },
                "summary": "Frequent PowerShell execution detected - potential misuse",
                "collected_at": "2025-09-23T04:56:12",
                "hash_value": "ce5cc73cbd0dee5f3837aff36bb90f05",
                "id": "9ea69520-432f-47ef-bff9-5d5f9d762925"
            },
            {
                "artifact_type": "messenger_chat",
                "source": "Messenger Analysis - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "sender": "+1234567890",
                    "message": "Check this suspicious link: http://malicious-site.com",
                    "platform": "WhatsApp",
                    "receiver": "+0987654321",
                    "timestamp": "2025-09-23T04:56:08.539854",
                    "attachment": None,
                    "message_type": "text"
                },
                "summary": "Suspicious message with potential malicious link detected",
                "collected_at": "2025-09-23T04:56:09",
                "hash_value": "085ac00bf08396e4e0de617ee94414e3",
                "id": "4bd28bdc-eb49-4b16-8d0d-3d7c3ef1a801"
            },
            {
                "artifact_type": "messenger_file",
                "source": "Telegram File Transfer - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "sender": "@suspicious_user",
                    "message": "Confidential file attached",
                    "platform": "Telegram",
                    "receiver": "@target_user",
                    "timestamp": "2025-09-23T04:56:08.539854",
                    "attachment": {
                        "file_name": "confidential_data.zip",
                        "file_size": 5242880,
                        "file_type": "application/zip"
                    },
                    "message_type": "file"
                },
                "summary": "File transfer through Telegram detected - potential data exfiltration",
                "collected_at": "2025-09-23T04:56:09",
                "hash_value": "76751f8e476baa9688ccd27d3018ef6a",
                "id": "b8306561-b42c-4e2a-82e9-9e76aa6c21e7"
            },
            {
                "artifact_type": "lnk_network",
                "source": "LNK Network Share - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "arguments": "",
                    "file_path": "C:\\Users\\User\\Desktop\\network_share.lnk",
                    "target_path": "\\\\192.168.1.100\\shared\\data",
                    "creation_time": "2025-09-23T04:56:05.454914",
                    "last_access_time": "2025-09-23T04:56:05.454914",
                    "working_directory": "C:\\Users\\User\\Desktop"
                },
                "summary": "Network share connection through LNK file detected",
                "collected_at": "2025-09-23T04:56:05",
                "hash_value": "0ec419fd5881ec9c073d86eca9e4ef3e",
                "id": "85d1951d-596b-4dda-bc81-c2e34ae32267"
            },
            {
                "artifact_type": "lnk_file",
                "source": "LNK File Analysis - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "arguments": "/c powershell -ExecutionPolicy Bypass -File malicious.ps1",
                    "file_path": "C:\\Users\\User\\Desktop\\suspicious_app.lnk",
                    "target_path": "C:\\Windows\\System32\\cmd.exe",
                    "creation_time": "2025-09-23T04:56:05.454914",
                    "last_access_time": "2025-09-23T04:56:05.454914",
                    "working_directory": "C:\\Temp"
                },
                "summary": "Suspicious LNK file with potentially malicious command execution",
                "collected_at": "2025-09-23T04:56:05",
                "hash_value": "a931cb2b7952e6036a4aed39ca5bff79",
                "id": "060bc354-c81d-4a20-8461-7d48e1b5d47e"
            },
            {
                "artifact_type": "deleted_log",
                "source": "Log Recovery Scan - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "md5_hash": "e3b0c44298fc1c149afbf4c8996fb924",
                    "file_size": 1024000,
                    "file_type": "application/log",
                    "deletion_time": "2025-09-23T04:56:02.374196",
                    "original_path": "C:\\Windows\\System32\\LogFiles\\security.log",
                    "recovery_status": "fully_recoverable"
                },
                "summary": "Deleted system log file recovered - potential evidence tampering",
                "collected_at": "2025-09-23T04:56:02",
                "hash_value": "199541ff126c5d6edef6b599c4543d27",
                "id": "f4042a24-734c-4859-8bd9-3d7484fb0610"
            },
            {
                "artifact_type": "deleted_file",
                "source": "File Recovery Scan - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
                    "file_size": 2048,
                    "file_type": "text/plain",
                    "deletion_time": "2025-09-23T04:56:02.374196",
                    "original_path": "C:\\Users\\User\\Documents\\sensitive_data.txt",
                    "recovery_status": "partially_recoverable"
                },
                "summary": "Deleted sensitive file detected and partially recovered",
                "collected_at": "2025-09-23T04:56:02",
                "hash_value": "3aa67f4d11f8f85f98226746e3e2a549",
                "id": "f6edd522-c44e-4d3d-b0be-6e1798b06548"
            },
            {
                "artifact_type": "browser_history",
                "source": "Browser History - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "url": "https://example.com/suspicious-site",
                    "title": "Suspicious Website",
                    "browser": "Chrome",
                    "visit_count": 5,
                    "last_visit_time": "2025-09-23T04:55:59.134118"
                },
                "summary": "Suspicious website visit detected in browser history",
                "collected_at": "2025-09-23T04:55:59",
                "hash_value": "59e81693e74629c582f5f6b8d78e2a43",
                "id": "b6daddd7-565c-49b9-9120-c16f20afa7d3"
            },
            {
                "artifact_type": "browser_download",
                "source": "Browser Downloads - Task 21c44cb1-938e-4273-827d-feb6d4d69e39",
                "data": {
                    "file_name": "malicious_file.exe",
                    "file_path": "C:\\Users\\User\\Downloads\\malicious_file.exe",
                    "file_size": 1024000,
                    "download_url": "https://malicious-site.com/file.exe",
                    "download_time": "2025-09-23T04:55:59.134118"
                },
                "summary": "Potentially malicious file download detected",
                "collected_at": "2025-09-23T04:55:59",
                "hash_value": "84f2238db707d0c56036999805362d5b",
                "id": "dfb3a4c2-9ae7-4932-8a7e-f688f30f4cda"
            }
        ]

        return example_artifacts

    def save_scenario(self, scenario: ScenarioCreate) -> bool:
        """
        시나리오 저장을 시뮬레이션하고 데이터를 검증합니다.
        """
        logger.info(f"[Test] save_scenario called for task {scenario.task_id}")
        logger.debug(scenario.model_dump())
        try:
            assert scenario.task_id, "task_id is required"
            assert scenario.job_id, "job_id is required"
            assert scenario.name, "name is required"
            assert scenario.steps, "steps are required"
            assert isinstance(scenario.steps, list), "steps must be a list"
            logger.info(f"[Test] Scenario for task {scenario.task_id} passed validation.")
            return True
        except AssertionError as e:
            logger.error(f"[Test] Scenario validation failed: {e}")
            return False

    def save_report(self, report: ReportCreate, user_id: str, job_id: str) -> Dict[str, Any]:
        """
        리포트 저장을 시뮬레이션하고 API와 유사한 형식으로 응답합니다.
        """
        logger.info(f"[Test] save_report called for task {report.task_id}")
        logger.debug(report.model_dump())
        try:
            # 입력값 검증
            assert report.task_id, "task_id is required"
            assert report.pc_id, "pc_id is required"
            assert report.title, "title is required"
            assert report.details, "details are required"
            assert isinstance(report.details, list), "details must be a list"
            assert user_id, "user_id is required"
            assert job_id, "job_id is required"
            
            logger.info(f"[Test] Report for task {report.task_id} passed validation.")
            
            # API 응답 형식으로 데이터 생성
            report_id = str(uuid.uuid4())
            created_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            
            response = {
                "report": {
                    "id": report_id,
                    "title": report.title,
                    "summary": report.summary or "",
                    "pc_id": report.pc_id,
                    "created_at": created_at,
                    "created_by": user_id,
                    "link": f"/reports/{report_id}"
                },
                "details": [
                    {
                        "id": str(uuid.uuid4()),
                        "report_id": report_id,
                        "section_type": detail.section_type.value,
                        "content": detail.content or "",
                        "order_no": detail.order_no if detail.order_no is not None else idx,
                        "created_at": created_at
                    }
                    for idx, detail in enumerate(report.details)
                ]
            }
            
            logger.info(f"[Test] Report response generated successfully with id {report_id}")
            logger.debug(response)
            return response
            
        except AssertionError as e:
            logger.error(f"[Test] Report validation failed: {e}")
            raise ValueError(f"Report validation failed: {e}")
        except Exception as e:
            logger.error(f"[Test] Error generating report response: {e}")
            raise

    def link_scenario_to_report_details(self, job_id: str, task_id: str, report_detail_id: str):
        """
        시나리오와 리포트 상세 정보 연결을 시뮬레이션합니다.
        """
        logger.info(f"[Test] link_scenario_to_report_details called for job {job_id}, task {task_id}")
        
        assert job_id, "job_id is required"
        assert task_id, "task_id is required"
        assert report_detail_id, "report_detail_id is required"
        return True

    def close(self):
        """
        세션 닫기를 시뮬레이션합니다.
        """
        logger.info("[Test] BackendClient closed.")
