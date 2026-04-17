"""内存特征数据库（学号 → L2归一化特征向量）"""
from __future__ import annotations
import os
import numpy as np
from typing import List, Optional


class FeatureDatabase:
    def __init__(self):
        self.student_ids: List[str] = []         # 外部 student_id（学号字符串）
        self.db_ids: List[int] = []              # 数据库内部 id（用于写 AttendanceRecord）
        self._feature_matrix: Optional[np.ndarray] = None  # (N, 512)

    # ── 构建 ───────────────────────────────────────────────────

    def add(self, student_id: str, db_id: int, feature_vec: np.ndarray) -> None:
        self.student_ids.append(student_id)
        self.db_ids.append(db_id)
        vec = feature_vec / (np.linalg.norm(feature_vec) + 1e-8)
        if self._feature_matrix is None:
            self._feature_matrix = vec.reshape(1, -1)
        else:
            self._feature_matrix = np.vstack([self._feature_matrix, vec])

    def rebuild(self, student_ids: List[str], db_ids: List[int],
                feature_matrix: np.ndarray) -> None:
        self.student_ids = student_ids
        self.db_ids = db_ids
        self._feature_matrix = feature_matrix

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.save(path, {
            "student_ids": self.student_ids,
            "db_ids": self.db_ids,
            "feature_matrix": self._feature_matrix,
        })

    def load(self, path: str) -> None:
        if not os.path.exists(path):
            return
        data = np.load(path, allow_pickle=True).item()
        self.student_ids = list(data.get("student_ids", []))
        self.db_ids = list(data.get("db_ids", []))
        self._feature_matrix = data.get("feature_matrix")

    # ── 查询 ───────────────────────────────────────────────────

    def query(self, query_vec: np.ndarray,
              threshold_high: float = 0.75,
              threshold_low: float = 0.50) -> dict:
        """余弦相似度最近邻匹配，O(N) 矩阵乘法"""
        if self._feature_matrix is None or len(self.student_ids) == 0:
            return {"status": "unknown", "confidence": 0.0}
        q = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        sims = self._feature_matrix @ q          # (N,)
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        base = {"confidence": best_sim,
                "student_id": self.student_ids[best_idx],
                "student_db_id": self.db_ids[best_idx]}
        if best_sim >= threshold_high:
            return {**base, "status": "present"}
        if best_sim >= threshold_low:
            return {**base, "status": "unverified"}
        return {"status": "unknown", "confidence": best_sim}

    def __len__(self) -> int:
        return len(self.student_ids)
