import sqlite3
import json
import logging
import os
import glob
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JSONDatabaseInserter:
    """
    새로운 prompt.json 구조의 JSON 데이터를 SQLite 데이터베이스에 삽입하는 클래스
    
    주요 특징:
    - 관재인ID 제거로 인한 구조 변경 반영
    - 모든 테이블에 자동으로 공고ID 설정
    - 트랜잭션 기반 안전한 데이터 삽입
    """
    
    def __init__(self, db_connection: sqlite3.Connection):
        """
        Args:
            db_connection: SQLite 데이터베이스 연결 객체
        """
        self.conn = db_connection
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.current_공고ID = None  # 현재 처리 중인 공고ID 저장
        
    def check_duplicate_announcement(self, 공고ID: str) -> bool:
        """
        공고ID가 이미 데이터베이스에 존재하는지 확인
        
        Args:
            공고ID: 확인할 공고ID
            
        Returns:
            bool: 중복인 경우 True, 아닌 경우 False
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM 기본정보 WHERE 공고ID = ?", (공고ID,))
        count = cursor.fetchone()[0]
        return count > 0

    def insert_json_data(self, json_data: Union[str, Dict]) -> bool:
        """
        JSON 데이터를 데이터베이스에 삽입
        
        Args:
            json_data: JSON 문자열 또는 딕셔너리
            
        Returns:
            bool: 성공 여부
        """
        try:
            # JSON 문자열인 경우 파싱
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data
            
            # 공고ID 중복 체크
            기본정보 = data.get('기본정보', {})
            공고ID = 기본정보.get('공고ID')
            if 공고ID and self.check_duplicate_announcement(str(공고ID)):
                logger.warning(f"공고ID {공고ID}는 이미 데이터베이스에 존재합니다. 건너뜁니다.")
                return False
                
            logger.info(f"JSON 데이터 삽입을 시작합니다. 공고ID: {공고ID}")
            
            # 트랜잭션 시작
            self.conn.execute("BEGIN TRANSACTION")
            
            # 1. 관재인 정보 삽입 (기본정보와 연결하지 않고 독립적으로 저장)
            trustee_data = data.get('관재인', {})
            if trustee_data:
                self._insert_trustee(trustee_data)
                logger.info("관재인 정보 삽입 완료")
            
            # 2. 매각공고 기본정보 삽입 (여기서 공고ID 생성 및 저장)
            self.current_공고ID = self._insert_auction_basic_info(
                data.get('기본정보', {}), 
                data.get('파일정보', {})
            )
            logger.info(f"매각공고 기본정보 삽입 완료. 공고ID: {self.current_공고ID}")
            
            # 3. 매각그룹목록 → 매각단위 테이블에 삽입
            sale_groups = data.get('매각그룹목록', data.get('매각단위', []))  # 호환성 지원
            self._insert_sale_groups(sale_groups)
            logger.info(f"매각단위 정보 삽입 완료. 그룹 수: {len(sale_groups)}")
            
            # 4. 원본자산목록 삽입 (자산정보 통합 처리)
            assets = data.get('원본자산목록', [])
            self._insert_original_assets_with_details(assets)
            logger.info(f"원본자산목록 삽입 완료. 자산 수: {len(assets)}")
            
            # 5. 회차별입찰정보 삽입
            bid_rounds = data.get('회차별입찰정보', [])
            self._insert_bid_rounds(bid_rounds)
            logger.info(f"회차별입찰정보 삽입 완료. 회차 수: {len(bid_rounds)}")
            
            # 6. 입찰조건 삽입
            self._insert_bid_conditions(data.get('입찰조건', {}))
            logger.info("입찰조건 삽입 완료")
            
            # 7. 강조사항 삽입
            highlights = data.get('강조사항', [])
            self._insert_highlights(highlights)
            logger.info(f"강조사항 삽입 완료. 항목 수: {len(highlights)}")
            
            # 8. 특별사항 삽입
            self._insert_special_matters(data.get('특별사항', {}))
            logger.info("특별사항 삽입 완료")
            
            # 트랜잭션 커밋
            self.conn.commit()
            logger.info(f"✅ JSON 데이터 삽입이 성공적으로 완료되었습니다. 공고ID: {self.current_공고ID}")
            return True
            
        except json.JSONDecodeError as e:
            self.conn.rollback()
            error_msg = f"JSON 파싱 오류: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
            
        except sqlite3.Error as e:
            self.conn.rollback()
            error_msg = f"데이터베이스 오류: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
            
        except Exception as e:
            self.conn.rollback()
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
            
    def _insert_trustee(self, trustee_data: Dict) -> Optional[int]:
        """
        관재인 정보 삽입 (기본정보와 연결하지 않고 독립적으로 저장)
        
        Args:
            trustee_data: 관재인 정보 딕셔너리
            
        Returns:
            Optional[int]: 관재인 ID (삽입된 경우)
        """
        if not trustee_data:
            logger.info("관재인 정보가 없어 건너뜁니다.")
            return None
            
        관재인명 = trustee_data.get('관재인명')
        전화번호 = trustee_data.get('전화번호')
        
        if not 관재인명:
            logger.warning("관재인명이 없어 관재인 정보를 저장하지 않습니다.")
            return None
            
        # 기존 관재인 확인 (중복 방지)
        existing = self.conn.execute(
            "SELECT ID FROM 관재인 WHERE 관재인명 = ? AND (전화번호 = ? OR 전화번호 IS NULL)",
            (관재인명, 전화번호)
        ).fetchone()
        
        if existing:
            logger.info(f"기존 관재인 발견: {관재인명} (ID: {existing[0]})")
            return existing[0]
            
        # 새 관재인 삽입
        cursor = self.conn.execute("""
            INSERT INTO 관재인 (관재인명, 직업, 주소, 전화번호, 팩스번호, 이메일)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            관재인명,
            trustee_data.get('직업', '변호사'),
            trustee_data.get('주소'),
            전화번호,
            trustee_data.get('팩스번호'),
            trustee_data.get('이메일')
        ))
        
        new_id = cursor.lastrowid
        logger.info(f"새 관재인 추가: {관재인명} (ID: {new_id})")
        return new_id
        
    def _insert_auction_basic_info(self, basic_info: Dict, file_info: Dict) -> str:
        """
        매각공고 기본정보 삽입 및 공고ID 반환 (관재인ID 제거됨)
        
        Args:
            basic_info: 기본정보 딕셔너리
            file_info: 파일정보 딕셔너리
            
        Returns:
            str: 생성된 공고ID
        """
        if not basic_info:
            raise ValueError("기본정보가 없습니다.")
            
        # 공고ID 생성 또는 추출
        공고ID = basic_info.get('공고ID')
        if not 공고ID:
            # 공고ID가 없으면 현재 시간 기반으로 생성
            공고ID = f"AUTO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.warning(f"공고ID가 없어 자동 생성했습니다: {공고ID}")
        else:
            # 숫자인 경우 문자열로 변환
            공고ID = str(공고ID)
            
        # 필수 필드 검증 및 기본값 설정
        사건번호 = basic_info.get('사건번호')
        if not 사건번호:
            logger.warning("사건번호가 없습니다.")
            
        채무자명 = basic_info.get('채무자명')
        if not 채무자명:
            logger.warning("채무자명이 없습니다.")
            
        # 관재인ID 필드가 제거된 기본정보 테이블에 삽입
        self.conn.execute("""
            INSERT OR REPLACE INTO 기본정보 (
                공고ID, 사건번호, 파일명, 용도구분, 총원본자산수, 총매각그룹수,
                채무자명, 채무자구분, 채무자세부유형, 파산법원,
                공고종류코드, 처분방식코드, 공고구성코드, 매각범위코드,
                파일업로드일시, 공고게시일자, 공고마감일자, 매각예정일자,
                최종수정자, 승인상태, 승인일시, 매각완료여부
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            공고ID,
            사건번호,
            file_info.get('파일명') if file_info else None,
            file_info.get('용도구분', '공고용') if file_info else '공고용',
            basic_info.get('총원본자산수', 0),
            basic_info.get('총매각그룹수', 0),
            채무자명,
            basic_info.get('채무자구분'),
            basic_info.get('채무자세부유형'),
            basic_info.get('파산법원'),
            basic_info.get('공고종류코드'),
            basic_info.get('처분방식코드'),
            basic_info.get('공고구성코드'),
            basic_info.get('매각범위코드'),
            basic_info.get('파일업로드일시'),
            basic_info.get('공고게시일자'),
            basic_info.get('공고마감일자'),
            basic_info.get('매각예정일자'),
            basic_info.get('최종수정자'),
            basic_info.get('승인상태', '대기중'),
            basic_info.get('승인일시'),
            int(basic_info.get('매각완료여부', False))
        ))
        
        return 공고ID
        
    def _insert_sale_groups(self, sale_groups: List[Dict]):
        """
        매각그룹목록을 매각단위 테이블에 삽입
        
        Args:
            sale_groups: 매각그룹목록 리스트
        """
        if not self.current_공고ID:
            raise ValueError("공고ID가 설정되지 않았습니다. 먼저 매각공고 기본정보를 삽입해주세요.")
            
        for group in sale_groups:
            매각그룹ID = group.get('매각그룹ID')
            매각방식 = group.get('매각방식')
            
            if 매각그룹ID is None:
                logger.warning(f"매각그룹ID가 없는 그룹을 건너뜁니다: {group}")
                continue
                
            if not 매각방식:
                logger.warning(f"매각방식이 없어 기본값 '개별매각'을 사용합니다. 그룹ID: {매각그룹ID}")
                매각방식 = '개별매각'
                
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO 매각단위 (공고ID, 매각그룹ID, 매각방식)
                    VALUES (?, ?, ?)
                """, (self.current_공고ID, 매각그룹ID, 매각방식))
                
            except sqlite3.Error as e:
                logger.error(f"매각단위 삽입 실패 - 그룹ID: {매각그룹ID}, 오류: {str(e)}")
                raise
                
    def _insert_original_assets_with_details(self, assets: List[Dict]):
        """
        원본자산목록과 자산별 상세정보를 함께 삽입
        
        Args:
            assets: 원본자산목록 리스트
        """
        if not self.current_공고ID:
            raise ValueError("공고ID가 설정되지 않았습니다.")
            
        for asset in assets:
            자산ID = asset.get('자산ID')
            자산명 = asset.get('자산명')
            
            if 자산ID is None:
                logger.warning(f"자산ID가 없는 자산을 건너뜁니다: {자산명}")
                continue
                
            if not 자산명:
                logger.warning(f"자산명이 없습니다. 자산ID: {자산ID}")
                
            try:
                # 1. 원본자산목록 삽입
                self.conn.execute("""
                    INSERT OR REPLACE INTO 원본자산목록 (
                        공고ID, 자산ID, 자산명, 대분류코드, 대분류명, 중분류코드, 중분류명,
                        소분류코드, 소분류명, 감정가, 위치, 규모, 현재상태, 특이사항,
                        관련사건번호, 매각그룹ID, 자산취득일자, 자산등록일자, 최종평가일자,
                        평가기관명, 매각우선순위, 매각제외사유, 환가포기여부, 환가포기사유
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.current_공고ID,
                    자산ID,
                    자산명,
                    asset.get('대분류코드'),
                    asset.get('대분류명'),
                    asset.get('중분류코드'),
                    asset.get('중분류명'),
                    asset.get('소분류코드'),
                    asset.get('소분류명'),
                    asset.get('감정가'),
                    asset.get('위치'),
                    asset.get('규모'),
                    asset.get('현재상태'),
                    asset.get('특이사항'),
                    asset.get('관련사건번호'),
                    asset.get('매각그룹ID'),
                    asset.get('자산취득일자'),
                    asset.get('자산등록일자'),
                    asset.get('최종평가일자'),
                    asset.get('평가기관명'),
                    asset.get('매각우선순위'),
                    asset.get('매각제외사유'),
                    int(asset.get('환가포기여부', 0)),
                    asset.get('환가포기사유')
                ))
                
                # 2. 자산정보 기반으로 자산 유형별 상세정보 삽입
                asset_info = asset.get('자산정보', {})
                if asset_info:
                    self._insert_asset_detail_by_type(asset, asset_info)
                    
            except sqlite3.Error as e:
                logger.error(f"자산 삽입 실패 - 자산ID: {자산ID}, 자산명: {자산명}, 오류: {str(e)}")
                raise
                
    def _insert_asset_detail_by_type(self, asset: Dict, asset_info: Dict):
        """
        자산 유형별 상세정보 삽입
        
        Args:
            asset: 자산 기본정보
            asset_info: 자산 상세정보
        """
        asset_type = asset.get('대분류코드')
        자산ID = asset.get('자산ID')
        
        try:
            if asset_type == 'RE':  # 부동산
                self._insert_real_estate_info(자산ID, asset_info)
            elif asset_type == 'CL':  # 채권
                self._insert_credit_info(자산ID, asset_info)
            elif asset_type == 'MP':  # 동산
                self._insert_movable_info(자산ID, asset_info)
            elif asset_type == 'IP':  # 지적재산권
                self._insert_ip_info(자산ID, asset_info)
            elif asset_type == 'ES':  # 주식
                self._insert_stock_info(자산ID, asset_info)
            elif asset_type == 'TE':  # 운송수단
                self._insert_vehicle_info(자산ID, asset_info)
            elif asset_type == 'OA':  # 기타자산
                self._insert_other_asset_info(자산ID, asset_info)
            elif asset_type == 'IC':  # 출자증권
                self._insert_investment_info(자산ID, asset_info)
            else:
                logger.warning(f"알 수 없는 자산 유형: {asset_type} (자산ID: {자산ID})")
                
        except sqlite3.Error as e:
            logger.error(f"자산 상세정보 삽입 실패 - 자산ID: {자산ID}, 유형: {asset_type}, 오류: {str(e)}")
            raise
            
    def _insert_real_estate_info(self, 자산ID: int, asset_info: Dict):
        """부동산정보 삽입"""
        # 면적 정보 처리
        대지면적_str = asset_info.get('대지면적', '')
        전체면적_float = None
        
        if 대지면적_str:
            try:
                # "380㎡" 같은 형식에서 숫자만 추출
                import re
                numbers = re.findall(r'[\d.]+', str(대지면적_str))
                if numbers:
                    전체면적_float = float(numbers[0])
            except (ValueError, IndexError):
                logger.warning(f"대지면적 파싱 실패: {대지면적_str}")
                전체면적_float = None
                
        self.conn.execute("""
            INSERT OR REPLACE INTO 부동산정보 (
                공고ID, 자산ID, 주소, 지목, 용도지역, 용도지구, 건물구조, 건축면적,
                대지면적, 연면적, 전체면적, 지분표기, 지분율, 실제매각면적,
                실제매각면적_평, 권리관계, 담보설정, 개별공시지가, 기타권리사항, 기타정보
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.current_공고ID, 자산ID,
            asset_info.get('주소'),
            asset_info.get('지목'),
            asset_info.get('용도지역'),
            asset_info.get('용도지구'),
            asset_info.get('건물구조'),
            asset_info.get('건축면적'),
            대지면적_str,  # 원본 문자열 저장
            asset_info.get('연면적'),
            전체면적_float,  # 숫자로 변환된 값 저장
            asset_info.get('지분표기', asset_info.get('지분내역')),  # 호환성 지원
            asset_info.get('지분율'),
            asset_info.get('실제매각면적'),
            asset_info.get('실제매각면적_평'),
            asset_info.get('권리관계'),
            asset_info.get('담보설정'),
            asset_info.get('개별공시지가'),
            asset_info.get('기타권리사항'),
            asset_info.get('기타정보')
        ))
        
    def _insert_credit_info(self, 자산ID: int, asset_info: Dict):
        """채권정보 삽입"""
        self.conn.execute("""
            INSERT OR REPLACE INTO 채권정보 (
                공고ID, 자산ID, 채권원금, 경과이자, 총채권액, 채무자명,
                채무자주소, 담보유무, 소멸시효, 회수가능성, 예상회수금액
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.current_공고ID, 자산ID,
            asset_info.get('채권원금'),
            asset_info.get('경과이자'),
            asset_info.get('총채권액'),
            asset_info.get('채무자명'),
            asset_info.get('채무자주소'),
            asset_info.get('담보유무'),
            asset_info.get('소멸시효'),
            asset_info.get('회수가능성'),
            asset_info.get('예상회수금액')
        ))
        
    def _insert_movable_info(self, 자산ID: int, asset_info: Dict):
        """동산정보 삽입"""
        # 감가상각율을 REAL 타입으로 처리
        감가상각율_value = asset_info.get('감가상각율')
        if isinstance(감가상각율_value, str):
            try:
                감가상각율_value = float(감가상각율_value.replace('%', ''))
            except (ValueError, AttributeError):
                감가상각율_value = None
                
        self.conn.execute("""
            INSERT OR REPLACE INTO 동산정보 (
                공고ID, 자산ID, 수량, 단위, 제조사, 모델명, 제조년도,
                구입가격, 현재상태, 감가상각율, 추정가치, 보관장소
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.current_공고ID, 자산ID,
            asset_info.get('수량'),
            asset_info.get('단위'),
            asset_info.get('제조사'),
            asset_info.get('모델명'),
            asset_info.get('제조년도'),
            asset_info.get('구입가격'),
            asset_info.get('현재상태'),
            감가상각율_value,
            asset_info.get('추정가치'),
            asset_info.get('보관장소')
        ))
        
    def _insert_ip_info(self, 자산ID: int, asset_info: Dict):
        """지적재산권정보 삽입"""
        self.conn.execute("""
            INSERT OR REPLACE INTO 지적재산권정보 (
                공고ID, 자산ID, 출원번호, 등록번호, 출원일, 등록일,
                만료일, 발명명칭, 연차료납부상태, 실시권현황, 추정가치
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.current_공고ID, 자산ID,
            asset_info.get('출원번호'),
            asset_info.get('등록번호'),
            asset_info.get('출원일'),
            asset_info.get('등록일'),
            asset_info.get('만료일'),
            asset_info.get('발명명칭'),
            asset_info.get('연차료납부상태'),
            asset_info.get('실시권현황'),
            asset_info.get('추정가치')
        ))
        
    def _insert_stock_info(self, 자산ID: int, asset_info: Dict):
        """주식정보 삽입"""
        self.conn.execute("""
            INSERT OR REPLACE INTO 주식정보 (
                공고ID, 자산ID, 발행회사, 주식수, 액면가, 지분율,
                취득가격, 장부가, 상장여부, 최근평가액, 양도제한
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.current_공고ID, 자산ID,
            asset_info.get('발행회사'),
            asset_info.get('주식수'),
            asset_info.get('액면가'),
            asset_info.get('지분율'),
            asset_info.get('취득가격'),
            asset_info.get('장부가'),
            asset_info.get('상장여부'),
            asset_info.get('최근평가액'),
            asset_info.get('양도제한')
        ))
        
    def _insert_vehicle_info(self, 자산ID: int, asset_info: Dict):
        """운송수단정보 삽입"""
        self.conn.execute("""
            INSERT OR REPLACE INTO 운송수단정보 (
                공고ID, 자산ID, 차량번호, 차량명칭, 연식, 배기량,
                주행거리, 연료, 사고이력, 할부잔액, 보험만료일, 추정가치, 차대번호
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.current_공고ID, 자산ID,
            asset_info.get('차량번호'),
            asset_info.get('차량명칭'),
            asset_info.get('연식'),
            asset_info.get('배기량'),
            asset_info.get('주행거리'),
            asset_info.get('연료'),
            asset_info.get('사고이력'),
            asset_info.get('할부잔액'),
            asset_info.get('보험만료일'),
            asset_info.get('추정가치'),
            asset_info.get('차대번호')
        ))
        
    def _insert_other_asset_info(self, 자산ID: int, asset_info: Dict):
        """기타자산정보 삽입"""
        self.conn.execute("""
            INSERT OR REPLACE INTO 기타자산정보 (
                공고ID, 자산ID, 자산명칭, 자산유형, 취득일, 취득가격,
                현재시세, 연간유지비, 체납금액, 양도제한, 기타정보
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.current_공고ID, 자산ID,
            asset_info.get('자산명칭'),
            asset_info.get('자산유형'),
            asset_info.get('취득일'),
            asset_info.get('취득가격'),
            asset_info.get('현재시세'),
            asset_info.get('연간유지비'),
            asset_info.get('체납금액'),
            asset_info.get('양도제한'),
            asset_info.get('기타정보')
        ))
        
    def _insert_investment_info(self, 자산ID: int, asset_info: Dict):
        """출자증권정보 삽입"""
        self.conn.execute("""
            INSERT OR REPLACE INTO 출자증권정보 (
                공고ID, 자산ID, 출자기관명, 출자증권번호, 출자금액,
                출자일자, 만료일자, 배당률, 현재가치, 양도제한여부
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.current_공고ID, 자산ID,
            asset_info.get('출자기관명'),
            asset_info.get('출자증권번호'),
            asset_info.get('출자금액'),
            asset_info.get('출자일자'),
            asset_info.get('만료일자'),
            asset_info.get('배당률'),
            asset_info.get('현재가치'),
            asset_info.get('양도제한여부')
        ))
            
    def _insert_bid_rounds(self, bid_rounds: List[Dict]):
        """
        회차별입찰정보 삽입 (공고ID 자동 설정)
        
        Args:
            bid_rounds: 회차별입찰정보 리스트
        """
        if not self.current_공고ID:
            raise ValueError("공고ID가 설정되지 않았습니다.")
            
        for round_info in bid_rounds:
            매각그룹ID = round_info.get('매각그룹ID')
            회차 = round_info.get('회차')
            
            if 매각그룹ID is None or 회차 is None:
                logger.warning(f"매각그룹ID 또는 회차가 없는 입찰정보를 건너뜁니다: {round_info}")
                continue
                
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO 회차별입찰정보 (
                        공고ID, 매각그룹ID, 회차, 최저입찰가, 입찰보증금,
                        입찰시작시간, 입찰마감시간, 개찰시간
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.current_공고ID,
                    매각그룹ID,
                    회차,
                    round_info.get('최저입찰가'),
                    round_info.get('입찰보증금'),
                    round_info.get('입찰시작시간'),
                    round_info.get('입찰마감시간'),
                    round_info.get('개찰시간')
                ))
                
            except sqlite3.Error as e:
                logger.error(f"회차별입찰정보 삽입 실패 - 그룹ID: {매각그룹ID}, 회차: {회차}, 오류: {str(e)}")
                raise
            
    def _insert_bid_conditions(self, conditions: Dict):
        """
        입찰조건 삽입 (공고ID 자동 설정)
        
        Args:
            conditions: 입찰조건 딕셔너리
        """
        if not conditions:
            logger.info("입찰조건 정보가 없어 건너뜁니다.")
            return
            
        if not self.current_공고ID:
            raise ValueError("공고ID가 설정되지 않았습니다.")
            
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO 입찰조건 (
                    공고ID, 입찰공개성코드, 제출방법코드, 입찰방식코드, 입찰장소,
                    우편입찰, 직접방문, 이메일입찰, 온비드, 팩스입찰,
                    보증금납부방식, 은행명, 계좌번호, 예금주,
                    개인필요서류, 법인필요서류, 대리인필요서류, 봉투표시,
                    입찰자유의사항, 낙찰자유의사항, 차순위유의사항, 유찰자유의사항, 우선매각조건,
                    입찰회차구분, 총액단가구분, 입찰금액공개여부, 공동입찰허용여부,
                    차순위정책, 낙찰자결정방식, 입찰성립조건, 보증금반환방식, 개찰결과통지방법
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.current_공고ID,  # 자동으로 현재 공고ID 설정
                conditions.get('입찰공개성코드'),
                conditions.get('제출방법코드'),
                conditions.get('입찰방식코드'),
                conditions.get('입찰장소'),
                int(conditions.get('우편입찰', 0)),
                int(conditions.get('직접방문', 0)),
                int(conditions.get('이메일입찰', 0)),
                int(conditions.get('온비드', 0)),
                int(conditions.get('팩스입찰', 0)),
                conditions.get('보증금납부방식'),
                conditions.get('은행명'),
                conditions.get('계좌번호'),
                conditions.get('예금주'),
                conditions.get('개인필요서류'),
                conditions.get('법인필요서류'),
                conditions.get('대리인필요서류'),
                conditions.get('봉투표시'),
                conditions.get('입찰자유의사항'),
                conditions.get('낙찰자유의사항'),
                conditions.get('차순위유의사항'),
                conditions.get('유찰자유의사항'),
                conditions.get('우선매각조건'),
                conditions.get('입찰회차구분'),
                conditions.get('총액단가구분'),
                conditions.get('입찰금액공개여부'),
                conditions.get('공동입찰허용여부'),
                conditions.get('차순위정책'),
                conditions.get('낙찰자결정방식'),
                conditions.get('입찰성립조건'),
                conditions.get('보증금반환방식'),
                conditions.get('개찰결과통지방법')
            ))
            
        except sqlite3.Error as e:
            logger.error(f"입찰조건 삽입 실패: {str(e)}")
            raise
        
    def _insert_highlights(self, highlights: List[Dict]):
        """
        강조사항 삽입 (공고ID 자동 설정)
        
        Args:
            highlights: 강조사항 리스트
        """
        if not highlights:
            logger.info("강조사항이 없어 건너뜁니다.")
            return
            
        if not self.current_공고ID:
            raise ValueError("공고ID가 설정되지 않았습니다.")
            
        for highlight in highlights:
            강조유형 = highlight.get('강조유형')
            강조내용 = highlight.get('강조내용')
            
            if not 강조유형 or not 강조내용:
                logger.warning(f"강조유형 또는 강조내용이 없는 항목을 건너뜁니다: {highlight}")
                continue
                
            try:
                self.conn.execute("""
                    INSERT INTO 강조사항 (공고ID, 강조유형, 강조내용)
                    VALUES (?, ?, ?)
                """, (self.current_공고ID, 강조유형, 강조내용))
                
            except sqlite3.Error as e:
                logger.error(f"강조사항 삽입 실패 - 유형: {강조유형}, 오류: {str(e)}")
                raise
            
    def _insert_special_matters(self, special: Dict):
        """
        특별사항 삽입 (공고ID 자동 설정)
        
        Args:
            special: 특별사항 딕셔너리
        """
        if not special:
            logger.info("특별사항 정보가 없어 건너뜁니다.")
            return
            
        if not self.current_공고ID:
            raise ValueError("공고ID가 설정되지 않았습니다.")
            
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO 특별사항 (
                    공고ID, 농지취득자격증명, 상속등기미완료, 가압류, 근저당권, 임차권,
                    기타권리제한, 체납세액, 환가포기여부, 환가포기사유,
                    임의매각가능성, 무응찰시처리방안
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.current_공고ID,  # 자동으로 현재 공고ID 설정
                int(special.get('농지취득자격증명', 0)),
                int(special.get('상속등기미완료', 0)),
                int(special.get('가압류', 0)),
                int(special.get('근저당권', 0)),
                int(special.get('임차권', 0)),
                int(special.get('기타권리제한', 0)),
                special.get('체납세액', 0),
                int(special.get('환가포기여부', 0)),
                special.get('환가포기사유'),
                special.get('임의매각가능성'),
                special.get('무응찰시처리방안')
            ))
            
        except sqlite3.Error as e:
            logger.error(f"특별사항 삽입 실패: {str(e)}")
            raise

# 사용 예시 및 테스트 함수
def test_inserter_with_sample_data():
    """샘플 데이터로 삽입 테스트"""
    import tempfile
    import os
    
    # 임시 데이터베이스 생성
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_db_path = tmp_file.name
    
    try:
        # 데이터베이스 연결 및 스키마 생성
        conn = sqlite3.connect(tmp_db_path)
        
        # 여기서 스키마 생성 코드 실행 필요 (pg_schema.py의 create_all_tables 함수)
        # from pg_schema import create_all_tables
        # create_all_tables(conn)
        
        # JSON 삽입기 생성
        inserter = JSONDatabaseInserter(conn)
        
        # 테스트 JSON 데이터
        test_data = {
            "파일정보": {
                "파일명": "테스트_파일.pdf",
                "용도구분": "공고용"
            },
            "기본정보": {
                "공고ID": "TEST001",
                "사건번호": "2024하단999",
                "총원본자산수": 1,
                "총매각그룹수": 1,
                "채무자명": "테스트채무자",
                "채무자구분": "개인"
            },
            "관재인": {
                "관재인명": "테스트관재인",
                "직업": "변호사",
                "전화번호": "02-1234-5678"
            },
            "매각그룹목록": [
                {
                    "매각그룹ID": 0,
                    "매각방식": "일괄매각"
                }
            ],
            "원본자산목록": [
                {
                    "자산ID": 0,
                    "자산명": "테스트 부동산",
                    "대분류코드": "RE",
                    "대분류명": "부동산",
                    "매각그룹ID": 0,
                    "자산정보": {
                        "주소": "서울특별시 강남구",
                        "지목": "대지",
                        "대지면적": "100㎡"
                    }
                }
            ]
        }
        
        # 데이터 삽입 테스트
        success = inserter.insert_json_data(test_data)
        
        if success:
            print(f"✅ 테스트 성공! 공고ID: {inserter.current_공고ID}")
            
            # 삽입된 데이터 확인
            cursor = conn.execute("SELECT 공고ID, 채무자명 FROM 기본정보")
            result = cursor.fetchone()
            if result:
                print(f"삽입된 공고: {result[0]} - {result[1]}")
        else:
            print("❌ 테스트 실패")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류: {str(e)}")
    finally:
        conn.close()
        os.unlink(tmp_db_path)  # 임시 파일 삭제

def process_json_folder(json_folder_path: str = 'json', db_path: str = 'db.db') -> None:
    """
    json 폴더의 모든 JSON 파일을 처리하여 DB에 삽입
    공고ID가 중복인 경우 건너뜀
    
    Args:
        json_folder_path: JSON 파일들이 있는 폴더 경로
        db_path: SQLite 데이터베이스 파일 경로
    """
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        logger.info(f"데이터베이스에 연결했습니다: {db_path}")
        
        # JSON 삽입기 생성
        inserter = JSONDatabaseInserter(conn)
        
        # json 폴더에서 모든 .json 파일 찾기
        json_pattern = os.path.join(json_folder_path, '*.json')
        json_files = glob.glob(json_pattern)
        
        if not json_files:
            logger.warning(f"'{json_folder_path}' 폴더에 JSON 파일이 없습니다.")
            return
        
        logger.info(f"처리할 JSON 파일 {len(json_files)}개를 찾았습니다.")
        
        success_count = 0
        duplicate_count = 0
        error_count = 0
        
        # 각 JSON 파일 처리
        for json_file in sorted(json_files):
            logger.info(f"\n=== 파일 처리 중: {json_file} ===")
            
            try:
                # JSON 파일 읽기
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # 데이터 삽입 시도
                result = inserter.insert_json_data(json_data)
                
                if result:
                    success_count += 1
                    logger.info(f"✅ 성공: {json_file} (공고ID: {inserter.current_공고ID})")
                else:
                    duplicate_count += 1
                    logger.info(f"⚠️ 중복 건너뜀: {json_file}")
                    
            except json.JSONDecodeError as e:
                error_count += 1
                logger.error(f"❌ JSON 파싱 오류: {json_file} - {str(e)}")
            except Exception as e:
                error_count += 1
                logger.error(f"❌ 처리 오류: {json_file} - {str(e)}")
        
        # 결과 요약
        logger.info(f"\n=== 처리 완료 ===")
        logger.info(f"총 파일 수: {len(json_files)}")
        logger.info(f"성공: {success_count}")
        logger.info(f"중복 건너뜀: {duplicate_count}")
        logger.info(f"오류: {error_count}")
        
        if success_count > 0:
            logger.info(f"✅ {success_count}개 파일이 성공적으로 처리되었습니다.")
        if duplicate_count > 0:
            logger.info(f"⚠️ {duplicate_count}개 파일이 중복으로 인해 건너뛰어졌습니다.")
        if error_count > 0:
            logger.warning(f"❌ {error_count}개 파일에서 오류가 발생했습니다.")
            
    except sqlite3.Error as e:
        logger.error(f"데이터베이스 오류: {str(e)}")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("데이터베이스 연결을 닫았습니다.")

# 메인 실행 부분
def main():
    """메인 실행 함수"""
    try:
        # json 폴더의 모든 파일 처리
        process_json_folder()
            
    except Exception as e:
        logger.error(f"메인 실행 중 오류: {str(e)}")

if __name__ == "__main__":
    # 테스트 실행    
    print("\n=== 실제 데이터 삽입 ===")
    main()