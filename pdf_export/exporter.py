"""
PDF Report Exporter
보고서 데이터를 PDF로 변환하고 S3에 업로드하는 통합 클래스
"""

import os
import tempfile
from typing import Optional  # ✅ 이 줄 추가
from pdf_export.pdf_generator import SecurityReportPDF
from pdf_export.s3_manager import S3Manager

class PDFReportExporter:
    """
    보고서를 PDF로 변환하고 S3에 업로드하는 통합 클래스
    """
    
    def __init__(self):
        """PDFReportExporter 초기화"""
        self.pdf_generator = SecurityReportPDF()
        self.s3_manager = S3Manager()
    
    def generate_and_upload(
        self, 
        report_data: dict, 
        delete_local: bool = True,
        custom_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        보고서 데이터를 PDF로 변환하고 S3에 업로드
        
        Args:
            report_data: 보고서 데이터 딕셔너리
                - report: 보고서 메타데이터
                - main_sections: 보고서 섹션 리스트
            delete_local: 로컬 임시 파일 삭제 여부 (기본값: True)
            custom_filename: 사용자 지정 파일명 (기본값: None, 자동 생성)
        
        Returns:
            S3 업로드된 PDF URL (성공시), None (실패시)
        
        Example:
            >>> exporter = PDFReportExporter()
            >>> report = {...}  # 보고서 데이터
            >>> pdf_url = exporter.generate_and_upload(report)
            >>> print(f"PDF URL: {pdf_url}")
        """
        
        # 1. 파일명 생성
        if custom_filename:
            filename = custom_filename if custom_filename.endswith('.pdf') else f"{custom_filename}.pdf"
        else:
            report_id = report_data.get('report', {}).get('id', 'unknown')
            pc_id = report_data.get('report', {}).get('pc_id', 'unknown')
            filename = f"report_{pc_id}_{report_id[:8]}.pdf"
        
        # 2. 임시 파일 생성
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        
        try:
            print("=" * 60)
            print("📄 보고서 PDF 생성 시작...")
            print("=" * 60)
            
            # 3. PDF 생성
            self.pdf_generator.generate_from_json(
                json_data=report_data,
                output_path=temp_path
            )
            
            print()
            print("=" * 60)
            print("📤 S3 업로드 시작...")
            print("=" * 60)
            
            # 4. S3 업로드 (타임스탬프 없이 업로드)
            s3_key = self.s3_manager.generate_s3_key(filename, include_timestamp=False)
            s3_url = self.s3_manager.upload_file(
                local_path=temp_path,
                s3_key=s3_key,
                metadata={
                    'report-id': report_data.get('report', {}).get('id', ''),
                    'pc-id': report_data.get('report', {}).get('pc_id', ''),
                    'generated-by': 'ForensicGenerator'
                }
            )
            
            if s3_url:
                print()
                print("=" * 60)
                print("✅ 보고서 PDF 생성 및 업로드 완료!")
                print(f"🌐 접근 URL: {s3_url}")
                print("=" * 60)
            else:
                print()
                print("=" * 60)
                print("❌ S3 업로드 실패")
                print("=" * 60)
            
            return s3_url
            
        except Exception as e:
            print()
            print("=" * 60)
            print(f"❌ PDF 생성 중 오류 발생: {e}")
            print("=" * 60)
            return None
            
        finally:
            # 5. 임시 파일 삭제
            if delete_local and os.path.exists(temp_path):
                self.s3_manager.delete_local_file(temp_path)
    
    def generate_pdf_only(
        self, 
        report_data: dict, 
        output_path: str
    ) -> bool:
        """
        PDF만 생성 (S3 업로드 없이)
        
        Args:
            report_data: 보고서 데이터
            output_path: 출력 파일 경로
        
        Returns:
            성공 여부
        """
        try:
            self.pdf_generator.generate_from_json(
                json_data=report_data,
                output_path=output_path
            )
            return True
        except Exception as e:
            print(f"❌ PDF 생성 실패: {e}")
            return False