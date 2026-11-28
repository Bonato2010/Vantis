"""
Camada de Gerenciamento do Banco de Dados Relacional (SQLite WAL / PostgreSQL ready).
Suporte a 20 canais com particionamento, integridade referencial e migrações automáticas.
"""
import sqlite3
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DB_PATH = BASE_DIR / "database/shorts_central.db"
SCHEMA_PATH = BASE_DIR / "database/schema.sql"

def get_db_connection(db_file: Optional[Path] = None) -> sqlite3.Connection:
    target = db_file or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_file: Optional[Path] = None):
    """Inicializa as tabelas consolidadas e popula categorias e os 20 canais se vazios."""
    target = db_file or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Executa o migrador consolidado
    from database.migrate import run_migrations
    run_migrations(target)

    with get_db_connection(target) as conn:
        cursor = conn.cursor()
        
        # 2. Categorias Iniciais Obrigatórias (15 Categorias)
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            initial_categories = [
                ("cortes_podcasts", "Cortes de Podcasts", "Cortes de entrevistas, podcasts e conversas informais"),
                ("entrevistas", "Entrevistas", "Entrevistas jornalísticas, talk-shows e encontros exclusivos"),
                ("jogadores_esportes", "Jogadores e Análises Esportivas", "Momentos icônicos, táticas e análises de atletas"),
                ("futebol_outros", "Futebol e Outros Esportes", "Futebol, basquete, lutas e esportes radicais"),
                ("humor", "Humor", "Comédia stand-up, situações engraçadas e timing cômico"),
                ("memes", "Memes", "Tendências de internet, paródias e cultura pop"),
                ("storytelling", "Histórias e Storytelling", "Contação de causos reais, suspense e reviravoltas"),
                ("animacoes", "Animações", "Mini-animações, explicadores visuais e histórias desenhadas"),
                ("curiosidades", "Curiosidades", "Fatos surpreendentes sobre o mundo e a humanidade"),
                ("noticias_acontecimentos", "Notícias e Acontecimentos", "Fatos recentes, eventos mundiais e cobertura"),
                ("casos_policiais", "Casos Policiais e Investigações", "Crimes reais, mistérios e investigações criminais"),
                ("desenvolvimento_pessoal", "Desenvolvimento Pessoal", "Produtividade, mentalidade, foco e evolução"),
                ("tecnologia", "Tecnologia", "Inteligência artificial, gadgets, novidades tech e inovação"),
                ("educacional", "Conteúdo Educacional", "Aulas curtas, história, ciência e aprendizado rápido"),
                ("entretenimento", "Entretenimento", "Cinema, séries, bastidores de celebridades e cultura")
            ]
            cursor.executemany(
                "INSERT INTO categories (slug, name, description) VALUES (?, ?, ?)",
                initial_categories
            )

        # 3. Inicialização dos 20 Canais se não existirem
        cursor.execute("SELECT COUNT(*) FROM channels")
        if cursor.fetchone()[0] == 0:
            initial_channels = []
            niches = [
                ("Podcasts & Papo Reto", "cortes_podcasts", "Humor e Opiniões fortes"),
                ("Futebol Clássico", "futebol_outros", "Lances e histórias de jogadores"),
                ("Mistérios & Crimes Reais", "casos_policiais", "Casos investigativos intrigantes"),
                ("Curiosidades do Mundo", "curiosidades", "Fatos rápidos e surpreendentes"),
                ("Mentalidade Alfa & Negócios", "desenvolvimento_pessoal", "Empreendedorismo e disciplina"),
                ("Tech & IA Descomplicada", "tecnologia", "Novidades da inteligência artificial"),
                ("Histórias da Vida Real", "storytelling", "Narrativas emocionantes de superação"),
                ("Stand-up & Zoeira", "humor", "Melhores tiradas de comediantes"),
                ("Ciência em 60 Segundos", "educacional", "Conceitos científicos explicados de forma simples"),
                ("Bastidores do Cinema", "entretenimento", "Segredos de filmes e séries famosos"),
                ("Lutas & UFC Raiz", "jogadores_esportes", "Momentos históricos das artes marciais"),
                ("Memes & Trends BR", "memes", "Cultura da internet brasileira"),
                ("Geopolítica Rápida", "noticias_acontecimentos", "O que está acontecendo no mundo"),
                ("Animações & Tiras", "animacoes", "Histórias visuais dinâmicas"),
                ("Grandes Entrevistas", "entrevistas", "Declarações marcantes de figuras públicas"),
                ("Finanças Sem Enrolação", "desenvolvimento_pessoal", "Educação financeira para jovens"),
                ("Carros & Velocidade", "curiosidades", "Supermáquinas e curiosidades automotivas"),
                ("Saúde & Longevidade", "educacional", "Hábitos para viver com mais energia"),
                ("Games & Esports", "entretenimento", "Jogadas inacreditáveis e novidades de games"),
                ("História Que Não Te Contaram", "educacional", "Curiosidades históricas pouco conhecidas")
            ]
            
            # Carrega mapeamento de pastas do Google Drive se disponível
            gdrive_map_file = BASE_DIR / "config/gdrive_folders.json"
            gdrive_map = {}
            if gdrive_map_file.exists():
                try:
                    with open(gdrive_map_file, "r", encoding="utf-8") as gf:
                        gdrive_map = json.load(gf)
                except Exception:
                    pass

            for num in range(1, 21):
                name, niche, strategy = niches[num - 1]
                gdrive_folder = gdrive_map.get(f"canal_{num:02d}", "")
                initial_channels.append((
                    num,
                    f"Canal {num:02d} - {name}",
                    niche,
                    strategy,
                    "Jovens e adultos (18-35)",
                    "pt-BR",
                    "BR",
                    "Cores vivas e modernas",
                    "Dinâmico 9:16 com legendas destacadas",
                    "Energético e envolvente",
                    "2_por_dia",
                    "Crescimento orgânico e retenção",
                    f"Estratégia editorial focada em {niche.lower()}",
                    gdrive_folder
                ))

            cursor.executemany("""
                INSERT INTO channels (
                    channel_number, name, niche, subniche, target_audience,
                    language, country, visual_identity, editing_style, communication_tone,
                    posting_frequency, goals, editorial_strategy, gdrive_folder_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, initial_channels)

        conn.commit()
    print("[Database] Banco relacional inicializado com sucesso!")

if __name__ == "__main__":
    init_db()
