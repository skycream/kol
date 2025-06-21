#!/usr/bin/env python3
"""
data 폴더 내의 모든 json 파일을 찾아서 DB에 삽입하는 스크립트

사용법:
    python process_all_json.py                    # 기본값 사용
    python process_all_json.py --data-dir custom # 커스텀 data 디렉토리
    python process_all_json.py --db-path test.db # 커스텀 DB 경로
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# json_inserter 모듈 임포트
from json_inserter import JSONDatabaseInserter

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'json_processing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


class JSONProcessor:
    """data 폴더 내의 JSON 파일들을 찾아서 DB에 삽입하는 클래스"""
    
    def __init__(self, data_dir: str = "data", db_path: str = "db.db"):
        """
        Args:
            data_dir: data 폴더 경로
            db_path: SQLite DB 파일 경로
        """
        self.data_dir = Path(data_dir)
        self.db_path = db_path
        self.processed_files = []
        self.duplicate_files = []
        self.error_files = []
        
    def find_json_files(self) -> List[Path]:
        """
        data 폴더 내의 모든 json 파일을 찾음
        
        Returns:
            JSON 파일 경로 리스트
        """
        json_files = []
        
        if not self.data_dir.exists():
            logger.error(f"data 디렉토리가 존재하지 않습니다: {self.data_dir}")
            return json_files
            
        # data/*/json/*.json 패턴으로 파일 찾기
        for id_dir in self.data_dir.iterdir():
            if id_dir.is_dir():
                json_dir = id_dir / "json"
                if json_dir.exists():
                    for json_file in json_dir.glob("*.json"):
                        json_files.append(json_file)
                        
        return sorted(json_files)
        
    def process_json_file(self, json_path: Path, inserter: JSONDatabaseInserter) -> Tuple[bool, str]:
        """
        개별 JSON 파일을 처리
        
        Args:
            json_path: JSON 파일 경로
            inserter: JSONDatabaseInserter 인스턴스
            
        Returns:
            (성공여부, 메시지) 튜플
        """
        try:
            # JSON 파일 읽기
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
            # 공고ID 추출
            공고ID = json_data.get('기본정보', {}).get('공고ID')
            if not 공고ID:
                return False, "공고ID가 없습니다"
                
            # 중복 체크
            if inserter.check_duplicate_announcement(str(공고ID)):
                return False, f"공고ID {공고ID}가 이미 존재합니다"
                
            # DB에 삽입
            result = inserter.insert_json_data(json_data)
            
            if result:
                return True, f"공고ID {공고ID} 삽입 성공"
            else:
                return False, "삽입 실패"
                
        except json.JSONDecodeError as e:
            return False, f"JSON 파싱 오류: {str(e)}"
        except Exception as e:
            return False, f"처리 오류: {str(e)}"
            
    def process_all(self) -> Dict[str, int]:
        """
        모든 JSON 파일을 처리
        
        Returns:
            처리 결과 통계
        """
        # JSON 파일 찾기
        json_files = self.find_json_files()
        
        if not json_files:
            logger.warning("처리할 JSON 파일이 없습니다.")
            return {"total": 0, "success": 0, "duplicate": 0, "error": 0}
            
        logger.info(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.")
        
        # DB 연결
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            inserter = JSONDatabaseInserter(conn)
            
            # 각 파일 처리
            for json_file in json_files:
                logger.info(f"\n처리 중: {json_file}")
                
                success, message = self.process_json_file(json_file, inserter)
                
                if success:
                    self.processed_files.append((json_file, message))
                    logger.info(f"✅ {message}")
                elif "이미 존재" in message:
                    self.duplicate_files.append((json_file, message))
                    logger.warning(f"⚠️ {message}")
                else:
                    self.error_files.append((json_file, message))
                    logger.error(f"❌ {message}")
                    
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 오류: {str(e)}")
        finally:
            if 'conn' in locals():
                conn.close()
                
        # 결과 통계 반환
        return {
            "total": len(json_files),
            "success": len(self.processed_files),
            "duplicate": len(self.duplicate_files),
            "error": len(self.error_files)
        }
        
    def print_summary(self, stats: Dict[str, int]):
        """처리 결과 요약 출력"""
        print("\n" + "="*60)
        print("📊 처리 결과 요약")
        print("="*60)
        print(f"📁 총 파일 수: {stats['total']}")
        print(f"✅ 성공: {stats['success']}")
        print(f"⚠️  중복: {stats['duplicate']}")
        print(f"❌ 오류: {stats['error']}")
        print("="*60)
        
        # 상세 내역
        if self.processed_files:
            print("\n✅ 성공적으로 처리된 파일:")
            for file_path, message in self.processed_files:
                print(f"  - {file_path.name}: {message}")
                
        if self.duplicate_files:
            print("\n⚠️  중복으로 건너뛴 파일:")
            for file_path, message in self.duplicate_files:
                print(f"  - {file_path.name}: {message}")
                
        if self.error_files:
            print("\n❌ 오류가 발생한 파일:")
            for file_path, message in self.error_files:
                print(f"  - {file_path.name}: {message}")


def check_db_exists(db_path: str) -> bool:
    """DB 파일 존재 여부 확인"""
    if not os.path.exists(db_path):
        logger.error(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        logger.info("먼저 pg_schema.py를 실행하여 데이터베이스를 생성해주세요.")
        logger.info("실행 명령: python pg_schema.py")
        return False
    return True


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="data 폴더 내의 모든 JSON 파일을 찾아서 DB에 삽입합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python process_all_json.py                        # 기본값 사용
  python process_all_json.py --data-dir custom_data # 커스텀 data 디렉토리
  python process_all_json.py --db-path custom.db    # 커스텀 DB 파일
  python process_all_json.py --dry-run              # 실제 삽입하지 않고 확인만
        """
    )
    
    parser.add_argument(
        "--data-dir",
        default="data",
        help="data 디렉토리 경로 (기본값: data)"
    )
    
    parser.add_argument(
        "--db-path",
        default="db.db",
        help="SQLite DB 파일 경로 (기본값: db.db)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 삽입하지 않고 처리 대상만 확인"
    )
    
    args = parser.parse_args()
    
    # DB 파일 확인
    if not check_db_exists(args.db_path):
        return
        
    # Dry run 모드
    if args.dry_run:
        print("🔍 DRY RUN 모드 - 실제 삽입하지 않고 대상만 확인합니다.")
        processor = JSONProcessor(args.data_dir, args.db_path)
        json_files = processor.find_json_files()
        
        print(f"\n📁 data 디렉토리: {args.data_dir}")
        print(f"💾 DB 파일: {args.db_path}")
        print(f"📋 발견된 JSON 파일: {len(json_files)}개")
        
        if json_files:
            print("\nJSON 파일 목록:")
            for idx, json_file in enumerate(json_files, 1):
                # ID 추출 (상위 디렉토리명)
                id_dir = json_file.parent.parent.name
                print(f"{idx:3d}. ID: {id_dir:10s} - {json_file.name}")
        return
        
    # 실제 처리
    print(f"🚀 JSON 파일 처리를 시작합니다.")
    print(f"📁 data 디렉토리: {args.data_dir}")
    print(f"💾 DB 파일: {args.db_path}")
    print("="*60)
    
    processor = JSONProcessor(args.data_dir, args.db_path)
    stats = processor.process_all()
    processor.print_summary(stats)
    
    print("\n✨ 처리가 완료되었습니다!")


if __name__ == "__main__":
    main()