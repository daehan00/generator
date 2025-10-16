"""
벡터 데이터베이스 관련 함수들
- 데이터베이스 설정은 한 곳에서 관리 (VectorDBConfig)
- Factory Pattern으로 쉽게 DB 교체 가능
- 검색 성능 최적화를 위해 메타데이터 최소화
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, date
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from chromadb.config import Settings as ChromaSettings


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
    Datetime 객체를 UTC 타임스탬프(초 단위)로 변환합니다.
    
    Args:
        dt: datetime 객체, ISO 형식 문자열, 또는 pandas Timestamp
    
    Returns:
        float: UTC 타임스탬프 (초 단위), 변환 실패 시 None
    """
    if dt is None:
        return None
    
    try:
        # pandas Timestamp 처리
        if hasattr(dt, 'timestamp'):  # pandas.Timestamp는 timestamp() 메서드가 있음
            return float(dt.timestamp())
        
        if isinstance(dt, str):
            # 슬래시 구분자를 대시로 변경 (예: '2025/06/26 11:45:37.500' -> '2025-06-26 11:45:37.500')
            dt = dt.replace('/', '-')
            
            # 다양한 날짜 형식 시도
            try:
                # ISO 형식 시도
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                # strptime으로 파싱 시도
                from dateutil import parser
                dt = parser.parse(dt)
        
        if isinstance(dt, datetime):
            # UTC 타임스탬프로 변환
            return dt.timestamp()
        elif isinstance(dt, date):
            # date를 datetime으로 변환 후 타임스탬프
            dt = datetime.combine(dt, datetime.min.time())
            return dt.timestamp()
        
        return None
    except Exception as e:
        print(f"  ⚠️  Datetime 변환 실패: {e} (값: {dt})")
        return None


def timestamp_to_datetime(ts: Optional[float]) -> Optional[str]:
    """
    UTC 타임스탬프를 ISO 형식 문자열로 변환합니다.
    
    Args:
        ts: UTC 타임스탬프 (초 단위)
    
    Returns:
        str: ISO 형식 문자열, 변환 실패 시 None
    """
    if ts is None:
        return None
    
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.isoformat()
    except Exception as e:
        print(f"  ⚠️  Timestamp 변환 실패: {e}")
        return None


# --------------------------------------------------------------------------
# 데이터베이스 설정 (한 곳에서만 수정하면 전체 적용)
# --------------------------------------------------------------------------

@dataclass
class VectorDBConfig:
    """벡터 DB 설정 - 여기만 수정하면 전체 DB 교체 가능"""
    db_type: str = "chroma"  # "chroma" | "pinecone" | "faiss" 등
    embedding_model: str = "gemini-embedding-001"
    embedding_provider: str = "google"  # "google" | "openai" | "huggingface"
    persist_directory: str = "./chroma"
    
    # Chroma 전용 설정
    chroma_settings: ChromaSettings = field(default_factory=lambda: ChromaSettings(
        anonymized_telemetry=False,
        is_persistent=True
    ))
    
    def __post_init__(self):
        """Chroma 설정 초기화"""
        # persist_directory를 settings에 동적으로 반영
        self.chroma_settings.persist_directory = self.persist_directory

    # 다른 DB 추가 시 여기에 설정 추가
    # pinecone_api_key: Optional[str] = None
    # pinecone_environment: Optional[str] = None


# --------------------------------------------------------------------------
# RAG 검색 제한 설정 (토큰 제한)
# --------------------------------------------------------------------------

# 🔧 여기만 수정하면 전체 시스템에 적용됨
MAX_SEARCH_RESULTS = 300  # 한 번에 검색할 수 있는 최대 아티팩트 개수


# 기본 설정 인스턴스
DEFAULT_DB_CONFIG = VectorDBConfig()


def get_embeddings(config: VectorDBConfig = DEFAULT_DB_CONFIG):
    """
    설정에 따라 적절한 임베딩 모델을 반환합니다.
    
    Args:
        config: 벡터 DB 설정
    
    Returns:
        임베딩 모델 인스턴스
    """
    if config.embedding_provider == "google":
        return GoogleGenerativeAIEmbeddings(model=config.embedding_model)
    elif config.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=config.embedding_model)
    # 다른 provider 추가 가능
    else:
        raise ValueError(f"Unknown embedding provider: {config.embedding_provider}")


def create_vectorstore(
    collection_name: str,
    config: VectorDBConfig = DEFAULT_DB_CONFIG
) -> VectorStore:
    """
    설정에 따라 벡터 스토어를 생성합니다.
    ThreadPoolExecutor 환경에서 안전하게 동작하도록 PersistentClient를 명시적으로 사용합니다.
    
    Args:
        collection_name: 컬렉션 이름
        config: 벡터 DB 설정
    
    Returns:
        VectorStore 인스턴스
    """
    embeddings = get_embeddings(config)
    
    if config.db_type == "chroma":
        import chromadb
        
        # ThreadPoolExecutor 환경에서 안전하게 동작하도록 chromadb.PersistentClient 직접 사용
        client = chromadb.PersistentClient(
            path=config.persist_directory,
            settings=config.chroma_settings
        )
        
        return Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings
        )
    elif config.db_type == "pinecone":
        # from langchain_pinecone import PineconeVectorStore
        # return PineconeVectorStore(...)
        raise NotImplementedError("Pinecone support not yet implemented")
    elif config.db_type == "faiss":
        # from langchain_community.vectorstores import FAISS
        # return FAISS(...)
        raise NotImplementedError("FAISS support not yet implemented")
    else:
        raise ValueError(f"Unknown db_type: {config.db_type}")


# --------------------------------------------------------------------------
# 데이터베이스 저장 함수
# --------------------------------------------------------------------------


def save_to_chroma(
    artifacts: List[dict],
    collection_name: str = "filtered_artifacts",
    config: VectorDBConfig = DEFAULT_DB_CONFIG
) -> Dict:
    """
    필터링된 아티팩트를 벡터 데이터베이스에 저장합니다.
    메타데이터 최소화: ID와 필터링용 정보만 저장, 데이터는 page_content에 텍스트로 저장
    
    Args:
        artifacts: 저장할 아티팩트 리스트
        collection_name: 컬렉션 이름
        config: 벡터 DB 설정
    
    Returns:
        Dict: {"data_save_status": "success" | "failure", "message": str, "count": int}
    """
    try:
        if not artifacts:
            return {
                "data_save_status": "success",
                "message": "저장할 아티팩트가 없습니다.",
                "count": 0
            }
        
        print(f"--- 💾 {config.db_type.upper()} DB에 {len(artifacts)}개 아티팩트 저장 중... ---")
        
        # 1. 임베딩 모델 초기화
        embeddings = get_embeddings(config)
        
        # 2. 아티팩트를 Document로 변환
        documents = []
        
        for idx, artifact in enumerate(artifacts):
            # 아티팩트의 주요 정보 추출
            artifact_type = artifact.get('artifact_type', 'unknown')
            artifact_id = artifact.get('id', f'artifact_{idx}')
            source = artifact.get('source', 'unknown')
            data = convert_datetime_to_str(artifact.get('data', {}))
            collected_at = convert_datetime_to_str(artifact.get('collected_at', None))
            
            # 🔹 검색 가능한 텍스트 생성 (타입 + data 필드들)
            # 예: "Type: usb_files\ndevice_name: Samsung Galaxy S10\nserial_number: SM_G975F..."
            content_parts = [f"Type: {artifact_type}"]
            for key, value in data.items():
                if value:  # None이나 빈 문자열 제외
                    # datetime 객체는 문자열로 변환하여 텍스트에 포함
                    if isinstance(value, (datetime, date)):
                        content_parts.append(f"{key}: {value.isoformat()}")
                    else:
                        content_parts.append(f"{key}: {value}")
            
            page_content = "\n".join(content_parts)
            
            # 🔹 메타데이터는 최소한만 저장 (ID와 검색 필터용 정보만)
            # datetime은 타임스탬프(숫자)로 저장하여 Chroma DB 필터링 가능하게 함
            datetime_timestamp = datetime_to_timestamp(collected_at)
            
            metadata = {
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "source": source,
                "datetime": collected_at,  # ISO 문자열 (검색 결과 표시용)
                "timestamp": datetime_timestamp,  # 타임스탬프 (필터링용)
                "index": idx
            }
            
            documents.append(
                Document(page_content=page_content, metadata=metadata)
            )
        
        # 3. 벡터 DB에 저장 (DB 타입에 따라 자동 선택)
        if config.db_type == "chroma":
            # 🔹 대용량 데이터 처리: 5,000개씩 배치로 나눠서 저장
            BATCH_SIZE = 5000
            total_docs = len(documents)
            
            if total_docs <= BATCH_SIZE:
                # 5,000개 이하면 한 번에 저장
                vectorstore = Chroma.from_documents(
                    documents=documents,
                    embedding=embeddings,
                    collection_name=collection_name,
                    persist_directory=config.persist_directory
                )
                print(f"  ✅ {total_docs}개 아티팩트 저장 완료")
            else:
                # 5,000개 초과 시 배치 저장
                print(f"  📦 대용량 데이터 감지: {total_docs:,}개를 {BATCH_SIZE:,}개씩 배치 저장")
                
                # 첫 번째 배치로 벡터스토어 생성
                first_batch = documents[:BATCH_SIZE]
                vectorstore = Chroma.from_documents(
                    documents=first_batch,
                    embedding=embeddings,
                    collection_name=collection_name,
                    persist_directory=config.persist_directory
                )
                print(f"     ✓ 배치 1/{(total_docs + BATCH_SIZE - 1) // BATCH_SIZE}: {len(first_batch):,}개 저장 완료")
                
                # 나머지 배치 추가
                for batch_idx in range(BATCH_SIZE, total_docs, BATCH_SIZE):
                    batch_num = (batch_idx // BATCH_SIZE) + 1
                    batch_docs = documents[batch_idx:batch_idx + BATCH_SIZE]
                    
                    vectorstore.add_documents(batch_docs)
                    print(f"     ✓ 배치 {batch_num}/{(total_docs + BATCH_SIZE - 1) // BATCH_SIZE}: {len(batch_docs):,}개 저장 완료")
                
                print(f"  ✅ 전체 {total_docs:,}개 아티팩트 배치 저장 완료")
        else:
            raise NotImplementedError(f"{config.db_type} 저장 미구현")
        
        print(f"  📁 위치: {config.persist_directory}/{collection_name}")
        
        return {
            "data_save_status": "success",
            "message": f"{len(documents)}개 아티팩트 저장 완료",
            "count": len(documents),
            "collection_name": collection_name,  # RAG tool에서 사용
            "db_config": {  # RAG tool이 DB 재생성에 필요한 정보
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
    워크플로우 노드: 필터링된 데이터를 벡터 데이터베이스에 저장합니다.
    매 작업마다 새로운 벡터 DB로 시작합니다.
    
    Args:
        state: AgentState (TypedDict)
    
    Returns:
        Dict: 업데이트된 상태 (data_save_status, collection_name, db_config 포함)
    """
    print("--- 💾 Node: 필터링된 데이터 저장 시도... ---")
    
    filtered_artifacts = state.get("filtered_artifacts", [])
    
    # 🔹 간단한 고정 컬렉션 이름 사용 (Chroma 이름 규칙 준수)
    collection_name = "artifacts_collection"
    
    # 🔹 벡터 DB 초기화 (이전 컬렉션 삭제)
    try:
        import shutil
        chroma_path = Path(DEFAULT_DB_CONFIG.persist_directory) / collection_name
        if chroma_path.exists():
            shutil.rmtree(chroma_path)
            print(f"  🗑️  이전 벡터 DB 컬렉션 초기화 완료")
    except Exception as e:
        print(f"  ⚠️  벡터 DB 초기화 중 오류 (무시): {e}")
    
    # 기본 설정으로 저장 (여기서 DB 타입 변경 가능)
    result = save_to_chroma(
        artifacts=filtered_artifacts,
        collection_name=collection_name,
        config=DEFAULT_DB_CONFIG  # 설정 변경 시 여기만 수정
    )
    
    if result["data_save_status"] == "success":
        print(f"--- ✅ Node: 데이터 저장 성공 ({result['count']}개) ---")
    else:
        print(f"--- ❌ Node: 데이터 저장 실패 ---")
    
    return result

