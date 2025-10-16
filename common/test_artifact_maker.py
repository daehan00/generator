from unknown_data.test import TestHelper
from unknown_data import Config_db, Category
from dotenv import load_dotenv
import os

load_dotenv("../.env")

db_config = Config_db(
    dbms=os.getenv("dbms", ""),
    username=os.getenv("username", ""),
    password=os.getenv("password", ""),
    ip=os.getenv("ip", ""),
    port=int(os.getenv("port", 5432)),
    database_name=os.getenv("database_name", "")
)



import datetime
import uuid

def category_make_test_artifacts(task_id: str, category: Category, artifact_list: list, helper: TestHelper, limit: int) -> int:
    data = helper.get_encoded_results(task_id, category)

    white_list = ["urls", "visits", "visited_links", "keywords", "keywork_search_terms", "autofill", "downloads", "download_url_chains", "logins"]
    white_list_set = set()
    for i in white_list:
        white_list_set.update(("chrome."+i, "edge."+i))

    cnt = 0
    for d in data.data:
        artifact_type = d.name.lower()

        if category == Category.BROWSER and artifact_type not in white_list_set:
            continue

        collected_at = datetime.datetime.now(tz=datetime.UTC)
        collected_at_str = collected_at.isoformat()
        
        # to_dict('records')를 사용하여 한 번에 모든 행을 딕셔너리 리스트로 변환 (훨씬 빠름!)
        if limit > 0:
            records = d.data.head(limit).to_dict('records')
        else:
            records = d.data.to_dict('records')
        
        # 리스트 컴프리헨션으로 artifacts 생성 (for 루프보다 빠름)
        artifacts = [
            {
                "id": str(uuid.uuid4()),
                "artifact_type": artifact_type,
                "source": None,
                "data": record,
                "collected_at": collected_at_str
            }
            for record in records
        ]
        
        artifact_list.extend(artifacts)
        len_records = len(records)
        cnt += len_records
        # print(f"    {artifact_type}: {len_records}개 행 추가됨")
    del data
    return cnt

def make_test_artifacts(task_id: str, limit: int = 0) -> list:
    helper = TestHelper(db_config)
    artifact_list = []

    for category in Category:
        # print(f"현재 {len(artifact_list)}개 아티팩트 존재.")
        cnt = category_make_test_artifacts(task_id, category, artifact_list, helper, limit)
        # print(f"{category.name}: {cnt}개 추가.")

    print(f"\n총 {len(artifact_list)}개의 artifact 생성됨")
    return artifact_list