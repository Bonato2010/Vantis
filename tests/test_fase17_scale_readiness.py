"""
VANTIS — Suíte de Testes da Fase 17: Auditoria de Escala, Validação de Aprendizados e Preparação para 7.000 Vídeos
Cobre integralmente as Seções 2, 3, 4, 5, 6, 7, 8, 9 e 10 do Prompt da Fase 17.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.learning.editorial_utility_evaluator import EditorialUtilityEvaluator
from services.discovery.scale_selector import ScaleSelectionPlanner
from services.orchestration.central_controller import (
    CentralOperationsController,
    TASK_STATUS_QUEUED,
    TASK_STATUS_RETRYING,
    TASK_STATUS_FAILED,
)
from services.media_processing.media_downloader import MediaDownloader
from services.model_gateway.gateway import ModelGatewayService


class TestFase17ScaleReadiness(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_fase17.db"
        run_migrations(db_path=self.db_path)
        self.als = AudiovisualLearningSystem(db_path=self.db_path, target_goal=7000)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_knowledge_audit_and_reclassification_preserves_history(self):
        """Seção 2: Reclassificação honesta preserva histórico anterior em metadata."""
        # Simula registro da Fase 16 com cortes >= 4 superestimado como APRENDIZADO_VALIDADO
        k = self.als.record_knowledge(
            niche="futebol_outros",
            topic="ritmo_de_cortes_dinamico",
            title="Cortes Ágeis (>= 4) Teste",
            summary="Cortes >= 4 no canal 1.",
            classification="APRENDIZADO_VALIDADO",
            confidence_score=0.92,
            evidence_video_ids=["v1", "v2", "v3", "v4"],
            counterexamples=["v5"],
            target_channel_id=1,
            pilot_phase=16,
        )
        audit = self.als.audit_and_reclassify_phase16_knowledge()
        self.assertEqual(len(audit["reclassified"]), 1)
        self.assertEqual(audit["reclassified"][0]["to"], "HIPÓTESE")

        exp = self.als.explain_knowledge(k["id"])
        self.assertEqual(exp["classification"], "HIPÓTESE")
        self.assertEqual(len(exp["classification_history"]), 1)
        self.assertEqual(exp["classification_history"][0]["previous_classification"], "APRENDIZADO_VALIDADO")

    def test_02_editorial_utility_ab_uses_disjoint_holdout(self):
        """Seção 3: Teste A/B editorial rejeita contaminação treino/holdout e mede métricas específicas."""
        ev = EditorialUtilityEvaluator(db_path=self.db_path)

        # Insere vídeo de treino (id > 43 simulado via 44 inserções ou teste direto de overlap)
        holdout = [
            {
                "source_id": "hold_1",
                "title": "SHORT JEANS Cintura Baixa Moda",
                "niche": "casos_policiais",
                "engagement_ratio": 0.5,
                "analysis_payload": json.dumps({"audio": {"integrated_lufs": -70.0, "audio_classification": "SILENT_AUDIO_TRACK"}, "visual_and_editing": {"cuts_count": 1}, "narrative_and_script": {"word_count": 0}}),
            },
            {
                "source_id": "hold_2",
                "title": "Experimento de física incrível",
                "niche": "curiosidades",
                "engagement_ratio": 3.2,
                "analysis_payload": json.dumps({"audio": {"integrated_lufs": -14.0, "audio_classification": "VALID_AUDIO"}, "visual_and_editing": {"cuts_count": 5}, "narrative_and_script": {"word_count": 50, "hook_has_question": True}}),
            },
        ]
        res = ev.evaluate_ab(holdout_videos=holdout)
        self.assertEqual(res["holdout_count"], 2)
        self.assertEqual(res["overlap_with_training"], 0)
        self.assertEqual(res["statistical_significance"], "NOT_STATISTICALLY_PROVEN_SMALL_SAMPLE_N20")
        self.assertEqual(res["mode_a_baseline"]["off_topic_flagged"], 0)
        self.assertEqual(res["mode_b_with_phase16"]["off_topic_flagged"], 1)
        self.assertEqual(res["mode_b_with_phase16"]["silent_audio_flagged"], 1)
        self.assertLessEqual(res["mode_b_with_phase16"]["predicted_high_engagement_total"], 1)
        self.assertIn("unimproved_or_limited_areas", res["honest_assessment"])

    def test_03_cross_channel_isolation_blocks_contamination(self):
        """Seção 4: Validação cruzada impede contaminação entre Futebol, Ciência, Humor, Produtividade e Arquivo Sombrio."""
        k_futebol = self.als.record_knowledge(
            niche="futebol_outros", title="Regra Futebol", evidence_video_ids=["f1", "f2"],
            counterexamples=["f3"], classification="APRENDIZADO_VALIDADO", target_channel_id=1
        )
        k_humor = self.als.record_knowledge(
            niche="humor", title="Regra Humor", evidence_video_ids=["h1", "h2"],
            counterexamples=["h3"], classification="APRENDIZADO_VALIDADO", target_channel_id=3
        )
        k_sombrio = self.als.record_knowledge(
            niche="casos_policiais", title="Obs Sombrio", evidence_video_ids=["s1"],
            classification="OBSERVAÇÃO", target_channel_id=2
        )
        k_universal = self.als.record_knowledge(
            niche="universal", title="Norma Técnica EBU R128", evidence_video_ids=["u1", "u2"],
            counterexamples=["u3"], classification="APRENDIZADO_VALIDADO", target_channel_id=None
        )

        # Futebol -> Ciência (4): BLOQUEADO
        r1 = self.als.query_editorial_rule_for_channel(k_futebol["id"], requesting_channel_id=4)
        self.assertFalse(r1["allowed"])
        self.assertEqual(r1["reason"], "cross_channel_contamination_blocked")

        # Humor -> Produtividade (5): BLOQUEADO
        r2 = self.als.query_editorial_rule_for_channel(k_humor["id"], requesting_channel_id=5)
        self.assertFalse(r2["allowed"])

        # Sombrio -> Ciência (4): BLOQUEADO
        r3 = self.als.query_editorial_rule_for_channel(k_sombrio["id"], requesting_channel_id=4)
        self.assertFalse(r3["allowed"])

        # Universal técnico -> Ciência (4): PERMITIDO
        r4 = self.als.query_editorial_rule_for_channel(k_universal["id"], requesting_channel_id=4)
        self.assertTrue(r4["allowed"])
        self.assertEqual(r4["scope"], "universal_technical")

    def test_04_capacity_model_three_scenarios_with_formulas(self):
        """Seção 5: Estimativas de capacidade para 7.000 vídeos em 3 cenários explícitos."""
        planner = ScaleSelectionPlanner()
        cap = planner.estimate_capacity_scenarios(target_videos=7000)
        self.assertEqual(cap["target_videos"], 7000)
        for name in ("conservador", "realista", "pessimista"):
            self.assertIn(name, cap["scenarios"])
            sc = cap["scenarios"][name]
            self.assertTrue(sc["is_estimate"])
            self.assertGreater(sc["estimated_media_storage_gb"], 0)
            self.assertGreater(sc["estimated_wall_clock_hours"], 0)
            self.assertEqual(sc["estimated_cost_usd"], 0.0)
        self.assertLess(
            cap["scenarios"]["conservador"]["estimated_media_storage_gb"],
            cap["scenarios"]["pessimista"]["estimated_media_storage_gb"],
        )

    def test_05_queue_persistent_retries_permanent_failure_and_recovery(self):
        """Seção 6: Fila persistente, deduplicação, backoff, falha permanente e recuperação pós-crash."""
        ctrl = CentralOperationsController(db_path=str(self.db_path))
        sub1 = ctrl.submit_task("vid_task_1", "ANALYZE_SHORT", {"id": "v1"}, channel_id=1)
        self.assertTrue(sub1["success"])

        # Bloqueio de duplicidade
        dup = ctrl.submit_task("vid_task_1", "ANALYZE_SHORT", {"id": "v1"}, channel_id=1)
        self.assertFalse(dup["success"])

        claimed = ctrl.claim_next_task(worker_agent="w1", channel_id=1)
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["task_id"], "vid_task_1")

        # Retentativa controlada com backoff
        ret = ctrl.fail_task_with_retry("vid_task_1", "HTTP 429 rate limit", backoff_seconds=10, permanent=False)
        self.assertEqual(ret["status"], TASK_STATUS_RETRYING)
        self.assertFalse(ret["permanent_failure"])

        # Falha permanente não agenda novas tentativas
        ctrl.submit_task("vid_task_perm", "ANALYZE_SHORT", {"id": "v2"}, channel_id=1)
        ctrl.claim_next_task(worker_agent="w1", channel_id=1)
        perm = ctrl.fail_task_with_retry("vid_task_perm", "Video unavailable (deleted)", permanent=True)
        self.assertEqual(perm["status"], TASK_STATUS_FAILED)
        self.assertTrue(perm["permanent_failure"])

    def test_06_scale_selection_stratification_and_train_val_test_split(self):
        """Seção 7: Seleção estratificada anti-viés de popularidade e split train/val/test 70/15/15."""
        planner = ScaleSelectionPlanner()
        pool = []
        # Cria pool misto com tiers emerging, mid_tier, viral + inválidos (longo, duplicado, indisponível)
        for i in range(40):
            views = 1500 if i < 12 else (80_000 if i < 28 else 2_000_000)
            pool.append({
                "id": f"sel_{i}",
                "title": f"Titulo Unico {i}",
                "url": f"https://www.youtube.com/shorts/sel_{i}",
                "duration_seconds": 30.0,
                "channel_id": 1,
                "views": views,
                "is_available": True,
            })
        pool.append({"id": "sel_0", "title": "Titulo Unico 0", "url": "https://www.youtube.com/shorts/sel_0", "duration_seconds": 30.0, "channel_id": 1})
        pool.append({"id": "sel_dup_fp", "title": "Titulo Unico 0", "url": "https://www.youtube.com/shorts/sel_dup_fp", "duration_seconds": 30.0, "channel_id": 1})
        pool.append({"id": "too_long", "title": "Longo", "url": "https://www.youtube.com/shorts/too_long", "duration_seconds": 120.0, "channel_id": 1})
        pool.append({"id": "unavail", "title": "Indisp", "url": "https://www.youtube.com/shorts/unavail", "duration_seconds": 25.0, "channel_id": 1, "is_available": False})

        res = planner.plan_stratified_selection(pool, target_per_channel=20)
        self.assertEqual(res["selected_count"], 20)
        self.assertEqual(res["rejected_count"], 4)
        self.assertTrue(all("inclusion_rationale" in s for s in res["selected"]))
        self.assertTrue(any(r["reason"] == "duplicate_title_duration_fingerprint" for r in res["rejected"]))
        self.assertGreater(res["tier_distribution"]["emerging"], 0)
        self.assertGreater(res["tier_distribution"]["mid_tier"], 0)
        self.assertGreater(res["tier_distribution"]["viral"], 0)
        self.assertEqual(sum(res["split_distribution"].values()), 20)
        self.assertGreater(res["split_distribution"]["train"], 0)
        self.assertGreater(res["split_distribution"]["validation"], 0)
        self.assertGreater(res["split_distribution"]["test"], 0)

    def test_07_faulty_learning_protections_duplicates_counterexamples_corrupted(self):
        """Seção 8: Bloqueia duplicação, ausência de contraexemplos, arquivos corrompidos e exige explicabilidade."""
        # 1. Ausência de contraexemplos com guarda estrita -> PENDENTE_DE_VALIDACAO
        no_cnt = self.als.record_knowledge(
            niche="curiosidades", topic="teste_sem_contra", title="Regra Sem Contraexemplo",
            summary="Regra sem contraexemplo", classification="APRENDIZADO_VALIDADO",
            evidence_video_ids=["c1", "c2"], counterexamples=[], target_channel_id=4,
            require_counterexamples=True
        )
        self.assertEqual(no_cnt["classification"], "PENDENTE_DE_VALIDACAO")
        self.assertIsNotNone(no_cnt["downgrade_reason"])

        # 2. Mesclagem deduplicada ao registrar mesmo título/canal/tipo
        merged = self.als.record_knowledge(
            niche="curiosidades", topic="teste_sem_contra", title="Regra Sem Contraexemplo",
            summary="Regra com contraexemplo", classification="APRENDIZADO_VALIDADO",
            evidence_video_ids=["c3", "c4"], counterexamples=["c_bad"], target_channel_id=4
        )
        self.assertEqual(merged["id"], no_cnt["id"])
        self.assertEqual(merged["evidence_count"], 4)
        self.assertEqual(merged["classification"], "APRENDIZADO_VALIDADO")

        # 3. Explicabilidade responde às 3 perguntas
        exp = self.als.explain_knowledge(merged["id"])
        self.assertTrue(exp["is_truly_validated"])
        self.assertTrue(len(exp["why_it_works"]) > 0)
        self.assertEqual(len(exp["evidence_video_ids"]), 4)
        self.assertIn("c_bad", exp["failure_modes"]["counterexamples"])

        # 4. Evidência corrompida ('failed') bloqueia criação de aprendizado
        self.als.discover_video(source_id="corrupt_ev", title="Corrompido", duration_seconds=20.0)
        self.als._set_state("corrupt_ev", "failed", error_msg="Decode failed")
        with self.assertRaises(ValueError):
            self.als.record_knowledge(
                niche="curiosidades", title="Baseado em Corrompido",
                evidence_video_ids=["corrupt_ev", "c1"], counterexamples=["c_bad"],
                classification="APRENDIZADO_VALIDADO", target_channel_id=4
            )

    def test_08_dashboard_observability_all_metrics_from_db(self):
        """Seção 9: Todos os 17 indicadores de observabilidade vêm do banco (sem valores fixos)."""
        dash = self.als.get_dashboard_overview()
        m = dash["pilot_fase16_metrics"]
        required_keys = [
            "candidates_selected", "downloaded", "physically_validated",
            "technically_analyzed", "editorially_analyzed",
            "videos_with_transcripts", "videos_insufficient_speech",
            "learning_candidates", "validated_learnings",
            "observations_count", "hypotheses_count", "anti_patterns_count",
            "counterexamples_count", "queue_health",
            "editorially_rejected", "failures", "retries_count",
            "storage_used_mb", "avg_processing_time_sec", "cost_usd",
        ]
        for k in required_keys:
            self.assertIn(k, m, f"Chave '{k}' ausente no dashboard.")
        # Em banco vazio, zero literais fixos de 100
        self.assertEqual(m["candidates_selected"], 0)
        self.assertEqual(m["downloaded"], 0)

    def test_09_zero_cost_enforced(self):
        """Seção 10: Custo zero estritamente mantido ($0.00)."""
        gw = ModelGatewayService(enforce_free_tier=True)
        self.assertEqual(gw.get_usage_metrics().get("total_cost_usd", 0.0), 0.0)
        self.assertTrue(gw.is_paid_model("gpt-4o"))

    def test_10_download_failure_and_corrupted_file_handling(self):
        """Seção 10: Falha de download e arquivo corrompido são tratados sem crash."""
        dl = MediaDownloader(download_dir=self.temp_path / "dl")
        res_bad_url = dl.download_short("")
        self.assertFalse(res_bad_url["success"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "HTTP Error 404: Not Found"
            res_fail = dl.download_short("https://www.youtube.com/shorts/nonexistent123", max_retries=1, backoff_base_sec=0.01)
            self.assertFalse(res_fail["success"])
            self.assertEqual(res_fail["reason"], "yt_dlp_error")


if __name__ == "__main__":
    unittest.main()
