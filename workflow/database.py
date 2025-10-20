"""
벡터 데이터베이스 관련 함수들
- 데이터베이스 설정은 한 곳에서 관리 (VectorDBConfig)
- Factory Pattern으로 쉽게 DB 교체 가능
- 검색 성능 최적화를 위해 메타데이터 최소화
"""
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, date
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from chromadb.config import Settings as ChromaSettings
import chromadb
import threading
import logging

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# 유틸리티 함수 (내부 사용)
# --------------------------------------------------------------------------

def convert_datetime_to_str(obj: Any) -> Any:
    """재귀적으로 객체 내의 모든 datetime 객체를 문자열로 변환"""
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
    """Datetime 객체를 UTC 타임스탬프로 변환 (pandas Timestamp, ISO 문자열, datetime 지원)"""
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
        logger.warning("Datetime 변환 실패: %s (값: %s)", e, dt)
        return None

# --------------------------------------------------------------------------
# 데이터베이스 설정 (한 곳에서만 수정하면 전체 적용)
# --------------------------------------------------------------------------

@dataclass
class VectorDBConfig:
    """벡터 DB 설정 - 한 곳에서 DB 교체 가능"""
    db_type: str = "chroma"
    embedding_model: str = "gemini-embedding-001"
    embedding_provider: str = "google"
    persist_directory: str = "./chroma"
    chroma_settings: ChromaSettings = field(default_factory=lambda: ChromaSettings(
        anonymized_telemetry=False,
        is_persistent=True
    ))
    
    def __post_init__(self):
        self.chroma_settings.persist_directory = self.persist_directory


# --------------------------------------------------------------------------
# RAG 검색 제한 설정
# --------------------------------------------------------------------------

MAX_SEARCH_RESULTS = 300  # 최대 검색 결과 개수

DEFAULT_DB_CONFIG = VectorDBConfig()


# --------------------------------------------------------------------------
# Config 정규화
# --------------------------------------------------------------------------

def normalize_config(config: Union[None, dict, VectorDBConfig]) -> VectorDBConfig:
    """config를 VectorDBConfig 객체로 정규화"""
    if config is None:
        return DEFAULT_DB_CONFIG
    
    if isinstance(config, VectorDBConfig):
        return config
    
    if isinstance(config, dict):
        try:
            return VectorDBConfig(
                db_type=config.get("db_type", DEFAULT_DB_CONFIG.db_type),
                embedding_model=config.get("embedding_model", DEFAULT_DB_CONFIG.embedding_model),
                embedding_provider=config.get("embedding_provider", DEFAULT_DB_CONFIG.embedding_provider),
                persist_directory=config.get("persist_directory", DEFAULT_DB_CONFIG.persist_directory),
                chroma_settings=config.get("chroma_settings", DEFAULT_DB_CONFIG.chroma_settings)
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error("Config 변환 실패: %s", e)
            raise TypeError(f"dict를 VectorDBConfig로 변환 실패: {e}") from e
    
    raise TypeError(f"config는 None, dict, 또는 VectorDBConfig여야 합니다. 현재: {type(config)}")


def parse_document_content(page_content: str) -> Dict[str, str]:
    """Document의 page_content를 파싱하여 data dict로 변환"""
    data = {}
    lines = page_content.strip().split('\n')
    
    for line in lines:
        if ':' in line and not line.startswith('Type:'):
            key, value = line.split(':', 1)
            data[key.strip()] = value.strip()
    
    return data


# --------------------------------------------------------------------------
# 임베딩 모델
# --------------------------------------------------------------------------

def get_embeddings(config: VectorDBConfig = DEFAULT_DB_CONFIG):
    """설정에 따라 임베딩 모델을 반환합니다."""
    if config.embedding_provider == "google":
        return GoogleGenerativeAIEmbeddings(model=config.embedding_model)
    elif config.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=config.embedding_model)
    else:
        raise ValueError(f"Unknown embedding provider: {config.embedding_provider}")


# --------------------------------------------------------------------------
# 전역 ChromaDB 클라이언트 (스레드 안전)
# --------------------------------------------------------------------------

_global_chroma_client: Optional[Any] = None
_global_client_path: Optional[str] = None
_client_lock = threading.Lock()


def get_chroma_client(config: VectorDBConfig = DEFAULT_DB_CONFIG) -> Any:
    """전역 ChromaDB 클라이언트 반환 (스레드 안전, Double-checked locking)"""
    global _global_chroma_client, _global_client_path
    
    persist_directory = config.persist_directory
    
    # Fast path: 락 없이 빠른 체크
    if _global_chroma_client is not None and _global_client_path == persist_directory:
        return _global_chroma_client
    
    # Slow path: 락 획득 후 클라이언트 생성
    with _client_lock:
        # Double-checked locking
        if _global_chroma_client is not None:
            if _global_client_path == persist_directory:
                logger.debug("기존 ChromaDB 클라이언트 재사용: %s", persist_directory)
                return _global_chroma_client
            else:
                logger.warning(
                    "다른 경로 요청, 기존 클라이언트 반환 (충돌 방지): %s -> %s",
                    _global_client_path, persist_directory
                )
                return _global_chroma_client
        
        # 새 클라이언트 생성
        logger.info("새 ChromaDB 클라이언트 생성: %s", persist_directory)
        
        try:
            _global_chroma_client = chromadb.PersistentClient(path=persist_directory)
            _global_client_path = persist_directory
            return _global_chroma_client
        except Exception as e:
            logger.error("ChromaDB 클라이언트 생성 실패: %s", e)
            raise ValueError(f"ChromaDB 클라이언트 생성 실패: {e}") from e


# --------------------------------------------------------------------------
# 벡터 스토어 생성
# --------------------------------------------------------------------------

def create_vectorstore(
    collection_name: str,
    config: VectorDBConfig = DEFAULT_DB_CONFIG
) -> VectorStore:
    """
    벡터 스토어 생성 (전역 클라이언트 재사용으로 설정 충돌 방지)
    """
    embeddings = get_embeddings(config)
    
    if config.db_type == "chroma":
        client = get_chroma_client(config)
        return Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings
        )
    elif config.db_type == "pinecone":
        raise NotImplementedError("Pinecone support not yet implemented")
    elif config.db_type == "faiss":
        raise NotImplementedError("FAISS support not yet implemented")
    else:
        raise ValueError(f"Unknown db_type: {config.db_type}")


# --------------------------------------------------------------------------
# 데이터베이스 저장 함수
# --------------------------------------------------------------------------

def _artifact_to_document(artifact: dict, idx: int) -> Document:
    """아티팩트를 검색 가능한 Document로 변환"""
    artifact_type = artifact.get('artifact_type', 'unknown')
    artifact_id = artifact.get('id', f'artifact_{idx}')
    source = artifact.get('source', 'unknown')
    data = convert_datetime_to_str(artifact.get('data', {}))
    collected_at = convert_datetime_to_str(artifact.get('collected_at', None))
    
    # 검색 가능한 텍스트 생성
    content_parts = [f"Type: {artifact_type}"]
    for key, value in data.items():
        if value:
            if isinstance(value, (datetime, date)):
                content_parts.append(f"{key}: {value.isoformat()}")
            else:
                content_parts.append(f"{key}: {value}")
    
    page_content = "\n".join(content_parts)
    
    # 메타데이터 (ID와 필터링용 정보만)
    metadata = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "source": source,
        "datetime": collected_at,
        "timestamp": datetime_to_timestamp(collected_at),
        "index": idx
    }
    
    return Document(page_content=page_content, metadata=metadata)


def save_to_chroma(
    artifacts: List[dict],
    collection_name: str = "filtered_artifacts",
    config: VectorDBConfig = DEFAULT_DB_CONFIG
) -> Dict:
    """
    아티팩트를 벡터 DB에 저장 (배치 처리 지원)
    """
    try:
        if not artifacts:
            return {
                "data_save_status": "success",
                "message": "저장할 아티팩트가 없습니다.",
                "count": 0
            }
        
        print(f"--- 💾 {config.db_type.upper()} DB에 {len(artifacts):,}개 아티팩트 저장 중... ---")
        
        embeddings = get_embeddings(config)
        documents = [_artifact_to_document(art, idx) for idx, art in enumerate(artifacts)]
        
        # ChromaDB 배치 저장
        if config.db_type == "chroma":
            BATCH_SIZE = 5000
            total_docs = len(documents)
            
            if total_docs <= BATCH_SIZE:
                vectorstore = Chroma.from_documents(
                    documents=documents,
                    embedding=embeddings,
                    collection_name=collection_name,
                    persist_directory=config.persist_directory
                )
                print(f"  ✅ {total_docs:,}개 아티팩트 저장 완료")
            else:
                # 대용량 배치 저장
                print(f"  📦 {total_docs:,}개를 {BATCH_SIZE:,}개씩 배치 저장")
                
                # 첫 번째 배치
                vectorstore = Chroma.from_documents(
                    documents=documents[:BATCH_SIZE],
                    embedding=embeddings,
                    collection_name=collection_name,
                    persist_directory=config.persist_directory
                )
                print(f"     ✓ 배치 1/{(total_docs + BATCH_SIZE - 1) // BATCH_SIZE}")
                
                # 나머지 배치
                for i in range(BATCH_SIZE, total_docs, BATCH_SIZE):
                    batch_docs = documents[i:i + BATCH_SIZE]
                    vectorstore.add_documents(batch_docs)
                    print(f"     ✓ 배치 {(i // BATCH_SIZE) + 1}/{(total_docs + BATCH_SIZE - 1) // BATCH_SIZE}")
                
                print(f"  ✅ 전체 {total_docs:,}개 배치 저장 완료")
        else:
            raise NotImplementedError(f"{config.db_type} 저장 미구현")
        
        print(f"  📁 위치: {config.persist_directory}/{collection_name}")
        
        return {
            "data_save_status": "success",
            "message": f"{len(documents):,}개 아티팩트 저장 완료",
            "count": len(documents),
            "collection_name": collection_name,
            "db_config": {
                "db_type": config.db_type,
                "embedding_model": config.embedding_model,
                "embedding_provider": config.embedding_provider,
                "persist_directory": config.persist_directory
            }
        }
        
    except Exception as e:
        error_msg = f"벡터 DB 저장 실패: {type(e).__name__} - {str(e)}"
        print(f"  ❌ {error_msg}")
        return {
            "data_save_status": "failure",
            "message": error_msg,
            "count": 0
        }


def save_data_node(state) -> Dict[str, Any]:
    """
    필터링된 데이터를 벡터 DB에 저장 (매 작업마다 초기화)
    """
    print("--- 💾 Node: 필터링된 데이터 저장 시도... ---")
    
    filtered_artifacts = state.get("filtered_artifacts", [])
    collection_name = "artifacts_collection"
    
    # 이전 컬렉션 삭제
    try:
        client = get_chroma_client(DEFAULT_DB_CONFIG)
        try:
            client.delete_collection(name=collection_name)
            logger.info("기존 컬렉션 '%s' 삭제", collection_name)
            print(f"  🗑️  이전 컬렉션 초기화 완료")
        except Exception:
            logger.debug("컬렉션 없음, 새로 생성")
            print(f"  ℹ️  새로운 컬렉션 생성 준비")
    except Exception as e:
        logger.warning("초기화 중 오류 (무시): %s", e)
        print(f"  ⚠️  초기화 중 오류 (무시): {e}")
    
    # 저장
    result = save_to_chroma(
        artifacts=filtered_artifacts,
        collection_name=collection_name,
        config=DEFAULT_DB_CONFIG
    )
    
    status = "성공" if result["data_save_status"] == "success" else "실패"
    print(f"--- {'✅' if status == '성공' else '❌'} Node: 데이터 저장 {status} ({result.get('count', 0):,}개) ---")
    
    return result

