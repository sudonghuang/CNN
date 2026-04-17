"""单元测试：FeatureDatabase（人脸特征库）"""
import pytest
import numpy as np


def test_add_and_query_hit():
    """添加特征向量后，相同向量的余弦相似度应达 1.0（命中 present）"""
    from app.ai.feature_database import FeatureDatabase

    db = FeatureDatabase()
    vec = np.random.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)

    db.add("stu001", 1, vec)
    result = db.query(vec, threshold_high=0.75, threshold_low=0.50)

    assert result["status"] == "present"
    assert result["student_id"] == "stu001"
    assert result["confidence"] >= 0.99


def test_query_unknown():
    """垂直向量之间余弦相似度为 0，应返回 unknown"""
    from app.ai.feature_database import FeatureDatabase

    db = FeatureDatabase()
    vec_a = np.array([1.0] + [0.0] * 511, dtype=np.float32)
    vec_b = np.array([0.0, 1.0] + [0.0] * 510, dtype=np.float32)

    db.add("stu001", 1, vec_a)
    result = db.query(vec_b, threshold_high=0.75, threshold_low=0.50)
    assert result["status"] == "unknown"


def test_save_and_load(tmp_path):
    """特征库保存后重新加载应可正常查询"""
    from app.ai.feature_database import FeatureDatabase

    save_path = str(tmp_path / "features.npy")
    db = FeatureDatabase()
    vec = np.random.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)
    db.add("stu_save", 42, vec)
    db.save(save_path)

    db2 = FeatureDatabase()
    db2.load(save_path)
    result = db2.query(vec, threshold_high=0.75, threshold_low=0.50)
    assert result["status"] == "present"
    assert result["student_db_id"] == 42


def test_empty_database_returns_unknown():
    """空特征库对任意向量应返回 unknown"""
    from app.ai.feature_database import FeatureDatabase

    db = FeatureDatabase()
    vec = np.random.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)
    result = db.query(vec, threshold_high=0.75, threshold_low=0.50)
    assert result["status"] == "unknown"


def test_multiple_students_best_match():
    """多学生时应返回相似度最高的那个"""
    from app.ai.feature_database import FeatureDatabase

    db = FeatureDatabase()
    vec1 = np.array([1.0] + [0.0] * 511, dtype=np.float32)
    vec2 = np.array([0.0, 1.0] + [0.0] * 510, dtype=np.float32)
    db.add("stu_a", 1, vec1)
    db.add("stu_b", 2, vec2)

    # 查询与 vec1 完全相同
    result = db.query(vec1, threshold_high=0.75, threshold_low=0.50)
    assert result["status"] == "present"
    assert result["student_id"] == "stu_a"
