"""
PostgreSQL + pgvector Adapter para IAS
Gerencia conexão e consultas nativas quando DATABASE_URL estiver configurada.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("IAS.pgvector")

class PgVectorAdapter:
    def __init__(self, database_url: Optional[str] = None):
        self.db_url = database_url or os.environ.get("DATABASE_URL")
        self.connected = False
        self._check_connection()

    def _check_connection(self):
        if not self.db_url:
            self.connected = False
            return
        try:
            import psycopg2
            from pgvector.psycopg2 import register_vector
            conn = psycopg2.connect(self.db_url)
            register_vector(conn)
            conn.close()
            self.connected = True
        except Exception as e:
            logger.warning(f"PostgreSQL/pgvector offline ou indisponível: {e}")
            self.connected = False

    def is_available(self) -> bool:
        return self.connected

    def query_similarity(self, table: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Executa busca de cosseno via operador <=> do pgvector."""
        if not self.connected:
            return []
        import psycopg2
        import numpy as np
        
        results = []
        try:
            conn = psycopg2.connect(self.db_url)
            with conn.cursor() as cur:
                # <=> representa distância de cosseno no pgvector (1 - cos_sim)
                cur.execute(f"""
                    SELECT id, doc_id, category, metadata, 1 - (embedding <=> %s) AS similarity
                    FROM {table}
                    ORDER BY embedding <=> %s
                    LIMIT %s
                """, (np.array(query_vector), np.array(query_vector), top_k))
                rows = cur.fetchall()
                for r in rows:
                    results.append({
                        "id": r[0],
                        "doc_id": r[1],
                        "category": r[2],
                        "metadata": r[3],
                        "similarity": float(r[4])
                    })
            conn.close()
        except Exception as e:
            logger.error(f"Erro na query pgvector: {e}")
        return results
