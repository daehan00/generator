from test.testAnalyzer import BackendClient
from typing import List
from test.DevAnalyzer import DevAnalyzer

import logging
import sys


# 기존 핸들러들 제거 (중복 방지)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# 로깅 설정 추가 (콘솔 + 파일)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # 노트북 출력으로 로그 표시
    ]
)

# 루트 로거 레벨 설정
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)




def test_data_loader_v1(task_id: str, limit: int = 0, months: int = 12) -> List:
    backend_client = BackendClient()
    analyzer = DevAnalyzer(backend_client, months)

    analyzer.run_filter_test(task_id)

    if limit > 0:
        return analyzer.created_artifacts[:limit]
    return analyzer.created_artifacts

if __name__ == "__main__":
    # print(len(test_data_loader_v1("session-20251002-052932-151e52e9")))
    print(len(test_data_loader_v1("session-20250930-060607-59984faf")))
