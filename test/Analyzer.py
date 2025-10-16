from dataclasses import dataclass
import logging
from unknown_data import Category, ResultDataFrames
from unknown_data.test import TestHelper
from unknown_data.loader.base import Config_db
import gc  # 가비지 컬렉션을 위한 모듈
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
import enum
import uuid

logger = logging.getLogger(__name__)



class BackendClient:
    """테스트용 BackendClient - 실제 전송 대신 데이터 검증 및 출력"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"BackendClient")
        self.sent_artifacts: List[Dict[str, Any]] = []
        self.sent_analysis_results: List[Dict[str, Any]] = []
        self.artifact_id_counter = 1
        self.analysis_result_id_counter = 1
    
    def send_artifact_datas(self, artifacts: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """아티팩트 데이터 검증 및 테스트 결과 반환"""
        self.logger.info(f"🧪 [TEST] Received {len(artifacts)} artifacts for validation")
        
        # 데이터 검증
        created_artifacts = []
        for i, artifact in enumerate(artifacts):
            # 필수 필드 검증
            required_fields = ['data', 'collected_at', 'artifact_type']
            missing_fields = [field for field in required_fields if field not in artifact]
            
            if missing_fields:
                self.logger.error(f"❌ Artifact {i}: Missing required fields: {missing_fields}")
                return None
            
            # 데이터 타입 검증
            if not isinstance(artifact['data'], dict):
                self.logger.error(f"❌ Artifact {i}: 'data' field must be a dictionary")
                return None
            
            # 테스트용 ID 생성 및 완전한 아티팩트 객체 생성
            created_artifact = {
                "id": str(uuid.uuid4()),
                **artifact,
                # "created_at": datetime.now(timezone.utc).isoformat(),
                "status": ""
            }
            created_artifacts.append(created_artifact)
            self.artifact_id_counter += 1
            
        self.sent_artifacts.extend(created_artifacts)
        self.logger.info(f"✅ [TEST] Successfully validated and stored {len(created_artifacts)} artifacts")
        self.logger.info(f"🔢 [TEST] Total artifacts stored: {len(self.sent_artifacts)}")
        
        return created_artifacts
    
    def send_analysis_result_with_artifacts(self, analysis_result_data: Dict[str, Any]) -> Optional[str]:
        """분석 결과 데이터 검증 및 테스트 결과 반환"""
        self.logger.info(f"🧪 [TEST] Received analysis result for behavior: {analysis_result_data.get('behavior')}")
        
        # 필수 필드 검증
        required_fields = ['job_id', 'task_id', 'behavior', 'analysis_summary', 'risk_level', 'artifact_ids']
        missing_fields = [field for field in required_fields if field not in analysis_result_data]
        
        if missing_fields:
            self.logger.error(f"❌ Analysis result missing required fields: {missing_fields}")
            return None
        
        # 위험도 검증
        valid_risk_levels = [level.value for level in RiskLevel]
        if analysis_result_data['risk_level'] not in valid_risk_levels and analysis_result_data['risk_level']:
            self.logger.error(f"❌ Invalid risk level: {analysis_result_data['risk_level']}")
            return None
        
        # 테스트용 ID 생성
        result_id = f"test_analysis_{self.analysis_result_id_counter}"
        self.analysis_result_id_counter += 1
        
        # 결과 저장
        stored_result = {
            "id": result_id,
            **analysis_result_data,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.sent_analysis_results.append(stored_result)
        
        # 결과 출력
        self.logger.info(f"📋 [TEST] Analysis Result Details:")
        self.logger.info(f"  - Behavior: {analysis_result_data['behavior']}")
        self.logger.info(f"  - Risk Level: {analysis_result_data['risk_level']}")
        self.logger.info(f"  - Summary: {analysis_result_data['analysis_summary']}")
        self.logger.info(f"  - Artifact Count: {len(analysis_result_data['artifact_ids'])}")
        
        self.logger.info(f"✅ [TEST] Successfully stored analysis result with ID: {result_id}")
        return result_id
    
    def get_test_summary(self) -> Dict[str, Any]:
        """테스트 실행 결과 요약"""
        return {
            "total_artifacts": len(self.sent_artifacts),
            "total_analysis_results": len(self.sent_analysis_results),
            "artifacts_by_type": self._count_by_field(self.sent_artifacts, 'artifact_type'),
            "artifacts_by_behavior": self._count_by_field_behavior(self.sent_analysis_results, 'behavior'),
            "artifacts_by_risk_level": self._count_by_field(self.sent_analysis_results, 'risk_level')
        }
    
    def _count_by_field(self, items: List[Dict], field: str) -> Dict[str, int]:
        """필드별 카운트"""
        counts = {}
        for item in items:
            value = item.get(field, 'unknown')
            counts[value] = counts.get(value, 0) + 1
        return counts

    def _count_by_field_behavior(self, items: List[Dict], field: str) -> Dict[str, int]:
        """필드별 카운트"""
        counts = {}
        for item in items:
            value = item.get(field, 'unknown')
            counts[value] = len(item["artifact_ids"])
        return counts



@dataclass
class Artifact:
    data: Dict[str, Any]
    collected_at: datetime
    artifact_type: Optional[str] = None
    source: Optional[str] = None
    summary: Optional[str] = None
    hash_value: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Artifact 객체를 딕셔너리로 변환"""
        return {
            'data': self.data,
            'collected_at': self.collected_at.isoformat() if isinstance(self.collected_at, datetime) else self.collected_at,
            'artifact_type': self.artifact_type,
            'source': self.source,
            'summary': self.summary,
            'hash_value': self.hash_value
        }


class RiskLevel(str, enum.Enum):
    normal = "normal"
    suspicious = "suspicious"
    dangerous = "dangerous"


class BehaviorType(str, enum.Enum):
    acquisition = "acquisition"
    forgery = "forgery"
    upload = "upload"
    deletion = "deletion"
    etc = "etc"

FILE_COLUMN_MAP = {
    # 브라우저
    "binary": {"keyword": "file_neme", "time": "timestamp"},
    "browser_collected_files": {"keyword": "file_neme", "time": "timestamp"},
    "browser_discovered_profiles": {"keyword": "base_path", "time": None},
    "Chrome.keyword_search_terms": {"keyword": "term", "time": None},
    "Edge.keyword_search_terms": {"keyword": "term", "time": None},
    "Chrome_keyword": {"keyword": "keyword", "time": "last_visited"},
    "Edge_keyword": {"keyword": "keyword", "time": "last_visited"},
    "Chrome.urls": {"keyword": "title", "time": "last_visit_time"},
    "Edge.urls": {"keyword": "title", "time": "last_visit_time"},
    "Chrome.visits": {"keyword": "url", "time": "visit_time"},
    "Edge.visits": {"keyword": "url", "time": "visit_time"},
    "Chrome.visited_links": {"keyword": "link_url_id", "time": None},
    "Edge.visited_links": {"keyword": "link_url_id", "time": None},
    "Chrome.autofill": {"keyword": "value", "time": "date_created"},
    "Edge.autofill": {"keyword": "value", "time": "date_created"},
    "Chrome.addresses": {"keyword": "guid", "time": "use_date"},
    "Edge.addresses": {"keyword": "guid", "time": "use_date"},
    "Chrome.autofill_sync_metadata": {"keyword": "storage_key", "time": None},
    "Edge.autofill_sync_metadata": {"keyword": "storage_key", "time": None},
    "Chrome.downloads": {"keyword": "target_path", "time": "end_time"},
    "Edge.downloads": {"keyword": "target_path", "time": "end_time"},
    "Chrome.downloads_url_chains": {"keyword": "url", "time": None},
    "Edge.downloads_url_chains": {"keyword": "url", "time": None},
    "Chrome.logins": {"keyword": "signon_realm", "time": "date_last_used"},
    "Edge.logins": {"keyword": "signon_realm", "time": "date_last_used"},
    
    # 휴지통
    "data_sources": {"keyword": "has_mft_data", "time": None},
    "mft_deleted_files": {"keyword": "file_name", "time": "deleted_time"},
    "recycle_bin_files": {"keyword": "original_file_name", "time": "deleted_time"},
    "statistics": {"keyword": "total_deleted_files", "time": None},

    # LNK
    "lnk_files": {"keyword": "file_name", "time": "target_info__target_times__access"},
    
    # 메신저
    "Discord.files": {"keyword": "file_name", "time": "last_modified"},
    "KakaoTalk.files": {"keyword": "file_name", "time": "last_modified"},
    
    # 프리패치
    "prefetch_files": {"keyword": "file_name", "time": "last_run_times_1"},
    
    # USB
    "usb_devices": {"keyword": "setupapi_info__user_account", "time": "setupapi_info__last_connection_time"}
}

class Analyzer:
    def __init__(self, backend_client: BackendClient) -> None:
        self.task_id: str = ''
        self.backend_client = backend_client    
        self.created_artifacts: List[Dict[str, Any]] = []
        self.set_database_settings()

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

    def analyze(self, task_id: str, job_id:str):
        self.task_id = task_id
        self.job_id = job_id

        try:
            for category in Category:
                logger.debug(f"🔄 Processing category: {category.name}")
                
                self._filter_and_save_artifacts(category)
            
            logger.info(f"Artifact processing completed successfully for task: {task_id}")

            self._make_and_save_analyze_results()

            logger.info(f"Analysis process completed successfully for task: {task_id}")

        except Exception as e:
            logger.error(f"❌ Analysis failed for task {task_id}: {e}", exc_info=True)
            raise

    def _filter_and_save_artifacts(self, category: Category):
        """ 원본 아티팩트들에 대한 처리 메서드"""
        try:
            # 1. 원본 아티팩트 데이터 로드(데이터 타입: ResultDataFrames)
            df_results = self._load_data(category)
            
            # 2. 아티팩트 데이터 필터링 처리(데이터 타입: ResultDataFrames)
            # dataframes_dict가 None인 경우 로그만 출력하고 빈 데이터로 처리
            if df_results is None:
                logger.error(f"No data found for category: {category.name}")
                return

            logger.debug(f"Filtering data for category: {category.name}")
            filtered_data = self._filter_data(category, df_results)
            logger.debug(f"Filtering data success: {category.name}")

            if filtered_data.data is None:
                logger.info(f"No data is found to analyze for category: {category.name}")
                return
            
            # 3. ResultDataFrames에서 백엔드로 전송하기 위한 형태로 가공
            artifacts_data = self._filtered_data_to_artifacts_data(filtered_data)
            
            # 4. 가공된 데이터 백엔드로 전송
            logger.debug(f"Sending data to backend for category: {category.name}")
            success = self._send_data_to_backend(category, artifacts_data)
            
            # 메모리 해제: 분석 결과 삭제
            del filtered_data
            del artifacts_data
            # df_results 해제
            if df_results is not None:
                del df_results
            gc.collect()

            if not success:
                raise
        except Exception as e:
            logger.error(f"❌ {category.name} Analysis failed for task {self.task_id}: {e}", exc_info=True)
            raise
    
    def _load_data(self, category: Category) -> ResultDataFrames:
        """카테고리별 데이터 로드 - helper를 이용하여 데이터베이스에서 데이터 로드"""
        try:
            logger.debug(f"Starting data load for category: {category.name}")
            
            # helper를 사용하여 데이터 로드 및 인코딩 처리
            df_results = self.helper.get_encoded_results(self.task_id, category)
            
            if not df_results:
                logger.error(f"No dataframes found for category {category.name} and task {self.task_id}")
                raise ValueError(f"No data available for category {category.name} and task {self.task_id}")
            
            logger.debug(f"Successfully loaded {len(df_results.data)} dataframes for category: {category.name}")
            return df_results
            
        except Exception as e:
            logger.error(f"Failed to load data for category {category.name}: {e}", exc_info=True)
            raise
    
    def _filter_data(self, category: Category, df_results: ResultDataFrames) -> ResultDataFrames:
        """
        <개발이 필요한 메서드>
        수많은 데이터 중 필요없는 데이터를 버리고 필터링하는 과정
        임시로 작성해놓은 메서드이다.
        """
        # for result in df_results.data:
        #     result.data = result.data.head(5) # 현재는 데이터프레임별로 5개씩만 가져와서 저장하는 테스트 코드.
        
        return ResultDataFrames()
    
    def _minha_hamsu(self, artifact_type: str):
        data = FILE_COLUMN_MAP.get(artifact_type, {})
        return data.get("keyword", ""), data.get("time", "")


    def _filtered_data_to_artifacts_data(self, filtered_data: ResultDataFrames) -> List[Dict[str, Any]]:
        """ 처리한 데이터를 백엔드로 전송하기 위한 형태로 변환 """
        artifacts_dict_list = []
        
        for data in filtered_data.data:
            artifacts_json = data.data.to_dict('records')
            data_name = data.name if hasattr(data, 'name') else 'unknown'
            
            # 공통 메타데이터 (반복되는 부분을 미리 계산)
            artifact_type = f"{data_name}_data"

            source_key, time_key = self._minha_hamsu(data_name)
            
            for artifact_data in artifacts_json:
                # 타입 안전성을 위한 캐스팅
                artifact_data_dict: Dict[str, Any] = {str(k): v for k, v in artifact_data.items()}
                
                # 직접 딕셔너리 생성 (객체 생성 오버헤드 없음)
                artifact_dict = {
                    'data': artifact_data_dict,
                    # 'collected_at': current_time_iso,
                    'artifact_type': artifact_type,
                    'source': artifact_data_dict.get(source_key, None),
                    'collected_at': artifact_data_dict.get(time_key, None),
                }
                
                artifacts_dict_list.append(artifact_dict)

        return artifacts_dict_list
    
    def _send_data_to_backend(self, category: Category, artifacts_data: List[Dict[str, Any]]) -> bool:
        """ 변환된 데이터를 받아 백엔드로 전송 """

        logger.debug(f"📦 Sending {len(artifacts_data)} filtered artifacts for category: {category.name}")
        
        # 이미 딕셔너리 형태이므로 바로 전송
        created_artifacts = self.backend_client.send_artifact_datas(artifacts_data)
        
        if created_artifacts is not None:
            # 생성된 완전한 아티팩트 객체들을 저장
            self.created_artifacts.extend(created_artifacts)
            
            logger.debug(f"✅ Successfully sent {len(artifacts_data)} artifacts for category: {category.name}")
            logger.debug(f"📋 Stored {len(created_artifacts)} complete artifact objects")
            logger.debug(f"🔢 Total artifacts stored so far: {len(self.created_artifacts)}")
            return True
        else:
            logger.error(f"❌ Failed to send artifacts for category: {category.name}")
            return False

    def _make_and_save_analyze_results(self):
        """ 행위에 따른 분류결과를 저장 """
        self.analyze_results = {
            behavior: {
                "job_id": self.job_id,
                "task_id": self.task_id,
                "behavior": behavior.name,
                "analysis_summary": "",
                "risk_level": "",
                "artifact_ids": []
            } for behavior in BehaviorType
        }

        # 분석 결과 생성
        self._generate_analysis_result()

        # analyze_results 순회하면서 저장
        failed_behaviors = []
        for behavior in self.analyze_results.keys():
            # 모든 behavior에 대해 백엔드로 제출
            result = self.analyze_results[behavior]
            analysis_result_id = self.backend_client.send_analysis_result_with_artifacts(result)
            
            if analysis_result_id is None:
                failed_behaviors.append(behavior)
                logger.error(f"Failed to save analysis result for behavior: {behavior}")
            else:
                logger.debug(f"Successfully saved analysis result for behavior: {behavior} (ID: {analysis_result_id})")
        
        if failed_behaviors:
            raise RuntimeError(f"Failed to save analysis results for behaviors: {[b.name for b in failed_behaviors]}")

    def _generate_analysis_result(self):
        """
        <개발이 필요한 메서드>
        self.created_artifacts를 활용하여 분류결과를 생성함.
        결과는 self.analyze_results에 업데이트할 것.
        """
        pass