#!/usr/bin/env python3
"""
빠른 검색 테스트 스크립트

단일 쿼리를 빠르게 테스트하기 위한 간단한 스크립트입니다.
대화형 UI 없이 바로 결과를 확인할 수 있습니다.

사용 방법:
    python quick_test.py "USB 장치에서 복사된 파일을 찾아주세요"
    python quick_test.py "2025년 6월 이후 브라우저 히스토리"
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def quick_search(query: str, collection_name: str = "artifacts_collection"):
    """빠른 검색 수행"""
    from workflow.tools import query_planner_tool, artifact_search_tool
    
    print("=" * 80)
    print(f"검색 쿼리: {query}")
    print("=" * 80)
    print()
    
    # 1. 쿼리 생성
    print("🧠 쿼리 생성 중...")
    try:
        structured_query = query_planner_tool.invoke({"natural_language_goal": query})
        print(f"✅ 쿼리 생성 완료")
        print(f"   - query_text: {structured_query.get('query_text')}")
        print(f"   - filters: artifact_types={structured_query.get('filter_artifact_types')}")
        print(f"   - max_results: {structured_query.get('max_results')}")
        print()
    except Exception as e:
        print(f"❌ 쿼리 생성 실패: {e}")
        return
    
    # 2. 검색 수행
    print("🔍 검색 수행 중...")
    try:
        result = artifact_search_tool.invoke({
            "structured_query": structured_query,
            "collection_name": collection_name,
            "db_config": None,
        }, config={"recursion_limit": 40})
        
        artifacts = result.get("artifacts", [])
        message = result.get("message", "검색 완료")
        
        print(f"✅ {message}")
        print()
        
        if not artifacts:
            print("⚠️  검색 결과가 없습니다.")
            return
        
        # 결과 출력
        print(f"📊 검색 결과: {len(artifacts)}개")
        print("-" * 80)
        
        for idx, artifact in enumerate(artifacts[:10], 1):  # 상위 10개만
            print(f"\n[{idx}]")
            print(f"  ID: {artifact.get('id', 'N/A')}")
            print(f"  Type: {artifact.get('artifact_type', 'N/A')}")
            print(f"  Source: {artifact.get('source', 'N/A')}")
            print(f"  Time: {artifact.get('datetime', 'N/A')}")
            
            # 주요 정보만 출력
            for key in artifact.keys():
                if key in artifact and artifact[key]:
                    print(f"  {key}: {artifact[key]}")
        
        if len(artifacts) > 10:
            print(f"\n... 외 {len(artifacts) - 10}개 결과 생략 ...")
        
    except Exception as e:
        print(f"❌ 검색 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    # 환경 변수 확인
    # if not os.getenv("GOOGLE_API_KEY"):
    #     print("⚠️  경고: GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
    #     print()
    
    # 명령줄 인자 확인
    if len(sys.argv) < 2:
        print("사용법: python quick_test.py \"검색 쿼리\"")
        print()
        print("예시:")
        print('  python quick_test.py "USB 장치에서 복사된 파일"')
        print('  python quick_test.py "2025년 6월 이후 브라우저 히스토리"')
        print('  python quick_test.py "PDF 파일 다운로드 기록"')
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    quick_search(query)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
