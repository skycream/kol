import os
import time
import re
import requests
import hashlib
import logging
from datetime import datetime
from typing import Dict, Set, Optional, Tuple
from bs4 import BeautifulSoup
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class CrawlerConfig:
    """크롤러 설정 클래스"""
    DEFAULT_START_ID: int = 29200
    BASE_PAGE: str = "https://www.scourt.go.kr/portal/notice/realestate/RealNoticeView.work"
    DOWNLOAD_URL: str = "https://file.scourt.go.kr/AttachDownload"
    DOWNLOAD_FOLDER_NAME: str = "Crawler"  # 변경 가능한 폴더명
    MAX_EXPIRED: int = 200
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5
    REQUEST_DELAY: float = 2.0
    HEADERS: Dict[str, str] = None

    def __post_init__(self):
        if self.HEADERS is None:
            self.HEADERS = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }


class FileManager:
    """파일 관리 클래스"""

    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.base_dir = Path(config.DOWNLOAD_FOLDER_NAME)
        self.base_dir.mkdir(exist_ok=True)

    def get_download_dir(self, seq_id: int) -> Path:
        """특정 seq_id의 다운로드 디렉토리 반환 (pdf 하위 폴더 포함)"""
        download_dir = self.base_dir / str(seq_id) / "pdf"
        download_dir.mkdir(parents=True, exist_ok=True)
        return download_dir

    def get_last_seq_id_from_folders(self) -> int:
        """폴더 구조에서 마지막 seq_id 찾기"""
        try:
            if not self.base_dir.exists():
                return self.config.DEFAULT_START_ID

            # 숫자로 된 폴더명들 찾기
            seq_ids = []
            for folder in self.base_dir.iterdir():
                if folder.is_dir() and folder.name.isdigit():
                    seq_ids.append(int(folder.name))

            if seq_ids:
                last_id = max(seq_ids)
                print(f"Found last seq_id from folder structure: {last_id}")
                return last_id + 1  # 다음 ID부터 시작
            else:
                print(f"No existing folders found, starting from: {self.config.DEFAULT_START_ID}")
                return self.config.DEFAULT_START_ID

        except Exception as e:
            print(f"Error reading folder structure: {e}")
            return self.config.DEFAULT_START_ID

    def file_exists_in_folder(self, seq_id: int, filename: str) -> bool:
        """특정 폴더에 파일이 존재하는지 확인 (pdf 하위 폴더에서)"""
        download_dir = self.base_dir / str(seq_id) / "pdf"
        if not download_dir.exists():
            return False

        filepath = download_dir / filename
        return filepath.exists()


class DataExtractor:
    """데이터 추출 클래스"""

    @staticmethod
    def clean_text(text: str) -> str:
        """텍스트 정리"""
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def clean_filename(text: str) -> str:
        """파일명에 부적절한 문자 제거"""
        return re.sub(r'[\\/*?:"<>|\n\r\t;]', '_', text).strip()

    def extract_table_data(self, soup: BeautifulSoup, seq_id: int) -> Dict[str, str]:
        """테이블 데이터 추출"""
        try:
            content_div = soup.find("div", class_="contentIn")
            if not content_div:
                logging.warning(f"[{seq_id}] contentIn div not found")
                return {}

            table = content_div.find("table")
            if not table:
                logging.warning(f"[{seq_id}] Table not found")
                return {}

            data = {}
            rows = table.find_all("tr")

            for row in rows:
                th = row.find("th")
                tds = row.find_all("td")

                if not (th and tds):
                    continue

                th_text = self.clean_text(th.get_text())

                # 각 필드별 처리
                if th_text == "매각기관":
                    data["매각기관"] = self.clean_text(tds[0].get_text())
                elif th_text == "관할법원":
                    data["관할법원"] = self.clean_text(tds[0].get_text())
                elif th_text == "제목":
                    data["제목"] = self.clean_text(tds[0].get_text())
                    if len(tds) >= 2:
                        data["조회수"] = self.clean_text(tds[1].get_text())
                elif th_text == "작성일":
                    data["작성일"] = self.clean_text(tds[0].get_text())
                    if len(tds) >= 2:
                        data["공고만료일"] = self.clean_text(tds[1].get_text())
                elif th_text == "공고만료일":
                    data["공고만료일"] = self.clean_text(tds[0].get_text())
                elif th_text == "첨부파일":
                    data["첨부파일"] = self.clean_text(tds[0].get_text())
                elif th_text == "전화번호":
                    data["전화번호"] = self.clean_text(tds[0].get_text())

            print(f"[{seq_id}] Extracted data: {data}")
            return data

        except Exception as e:
            print(f"[{seq_id}] Table extraction error: {e}")
            return {}

    def extract_download_info(self, soup: BeautifulSoup, seq_id: int) -> Dict[str, str]:
        """다운로드 정보 추출"""
        a_tag = soup.find("a", href=re.compile(r"javascript:download"))
        if not a_tag:
            print(f"[{seq_id}] Download link not found")
            return {}

        match = re.search(r"download\('([^']+)',\s*'([^']+)'\)", a_tag['href'])
        if not match:
            print(f"[{seq_id}] Invalid download link format")
            return {}

        download_info = {
            "file": match.group(1),
            "downFile": match.group(2),
            "path": "011"
        }

        print(f"[{seq_id}] Download info: {download_info}")
        return download_info


class CourtCrawler:
    """법원 공고 크롤러 메인 클래스"""

    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        self.file_manager = FileManager(self.config)
        self.extractor = DataExtractor()
        self.session = requests.Session()
        self.session.headers.update(self.config.HEADERS)
        self.downloaded_files = set()  # 메모리에서만 중복 체크

    def generate_file_hash(self, data: Dict[str, str]) -> str:
        """파일의 고유 해시 생성 (조회수 제외)"""
        key_fields = ["매각기관", "관할법원", "제목", "작성일", "공고만료일", "downFile", "전화번호"]
        key_parts = [data.get(field, "") for field in key_fields]
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()

    def create_filename(self, data: Dict[str, str], seq_id: int) -> str:
        """파일명 생성"""
        try:
            # 원본 파일명에서 확장자 분리
            original_filename = data.get("downFile", "unknown")
            if '.' in original_filename:
                name_part, ext = original_filename.rsplit('.', 1)
                ext = '.' + ext
            else:
                name_part, ext = original_filename, ""

            # 파일명 구성 요소들
            components = [
                str(seq_id),
                data.get("매각기관", ""),
                data.get("관할법원", ""),
                data.get("제목", ""),
                data.get("조회수", ""),
                data.get("작성일", ""),
                data.get("공고만료일", ""),
                name_part,
                data.get("전화번호", "")
            ]

            # 각 구성 요소 정리
            cleaned_components = [self.extractor.clean_filename(comp) for comp in components]

            # 세미콜론으로 연결하고 확장자 추가
            filename = ";".join(cleaned_components) + ext

            # 파일명이 너무 길면 줄이기 (Windows 파일명 제한: 260자)
            if len(filename) > 200:
                # 제목 부분만 줄이기
                title_idx = 3
                max_title_length = 50
                if len(cleaned_components[title_idx]) > max_title_length:
                    cleaned_components[title_idx] = cleaned_components[title_idx][:max_title_length] + "..."
                filename = ";".join(cleaned_components) + ext

            return filename

        except Exception as e:
            print(f"[{seq_id}] Filename creation error: {e}")
            return f"{seq_id}_{self.extractor.clean_filename(data.get('downFile', 'unknown'))}"

    def fetch_page_data(self, seq_id: int) -> Optional[Dict]:
        """페이지에서 데이터 가져오기"""
        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = self.session.get(
                    self.config.BASE_PAGE,
                    params={"seq_id": seq_id},
                    timeout=30
                )

                if response.status_code != 200:
                    print(f"[{seq_id}] HTTP {response.status_code}")
                    continue

                soup = BeautifulSoup(response.text, "html.parser")

                # 만료된 공고 확인
                if "공고만료일 지난 건으로 조회되지 않습니다." in soup.text:
                    return "EXPIRED"

                # 데이터 추출
                download_info = self.extractor.extract_download_info(soup, seq_id)
                if not download_info:
                    return {}

                table_data = self.extractor.extract_table_data(soup, seq_id)

                # 데이터 병합
                combined_data = {**download_info, **table_data}
                return combined_data

            except Exception as e:
                print(f"[{seq_id}] Attempt {attempt + 1} failed: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY)

        return None

    def download_file(self, data: Dict[str, str], seq_id: int) -> bool:
        """파일 다운로드 (pdf 하위 폴더에 저장)"""
        if not all(k in data for k in ("file", "path", "downFile")):
            print(f"[{seq_id}] Missing required fields")
            return False

        # 파일 해시 생성
        file_hash = self.generate_file_hash(data)

        # 메모리에서 중복 확인
        if file_hash in self.downloaded_files:
            print(f"[{seq_id}] Already downloaded (hash: {file_hash[:8]}...)")
            return False

        # 파일명 생성
        filename = self.create_filename(data, seq_id)

        # seq_id/pdf 폴더에 저장
        download_dir = self.file_manager.get_download_dir(seq_id)
        filepath = download_dir / filename

        # 파일 존재 확인
        if filepath.exists():
            print(f"[{seq_id}] File already exists: {filename}")
            self.downloaded_files.add(file_hash)
            return False

        # 다운로드 시도
        for attempt in range(self.config.MAX_RETRIES):
            try:
                post_data = {
                    'file': data['file'],
                    'path': data['path'],
                    'downFile': data['downFile']
                }

                response = self.session.post(
                    self.config.DOWNLOAD_URL,
                    data=post_data,
                    timeout=60
                )

                content_type = response.headers.get("Content-Type", "").lower()

                if (response.status_code == 200 and
                        ("application/pdf" in content_type or "application/octet-stream" in content_type)):

                    # 파일 저장
                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    # 다운로드 기록 (메모리에서만)
                    self.downloaded_files.add(file_hash)

                    print(f"[{seq_id}] Downloaded to pdf folder: {filename}")
                    return True

                else:
                    print(f"[{seq_id}] Download failed (status: {response.status_code}, type: {content_type})")

            except Exception as e:
                print(f"[{seq_id}] Download attempt {attempt + 1} failed: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY)

        return False

    def get_starting_seq_id(self) -> int:
        """시작할 seq_id 결정"""
        return self.file_manager.get_last_seq_id_from_folders()

    def run(self):
        """크롤러 실행"""
        start_time = datetime.now()
        print("=== Court Crawler Started ===")
        print(f"Download folder: {self.config.DOWNLOAD_FOLDER_NAME}")
        print("PDF files will be saved in: [ID]/pdf/ subfolders")

        # 상태 로드
        current_id = self.get_starting_seq_id()

        print(f"Starting from seq_id: {current_id}")

        expired_count = 0
        download_count = 0

        try:
            while True:
                print(f"Processing seq_id: {current_id}")

                # 페이지 데이터 가져오기
                page_data = self.fetch_page_data(current_id)

                if page_data is None:
                    print(f"[{current_id}] Failed to fetch data")
                    break

                if page_data == "EXPIRED":
                    expired_count += 1
                    print(f"[{current_id}] Expired ({expired_count}/{self.config.MAX_EXPIRED})")

                    if expired_count >= self.config.MAX_EXPIRED:
                        print(f"Reached max expired limit ({self.config.MAX_EXPIRED})")
                        break

                elif page_data:
                    # 다운로드 시도
                    success = self.download_file(page_data, current_id)
                    if success:
                        download_count += 1
                        expired_count = 0  # 성공시 만료 카운트 리셋
                    else:
                        expired_count = 0  # 이미 다운로드한 파일도 만료 카운트 리셋

                current_id += 1
                time.sleep(self.config.REQUEST_DELAY)

        except KeyboardInterrupt:
            print("Interrupted by user")
        except Exception as e:
            print(f"Unexpected error: {e}")

        finally:
            # 실행 결과 요약
            end_time = datetime.now()
            duration = end_time - start_time

            print("=== Crawling Summary ===")
            print(f"Duration: {duration}")
            print(f"New downloads: {download_count}")
            print(f"Last seq_id: {current_id - 1}")

    def close(self):
        """리소스 정리"""
        if hasattr(self, 'session') and self.session:
            self.session.close()

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.close()


# 모듈이 직접 실행될 때만 실행되는 함수들
def main():
    """메인 함수 - 직접 실행 시에만 사용"""
    # 기본 설정으로 크롤러 생성
    config = CrawlerConfig()

    # 원하는 경우 폴더명 변경 가능
    # config.DOWNLOAD_FOLDER_NAME = "MyDownloads"

    with CourtCrawler(config) as crawler:
        # 크롤러 실행
        crawler.run()


def main_with_custom_folder():
    """커스텀 폴더명으로 실행하는 예시 - 직접 실행 시에만 사용"""
    config = CrawlerConfig()
    config.DOWNLOAD_FOLDER_NAME = "CourtNotices"  # 원하는 폴더명으로 변경

    with CourtCrawler(config) as crawler:
        crawler.run()


# 다른 모듈에서 import해서 사용할 수 있는 편의 함수들
def create_crawler(folder_name: str = "Crawler", **kwargs) -> CourtCrawler:
    """크롤러 인스턴스 생성 편의 함수"""
    config = CrawlerConfig()
    config.DOWNLOAD_FOLDER_NAME = folder_name

    # 추가 설정이 있으면 적용
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return CourtCrawler(config)


def quick_crawl(folder_name: str = "Crawler", max_expired: int = 10, **kwargs):
    """빠른 크롤링 실행 함수"""
    config = CrawlerConfig()
    config.DOWNLOAD_FOLDER_NAME = folder_name
    config.MAX_EXPIRED = max_expired

    # 추가 설정
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    with CourtCrawler(config) as crawler:
        crawler.run()
        return f"Crawling completed in folder: {folder_name}"


if __name__ == "__main__":
    main()