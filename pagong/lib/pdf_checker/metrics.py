"""
텍스트 인식률 측정을 위한 메트릭 클래스
"""
import re
from typing import Dict, Tuple, List
from difflib import SequenceMatcher
import Levenshtein


class TextMetrics:
    """텍스트 인식 정확도를 측정하는 다양한 메트릭 제공"""
    
    @staticmethod
    def character_error_rate(reference: str, hypothesis: str) -> float:
        """
        문자 오류율(CER) 계산
        CER = (S + D + I) / N
        S: 대체(substitutions), D: 삭제(deletions), I: 삽입(insertions), N: 전체 문자 수
        """
        if not reference:
            return 0.0 if not hypothesis else 1.0
            
        distance = Levenshtein.distance(reference, hypothesis)
        return distance / len(reference)
    
    @staticmethod
    def word_error_rate(reference: str, hypothesis: str) -> float:
        """
        단어 오류율(WER) 계산
        """
        ref_words = reference.split()
        hyp_words = hypothesis.split()
        
        if not ref_words:
            return 0.0 if not hyp_words else 1.0
            
        distance = Levenshtein.distance(ref_words, hyp_words)
        return distance / len(ref_words)
    
    @staticmethod
    def similarity_ratio(reference: str, hypothesis: str) -> float:
        """
        두 텍스트 간의 유사도 비율 (0-1)
        """
        return SequenceMatcher(None, reference, hypothesis).ratio()
    
    @staticmethod
    def accuracy_score(reference: str, hypothesis: str) -> float:
        """
        전체 정확도 점수 (0-100)
        """
        cer = TextMetrics.character_error_rate(reference, hypothesis)
        return (1 - cer) * 100
    
    @staticmethod
    def detailed_metrics(reference: str, hypothesis: str) -> Dict[str, float]:
        """
        상세한 메트릭 정보 반환
        """
        return {
            "character_error_rate": TextMetrics.character_error_rate(reference, hypothesis),
            "word_error_rate": TextMetrics.word_error_rate(reference, hypothesis),
            "similarity_ratio": TextMetrics.similarity_ratio(reference, hypothesis),
            "accuracy_score": TextMetrics.accuracy_score(reference, hypothesis),
            "character_accuracy": (1 - TextMetrics.character_error_rate(reference, hypothesis)) * 100,
            "word_accuracy": (1 - TextMetrics.word_error_rate(reference, hypothesis)) * 100
        }
    
    @staticmethod
    def analyze_errors(reference: str, hypothesis: str) -> Dict[str, any]:
        """
        오류 유형 분석
        """
        ref_chars = list(reference)
        hyp_chars = list(hypothesis)
        
        # Levenshtein 연산 계산
        ops = Levenshtein.editops(reference, hypothesis)
        
        error_analysis = {
            "total_errors": len(ops),
            "substitutions": sum(1 for op in ops if op[0] == 'replace'),
            "deletions": sum(1 for op in ops if op[0] == 'delete'),
            "insertions": sum(1 for op in ops if op[0] == 'insert'),
            "error_positions": [(op[0], op[1], op[2]) for op in ops]
        }
        
        return error_analysis
    
    @staticmethod
    def structural_accuracy(reference: str, hypothesis: str) -> Dict[str, float]:
        """
        구조적 정확도 측정 (줄바꿈, 단락 등)
        """
        ref_lines = reference.split('\n')
        hyp_lines = hypothesis.split('\n')
        
        # 줄 수 일치도
        line_count_accuracy = 1 - abs(len(ref_lines) - len(hyp_lines)) / max(len(ref_lines), 1)
        
        # 단락 수 일치도
        ref_paragraphs = [p for p in reference.split('\n\n') if p.strip()]
        hyp_paragraphs = [p for p in hypothesis.split('\n\n') if p.strip()]
        paragraph_accuracy = 1 - abs(len(ref_paragraphs) - len(hyp_paragraphs)) / max(len(ref_paragraphs), 1)
        
        # 공백 패턴 일치도
        ref_spaces = len(re.findall(r'\s+', reference))
        hyp_spaces = len(re.findall(r'\s+', hypothesis))
        space_accuracy = 1 - abs(ref_spaces - hyp_spaces) / max(ref_spaces, 1)
        
        return {
            "line_structure_accuracy": line_count_accuracy * 100,
            "paragraph_structure_accuracy": paragraph_accuracy * 100,
            "whitespace_accuracy": space_accuracy * 100
        }