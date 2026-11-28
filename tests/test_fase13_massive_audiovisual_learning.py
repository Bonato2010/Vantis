"""
Testes Automatizados - Fase 13 / VANTIS: Sistema de Aprendizado Audiovisual Massivo (7.000+ Vídeos).
Valida catalogação em escala, deduplicação multimodal inteligente, processamento por etapas,
síntese de conhecimento editorial com evidências, isolamento multicanal e governança de qualidade.
"""
import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem

class TestFase13MassiveAudiovisualLearning(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_fase13.db")
        run_migrations(db_path=self.test_db)
        self.learning_sys = AudiovisualLearningSystem(db_path=self.test_db, target_goal=7000)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_configurable_target_and_scale(self):
        """Valida que a meta inicial de 7.000 vídeos é configurável para expansão futura."""
        self.assertEqual(self.learning_sys.target_goal, 7000)
        new_goal = self.learning_sys.set_target_goal(15000)
        self.assertEqual(new_goal, 15000)
        self.assertEqual(self.learning_sys.target_goal, 15000)

        with self.assertRaises(ValueError):
            self.learning_sys.set_target_goal(0)

    def test_02_multimodal_fingerprint_and_deduplication(self):
        """Valida que a deduplicação usa fingerprint multimodal e não apenas o título."""
        # 1. Cadastra vídeo original
        res1 = self.learning_sys.discover_video(
            source_id="yt_vid_orig_01",
            original_url="https://youtube.com/shorts/yt_vid_orig_01",
            title="O Segredo Mais Chocante da História do Futebol!",
            creator="FutebolMaster",
            niche="futebol",
            duration_seconds=42.0,
            views_count=100000,
            likes_count=5000
        )
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["processing_state"], "discovered")

        # 2. Tenta cadastrar reupload com título ligeiramente alterado mas mesmo criador e duração idêntica
        res2 = self.learning_sys.discover_video(
            source_id="yt_vid_reup_02",
            original_url="https://youtube.com/shorts/yt_vid_reup_02",
            title="O Segredo Mais Chocante da História do Futebol",  # sem exclamação, mesmas palavras
            creator="FutebolMaster",
            niche="futebol",
            duration_seconds=42.2,  # dentro da tolerância de balde de 1.5s
            views_count=500,
            likes_count=20
        )
        self.assertEqual(res2["status"], "REJECTED_DUPLICATE")
        self.assertEqual(res2["reason"], "duplicate_fingerprint")

        # 3. Tenta cadastrar mesmo source_id novamente
        res3 = self.learning_sys.discover_video(
            source_id="yt_vid_orig_01",
            original_url="https://youtube.com/shorts/yt_vid_orig_01",
            title="Qualquer Título",
            creator="OutroCriador",
            niche="futebol",
            duration_seconds=42.0
        )
        self.assertEqual(res3["status"], "ALREADY_CATALOGED")

    def test_03_diversity_filters_per_creator(self):
        """Valida cap de diversidade por fonte/criador para evitar monopólio de um único canal."""
        self.learning_sys.max_per_creator = 3  # Configura cap de 3 para teste rápido

        creator_name = "CanalMonopolio"
        for i in range(3):
            res = self.learning_sys.discover_video(
                source_id=f"yt_mono_{i}",
                original_url=f"https://youtube.com/shorts/yt_mono_{i}",
                title=f"Vídeo Único Número {i} do Monopólio",
                creator=creator_name,
                niche="curiosidades",
                duration_seconds=20.0 + (i * 5.0)  # durações distintas para não colidir fingerprint
            )
            self.assertEqual(res["status"], "SUCCESS")

        # 4º vídeo do mesmo criador deve ser rejeitado por cap de diversidade
        res4 = self.learning_sys.discover_video(
            source_id="yt_mono_exceeded",
            original_url="https://youtube.com/shorts/yt_mono_exceeded",
            title="Vídeo Excedente do Monopólio",
            creator=creator_name,
            niche="curiosidades",
            duration_seconds=55.0
        )
        self.assertEqual(res4["status"], "REJECTED_DIVERSITY")
        self.assertEqual(res4["reason"], "diversity_cap_exceeded_creator")

    def test_04_multimodal_processing_states_rigor(self):
        """Valida que o estado 'fully_analyzed' só é atingido quando todas as modalidades são processadas."""
        sid = "yt_multi_test_01"
        self.learning_sys.discover_video(
            source_id=sid,
            original_url=f"https://youtube.com/shorts/{sid}",
            title="Mistério dos Bastidores da Copa do Mundo",
            creator="FutebolInvestigativo",
            niche="futebol",
            duration_seconds=45.0,
            views_count=50000,
            likes_count=3500
        )

        # 1. Metadados
        meta_res = self.learning_sys.process_metadata(sid, tags=["futebol", "copa", "bastidores"])
        self.assertEqual(meta_res["state"], "metadata_processed")

        # Tentativa precoce de finalização multimodal deve recusar 'fully_analyzed'
        early_fin = self.learning_sys.finalize_multimodal_analysis(sid)
        self.assertNotEqual(early_fin["final_state"], "fully_analyzed")
        self.assertLess(early_fin["completeness_percentage"], 100.0)

        # 2. Transcrição
        script_sample = "Você sabia que esse golaço mudou tudo? Olha o que aconteceu quando o árbitro apitou. Curte para a parte 2."
        trans_res = self.learning_sys.process_transcript(sid, script_sample)
        self.assertEqual(trans_res["state"], "transcript_processed")
        self.assertTrue(trans_res["metrics"]["hook_has_psychological_trigger"])
        self.assertTrue(trans_res["metrics"]["has_call_to_action"])

        # 3. Áudio
        audio_res = self.learning_sys.process_audio(sid, speech_clarity_score=92.5, estimated_lufs=-14.1)
        self.assertEqual(audio_res["state"], "audio_processed")
        self.assertTrue(audio_res["audio"]["loudness_compliant_ebur128"])

        # 4. Visual
        visual_res = self.learning_sys.process_visual(sid, cuts_count=14, aspect_ratio="9:16", has_subtitles_on_screen=True)
        self.assertEqual(visual_res["state"], "visual_processed")
        self.assertTrue(visual_res["visual"]["is_vertical_9_16"])

        # 5. Finalização Multimodal Completa
        fin_res = self.learning_sys.finalize_multimodal_analysis(sid)
        self.assertEqual(fin_res["final_state"], "fully_analyzed")
        self.assertEqual(fin_res["completeness_percentage"], 100.0)

    def test_05_knowledge_synthesis_with_evidence_and_confidence(self):
        """Valida que o conhecimento editorial sintetizado possui evidências rastreáveis e confiança calculada."""
        # Cadastra e analisa 3 vídeos com ganchos interrogativos e cortes rápidos
        for i in range(3):
            sid = f"yt_evidence_vid_{i}"
            self.learning_sys.discover_video(
                source_id=sid,
                original_url=f"https://youtube.com/shorts/{sid}",
                title=f"Investigação Policial Caso #{i}",
                creator=f"Detetive_{i}",
                niche="casos_policiais",
                duration_seconds=35.0 + (i * 3.0),
                views_count=120000,
                likes_count=8000
            )
            self.learning_sys.process_metadata(sid)
            self.learning_sys.process_transcript(sid, f"Por que a polícia nunca revelou esse detalhe chocante no caso #{i}? Descubra agora.")
            self.learning_sys.process_audio(sid, speech_clarity_score=90.0, estimated_lufs=-14.0)
            self.learning_sys.process_visual(sid, cuts_count=12, aspect_ratio="9:16")
            self.learning_sys.finalize_multimodal_analysis(sid)

        # Sintetiza conhecimento para o nicho de casos policiais
        knowledge_items = self.learning_sys.synthesize_editorial_knowledge(niche="casos_policiais", min_evidence_count=2)
        self.assertGreaterEqual(len(knowledge_items), 2)

        hook_k = next((k for k in knowledge_items if k["type"] == "hook_formula"), None)
        self.assertIsNotNone(hook_k)
        self.assertIn("Gancho Interrogativo", hook_k["title"])
        self.assertEqual(hook_k["classification"], "evidence_based_conclusion")
        self.assertGreaterEqual(hook_k["confidence_score"], 0.60)
        self.assertGreaterEqual(hook_k["evidence_count"], 2)
        self.assertTrue(all(vid.startswith("yt_evidence_vid_") for vid in hook_k["evidence_video_ids"]))

    def test_06_channel_memory_isolation_and_cross_pollination(self):
        """Valida isolamento estrito de memória entre os 5 canais piloto e cross-pollination controlada."""
        # Cria conhecimento específico para o Canal 1 (Futebol, ID=1)
        k1 = self.learning_sys.record_knowledge(
            niche="futebol",
            knowledge_type="hook_formula",
            title="Gancho de Rivalidade Histórica",
            summary="Citar o clássico rival nos primeiros 2s aumenta a retenção dos torcedores.",
            classification="evidence_based_conclusion",
            confidence_score=0.91,
            evidence_video_ids=["yt_fut_01", "yt_fut_02"],
            actionable_recommendation="Iniciar com 'O maior erro do Corinthians contra o Palmeiras...'",
            anti_pattern_warning="Não use elogios neutros ao adversário.",
            target_channel_id=1
        )

        # Cria conhecimento universal
        self.learning_sys.record_knowledge(
            niche="universal",
            knowledge_type="editing_principle",
            title="Legendas Amarelas Dinâmicas",
            summary="Legendas com destaque em amarelo nas palavras-chave aceleram a leitura.",
            classification="evidence_based_conclusion",
            confidence_score=0.95,
            evidence_video_ids=["yt_univ_01"],
            actionable_recommendation="Destacar 1 palavra por frase em amarelo #FFD700.",
            anti_pattern_warning="Legendas brancas minúsculas sem fundo.",
            target_channel_id=None
        )

        # Memória do Canal 1 (Futebol): deve conter Gancho de Rivalidade e Legendas Amarelas
        mem_ch1 = self.learning_sys.get_channel_editorial_memory(channel_id=1)
        titles_ch1 = [k["title"] for k in mem_ch1["knowledge_items"]]
        self.assertIn("Gancho de Rivalidade Histórica", titles_ch1)
        self.assertIn("Legendas Amarelas Dinâmicas", titles_ch1)

        # Memória do Canal 2 (Casos Policiais, ID=2): NÃO pode conter Gancho de Rivalidade do Futebol!
        mem_ch2 = self.learning_sys.get_channel_editorial_memory(channel_id=2)
        titles_ch2 = [k["title"] for k in mem_ch2["knowledge_items"]]
        self.assertIn("Legendas Amarelas Dinâmicas", titles_ch2)  # universal presente
        self.assertNotIn("Gancho de Rivalidade Histórica", titles_ch2)  # isolamento preservado!

        # Executa Cross-Pollination justificada: transferir técnica do Canal 1 para o Canal 3 (Humor, ID=3)
        cp_res = self.learning_sys.cross_pollinate_technique(
            source_channel_id=1,
            target_channel_id=3,
            knowledge_id=k1["id"],
            transfer_rationale="Testar se rivalidade futebolística adaptada para paródia de humor gera o mesmo lift de engajamento."
        )
        self.assertEqual(cp_res["status"], "CROSS_POLLINATION_REGISTERED")
        self.assertEqual(cp_res["target_channel_id"], 3)

        # Verifica se o experimento foi registrado no canal de humor
        mem_ch3 = self.learning_sys.get_channel_editorial_memory(channel_id=3)
        self.assertGreaterEqual(mem_ch3["experiments_count"], 1)

    def test_07_editorial_experiment_lifecycle(self):
        """Valida ciclo completo de experimentação: hipótese, variação, avaliação e atualização de memória."""
        with self.learning_sys._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO editorial_experiments (
                    channel_id, title, hypothesis, evidence_motivation,
                    content_variation, evaluation_metric, status
                ) VALUES (1, 'Teste de Gancho com Pausa Dramática',
                          'Pausar 0.5s após a pergunta inicial aumenta a taxa de comentários',
                          'Estudo de 50 vídeos de futebol com alta retenção',
                          'Silêncio total na trilha sonora no segundo 2.5', 'comment_sentiment', 'PLANNED')
            """)
            exp_id = cursor.lastrowid
            conn.commit()

        eval_res = self.learning_sys.evaluate_experiment(
            experiment_id=exp_id,
            result_metrics={"lift_comments_pct": 34.2, "sample_size": 5},
            conclusion="Hipótese confirmada: o momento de silêncio despertou surpresa e aumentou em 34% os comentários no Shorts."
        )
        self.assertEqual(eval_res["status"], "EVALUATED")
        self.assertTrue(eval_res["memory_updated"])

    def test_08_checkpointed_batch_processing_and_resumption(self):
        """Valida que o processamento em lotes salva checkpoints e retoma do ponto exato."""
        # Cadastra 6 vídeos pendentes
        for i in range(6):
            self.learning_sys.discover_video(
                source_id=f"yt_batch_{i}",
                original_url=f"https://youtube.com/shorts/yt_batch_{i}",
                title=f"Curiosidade Científica Incrível #{i}",
                creator="CienciaRapida",
                niche="curiosidades",
                duration_seconds=30.0 + i
            )

        batch_id = "test_batch_001"
        # Executa lote 1 com tamanho 3
        res1 = self.learning_sys.run_batch_processing(batch_id=batch_id, batch_size=3, target_goal=10)
        self.assertEqual(res1["batch_processed"], 3)
        self.assertEqual(res1["total_processed"], 3)
        self.assertEqual(res1["success_count"], 3)
        self.assertEqual(res1["status"], "RUNNING")

        # Executa lote 2 (retomada): deve processar os próximos 3
        res2 = self.learning_sys.run_batch_processing(batch_id=batch_id, batch_size=3, target_goal=10)
        self.assertEqual(res2["batch_processed"], 3)
        self.assertEqual(res2["total_processed"], 6)
        self.assertEqual(res2["success_count"], 6)

    def test_09_quality_audit_and_source_bias_detection(self):
        """Valida auditoria de qualidade, detecção de viés de fonte e integridade de conclusões."""
        # 1. Cadastra vídeos com viés de um único criador
        for i in range(5):
            self.learning_sys.discover_video(
                source_id=f"yt_audit_{i}",
                original_url=f"https://youtube.com/shorts/yt_audit_{i}",
                title=f"Vídeo de Produtividade #{i}",
                creator="CriadorDominante",  # único criador dominante
                niche="desenvolvimento_pessoal",
                duration_seconds=25.0 + i
            )
            self.learning_sys.process_metadata(f"yt_audit_{i}")
            self.learning_sys.process_transcript(f"yt_audit_{i}", "Como ter foco inabalável trabalhando em casa.")
            self.learning_sys.process_audio(f"yt_audit_{i}")
            self.learning_sys.process_visual(f"yt_audit_{i}", cuts_count=6)
            self.learning_sys.finalize_multimodal_analysis(f"yt_audit_{i}")

        audit = self.learning_sys.run_quality_audit()
        self.assertEqual(audit["total_discovered"], 5)
        self.assertEqual(audit["total_fully_analyzed"], 5)
        self.assertTrue(audit["has_source_bias"])
        self.assertEqual(audit["max_creator_share_percentage"], 100.0)
        self.assertGreater(audit["overall_health_score"], 0)

    def test_10_dashboard_overview_telemetry(self):
        """Valida que get_dashboard_overview retorna todas as métricas para a interface."""
        overview = self.learning_sys.get_dashboard_overview()
        self.assertEqual(overview["target_goal"], 7000)
        self.assertIn("progress_percentage", overview)
        self.assertIn("states_breakdown", overview)
        self.assertIn("niche_distribution", overview)
        self.assertIn("language_distribution", overview)
        self.assertIn("health_score", overview)
        self.assertIn("top_knowledge", overview)
        self.assertIn("recent_experiments", overview)

    def test_11_rest_api_endpoints_learning_system(self):
        """Testa todos os endpoints REST de aprendizado audiovisual via TestClient."""
        from fastapi.testclient import TestClient
        from web.app import app
        client = TestClient(app)

        # 1. GET /api/learning/overview
        res_ov = client.get("/api/learning/overview")
        self.assertEqual(res_ov.status_code, 200)
        self.assertIn("target_goal", res_ov.json())

        # 2. POST /api/learning/discover
        disc_payload = {
            "source_id": "yt_api_test_01",
            "original_url": "https://youtube.com/shorts/yt_api_test_01",
            "title": "A Incrível Tática que o Técnico Escondeu",
            "creator": "TaticaPro",
            "niche": "futebol",
            "duration_seconds": 38.0,
            "views_count": 80000,
            "likes_count": 4500
        }
        res_disc = client.post("/api/learning/discover", json=disc_payload)
        self.assertEqual(res_disc.status_code, 200)
        self.assertIn(res_disc.json()["status"], ["SUCCESS", "ALREADY_CATALOGED"])

        # 3. GET /api/learning/catalog
        res_cat = client.get("/api/learning/catalog?limit=10")
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn("items", res_cat.json())

        # 4. POST /api/learning/batch-run
        batch_payload = {"batch_id": "api_test_batch", "batch_size": 5, "target_goal": 7000}
        res_batch = client.post("/api/learning/batch-run", json=batch_payload)
        self.assertEqual(res_batch.status_code, 200)

        # 5. POST /api/learning/audit
        res_audit = client.post("/api/learning/audit")
        self.assertEqual(res_audit.status_code, 200)
        self.assertIn("overall_health_score", res_audit.json())

        # 6. POST /api/learning/target-goal
        res_goal = client.post("/api/learning/target-goal", json={"target_goal": 8500})
        self.assertEqual(res_goal.status_code, 200)
        self.assertEqual(res_goal.json()["target_goal"], 8500)

        # 7. GET /api/channels/1/editorial-memory
        res_mem = client.get("/api/channels/1/editorial-memory")
        self.assertEqual(res_mem.status_code, 200)
        self.assertEqual(res_mem.json()["channel_id"], 1)

if __name__ == "__main__":
    unittest.main()
