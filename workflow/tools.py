"""
RAG Agent가 사용하는 도구(Tools) 정의
"""
from typing import Dict, Optional, Union
import logging

from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from workflow.classes import StructuredQuery
from workflow.database import (
    VectorDBConfig,
    MAX_SEARCH_RESULTS,
    create_vectorstore,
    normalize_config,
    parse_document_content
)
from workflow.utils import (
    ChromaDBError,
    get_metadata_info,
    format_metadata_section,
    create_search_error_response,
    datetime_to_timestamp,
    llm_medium
)
from workflow.prompts import (
    QUERY_PLANNER_SYSTEM_PROMPT,
    QUERY_PLANNER_USER_PROMPT
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# 도구 컨텍스트 설정 (State 정보 전달용)
# --------------------------------------------------------------------------

class ToolContext:
    """도구가 State 정보에 접근할 수 있도록 하는 컨텍스트"""
    collection_name: str = "artifacts_collection"
    db_config: Optional[Dict] = None
    
    @classmethod
    def set_context(cls, collection_name: str, db_config: Optional[Dict] = None):
        """State에서 컨텍스트 정보 설정"""
        cls.collection_name = collection_name
        cls.db_config = db_config
    
    @classmethod
    def get_collection_name(cls) -> str:
        """현재 컬렉션 이름 반환"""
        return cls.collection_name
    
    @classmethod
    def get_db_config(cls) -> Optional[Dict]:
        """현재 DB 설정 반환"""
        return cls.db_config


# --------------------------------------------------------------------------
# RAG Tools
# --------------------------------------------------------------------------


@tool
def query_planner_tool(natural_language_goal: str) -> Dict:
    """
    자연어 검색 목표를 구조화된 쿼리로 변환 (내부 함수)
    
    2단계 검색 시스템:
    - 1차: 메타데이터 필터 (artifact_type, datetime)
    - 2차: 벡터 유사도 검색
    
    Returns: StructuredQuery dict (query_text, filters, max_results, threshold)
    """
    logger.info("검색 쿼리 생성 시작: %s", natural_language_goal)
    
    # State에서 컨텍스트 정보 가져오기
    collection_name = ToolContext.get_collection_name()
    db_config = ToolContext.get_db_config()
    
    try:
        # 메타데이터 정보 수집
        metadata_info = get_metadata_info(collection_name, db_config)
        
        if metadata_info["total_count"] > 0:
            logger.info(
                "메타데이터: %d개 아티팩트, %d개 타입",
                metadata_info["total_count"],
                len(metadata_info["artifact_types"])
            )
        else:
            logger.warning("메타데이터 없음 (빈 DB)")
        
    except ChromaDBError as e:
        logger.debug("메타데이터 수집 실패 (내부): %s", e)
        # 메타데이터 없이 계속 진행
        metadata_info = {
            "artifact_types": [],
            "datetime_range": {"earliest": None, "latest": None},
            "total_count": 0
        }
    
    # 프롬프트 생성
    metadata_section = format_metadata_section(metadata_info)
    system_prompt = QUERY_PLANNER_SYSTEM_PROMPT.format(metadata_section=metadata_section)
    user_prompt = QUERY_PLANNER_USER_PROMPT.format(natural_language_goal=natural_language_goal)
    
    structured_llm = llm_medium.with_structured_output(StructuredQuery)
    
    try:
        response: StructuredQuery = structured_llm.invoke([  # type: ignore
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        logger.info("쿼리 생성 완료: %s", response.query_text)
        return response.model_dump()
        
    except Exception as e:
        logger.warning("쿼리 생성 실패, 기본 쿼리로 폴백: %s", str(e))
        
        # 폴백: 기본 쿼리 반환
        fallback_query = StructuredQuery(
            query_text=natural_language_goal,
            filter_artifact_types=None,
            filter_datetime_start=None,
            filter_datetime_end=None,
            max_results=20,
            similarity_threshold=0.3
        )
        
        logger.info("기본 쿼리 사용: %s", fallback_query.query_text)
        return fallback_query.model_dump()


@tool
def artifact_search_tool(
    structured_query: Dict,
    collection_name: Optional[str] = None,
    db_config: Union[None, dict, VectorDBConfig] = None
) -> Dict:
    """
    StructuredQuery로 벡터 검색 수행 (내부 함수)
    
    2단계 검색: 메타데이터 필터 → 벡터 유사도 검색
    Returns: Dict (results, query_info, total_count, limited)
    """
    logger.info("아티팩트 검색 시작")
    
    # 컨텍스트에서 기본값 가져오기
    if collection_name is None:
        collection_name = ToolContext.get_collection_name()
    if db_config is None:
        db_config = ToolContext.get_db_config()
    
    try:
        # Config 정규화
        config = normalize_config(db_config)
        
        # 벡터 DB 재생성 (state에서 전달된 설정 사용)
        vectorstore = create_vectorstore(
            config=config,
            collection_name=collection_name
        )
        
        # 검색 파라미터 추출
        query_text = structured_query.get("query_text", "")
        filter_types = structured_query.get("filter_artifact_types", [])
        filter_datetime_start = structured_query.get("filter_datetime_start")
        filter_datetime_end = structured_query.get("filter_datetime_end")
        
        # 검색 개수 제한
        requested_max = structured_query.get("max_results", 300)
        max_results = max(1, min(requested_max, MAX_SEARCH_RESULTS))
        limited = max_results < requested_max
        similarity_threshold = structured_query.get("similarity_threshold", 0.5)
        
        if limited:
            logger.warning("max_results %d는 %d로 제한됩니다", requested_max, max_results)
        
        # 🔹 1차 필터: 메타데이터 필터 구성
        filter_conditions = []
        
        # artifact_type 필터
        if filter_types:
            filter_conditions.append({"artifact_type": {"$in": filter_types}})
        
        # datetime 필터 (timestamp로 변환)
        if filter_datetime_start:
            start_ts = datetime_to_timestamp(filter_datetime_start)
            if start_ts is not None:
                filter_conditions.append({"timestamp": {"$gte": start_ts}})
        
        if filter_datetime_end:
            end_ts = datetime_to_timestamp(filter_datetime_end)
            if end_ts is not None:
                filter_conditions.append({"timestamp": {"$lte": end_ts}})
        
        # ChromaDB 필터 구성
        if not filter_conditions:
            metadata_filter = None
            logger.info("1차 필터: 없음 (전체 검색)")
        elif len(filter_conditions) == 1:
            metadata_filter = filter_conditions[0]
            logger.info("1차 필터 적용: %s", metadata_filter)
        else:
            metadata_filter = {"$and": filter_conditions}
            logger.info("1차 필터 적용 (다중 조건): %d개", len(filter_conditions))
        
        # 🔹 2차 검색: 유사도 검색 (1차 필터 결과 대상)
        search_k = max_results * 2
        
        # 동기 방식으로 검색 실행
        results_with_scores = vectorstore.similarity_search_with_score(
            query=query_text,
            k=search_k,
            filter=metadata_filter
        )
        
        # 검색 통계
        initial_count = len(results_with_scores)
        logger.info("1차 필터 통과: %d개", initial_count)
        
        # 🔹 유사도 임계값 필터링 (거리가 작을수록 유사함)
        distance_threshold = 1.0 - similarity_threshold
        filtered_results = [
            (doc, score) 
            for doc, score in results_with_scores 
            if score <= distance_threshold
        ][:max_results]
        
        results = [doc for doc, score in filtered_results]
        filtered_count = len(results)
        
        logger.info("2차 필터 (유사도 %.2f) 통과: %d개", similarity_threshold, filtered_count)
        if limited:
            logger.warning("토큰 제한으로 %d개 → %d개로 제한됨", requested_max, max_results)
        
        # Document를 딕셔너리로 변환
        artifacts = []
        for doc in results:
            artifact_dict = parse_document_content(doc.page_content)
            artifact_dict["id"] = doc.metadata.get("artifact_id", "unknown")
            artifact_dict["artifact_type"] = doc.metadata.get("artifact_type", "unknown")
            artifacts.append(artifact_dict)
        
        # 결과 메시지 생성
        if limited:
            message = f"✅ {filtered_count}개 검색 완료 (요청: {requested_max}개 → 토큰 제한으로 {max_results}개로 제한됨)"
        elif filtered_count < requested_max:
            message = f"✅ {filtered_count}개 검색 완료 (유사도 임계값 {similarity_threshold}로 필터링)"
        else:
            message = f"✅ {filtered_count}개 검색 완료"
        
        logger.info(message)
        
        # 결과 반환
        return {
            "artifacts": artifacts,
            "message": message,
            "metadata": {
                "requested": requested_max,
                "returned": filtered_count,
                "filtered_from": initial_count,
                "limited": limited,
                "threshold": similarity_threshold,
                "filter_types": filter_types or [],
                "filter_datetime_start": filter_datetime_start,
                "filter_datetime_end": filter_datetime_end,
                "filter_used": bool(filter_conditions)
            }
        }
        
    except ChromaDBError as e:
        logger.debug("ChromaDB 오류 (내부): %s", str(e), exc_info=True)
        return create_search_error_response(f"ChromaDB 오류: {str(e)}", structured_query)
    except Exception as e:
        logger.debug("아티팩트 검색 실패 (내부): %s - %s", type(e).__name__, str(e), exc_info=True)
        return create_search_error_response(f"아티팩트 검색 실패: {type(e).__name__} - {str(e)}", structured_query)


@tool
def search_artifacts_tool(natural_language_goal: str) -> Dict:
    """
    디지털 포렌식 아티팩트를 검색합니다. (통합 도구)
    
    [통합 기능]
    - 자연어 검색 목표 입력 → 자동으로 최적화된 쿼리 생성 (AI 기반)
    - 2단계 검색 즉시 실행 (메타데이터 필터 + 벡터 유사도)
    - 검색 결과 직접 반환 (한 번의 도구 호출로 완료)
    
    [검색 프로세스]
    내부 1단계: 쿼리 최적화 (자동)
       - LLM이 검색 목표 분석
       - 메타데이터 기반 최적 필터 자동 결정
       - artifact_type, datetime, 필터 생성
    
    내부 2단계: 실제 검색 (자동)
       - 1차: 메타데이터 필터링
       - 2차: 벡터 유사도 검색
       - 결과 반환
    
    [검색 팁]
    구체적으로 작성할수록 정확한 결과:
    - "2024년 1월 15일 오전 USB로 전송된 문서 파일" ✅
    - "브라우저 다운로드 기록에서 .exe 파일" ✅
    - "의심스러운 파일" ❌ (너무 광범위)
    
    [검색 결과 구조]
    - artifacts: 실제 검색된 아티팩트 리스트
    - message: 검색 완료 메시지
    - metadata: 검색 통계 (개수, 필터 적용 여부 등)
    
    Args:
        natural_language_goal: 구체적인 검색 목표 (자연어)
    
    Returns:
        Dict: {
            "artifacts": [
                {
                    "id": "artifact_001",
                    "artifact_type": "usb_files",
                    "device_name": "Samsung",
                    "file_name": "secret.pdf",
                    ...
                }
            ],
            "message": "18개 검색 완료",
            "metadata": {
                "requested": 20,
                "returned": 18,
                "filtered_from": 150,
                "limited": False,
                "threshold": 0.7,
                "filter_types": ["usb_files"]
            }
        }
    
    Examples:
        >>> search_artifacts_tool("USB로 전송된 기밀 문서")
        {'artifacts': [...], 'message': '5개 검색 완료'}
        
        >>> search_artifacts_tool("2024-01-15 오전 브라우저 다운로드 기록")
        {'artifacts': [...], 'message': '12개 검색 완료'}
        
        >>> search_artifacts_tool("이력서 관련 웹사이트 접속 기록")
        {'artifacts': [...], 'message': '8개 검색 완료'}
    
    Note:
        - 최대 300개 결과 제한
        - 검색 결과가 적으면 더 광범위한 키워드로 재시도 권장
        - 시간, 타입 필터를 포함하면 검색 속도 대폭 향상
    """
    logger.info("=== 통합 검색 실행 ===")
    
    # Step 1: 쿼리 생성
    logger.info("Step 1/2: 검색 쿼리 최적화 중...")
    try:
        query_result = query_planner_tool.invoke({"natural_language_goal": natural_language_goal})
        logger.info("쿼리 생성 완료")
    except Exception as e:
        logger.error("쿼리 생성 실패: %s", str(e), exc_info=True)
        return {
            "artifacts": [],
            "message": f"❌ 쿼리 생성 실패: {str(e)}",
            "metadata": {"returned": 0}
        }
    
    # Step 2: 검색 실행
    logger.info("Step 2/2: 아티팩트 검색 중...")
    try:
        search_result = artifact_search_tool.invoke({
            "structured_query": query_result,
            "collection_name": None,
            "db_config": None
        })
        
        artifacts_count = len(search_result.get("artifacts", []))
        logger.info("통합 검색 완료: %d개 발견", artifacts_count)
        return search_result
        
    except Exception as e:
        logger.error("검색 실패: %s", str(e), exc_info=True)
        return {
            "artifacts": [],
            "message": f"❌ 검색 실패: {str(e)}",
            "metadata": {"returned": 0}
        }


# 웹 검색 도구 (Tavily)
web_search_tool = TavilySearch(max_results=3)
web_search_tool.name = "web_search_tool"
web_search_tool.description = """
웹에서 최신 정보를 검색합니다. 보안 위협, 공격 기법, CVE 정보 등 
외부 정보가 필요할 때 사용하세요.
"""


# 모든 도구를 리스트로 export
agent_tools = [
    search_artifacts_tool,  # 통합 검색 도구 (query_planner + artifact_search)
    web_search_tool
]
