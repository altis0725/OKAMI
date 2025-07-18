"""
OKAMI用ヘルパー関数群
システム全体で使う共通ユーティリティ
"""

import re
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import json


def generate_unique_id(prefix: str = "okami") -> str:
    """
    プレフィックス付きユニークID生成

    Args:
        prefix: IDの接頭辞

    Returns:
        ユニークID文字列
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_part = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{unique_part}"


def format_duration(seconds: float) -> str:
    """
    秒数を人間向けに整形

    Args:
        seconds: 秒数

    Returns:
        整形済み文字列
    """
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    文字列を安全に整形

    Args:
        text: 入力文字列
        max_length: 最大長

    Returns:
        整形済み文字列
    """
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    return text


def calculate_hash(data: Union[str, Dict, List]) -> str:
    """
    データのSHA256ハッシュ計算

    Args:
        data: ハッシュ化対象

    Returns:
        ハッシュ文字列
    """
    if isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True)
    elif not isinstance(data, str):
        data = str(data)
    
    return hashlib.sha256(data.encode()).hexdigest()


def parse_time_window(window_str: str) -> timedelta:
    """
    時間ウィンドウ文字列をtimedeltaに変換

    Args:
        window_str: 例 "1h", "30m", "1d"

    Returns:
        timedeltaオブジェクト
    """
    pattern = r'^(\d+)([hdms])$'
    match = re.match(pattern, window_str.lower())
    
    if not match:
        raise ValueError(f"Invalid time window format: {window_str}")
    
    value, unit = match.groups()
    value = int(value)
    
    if unit == 's':
        return timedelta(seconds=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    else:
        raise ValueError(f"Unknown time unit: {unit}")


def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    テキストからJSONオブジェクト抽出

    Args:
        text: JSONを含むテキスト

    Returns:
        抽出したJSON辞書またはNone
    """
    # Try to find JSON block
    json_pattern = r'```json\s*(.*?)\s*```'
    match = re.search(json_pattern, text, re.DOTALL)
    
    if match:
        json_str = match.group(1)
    else:
        # Try to find JSON object directly
        json_pattern = r'\{[^{}]*\}'
        matches = re.findall(json_pattern, text)
        if not matches:
            return None
        json_str = matches[0]
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    テキストを重複付きで分割

    Args:
        text: 分割対象
        chunk_size: チャンクサイズ
        overlap: チャンク間の重複

    Returns:
        チャンクリスト
    """
    if not text or chunk_size <= 0:
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size * 0.8:  # Only break if we're past 80% of chunk
                chunk = text[start:start + break_point + 1]
                end = start + break_point + 1
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    2つの辞書を再帰的にマージ

    Args:
        dict1: 1つ目の辞書
        dict2: 2つ目（優先）

    Returns:
        マージ済み辞書
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def truncate_dict(data: Dict[str, Any], max_depth: int = 3, max_items: int = 10) -> Dict[str, Any]:
    """
    ログ用に辞書を省略整形

    Args:
        data: 対象辞書
        max_depth: 最大ネスト深さ
        max_items: 各階層の最大件数

    Returns:
        省略済み辞書
    """
    def _truncate(obj: Any, depth: int) -> Any:
        if depth > max_depth:
            return "..."
        
        if isinstance(obj, dict):
            items = list(obj.items())[:max_items]
            result = {}
            for k, v in items:
                result[k] = _truncate(v, depth + 1)
            if len(obj) > max_items:
                result["..."] = f"({len(obj) - max_items} more items)"
            return result
        
        elif isinstance(obj, list):
            items = obj[:max_items]
            result = [_truncate(item, depth + 1) for item in items]
            if len(obj) > max_items:
                result.append(f"... ({len(obj) - max_items} more items)")
            return result
        
        elif isinstance(obj, str) and len(obj) > 100:
            return obj[:100] + "..."
        
        else:
            return obj
    
    return _truncate(data, 0)


def format_error(error: Exception, include_traceback: bool = False) -> Dict[str, Any]:
    """
    Format exception for logging

    Args:
        error: Exception object
        include_traceback: Include full traceback

    Returns:
        Formatted error dict
    """
    error_dict = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if include_traceback:
        import traceback
        error_dict["traceback"] = traceback.format_exc()
    
    # Add specific error details
    if hasattr(error, '__dict__'):
        error_attrs = {k: v for k, v in error.__dict__.items() 
                      if not k.startswith('_') and isinstance(v, (str, int, float, bool, list, dict))}
        if error_attrs:
            error_dict["error_details"] = error_attrs
    
    return error_dict


def calculate_success_rate(successes: int, total: int) -> float:
    """
    Calculate success rate safely

    Args:
        successes: Number of successes
        total: Total attempts

    Returns:
        Success rate (0-1)
    """
    if total <= 0:
        return 0.0
    return min(1.0, max(0.0, successes / total))