"""
PDF Export Module
보고서를 PDF로 변환하고 S3에 업로드하는 모듈
"""

from .exporter import PDFReportExporter
from .pdf_generator import SecurityReportPDF
from .s3_manager import S3Manager

__all__ = ['PDFReportExporter', 'SecurityReportPDF', 'S3Manager', 'export_report_to_pdf']


def export_report_to_pdf(report_data: dict, delete_local: bool = True) -> str:
    """
    보고서를 PDF로 변환하고 S3에 업로드하는 간편 함수
    
    Args:
        report_data: 보고서 데이터 (report_response(251020).py 형식)
        delete_local: 로컬 임시 파일 삭제 여부
    
    Returns:
        S3 업로드된 PDF URL
    
    Example:
        >>> from pdf_export import export_report_to_pdf
        >>> report = generate_report()
        >>> pdf_url = export_report_to_pdf(report)
        >>> print(f"PDF URL: {pdf_url}")
    """
    exporter = PDFReportExporter()
    return exporter.generate_and_upload(report_data, delete_local=delete_local)