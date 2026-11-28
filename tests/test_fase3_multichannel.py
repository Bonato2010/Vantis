"""
IAS Test Suite - Fase 3: Sistema Multicanal & Isolamento Editorial (20 Canais)
Valida:
1. Mapeamento íntegro e exclusivo de pastas Google Drive (5 TB) para todos os 20 canais.
2. Identidade editorial dos 5 canais piloto: arquétipos, nichos, tons, estilos de edição e voz.
3. Injeção de diretrizes editoriais personalizadas por canal (prevenção de homogeneização).
4. Isolamento estrito de configurações personalizadas (channel_settings) e finanças (financial_logs).
5. Execução do pipeline LangGraph respeitando as especificações visuais e pastas Drive de cada canal.
"""
import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.channel_manager import ChannelManager
from services.orchestration.langgraph_engine import IASOrchestrationEngine
from database.migrate import run_migrations

class TestFase3Multichannel(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_multichannel.db")
        # Aplica migrações 001, 002 e 003 no banco de teste
        run_migrations(db_path=self.test_db)
        self.channel_mgr = ChannelManager(db_path=self.test_db)
        self.engine = IASOrchestrationEngine(db_path=self.test_db)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_all_20_channels_gdrive_mapping(self):
        """Valida se todos os 20 canais possuem ID de pasta Google Drive preenchido e exclusivo."""
        channels = self.channel_mgr.list_all_channels()
        self.assertEqual(len(channels), 20)

        seen_folders = set()
        for ch in channels:
            folder_id = ch.get("gdrive_folder_id")
            self.assertIsNotNone(folder_id, f"Canal {ch['channel_number']} não possui gdrive_folder_id")
            self.assertGreater(len(folder_id), 10, f"ID de pasta inválido no canal {ch['channel_number']}")
            self.assertNotIn(folder_id, seen_folders, f"Pasta duplicada detectada: {folder_id}")
            seen_folders.add(folder_id)

        # Canal 1 e Canal 2 devem corresponder ao config/gdrive_folders.json
        self.assertEqual(channels[0]["gdrive_folder_id"], "1Qcd6DS3zA0OrNKSeDSPTHyl_P0y0l9jf")
        self.assertEqual(channels[1]["gdrive_folder_id"], "1fUETRbMIIjRTZyOyH_WPLNJcSUwjlPZ4")

    def test_02_pilot_channels_distinct_identities(self):
        """Valida que os 5 canais piloto possuem identidades editoriais 100% distintas."""
        p1 = self.channel_mgr.get_channel_profile(1)
        p2 = self.channel_mgr.get_channel_profile(2)
        p3 = self.channel_mgr.get_channel_profile(3)
        p4 = self.channel_mgr.get_channel_profile(4)
        p5 = self.channel_mgr.get_channel_profile(5)

        # 1. Arquétipos editoriais distintos
        archetypes = {p1["archetype_slug"], p2["archetype_slug"], p3["archetype_slug"], p4["archetype_slug"], p5["archetype_slug"]}
        self.assertEqual(len(archetypes), 5, "Existem canais piloto com arquétipos repetidos!")

        # 2. Nichos distintos
        niches = {p1["niche"], p2["niche"], p3["niche"], p4["niche"], p5["niche"]}
        self.assertEqual(len(niches), 5, "Existem canais piloto com nichos repetidos!")

        # 3. Vozes e timbres distintos
        voices = {
            p1["voice_profile"]["voice_id"],
            p2["voice_profile"]["voice_id"],
            p3["voice_profile"]["voice_id"],
            p4["voice_profile"]["voice_id"],
            p5["voice_profile"]["voice_id"]
        }
        self.assertEqual(len(voices), 5, "Existem canais piloto utilizando a mesma voz TTS!")

        # 4. Fontes e cores de legenda distintas
        fonts = {
            p1["subtitle_style"]["font"],
            p2["subtitle_style"]["font"],
            p3["subtitle_style"]["font"],
            p4["subtitle_style"]["font"]
        }
        self.assertGreaterEqual(len(fonts), 3)

        # 5. Ritmo WPM adaptado por gênero
        self.assertEqual(p1["wpm_target"], 170) # Futebol: ritmo acelerado
        self.assertEqual(p2["wpm_target"], 140) # Crime: ritmo pausado e tenso

    def test_03_editorial_prompt_guidelines(self):
        """Valida a injeção personalizada de diretrizes editoriais por canal."""
        g1 = self.channel_mgr.get_channel_editorial_guidelines(1)
        g2 = self.channel_mgr.get_channel_editorial_guidelines(2)

        self.assertIn("FUTEBOL EM 60 SEGUNDOS", g1)
        self.assertIn("fanatico_futebol", g1)
        self.assertIn("Isso aqui não é futebol, é aula!", g1)

        self.assertIn("ARQUIVO SOMBRIO", g2)
        self.assertIn("investigador_misterios", g2)
        self.assertIn("O detalhe que passou despercebido por todos.", g2)

        # Sem vazamento cruzado
        self.assertNotIn("investigador_misterios", g1)
        self.assertNotIn("Futebol", g2)

    def test_04_isolated_channel_settings(self):
        """Valida que configurações salvas para um canal não afetam outros canais."""
        self.channel_mgr.set_channel_setting(1, "custom_outro_text", "Inscreva-se no Futebol Shorts!")
        self.channel_mgr.set_channel_setting(2, "custom_outro_text", "Siga para novos mistérios sombrios.")

        s1 = self.channel_mgr.get_channel_settings(1)
        s2 = self.channel_mgr.get_channel_settings(2)

        self.assertEqual(s1["custom_outro_text"], "Inscreva-se no Futebol Shorts!")
        self.assertEqual(s2["custom_outro_text"], "Siga para novos mistérios sombrios.")

    def test_05_financial_isolation_by_channel(self):
        """Valida que o lançamento financeiro e apuração de custos e lucros é estritamente isolado por canal."""
        # Canal 1: $0.15 de custos de modelo e $2.50 de AdSense
        self.channel_mgr.record_financial_entry(1, "cost", "model_tokens", 0.15, "Geração de 3 roteiros")
        self.channel_mgr.record_financial_entry(1, "revenue", "adsense", 2.50, "Receita estimada semanal")

        # Canal 2: $0.40 de custos de modelo e $0.00 de receita
        self.channel_mgr.record_financial_entry(2, "cost", "model_tokens", 0.40, "Análise de vídeo investigativo")

        fin1 = self.channel_mgr.get_financial_summary(1)
        fin2 = self.channel_mgr.get_financial_summary(2)

        self.assertEqual(fin1["total_costs_usd"], 0.15)
        self.assertEqual(fin1["total_revenue_usd"], 2.50)
        self.assertEqual(fin1["net_profit_usd"], 2.35)
        self.assertGreater(fin1["roi_percentage"], 1000.0)

        self.assertEqual(fin2["total_costs_usd"], 0.40)
        self.assertEqual(fin2["total_revenue_usd"], 0.0)
        self.assertEqual(fin2["net_profit_usd"], -0.40)
        self.assertEqual(fin2["roi_percentage"], -100.0)

    def test_06_langgraph_workflow_multichannel_integration(self):
        """Valida a execução do LangGraph aplicando estilo e destino exclusivos para Canal 1 e Canal 2."""
        # Execução Canal 1 (Futebol)
        wf1 = self.engine.start_workflow(task_id="wf_ch1_001", target_id="vid_esporte", niche="futebol_outros", channel_id=1)
        res1_step9 = wf1["step_results"]["9_preparacao_materiais"]
        self.assertEqual(res1_step9["font_applied"], "Arial Black")

        resumed1 = self.engine.approve_and_resume("wf_ch1_001")
        res1_step12 = resumed1["step_results"]["12_distribuicao"]
        self.assertEqual(res1_step12["destination_channel"], "canal_01")
        self.assertEqual(res1_step12["gdrive_backup_id"], "1Qcd6DS3zA0OrNKSeDSPTHyl_P0y0l9jf")

        # Execução Canal 2 (Casos Reais)
        wf2 = self.engine.start_workflow(task_id="wf_ch2_001", target_id="vid_crime", niche="casos_policiais", channel_id=2)
        res2_step9 = wf2["step_results"]["9_preparacao_materiais"]
        self.assertEqual(res2_step9["font_applied"], "Consolas")

        resumed2 = self.engine.approve_and_resume("wf_ch2_001")
        res2_step12 = resumed2["step_results"]["12_distribuicao"]
        self.assertEqual(res2_step12["destination_channel"], "canal_02")
        self.assertEqual(res2_step12["gdrive_backup_id"], "1fUETRbMIIjRTZyOyH_WPLNJcSUwjlPZ4")

if __name__ == "__main__":
    unittest.main()
