"""
Response Quality Guardrail for OKAMI system
Ensures high-quality responses from agents
"""

from typing import Tuple, Any, Dict, Optional
import re
import structlog

logger = structlog.get_logger()


class ResponseQualityGuardrail:
    """Guardrail for ensuring response quality"""
    
    def __init__(self, min_quality_score: float = 7.0):
        """Initialize response quality guardrail
        
        Args:
            min_quality_score: Minimum acceptable quality score (0-10)
        """
        self.min_quality_score = min_quality_score
        
    def __call__(self, response: str) -> Tuple[bool, Any]:
        """Check response quality
        
        Args:
            response: Response to validate
            
        Returns:
            Tuple of (is_valid, response_or_error)
        """
        try:
            # Calculate quality score
            score, issues = self._calculate_quality_score(response)
            
            if score >= self.min_quality_score:
                logger.info(f"Response quality check passed", score=score)
                return (True, response)
            else:
                error_msg = f"Quality score {score:.1f} below threshold {self.min_quality_score}. Issues: {', '.join(issues)}"
                logger.warning(error_msg)
                return (False, error_msg)
                
        except Exception as e:
            logger.error(f"Quality check failed", error=str(e))
            return (False, f"Quality check error: {str(e)}")
    
    def _calculate_quality_score(self, response: str) -> Tuple[float, list]:
        """Calculate quality score for response
        
        Args:
            response: Response to score
            
        Returns:
            Tuple of (score, list_of_issues)
        """
        score = 10.0
        issues = []
        
        # Check length
        if len(response.strip()) < 20:
            score -= 3.0
            issues.append("response too short")
        elif len(response) > 5000:
            score -= 1.0
            issues.append("response too long")
            
        # Check for completeness
        if response.strip().endswith(("...", "[", "(")):
            score -= 2.0
            issues.append("incomplete response")
            
        # Check for placeholders
        placeholders = ["TODO", "FIXME", "XXX", "[INSERT", "[PLACEHOLDER]"]
        response_upper = response.upper()
        for placeholder in placeholders:
            if placeholder in response_upper:
                score -= 2.0
                issues.append(f"contains placeholder: {placeholder}")
                break
                
        # Check for structure
        if not any(c in response for c in ['.', '!', '?', '\n']):
            score -= 1.0
            issues.append("lacks structure")
            
        # Check for repetition
        words = response.lower().split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:  # More tolerant threshold
                score -= 2.0
                issues.append("excessive repetition")
                
        # Check for error indicators
        error_patterns = [
            r"error\s*:\s*",
            r"exception\s*:\s*",
            r"failed to",
            r"unable to",
            r"could not"
        ]
        for pattern in error_patterns:
            if re.search(pattern, response.lower()):
                score -= 1.0
                issues.append("contains error indicators")
                break
                
        return max(0.0, score), issues


class FactualAccuracyGuardrail:
    """Guardrail for checking factual accuracy"""
    
    def __init__(self, fact_sources: Optional[Dict[str, str]] = None):
        """Initialize factual accuracy guardrail
        
        Args:
            fact_sources: Dictionary of fact sources for validation
        """
        self.fact_sources = fact_sources or {}
        
    def __call__(self, response: str) -> Tuple[bool, Any]:
        """Check factual accuracy
        
        Args:
            response: Response to validate
            
        Returns:
            Tuple of (is_valid, response_or_error)
        """
        try:
            # Basic fact checking
            issues = []
            
            # Check for obvious falsehoods
            false_patterns = [
                (r"2\s*\+\s*2\s*=\s*5", "incorrect basic math"),
                (r"sun.*revolves.*earth", "incorrect astronomy"),
                (r"copyright\s+\d{4}", self._check_copyright_year)
            ]
            
            for pattern, check in false_patterns:
                if isinstance(check, str):
                    if re.search(pattern, response.lower()):
                        issues.append(check)
                else:
                    match = re.search(pattern, response.lower())
                    if match:
                        issue = check(match.group())
                        if issue:
                            issues.append(issue)
                            
            if issues:
                error_msg = f"Factual accuracy issues: {', '.join(issues)}"
                logger.warning(error_msg)
                return (False, error_msg)
                
            return (True, response)
            
        except Exception as e:
            logger.error(f"Fact check failed", error=str(e))
            return (False, f"Fact check error: {str(e)}")
            
    def _check_copyright_year(self, text: str) -> Optional[str]:
        """Check if copyright year is reasonable"""
        import datetime
        current_year = datetime.datetime.now().year
        
        match = re.search(r"copyright\s+(\d{4})", text.lower())
        if match:
            year = int(match.group(1))
            if year > current_year:
                return f"future copyright year: {year}"
                
        return None


class SafetyGuardrail:
    """Guardrail for ensuring safe outputs"""
    
    def __init__(self, check_code: bool = True):
        """Initialize safety guardrail
        
        Args:
            check_code: Whether to check for dangerous code patterns
        """
        self.check_code = check_code
        
    def __call__(self, response: str) -> Tuple[bool, Any]:
        """Check response safety
        
        Args:
            response: Response to validate
            
        Returns:
            Tuple of (is_valid, response_or_error)
        """
        try:
            issues = []
            
            # Check for PII patterns
            pii_patterns = [
                (r"\b\d{3}-\d{2}-\d{4}\b", "SSN pattern"),
                (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b", "credit card pattern"),
                (r"(?:password|pwd|pass)\s*[:=]\s*\S+", "exposed password")
            ]
            
            for pattern, issue in pii_patterns:
                if re.search(pattern, response):
                    issues.append(issue)
                    
            # Check for dangerous code patterns if enabled
            if self.check_code:
                dangerous_patterns = [
                    (r"rm\s+-rf\s+/", "dangerous file deletion"),
                    (r"eval\s*\(", "eval usage"),
                    (r"exec\s*\(", "exec usage"),
                    (r"__import__", "dynamic import"),
                    (r"subprocess.*shell\s*=\s*True", "shell injection risk")
                ]
                
                for pattern, issue in dangerous_patterns:
                    if re.search(pattern, response):
                        issues.append(issue)
                        
            if issues:
                error_msg = f"Safety issues detected: {', '.join(issues)}"
                logger.warning(error_msg)
                return (False, error_msg)
                
            return (True, response)
            
        except Exception as e:
            logger.error(f"Safety check failed", error=str(e))
            return (False, f"Safety check error: {str(e)}")


def create_quality_guardrail(min_score: float = 7.0) -> ResponseQualityGuardrail:
    """Create a quality guardrail instance"""
    return ResponseQualityGuardrail(min_quality_score=min_score)


def create_safety_guardrail(check_code: bool = True) -> SafetyGuardrail:
    """Create a safety guardrail instance"""
    return SafetyGuardrail(check_code=check_code)


def create_accuracy_guardrail(fact_sources: Optional[Dict] = None) -> FactualAccuracyGuardrail:
    """Create an accuracy guardrail instance"""
    return FactualAccuracyGuardrail(fact_sources=fact_sources)