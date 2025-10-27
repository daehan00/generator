"""
클래스 정의 모듈
"""

from typing import List, TypedDict, Annotated, Optional, Dict, Any, get_type_hints, get_origin
from pydantic import BaseModel, Field
import operator

from common.models import ScenarioCreate, ScenarioStepCreate


# --------------------------------------------------------------------------
# RAG 검색 제한 설정 (database.py와 동기화)
# --------------------------------------------------------------------------
# 🔧 주의: 이 값은 database.py의 MAX_SEARCH_RESULTS와 동일해야 함
MAX_SEARCH_RESULTS = 300  # 한 번에 검색할 수 있는 최대 아티팩트 개수


class ChunkAnalysisResult(BaseModel):
    """Map 단계에서 필터링된 중요 아티팩트 리스트"""
    important_artifacts: List[dict] = Field(
        description="정보유출과 관련된 중요한 아티팩트만 선별한 리스트. 각 아티팩트는 원본 데이터 구조 그대로 유지."
    )
    chunk_summary: str = Field(
        description="이 청크에서 발견된 의심 활동을 한 문장으로 간단히 요약 (예: '악성 파일 다운로드 및 실행')"
    )


class FilterResult(BaseModel):
    """필터링 결과 (index 리스트)"""
    important_indices: List[int] = Field(description="중요한 아티팩트의 index 번호 리스트")
    chunk_summary: str = Field(description="청크의 간단한 요약 (한 문장)")


class AgentState(TypedDict, total=False):
    """LangGraph 워크플로우 전체 상태 (필터링 + 에이전트 + 보고서)"""
    
    # -- 초기 입력 (필수) --
    job_id: str  # 작업 ID
    task_id: str  # 태스크 ID
    job_info: dict # 작업 관련 정보
    
    # -- 1단계: 필터링 관련 필드 (필수) --
    artifact_chunks: List[List[dict]]  # 청크로 나눈 아티팩트
    intermediate_results: List[ChunkAnalysisResult]  # 청크별 필터링 결과
    filter_iteration: int  # 현재 필터링 반복 횟수
    target_artifact_count: int  # 목표 아티팩트 개수
    current_strictness: str  # 현재 필터링 강도

    # -- 이후 단계 (선택) --
    current_chunk_index: Optional[int]  # 현재 처리 중인 청크 인덱스
    raw_user_requirements: Optional[str]  # 사용자 요구사항

    # -- 필터링 완료 후 --
    filtered_artifacts: Optional[List[dict]]  # 필터링된 최종 아티팩트
    data_save_status: Optional[str]  # 데이터 저장 상태 (success/failure)
    collection_name: Optional[str]  # 벡터 DB 컬렉션 이름 (RAG tool에서 사용)
    db_config: Optional[Dict[str, Any]]  # 벡터 DB 설정 (RAG tool이 DB 재생성에 필요)
    
    # -- 요구사항 분석 --
    analyzed_user_requirements: Optional[str]  # 분석된 사용자 요구사항
    # analyzed_system_requirements 제거: prompts.py의 AGENT_SYSTEM_PROMPT 사용
    
    # -- 2단계: 에이전트 분석 --
    messages: Annotated[Optional[List[Any]], operator.add]  # 에이전트 대화 히스토리
    analysis_failed: Optional[bool]  # 에이전트 분석 실패 여부 (오류 발생 시 True)
    
    # -- 3단계: 최종 결과 --
    final_report: Optional[ScenarioCreate]  # 최종 분석 보고서
    context: Optional[str]


class Artifact(BaseModel):
    """분석 대상이 되는 원본 아티팩트의 기본 구조
    
    Note: 입력 데이터에 다른 속성이 더 있을 수 있지만, 
          여기 지정된 필드만 추출하여 처리합니다.
    """
    id: str
    artifact_type: str
    source: str
    data: Dict[str, Any]


class StructuredQuery(BaseModel):
    """Query Planner가 생성하는 구조화된 아티팩트 검색 쿼리
    
    LLM이 자율적으로 필터링 여부를 판단합니다.
    모든 필터는 Optional이며, 기본값은 필터링 없음입니다.
    """
    
    # 벡터 검색 쿼리 (필수)
    query_text: str = Field(
        description="벡터 검색에 사용할 핵심 키워드 또는 문장"
    )
    
    # 1차 필터: artifact_type (Optional)
    filter_artifact_types: Optional[List[str]] = Field(
        default=None,
        description="1차 필터: 검색할 아티팩트 타입 리스트. None이면 필터링 안 함 (예: ['usb_files', 'browser_history'])"
    )
    
    # 1차 필터: datetime 범위 (Optional)
    filter_datetime_start: Optional[str] = Field(
        default=None,
        description="1차 필터: 검색 시작 시간 (ISO 8601 형식). None이면 필터링 안 함 (예: '2024-01-15T10:00:00')"
    )
    filter_datetime_end: Optional[str] = Field(
        default=None,
        description="1차 필터: 검색 종료 시간 (ISO 8601 형식). None이면 필터링 안 함 (예: '2024-01-15T20:00:00')"
    )
    
    # 2차 검색: 유사도
    max_results: Optional[int] = Field(
        default=10,
        ge=1,
        le=MAX_SEARCH_RESULTS,
        description=f"반환할 최대 결과 개수 (1~{MAX_SEARCH_RESULTS}개, 기본 10개)"
    )
    similarity_threshold: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="유사도 임계값 (0.0~1.0, 낮을수록 더 엄격한 필터링)"
    )


# 수정된 보고서를 직접 받기 위한 스키마
class ReviewedScenario(BaseModel):
    name: str = Field(description="보고서 제목")
    description: str = Field(description="수정된 전체 흐름 요약")
    job_id: str = Field(description="작업 ID")
    task_id: str = Field(description="태스크 ID")
    steps: List[ScenarioStepCreate] = Field(description="검토 후 수정된 Step 리스트 (5-10개)")
    review_summary: str = Field(description="수정 사항 요약")


def create_initial_state(**kwargs) -> dict:
    """
    AgentState의 필수 필드를 자동으로 검증하여 초기 상태 생성
    
    사용 예:
        initial_state = create_initial_state(
            job_id="test",
            task_id="123",
            job_info={},
            artifact_chunks=[artifacts]
        )
    """
    # TypedDict의 필수/선택 필드 자동 추출
    required_keys = AgentState.__required_keys__
    optional_keys = AgentState.__optional_keys__
    
    # 필수 필드 검증
    missing_keys = required_keys - kwargs.keys()
    if missing_keys:
        raise ValueError(f"필수 필드 누락: {missing_keys}")
    
    # 선택 필드 검증
    not_allowed_keys = kwargs.keys() - required_keys - optional_keys
    if not_allowed_keys:
        raise ValueError(f"허용되지 않은 키 입력: {not_allowed_keys}")
    
    return dict(kwargs)


class BooleanResponse(BaseModel):
    is_done: bool