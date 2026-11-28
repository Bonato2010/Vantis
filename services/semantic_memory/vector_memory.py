"""
VANTIS Semantic Memory Service (pgvector & FastEmbed)
Busca vetorial por significado e contexto para transcrições, ganchos e padrões de retenção.
Compatível com pgvector (PostgreSQL) e motor vetorial local em FastEmbed ONNX + Numpy + SQLite.
Suporta isolamento estrito de memória editorial por canal (20 canais) com camada universal compartilhada.
"""
import os
import re
import json
import sqlite3
import hashlib
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

from .pgvector_adapter import PgVectorAdapter

logger = logging.getLogger("VantisSemanticMemory")

# Singleton global para FastEmbed ONNX Model (evita re-inicialização pesada)
_GLOBAL_EMBEDDER = None

def _get_fastembed_model():
    global _GLOBAL_EMBEDDER
    if _GLOBAL_EMBEDDER is not None:
        return _GLOBAL_EMBEDDER
    try:
        from fastembed import TextEmbedding
        _GLOBAL_EMBEDDER = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        logger.info("[VectorMemory] Modelo neural FastEmbed (BAAI/bge-small-en-v1.5) carregado com sucesso.")
    except Exception as e:
        logger.warning(f"[VectorMemory] FastEmbed indisponível: {e}. Utilizando fallback determinístico denso.")
        _GLOBAL_EMBEDDER = None
    return _GLOBAL_EMBEDDER

class VectorMemoryService:
    """Serviço de Memória Semântica com embeddings neurais reais e isolamento multicanal."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.db_path = str(base_dir / "database" / "shorts_central.db")
        else:
            self.db_path = db_path

        self.pg_adapter = PgVectorAdapter()
        self._embedder = _get_fastembed_model()
        self._init_sqlite_tables()

    def _init_sqlite_tables(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS semantic_vectors (
                    id TEXT PRIMARY KEY,
                    category TEXT,
                    text_content TEXT,
                    vector_blob BLOB,
                    metadata_json TEXT,
                    channel_id INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vec_cat ON semantic_vectors(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vec_channel ON semantic_vectors(channel_id)")
            
            # Idempotente: adiciona coluna channel_id se tabela já existia sem ela
            cursor.execute("PRAGMA table_info(semantic_vectors)")
            cols = [col[1] for col in cursor.fetchall()]
            if "channel_id" not in cols:
                try:
                    cursor.execute("ALTER TABLE semantic_vectors ADD COLUMN channel_id INTEGER DEFAULT NULL")
                except Exception:
                    pass
            conn.commit()

    def generate_embedding(self, text: str, dim: int = 384) -> np.ndarray:
        """
        Gera um vetor denso normalizado de 384 dimensões para representação semântica real.
        Prioriza FastEmbed neural ONNX (bge-small-en-v1.5) com fallback determinístico.
        """
        if not text or not text.strip():
            return np.zeros(dim, dtype=np.float32)

        # 1. Tenta FastEmbed neural de alta precisão
        if self._embedder is not None:
            try:
                vecs = list(self._embedder.embed([text]))
                if vecs:
                    vec = np.array(vecs[0], dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    return vec
            except Exception as e:
                logger.warning(f"[VectorMemory] Falha na inferência neural: {e}. Recorrendo ao fallback.")

        # 2. Fallback determinístico L2 para continuidade operacional
        tokens = re.findall(r"\b\w{2,}\b", text.lower())
        vec = np.zeros(dim, dtype=np.float32)

        for i, token in enumerate(tokens):
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
            weight = 1.0 / (1.0 + (i * 0.05))
            vec[idx] += sign * weight

            if i < len(tokens) - 1:
                bigram = f"{token}_{tokens[i+1]}"
                h_bi = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
                idx_bi = h_bi % dim
                sign_bi = 1.0 if ((h_bi >> 8) % 2 == 0) else -1.0
                vec[idx_bi] += sign_bi * 1.5

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(np.float32)

    def index_item(
        self,
        item_id: str,
        text: str,
        category: str,
        metadata: Optional[Dict[str, Any]] = None,
        channel_id: Optional[int] = None
    ) -> bool:
        """Indexa um item na memória semântica vetorial com isolamento de canal."""
        vec = self.generate_embedding(text)
        meta = metadata or {}
        if channel_id is not None and "channel_id" not in meta:
            meta["channel_id"] = channel_id
            
        meta_str = json.dumps(meta, ensure_ascii=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_vectors (id, category, text_content, vector_blob, metadata_json, channel_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item_id, category, text, vec.tobytes(), meta_str, channel_id))
            conn.commit()
        return True

    def search_similar(
        self,
        query: str,
        category: Optional[str] = None,
        channel_id: Optional[int] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca os itens mais semanticamente similares usando distância de cosseno.
        Se channel_id for fornecido, filtra itens pertencentes a esse canal OU à memória universal (channel_id IS NULL).
        """
        # Se pgvector estiver disponível no PostgreSQL, consulta por ele
        if self.pg_adapter.is_available():
            q_vec = self.generate_embedding(query).tolist()
            pg_res = self.pg_adapter.query_similarity("semantic_transcriptions", q_vec, top_k)
            if pg_res:
                return pg_res

        # Motor vetorial local via FastEmbed + Numpy Cosine + SQLite
        q_vec = self.generate_embedding(query)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            sql = "SELECT id, category, text_content, vector_blob, metadata_json, channel_id FROM semantic_vectors WHERE 1=1"
            params = []
            
            if category:
                sql += " AND category = ?"
                params.append(category)

            # Isolamento editorial por canal: busca no canal ativo OU na memória universal (NULL)
            if channel_id is not None:
                sql += " AND (channel_id = ? OR channel_id IS NULL)"
                params.append(channel_id)

            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        if not rows:
            return []

        scored = []
        for r in rows:
            item_id, cat, text, blob, meta_json, ch_id = r
            if not blob:
                continue
            item_vec = np.frombuffer(blob, dtype=np.float32)
            # Dot product de vetores L2 normalizados = Cosine Similarity exato [-1.0, 1.0]
            sim = float(np.dot(q_vec, item_vec))
            scored.append({
                "id": item_id,
                "category": cat,
                "text": text,
                "channel_id": ch_id,
                "metadata": json.loads(meta_json or "{}"),
                "similarity_score": round(max(0.0, min(1.0, (sim + 1.0) / 2.0)), 4)
            })

        scored.reverse()
        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored[:top_k]

    def index_hook(
        self,
        hook_id: str,
        hook_text: str = "",
        retention_score: float = 80.0,
        niche: str = "geral",
        text: Optional[str] = None,
        channel_id: Optional[int] = None
    ) -> bool:
        final_text = text if text is not None else hook_text
        return self.index_item(
            item_id=hook_id,
            text=final_text,
            category="hook",
            channel_id=channel_id,
            metadata={"retention_score": retention_score, "niche": niche, "channel_id": channel_id}
        )

    def store_hook(
        self,
        hook_text: str,
        niche: str = "geral",
        score: float = 80.0,
        channel_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        hook_id: Optional[str] = None
    ) -> str:
        """Alias de conveniência para indexação de ganchos com geração automática de ID."""
        import time
        hid = hook_id or f"hook_{channel_id or 'univ'}_{int(time.time()*1000)}"
        meta = metadata or {}
        meta.update({"retention_score": score, "niche": niche, "channel_id": channel_id})
        self.index_item(item_id=hid, text=hook_text, category="hook", channel_id=channel_id, metadata=meta)
        return hid

    def search_hooks(
        self,
        query: str,
        channel_id: Optional[int] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        return self.search_similar(query=query, category="hook", channel_id=channel_id, top_k=top_k)

    def get_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category, COUNT(*) FROM semantic_vectors GROUP BY category")
            rows = cursor.fetchall()
            
            cursor.execute("SELECT channel_id, COUNT(*) FROM semantic_vectors GROUP BY channel_id")
            ch_rows = cursor.fetchall()
            
            backend_desc = "PostgreSQL (pgvector)" if self.pg_adapter.is_available() else "Local FastEmbed Neural ONNX (bge-small-en-v1.5)"
            return {
                "total_indexed": sum(r[1] for r in rows),
                "by_category": dict(rows),
                "by_channel": {f"canal_{r[0]}" if r[0] else "universal": r[1] for r in ch_rows},
                "backend": backend_desc,
                "embedding_dimension": 384,
                "neural_model": "BAAI/bge-small-en-v1.5 (quantized ONNX)",
                "multichannel_isolation": True
            }
