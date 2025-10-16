"""
RAG Agent가 사용하는 도구(Tools) 정의
"""
from typing import List, Dict, Optional
import asyncio
import nest_asyncio

from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from workflow.classes import StructuredQuery
from common.utils import llm_medium
from workflow.database import (
    create_vectorstore, 
    DEFAULT_DB_CONFIG,
    MAX_SEARCH_RESULTS,  # 검색 제한 상수
    datetime_to_timestamp  # datetime → timestamp 변환 함수
)
from workflow.prompts import (
    QUERY_PLANNER_SYSTEM_PROMPT,
    QUERY_PLANNER_USER_PROMPT
)

# ThreadPoolExecutor 환경에서 이벤트 루프를 사용할 수 있도록 설정
nest_asyncio.apply()


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
# 유틸리티 함수
# --------------------------------------------------------------------------

def parse_page_content(page_content: str) -> Dict[str, str]:
    """
    Document의 page_content를 파싱하여 data dict로 변환합니다.
    
    Args:
        page_content: "Type: usb_files\\ndevice_name: Samsung\\nfile_name: secret.pdf"
    
    Returns:
        {"device_name": "Samsung", "file_name": "secret.pdf"}
        (Type은 제외, metadata에 이미 있음)
    
    Example:
        >>> content = "Type: usb_files\\ndevice_name: Samsung Galaxy\\nfile_name: secret.pdf"
        >>> parse_page_content(content)
        {'device_name': 'Samsung Galaxy', 'file_name': 'secret.pdf'}
    """
    data = {}
    lines = page_content.strip().split('\n')
    
    for line in lines:
        if ':' in line and not line.startswith('Type:'):
            key, value = line.split(':', 1)
            data[key.strip()] = value.strip()
    
    return data


def get_metadata_info(collection_name: str, config=None) -> Dict:
    """
    벡터 DB에서 메타데이터 통계 정보를 추출합니다.
    LLM이 자율적으로 필터링을 판단할 수 있도록 정보를 제공합니다.
    
    ThreadPoolExecutor 환경에서 안전하게 동작하도록 chromadb.PersistentClient를 직접 사용합니다.
    
    Args:
        collection_name: 컬렉션 이름
        config: VectorDBConfig (None이면 DEFAULT_DB_CONFIG 사용)
    
    Returns:
        {
            "artifact_types": ["usb_files", "browser_history", ...],
            "datetime_range": {
                "earliest": "2024-01-01T00:00:00",
                "latest": "2024-01-31T23:59:59"
            },
            "total_count": 1000
        }
    """
    try:
        if config is None:
            config = DEFAULT_DB_CONFIG
        
        # ThreadPoolExecutor 환경에서 안전하게 동작하도록 chromadb.PersistentClient 직접 사용
        import chromadb
        
        client = chromadb.PersistentClient(
            path=config.persist_directory,
            settings=config.chroma_settings
        )
        
        # 컬렉션 가져오기 (없으면 예외 발생)
        collection = client.get_collection(name=collection_name)
        
        # 모든 메타데이터 가져오기
        all_data = collection.get(include=["metadatas"])
        all_metadata = all_data.get("metadatas", [])
        
        if not all_metadata:
            return {
                "artifact_types": [],
                "datetime_range": {"earliest": None, "latest": None},
                "total_count": 0
            }
        
        # 통계 수집
        artifact_types = set()
        datetimes = []
        
        for meta in all_metadata:
            if meta.get("artifact_type"):
                artifact_types.add(meta["artifact_type"])
            if meta.get("datetime"):
                datetimes.append(meta["datetime"])
        
        return {
            "artifact_types": sorted(list(artifact_types)),
            "datetime_range": {
                "earliest": min(datetimes) if datetimes else None,
                "latest": max(datetimes) if datetimes else None
            },
            "total_count": len(all_metadata)
        }
        
    except Exception as e:
        print(f"  ⚠️  메타데이터 정보 수집 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            "artifact_types": [],
            "datetime_range": {"earliest": None, "latest": None},
            "total_count": 0
        }


def format_metadata_section(metadata_info: dict) -> str:
    """
    메타데이터 정보를 프롬프트용 문자열로 포맷팅합니다.
    
    Args:
        metadata_info: get_metadata_info()로부터 반환된 메타데이터 딕셔너리
    
    Returns:
        str: 포맷팅된 메타데이터 섹션 문자열
    """
    total_count = metadata_info.get('total_count', 0)
    artifact_types = metadata_info.get('artifact_types', [])
    datetime_range = metadata_info.get('datetime_range', {})
    
    return f"""**데이터베이스 메타데이터:**
- 전체 아티팩트 수: {total_count:,}개
- 사용 가능한 Artifact Types: {artifact_types}
- 시간 범위: {datetime_range.get('earliest')} ~ {datetime_range.get('latest')}"""


# --------------------------------------------------------------------------
# RAG Tools
# --------------------------------------------------------------------------


@tool
def query_planner_tool(natural_language_goal: str) -> Dict:
    """
    디지털 포렌식 아티팩트 검색을 위한 구조화된 쿼리를 생성합니다.
    
    [중요] 이 도구는 검색 쿼리만 생성합니다. 실제 검색은 수행하지 않습니다.
    
    [이 도구의 역할]
    - 자연어 검색 목표 -> 구조화된 쿼리(StructuredQuery)로 변환
    - 최적의 필터 조합 자동 결정 (AI 기반)
    - 실제 데이터 검색은 하지 않음 -> artifact_search_tool 사용 필요
    
    [작업 흐름]
    1. query_planner_tool() <- 쿼리 생성 (이 도구)
       ↓ (StructuredQuery 반환)
    2. artifact_search_tool() <- 실제 검색 수행
       ↓ (검색 결과 반환)
    3. 결과 분석 및 활용
    
    [생성되는 쿼리 구조 - 2단계 검색 시스템]
    
    1단계: 1차 필터링 (메타데이터 기반 - 선택적)
       - artifact_type: 타입별 정확 매칭 (예: usb_files, browser_history, prefetch_file)
       - datetime: 시간 범위 필터링 (타임스탬프 기반)
       -> 검색 범위를 대폭 축소하여 성능 향상 (전체 10,000개 -> 수백 개)
    
    2단계: 2차 검색 (벡터 유사도 기반 - 필수)
       - 의미론적 유사도 검색으로 정확한 결과 추출
       - similarity_threshold로 정확도 조절
    
    [검색 목표 작성 팁]
    필터링 기능을 활용하여 더 구체적인 목표를 설정하세요:
    
    좋은 예:
    - "2024년 1월 15일 오전 9시-12시 사이에 USB를 통해 다운로드된 의심 파일 찾기"
      -> datetime, artifact_type 필터 모두 활용 가능
    - "브라우저 다운로드 기록에서 .exe 파일 검색"
      -> artifact_type 필터 활용
    
    나쁜 예:
    - "파일 찾기" -> 너무 광범위, 필터링 불가
    
    [자동 최적화]
    - 데이터베이스 메타데이터를 자동 분석하여 사용 가능한 필터 확인
    - LLM이 검색 목표에 맞는 최적의 필터 조합 자율 결정
    - 불확실한 경우 필터링 없이 전체 검색 (안전모드)
    
    Args:
        natural_language_goal: 구체적인 검색 목표 (시간, 타입, 소스 등 포함 권장)
    
    Returns:
        Dict: 최적화된 StructuredQuery (검색 쿼리 객체, 실제 데이터 아님!)
            - query_text: 벡터 검색 키워드
            - filter_artifact_types: 타입 필터 (Optional)
            - filter_datetime_start/end: 시간 범위 (Optional)
            - max_results: 반환 개수
            - similarity_threshold: 유사도 임계값
    
    Examples:
        >>> # Step 1: 쿼리 생성 (이 도구)
        >>> query = query_planner_tool("2024-01-15 오전에 USB로 전송된 문서 파일")
        >>> # query는 StructuredQuery 딕셔너리 (실제 데이터 아님!)
        
        >>> # Step 2: 실제 검색 수행 (artifact_search_tool)
        >>> results = artifact_search_tool(query, "artifacts_collection")
        >>> # results에 실제 검색된 아티팩트 포함
        
        >>> # Source 포함 검색
        >>> query_planner_tool("secret이 포함된 파일 찾기")
        
        >>> # 필터 없이 전체 검색
        >>> query_planner_tool("시스템 전체에서 암호화 관련 활동")
    """
    print("--- 🧠 Tool: 검색 쿼리 계획 중 ---")
    
    # State에서 컨텍스트 정보 가져오기
    collection_name = ToolContext.get_collection_name()
    db_config = ToolContext.get_db_config()
    
    # 1. 메타데이터 정보 수집
    print("  📊 메타데이터 분석 중...")
    metadata_info = get_metadata_info(collection_name, db_config)
    
    if metadata_info["total_count"] > 0:
        print(f"  ✅ 메타데이터 분석 완료:")
        print(f"     - 전체 아티팩트: {metadata_info['total_count']:,}개")
        print(f"     - Artifact Types: {len(metadata_info['artifact_types'])}개, {metadata_info['artifact_types']}")
        print(f"     - 시간 범위: {metadata_info['datetime_range']['earliest']} ~ {metadata_info['datetime_range']['latest']}")
    else:
        print(f"  ⚠️  메타데이터 없음 (빈 DB 또는 오류)")
    
    # 2. 프롬프트 생성
    metadata_section = format_metadata_section(metadata_info)
    system_prompt = QUERY_PLANNER_SYSTEM_PROMPT.format(metadata_section=metadata_section)
    user_prompt = QUERY_PLANNER_USER_PROMPT.format(natural_language_goal=natural_language_goal)
    
    
    structured_llm = llm_medium.with_structured_output(StructuredQuery)
    
    try:
        response: StructuredQuery = structured_llm.invoke([  # type: ignore
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        # 결과 출력
        print(f"  ✅ 쿼리 생성 완료:")
        print(f"     - query_text: {response.query_text}")
        print(f"     - 1차 필터:")
        print(f"       • artifact_types: {response.filter_artifact_types or '(필터링 없음)'}")
        print(f"       • datetime: {response.filter_datetime_start or '(없음)'} ~ {response.filter_datetime_end or '(없음)'}")
        print(f"     - 2차 검색:")
        print(f"       • max_results: {response.max_results}")
        print(f"       • similarity_threshold: {response.similarity_threshold}")
        
        return response.model_dump()
        
    except Exception as e:
        print(f"  ❌ 쿼리 생성 실패: {e}")
        
        # 폴백: 기본 쿼리 반환 (필터링 없음)
        fallback_query = StructuredQuery(
            query_text=natural_language_goal,  # 원본 목표를 그대로 사용
            filter_artifact_types=None,
            filter_datetime_start=None,
            filter_datetime_end=None,
            max_results=20,
            similarity_threshold=0.3
        )
        
        print(f"  🔄 기본 쿼리로 폴백")
        return fallback_query.model_dump()


@tool
def artifact_search_tool(
    structured_query: Dict,
    collection_name: Optional[str] = None,
    db_config: Optional[Dict] = None
) -> Dict:
    """
    구조화된 쿼리로 디지털 포렌식 아티팩트를 검색합니다.
    
    [주의] 이 도구는 직접 호출하지 마세요!
    반드시 query_planner_tool을 먼저 호출하여 최적화된 쿼리를 생성한 후,
    그 결과를 이 도구에 전달하세요.
    
    [검색 프로세스]
    1단계: 1차 필터링 (메타데이터 기반)
       - structured_query에 포함된 필터 적용:
         * filter_artifact_types: 타입 필터 (정확 일치)
         * filter_datetime: 시간 범위 필터 (타임스탬프 기반)
       - 전체 데이터에서 관련 있는 것만 추출 (성능 최적화)
    
    2단계: 2차 검색 (벡터 유사도 기반)
       - 1차 필터 통과한 데이터에서 의미론적 유사도 검색
       - similarity_threshold 적용하여 정확도 보장
    
    [검색 결과]
    - 각 아티팩트는 ID, artifact_type, 실제 데이터 포함
    - 메타데이터로 검색 통계 제공 (필터링 전후 개수 등)
    
    
    Args:
        structured_query: query_planner_tool이 생성한 StructuredQuery (Dict 형태)
        collection_name: 검색할 컬렉션 이름 (생략 시 State에서 자동 가져옴)
        db_config: DB 설정 (생략 시 State에서 자동 가져옴, None이면 기본값 사용)
    
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
                "filter_types": ["usb_files"],
                "filter_datetime_start": "2024-01-15T00:00:00",
                "filter_datetime_end": "2024-01-15T12:00:00",
                "filter_used": True
            }
        }
    
    Note:
        - 최대 300개 결과 제한 (토큰 제한)
        - 필터를 사용하면 검색 속도 대폭 향상
        - 결과 개수가 적으면 필터 조건 완화 권장
    """
    print("--- 🔎 Tool: 2단계 검색 실행 ---")
    
    # collection_name과 db_config가 제공되지 않으면 ToolContext에서 가져오기
    if collection_name is None:
        collection_name = ToolContext.get_collection_name()
    if db_config is None:
        db_config = ToolContext.get_db_config()
    
    try:
        # db_config가 없으면 기본 설정 사용
        if db_config is None:
            config = DEFAULT_DB_CONFIG
        else:
            from workflow.database import VectorDBConfig
            
            # dict를 VectorDBConfig로 변환
            config = VectorDBConfig(
                db_type=db_config.get("db_type", "chroma"),
                embedding_model=db_config.get("embedding_model", "gemini-embedding-001"),
                embedding_provider=db_config.get("embedding_provider", "google"),
                persist_directory=db_config.get("persist_directory", "./chroma")
            )
        
        # 벡터 DB 재생성 (state에서 전달된 설정 사용)
        vectorstore = create_vectorstore(
            config=config,
            collection_name=collection_name
        )
        
        # 검색 파라미터 추출
        query_text = structured_query.get("query_text", "")
        
        # 1차 필터링 파라미터 (Optional)
        filter_types = structured_query.get("filter_artifact_types", [])
        filter_datetime_start = structured_query.get("filter_datetime_start")
        filter_datetime_end = structured_query.get("filter_datetime_end")
        
        # 2차 검색 파라미터
        requested_max = structured_query.get("max_results", 300)
        max_results = int(requested_max)  # 정수형으로 변환
        similarity_threshold = structured_query.get("similarity_threshold", 0.5)
        
        # 🔒 토큰 제한 안전 장치: MAX_SEARCH_RESULTS로 제한
        limited = False
        if max_results > MAX_SEARCH_RESULTS:
            print(f"  ⚠️  max_results {max_results}는 너무 많습니다. {MAX_SEARCH_RESULTS}로 제한합니다.")
            max_results = MAX_SEARCH_RESULTS
            limited = True
        elif max_results < 1:
            print(f"  ⚠️  max_results {max_results}는 너무 적습니다. 1로 설정합니다.")
            max_results = 1
        
        # 🔹 1차 필터: 메타데이터 필터 구성
        filter_conditions = []
        
        # artifact_type 필터 (정확 일치)
        if filter_types:
            filter_conditions.append({"artifact_type": {"$in": filter_types}})
        
        # ✅ datetime 필터를 timestamp(숫자)로 변환하여 Chroma DB에서 직접 필터링
        # ChromaDB는 하나의 필드에 여러 연산자를 동시에 사용할 수 없으므로 분리
        if filter_datetime_start or filter_datetime_end:
            if filter_datetime_start:
                start_ts = datetime_to_timestamp(filter_datetime_start)
                if start_ts is not None:
                    filter_conditions.append({"timestamp": {"$gte": start_ts}})
            
            if filter_datetime_end:
                end_ts = datetime_to_timestamp(filter_datetime_end)
                if end_ts is not None:
                    filter_conditions.append({"timestamp": {"$lte": end_ts}})
        
        # Chroma DB 필터 구성: 조건이 여러 개면 $and로 묶기
        if len(filter_conditions) == 0:
            metadata_filter = None
            print(f"  🔍 1차 필터: 없음 (전체 검색)")
        elif len(filter_conditions) == 1:
            metadata_filter = filter_conditions[0]
            print(f"  🔍 1차 필터 적용: {metadata_filter}")
        else:
            metadata_filter = {"$and": filter_conditions}
            print(f"  🔍 1차 필터 적용 (다중 조건): {len(filter_conditions)}개 조건")
        
        # 🔹 2차 검색: 유사도 검색 (1차 필터 결과 대상)
        search_k = int(max_results * 2)  # 정수형으로 변환
        
        # ThreadPoolExecutor 환경에서 안전하게 검색 수행
        try:
            # 이벤트 루프가 없는 경우를 대비하여 새로운 루프 생성
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 동기 방식으로 검색 실행
        results_with_scores = vectorstore.similarity_search_with_score(
            query=query_text,
            k=search_k,
            filter=metadata_filter
        )
        
        # 검색 통계
        initial_count = len(results_with_scores)
        print(f"  📊 1차 필터 통과: {initial_count}개")
        
        # 🔹 유사도 임계값 필터링 (점수가 낮을수록 유사함)
        # Chroma는 거리(distance)를 반환하므로, 임계값보다 작은 것만 선택
        filtered_results = [
            (doc, score) 
            for doc, score in results_with_scores 
            if score <= (1.0 - similarity_threshold)  # 거리 → 유사도 변환
        ]
        
        # 🔹 최대 개수로 제한
        filtered_results = filtered_results[:max_results]
        results = [doc for doc, score in filtered_results]
        
        # 검색 통계
        filtered_count = len(results)
        
        print(f"  📊 2차 필터 (유사도 {similarity_threshold}) 통과: {filtered_count}개")
        if limited:
            print(f"  ⚠️  토큰 제한으로 {requested_max}개 → {max_results}개로 제한됨")
        
        # Document를 딕셔너리로 변환 (page_content 파싱)
        artifacts = []
        for doc in results:
            # page_content 파싱하여 data 추출 (모두 문자열)
            artifact_dict = parse_page_content(doc.page_content)
            
            # ID와 artifact_type을 data에 추가
            artifact_dict["id"] = doc.metadata.get("artifact_id", "unknown")
            artifact_dict["artifact_type"] = doc.metadata.get("artifact_type", "unknown")
            
            artifacts.append(artifact_dict)
        
        # 🎯 결과 메시지 생성
        if limited:
            message = f"✅ {filtered_count}개 검색 완료 (요청: {requested_max}개 → 토큰 제한으로 {max_results}개로 제한됨)"
        elif filtered_count < requested_max:
            message = f"✅ {filtered_count}개 검색 완료 (요청: {requested_max}개, 유사도 임계값 {similarity_threshold}로 필터링)"
        else:
            message = f"✅ {filtered_count}개 검색 완료"
        
        print(f"  {message}")
        
        # 🎯 결과와 메타데이터 함께 반환
        return {
            "artifacts": artifacts,  # List[Dict[str, str]] - ID 포함된 딕셔너리
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
                "filter_used": len(filter_conditions) > 0
            }
        }
        
    except Exception as e:
        error_msg = f"아티팩트 검색 실패: {type(e).__name__} - {str(e)}"
        print(f"  ❌ {error_msg}")
        
        # 실패 시 빈 결과 반환
        return {
            "artifacts": [],
            "message": f"❌ {error_msg}",
            "metadata": {
                "requested": structured_query.get("max_results", 10),
                "returned": 0,
                "filtered_from": 0,
                "limited": False,
                "threshold": structured_query.get("similarity_threshold", 0.5),
                "filter_types": structured_query.get("filter_artifact_types", []) or []
            }
        }


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
    print("--- 🔎 Tool: 통합 검색 실행 ---")
    
    # Step 1: 쿼리 생성 (내부)
    print("  🧠 Step 1/2: 검색 쿼리 최적화 중...")
    try:
        query_result = query_planner_tool.invoke({"natural_language_goal": natural_language_goal})
        print(f"  ✅ 쿼리 생성 완료")
    except Exception as e:
        print(f"  ❌ 쿼리 생성 실패: {e}")
        return {
            "artifacts": [],
            "message": f"❌ 쿼리 생성 실패: {str(e)}",
            "metadata": {"returned": 0}
        }
    
    # Step 2: 검색 실행 (내부)
    print("  🔍 Step 2/2: 아티팩트 검색 중...")
    try:
        search_result = artifact_search_tool.invoke({
            "structured_query": query_result,
            "collection_name": None,  # ToolContext에서 자동 가져옴
            "db_config": None
        })
        
        artifacts_count = len(search_result.get("artifacts", []))
        print(f"  ✅ 통합 검색 완료: {artifacts_count}개 발견")
        
        return search_result
        
    except Exception as e:
        print(f"  ❌ 검색 실패: {e}")
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
