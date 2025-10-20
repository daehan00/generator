import json
import logging
from typing import Any, Dict
from unknown_data import Category, ResultDataFrames, ResultDataFrame

from Analyzer import BackendClient, Analyzer



logger = logging.getLogger(__name__)


class TestAnalyzer(Analyzer):
    """테스트용 Analyzer - 개발이 필요한 메서드들을 오버라이딩"""
    
    def __init__(self, backend_client: BackendClient) -> None:
        super().__init__(backend_client)
    
    
    def run_final_test(self, task_id: str) -> Dict[str, Any]:
        """테스트 분석 실행 및 결과 반환"""
        logger.info(f"🚀 [TEST] Starting final test for task: {task_id}")
        job_id = "test_job_id"

        try:
            # 기본 분석 실행
            self.analyze(task_id, job_id)
            
            # 테스트 결과 요약
            test_summary = self.backend_client.get_test_summary()
            
            logger.info(f"📊 [TEST] Summary: {json.dumps(test_summary, indent=4)}")
            logger.info(f"🎉 [TEST] Test analysis completed successfully!")
            
            return {
                "status": "success",
                "task_id": task_id,
                "job_id": job_id,
                "summary": test_summary
            }
            
        except Exception as e:
            logger.error(f"❌ [TEST] Test analysis failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "task_id": task_id,
                "job_id": job_id,
                "error": str(e)
            }
    
    def run_filter_test(self, task_id: str, category: Category | None = None) -> Dict[str, Any]:
        logger.info(f"🚀 [TEST] Starting filtering test for task: {task_id}")
        job_id = "test_job_id"

        try:
            self.task_id = task_id
            self.job_id = job_id
            
            if category:
                self._filter_and_save_artifacts(category)
            else:
                for c in Category:
                    self._filter_and_save_artifacts(c)
                
            # 테스트 결과 요약
            test_summary = self.backend_client.get_test_summary()
            
            logger.info(f"📊 [TEST] Summary: {json.dumps(test_summary, indent=2)}")
            logger.info(f"🎉 [TEST] Test analysis completed successfully!")
            return {
                "status": "success",
                "task_id": task_id,
                "job_id": job_id,
                "summary": test_summary
            }
        except Exception as e:
            logger.error(f"❌ [TEST] Test analysis failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "task_id": task_id,
                "job_id": job_id,
                "error": str(e)
            }
        


class DevAnalyzer(TestAnalyzer):
    def __init__(self, backend_client: BackendClient) -> None:
        super().__init__(backend_client)
    