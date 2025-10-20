"""
워크플로우 유틸리티 함수
- 메타데이터 추출 및 포맷팅
- 에러 응답 생성
"""
import os
import logging
from dotenv import load_dotenv
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from workflow.database import VectorDBConfig, get_chroma_client

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

from langchain.chat_models import init_chat_model

logger = logging.getLogger(__name__)
llm_small = init_chat_model("google_genai:gemini-2.5-flash-lite", temperature=0)
llm_medium = init_chat_model("google_genai:gemini-2.5-flash", temperature=0)
llm_large = init_chat_model("google_genai:gemini-2.5-pro", temperature=0)


# --------------------------------------------------------------------------
# 예외 클래스 (tools.py에서 사용)
# --------------------------------------------------------------------------

class ChromaDBError(Exception):
    """ChromaDB 관련 기본 에러"""
    pass


class CollectionNotFoundError(ChromaDBError):
    """컬렉션을 찾을 수 없음"""
    def __init__(self, collection_name: str):
        super().__init__(f"컬렉션 '{collection_name}'을 찾을 수 없습니다")
        self.collection_name = collection_name


class MetadataExtractionError(ChromaDBError):
    """메타데이터 추출 실패"""
    pass


# --------------------------------------------------------------------------
# 메타데이터 관련 함수
# --------------------------------------------------------------------------

def get_metadata_info(
    collection_name: str,
    config: Union[None, dict, VectorDBConfig] = None
) -> Dict:
    """
    벡터 DB에서 메타데이터 통계 정보 추출
    (artifact_types, datetime_range, total_count)
    """
    try:
        from workflow.database import normalize_config
        
        # Config 정규화
        db_config = normalize_config(config)
        
        # 전역 클라이언트 가져오기
        client = get_chroma_client(db_config)
        
        # 컬렉션 가져오기
        try:
            collection = client.get_collection(name=collection_name)
        except Exception as e:
            raise CollectionNotFoundError(collection_name) from e
        
        # 메타데이터 가져오기
        results = collection.get(include=["metadatas"])
        metadatas = results.get("metadatas", [])
        
        if not metadatas:
            logger.warning("컬렉션 '%s'가 비어있습니다", collection_name)
            return {
                "artifact_types": [],
                "datetime_range": {"earliest": None, "latest": None},
                "total_count": 0
            }
        
        # artifact_type 수집
        artifact_types = set()
        datetimes = []
        
        for meta in metadatas:
            if meta.get("artifact_type"):
                artifact_types.add(meta["artifact_type"])
            if meta.get("datetime"):
                datetimes.append(meta["datetime"])
        
        result = {
            "artifact_types": sorted(list(artifact_types)),
            "datetime_range": {
                "earliest": min(datetimes) if datetimes else None,
                "latest": max(datetimes) if datetimes else None
            },
            "total_count": len(metadatas)
        }
        
        logger.info(
            "메타데이터 수집 완료: %d개 아티팩트, %d개 타입",
            result["total_count"],
            len(result["artifact_types"])
        )
        
        return result
        
    except CollectionNotFoundError:
        raise
    except Exception as e:
        logger.debug("메타데이터 추출 실패 (내부): %s", e, exc_info=True)
        raise MetadataExtractionError(f"메타데이터 추출 실패: {e}") from e


def format_metadata_section(metadata_info: dict) -> str:
    """메타데이터 정보를 프롬프트용 문자열로 포맷팅"""
    total_count = metadata_info.get('total_count', 0)
    artifact_types = metadata_info.get('artifact_types', [])
    datetime_range = metadata_info.get('datetime_range', {})
    
    return f"""**데이터베이스 메타데이터:**
- 전체 아티팩트 수: {total_count:,}개
- 사용 가능한 Artifact Types: {artifact_types}
- 시간 범위: {datetime_range.get('earliest')} ~ {datetime_range.get('latest')}"""


# --------------------------------------------------------------------------
# 에러 응답 생성
# --------------------------------------------------------------------------

def create_search_error_response(error_msg: str, structured_query: Dict) -> Dict:
    """검색 실패 시 표준 에러 응답 생성"""
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
#
#
#

def calculate_optimal_chunk_size(total_artifacts: int, target_chunks: int = 100) -> int:
    """
    아티팩트 총 개수에 따라 최적의 청크 사이즈 계산
    
    Args:
        total_artifacts: 전체 아티팩트 개수
        target_chunks: 목표 청크 개수 (기본 100개)
        
    Returns:
        최적화된 청크 사이즈
    """
    # 목표 청크 개수로 나눈 값
    calculated_size = total_artifacts // target_chunks
    
    # 최소/최대 제한 설정
    min_chunk_size = 500   # 너무 작으면 비효율
    max_chunk_size = 2000  # 너무 크면 토큰 초과 위험
    
    # 범위 내로 조정
    optimal_size = max(min_chunk_size, min(calculated_size, max_chunk_size))
    
    # 실제 청크 개수 계산
    actual_chunks = (total_artifacts + optimal_size - 1) // optimal_size
    
    print(f"📊 청크 사이즈 최적화 결과:")
    print(f"  - 전체 아티팩트: {total_artifacts:,}개")
    print(f"  - 청크 사이즈: {optimal_size}개")
    print(f"  - 예상 청크 개수: {actual_chunks}개")
    print(f"  - Map 단계 LLM 호출: {actual_chunks}번")
    print(f"  - 예상 처리 시간: ~{actual_chunks * 2.5:.0f}초 (약 {actual_chunks * 2.5 / 60:.1f}분)")
    
    return optimal_size


# --------------------------------------------------------------------------
# 유틸리티 함수
# --------------------------------------------------------------------------

def convert_datetime_to_str(obj: Any) -> Any:
    """
    재귀적으로 객체 내의 모든 datetime 객체를 문자열로 변환합니다.
    JSON 직렬화 가능하도록 만듭니다.
    
    Args:
        obj: 변환할 객체 (dict, list, datetime 등)
    
    Returns:
        datetime이 문자열로 변환된 객체
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_datetime_to_str(item) for item in obj)
    else:
        return obj


def datetime_to_timestamp(dt: Any) -> Optional[float]:
    """
    Datetime 객체를 UTC 타임스탬프로 변환합니다.
    
    pandas Timestamp, ISO 문자열, datetime 객체 모두 지원
    """
    if dt is None:
        return None
    
    try:
        # pandas Timestamp 처리
        if hasattr(dt, 'timestamp'):
            return float(dt.timestamp())
        
        if isinstance(dt, str):
            # 슬래시 구분자를 대시로 변경
            dt = dt.replace('/', '-')
            
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                from dateutil import parser
                dt = parser.parse(dt)
        
        if isinstance(dt, datetime):
            return dt.timestamp()
        elif isinstance(dt, date):
            dt = datetime.combine(dt, datetime.min.time())
            return dt.timestamp()
        
        return None
    except Exception as e:
        print(f"  ⚠️  Datetime 변환 실패: {e} (값: {dt})")
        return None


def timestamp_to_datetime(ts: Optional[float]) -> Optional[str]:
    """UTC 타임스탬프를 ISO 형식 문자열로 변환합니다."""
    if ts is None:
        return None
    
    try:
        return datetime.fromtimestamp(ts).isoformat()
    except Exception as e:
        print(f"  ⚠️  Timestamp 변환 실패: {e}")
        return None


def chunk_artifacts(artifacts: List[dict], chunk_size: int = 50) -> List[List[dict]]:
    """아티팩트를 청크로 분할"""
    return [artifacts[i:i+chunk_size] for i in range(0, len(artifacts), chunk_size)]