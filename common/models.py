import enum
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ScenarioBase(BaseModel):
    job_id: str
    task_id: str
    report_detail_id: Optional[str]
    name: str
    description: Optional[str]

class ScenarioStepCreate(BaseModel):
    order_no: int
    timestamp: Optional[datetime]
    description: str
    artifact_ids: List[str]

class ScenarioCreate(ScenarioBase):
    steps: List[ScenarioStepCreate] = Field(..., description="List Data of Scenariosteps")


class SectionTypeEnum(int, enum.Enum):
    analysis_objective = 0 # 분석 목적
    data_collection_method = 1 # 데이터 수집 방법 (정적)
    data_collection_period = 2 # 데이터 수집 기간
    analysis_schedule = 3 # 분석 일정(시작 - 종료 시간)
    analysis_method = 4 # 분석 방법 
    analysis_procedure = 5 # 분석 절차 
    analysis_limitation = 6 # 분석 한계 (정적처리)
    key_findings = 7 # 주요 발견 내용 (결과 요약)
    detailed_analysis = 8 # 상세 분석 -> analysis_results 들어감.
    Scenario_synthesis = 9 # 시나리오 종합
    result = 10 # 결과 종합 및 의견 제시

class ReportBase(BaseModel):
    title: str = Field(..., description="보고서 제목")
    summary: Optional[str] = Field(None, description="보고서 요약")
    pc_id: str = Field(..., description="관련 PC ID")
    task_id: str = Field(..., description="관련 Task ID")

class ReportDetailBase(BaseModel):
    section_type: SectionTypeEnum = Field(..., description="섹션 유형")
    content: Optional[str] = Field(None, description="상세 내용")
    order_no: Optional[int] = Field(None, description="순서")

class ReportDetailCreate(ReportDetailBase):
    pass

class ReportCreate(ReportBase):
    details: List[ReportDetailCreate] = Field(..., description="보고서 상세 항목 리스트")