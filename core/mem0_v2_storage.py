from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from crewai.memory.storage.interface import Storage


class Mem0V2Storage(Storage):
    """
    Mem0 v2 API 専用のストレージ実装。
    - 追加(保存): POST /v1/memories/ （body に version="v2" を指定）
    - 検索: POST /v2/memories/search/ （filters が必須）

    注意:
    - メタデータは 2000 文字程度の制限があるため、過大な場合は切り詰めます。
    - org_id / project_id を利用する場合は Mem0 側で有効化済みであること。
    """

    def __init__(self, *, user_id: str, org_id: Optional[str] = None, project_id: Optional[str] = None,
                 run_id: Optional[str] = None, includes: Optional[str] = None, excludes: Optional[str] = None,
                 infer: bool = True, api_key: Optional[str] = None, api_base: str = "https://api.mem0.ai") -> None:
        super().__init__()
        self.user_id = user_id
        self.org_id = org_id
        self.project_id = project_id
        self.run_id = run_id
        self.includes = includes
        self.excludes = excludes
        self.infer = infer
        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        self.api_base = api_base.rstrip("/")

        if not self.api_key:
            raise RuntimeError("MEM0_API_KEY is required for Mem0V2Storage")

        # v2 API は Authorization: Token <API_KEY> が正
        self._headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    def _truncate_metadata(self, metadata: Dict[str, Any], limit: int = 1900) -> Dict[str, Any]:
        try:
            import json

            raw = json.dumps(metadata, ensure_ascii=False)
            if len(raw) <= limit:
                return metadata
            # ざっくり縮める（長いキーや値を削る）
            trimmed: Dict[str, Any] = {}
            size = 0
            for k, v in metadata.items():
                chunk = json.dumps({k: v}, ensure_ascii=False)
                if size + len(chunk) > limit:
                    break
                trimmed[k] = v
                size += len(chunk)
            return trimmed
        except Exception:
            return metadata

    def save(self, value: Any, metadata: Dict[str, Any]) -> None:
        # v2 仕様の追加は /v1/memories/ に対して body で version="v2" を指定
        payload: Dict[str, Any] = {
            "messages": [{"role": "assistant", "content": str(value)}],
            "user_id": self.user_id,
            "infer": self.infer,
            "version": "v2",
        }
        if self.org_id:
            payload["org_id"] = self.org_id
        if self.project_id:
            payload["project_id"] = self.project_id
        if self.run_id:
            payload["run_id"] = self.run_id
        if self.includes:
            payload["includes"] = self.includes
        if self.excludes:
            payload["excludes"] = self.excludes

        # メタデータの過大を防ぐ
        payload["metadata"] = self._truncate_metadata(metadata or {})

        url = f"{self.api_base}/v1/memories/"
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.post(url, json=payload, headers=self._headers)
            if resp.status_code >= 400:
                # 過大時はさらに縮めて再試行（ベストエフォート）
                if resp.status_code == 400:
                    payload["metadata"] = {}
                    client.post(url, json=payload, headers=self._headers)

    def search(self, query: str, limit: int = 3, score_threshold: float = 0.35) -> List[Any]:
        # v2 search: /v2/memories/search/ （filters 必須）
        # 既定では user_id を AND フィルタとして付与し、run_id があれば併用
        filters: Dict[str, Any] = {"AND": [{"user_id": self.user_id}]}
        if self.run_id:
            filters["AND"].append({"run_id": self.run_id})

        payload: Dict[str, Any] = {
            "query": query,
            "limit": limit,
            "filters": filters,
        }
        # org_id / project_id はボディで指定可能（実機確認済み）
        if self.org_id:
            payload["org_id"] = self.org_id
        if self.project_id:
            payload["project_id"] = self.project_id

        url = f"{self.api_base}/v2/memories/search/"
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.post(url, json=payload, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
            # v2 の応答は配列、または {results: [...]} / {data: [...]} の場合あり
            results = data
            if isinstance(data, dict):
                results = data.get("results") or data.get("data") or []

            # CrewAI の期待に合わせて最低限のフィールド整形
            normalized: List[Dict[str, Any]] = []
            for r in results:
                # r が辞書でない場合も防御
                if not isinstance(r, dict):
                    normalized.append({"context": str(r), "metadata": {}, "score": 1.0})
                    continue
                item = {
                    "context": r.get("memory") or r.get("text") or r,
                    "metadata": r.get("metadata", {}),
                    "score": r.get("score", 1.0),
                }
                if item["score"] >= score_threshold:
                    normalized.append(item)
            return normalized

    def reset(self) -> None:
        # v2 には明示の reset エンドポイントがないため何もしない（将来的に対応）
        return
