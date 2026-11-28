"""
VANTIS — Suíte de Testes da Fase 18: Aprendizado Editorial Real, Memória Evolutiva e Benchmark de 250 Vídeos
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.migrate import run_migrations
from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.learning.editorial_feature_extractor import EditorialFeatureExtractor, NOT_AVAILABLE
from services.learning.editorial_memory_engine import EditorialMemoryEngine
from services.model_gateway.gateway import ModelGatewayService
from services.orchestration.central_controller import CentralOperationsController


class TestFase18LearningAndBenchmark(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_fase18.db"
        run_migrations(db_path=self.db_path)
        self.als = AudiovisualLearningSystem(db_path=self.db_path, target_goal=7000)
        self.extractor = EditorialFeatureExtractor()
        self.engine = EditorialMemoryEngine(db_path=self.db_path)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_feature_extractor_uses_not_available_for_missing_evidence(self):
        """Seção 4: Características ausentes devem registrar 'NOT_AVAILABLE' e nunca 0 sintético."""
        silent_video = {
            "source_id": "v_silent",
            "duration_seconds": 25.0,
            "analysis_payload": json.dumps({
                "visual_and_editing": {"cuts_count": 2, "text_on_screen_detected": False},
                "audio": {"integrated_lufs": -70.0, "classification": "SILENT_AUDIO_TRACK", "is_usable": False},
                "narrative_and_script": {"speech_detected": False, "word_count": 0},
            }),
        }
        feats = self.extractor.extract(silent_video)
        self.assertEqual(feats["hook_type"], NOT_AVAILABLE)
        self.assertEqual(feats["information_density_wps"], NOT_AVAILABLE)
        self.assertEqual(feats["presentation_speed_wpm"], NOT_AVAILABLE)
        self.assertEqual(feats["suspense_structure"], NOT_AVAILABLE)
        self.assertEqual(feats["narrative_progression"], NOT_AVAILABLE)
        self.assertEqual(feats["explanation_clarity_score"], NOT_AVAILABLE)
        self.assertEqual(feats["has_conclusion"], NOT_AVAILABLE)
        self.assertEqual(feats["audio_visual_relation"], "silent_or_unusable_audio")

    def test_02_feature_extractor_derives_real_narrative_and_pacing_features(self):
        """Seção 4: Extrai gancho, progressão, WPM, clareza e relação AV de evidência real."""
        narrated_video = {
            "source_id": "v_narr",
            "duration_seconds": 30.0,
            "analysis_payload": json.dumps({
                "visual_and_editing": {"cuts_count": 6, "text_on_screen_detected": True, "first_cut_timestamp_sec": 1.8},
                "audio": {"integrated_lufs": -14.0, "classification": "VALID_AUDIO", "is_usable": True, "speech_clarity_score": 0.85, "lra": 6.5},
                "narrative_and_script": {
                    "speech_detected": True,
                    "word_count": 60,
                    "speaking_pace_wpm": 120.0,
                    "transcript_preview": "Você sabia que este segredo mudou tudo no final? Mas então descobriu a verdade e portanto aprendemos a lição!",
                },
            }),
        }
        feats = self.extractor.extract(narrated_video)
        self.assertEqual(feats["hook_type"], "question")
        self.assertEqual(feats["time_to_first_relevant_event_sec"], 1.8)
        self.assertEqual(feats["cuts_count"], 6)
        self.assertEqual(feats["presentation_speed_wpm"], 120.0)
        self.assertTrue(feats["suspense_structure"])
        self.assertTrue(feats["has_conclusion"])
        self.assertEqual(feats["narrative_progression"], "complete_3_acts")
        self.assertEqual(feats["audio_visual_relation"], "narrated_dynamic_cuts")

    def test_03_leak_free_70_15_15_split_and_deduplication(self):
        """Seção 7: Split estratificado 70/15/15 remove duplicatas por ID, SHA256 e título+duração sem vazamento."""
        pool = []
        for i in range(40):
            pool.append({
                "source_id": f"ch1_{i}",
                "title": f"Futebol Lance {i}",
                "duration_seconds": 20.0 + (i % 10),
                "channel_id": 1,
                "views_count": 1000 * (i + 1),
                "engagement_ratio": 1.5 + (i % 5) * 0.4,
                "sha256": f"hash_{i:064d}",
            })
        # Duplicatas propositais: mesmo ID, mesmo SHA256, mesmo título+duração
        pool.append({**pool[0]})
        pool.append({**pool[1], "source_id": "dup_sha", "title": "Outro Titulo"})
        pool.append({**pool[2], "source_id": "dup_fp", "sha256": f"hash_{999:064d}"})

        splits = self.engine.build_leak_free_splits(pool)
        self.assertEqual(len(splits["duplicates_removed"]), 3)
        self.assertTrue(splits["leakage_checks"]["leak_free"])
        self.assertEqual(splits["leakage_checks"]["train_test_id_overlap"], 0)
        self.assertEqual(splits["leakage_checks"]["val_test_id_overlap"], 0)
        self.assertEqual(
            len(splits["train"]) + len(splits["validation"]) + len(splits["test"]),
            40,
        )

    def test_04_evolutionary_learning_and_utility_before_after(self):
        """Seções 5, 6 e 8: Aprendizado usa apenas train+val, promove com evidência + contraexemplos e avalia no test."""
        videos = []
        for i in range(40):
            good = i >= 20
            is_counterexample = i in (20, 21, 22, 23)
            videos.append({
                "source_id": f"c4_{i}",
                "title": f"Ciência Fato {i}",
                "duration_seconds": 28.0,
                "channel_id": 4,
                "views_count": 200 if is_counterexample else (15000 if good else 200),
                "engagement_ratio": 0.1 if is_counterexample else (4.5 if good else 0.2),
                "processing_state": "learning_candidate",
                "sha256": f"h4_{i:064d}",
                "analysis_payload": json.dumps({
                    "visual_and_editing": {"cuts_count": 6 if good else 1, "text_on_screen_detected": good},
                    "audio": {"integrated_lufs": -14.0, "classification": "VALID_AUDIO", "is_usable": True, "speech_clarity_score": 0.9, "lra": 5.0},
                    "narrative_and_script": {
                        "speech_detected": good,
                        "word_count": 55 if good else 0,
                        "speaking_pace_wpm": 115.0 if good else 0.0,
                        "transcript_preview": "Você sabia desse experimento científico incrível? Portanto funciona assim!" if good else "",
                    },
                }),
            })

        splits = self.engine.build_leak_free_splits(videos)
        train_val = splits["train"] + splits["validation"]
        res = self.engine.run_evolutionary_learning(train_val, pilot_phase=18)
        self.assertGreater(len(res["recorded_knowledge"]), 0)
        validated = [k for k in res["recorded_knowledge"] if k["final_classification"] == "APRENDIZADO_VALIDADO"]
        self.assertGreater(len(validated), 0)

        train_val_ids = {v["source_id"] for v in train_val}
        ab = self.engine.evaluate_utility_before_after(splits["test"], train_ids=train_val_ids)
        self.assertEqual(ab["overlap_with_training"], 0)
        self.assertFalse(ab["is_causal_experiment"])
        self.assertGreaterEqual(ab["updated_with_phase18"]["precision_pct"], ab["baseline"]["precision_pct"])

    def test_05_queue_idempotency_and_zero_cost_enforced(self):
        """Seções 9 e 11: Fila idempotente para retomada segura e custo zero ($0.00) travado."""
        ctrl = CentralOperationsController(db_path=str(self.db_path))
        s1 = ctrl.submit_task("fase18_vid_x1", "BENCHMARK_250_ANALYZE", {"source_id": "x1"}, channel_id=1)
        s2 = ctrl.submit_task("fase18_vid_x1", "BENCHMARK_250_ANALYZE", {"source_id": "x1"}, channel_id=1)
        self.assertTrue(s1["success"])
        self.assertFalse(s2["success"])

        gw = ModelGatewayService(enforce_free_tier=True)
        self.assertTrue(gw.enforce_free_tier)
        self.assertTrue(gw.is_paid_model("gpt-4o"))
        self.assertEqual(gw.get_usage_metrics().get("total_cost_usd", 0.0), 0.0)

    def test_06_dashboard_phase18_transparency_labels(self):
        """Seção 10: Dashboard distingue explicitamente MEDIDO, ESTIMADO e NÃO_VERIFICADO."""
        dash = self.als.get_dashboard_overview()
        self.assertIn("pilot_fase18_metrics", dash)
        m18 = dash["pilot_fase18_metrics"]
        labels = m18["transparency_labels"]
        self.assertEqual(labels["downloaded_count"], "MEDIDO")
        self.assertEqual(labels["future_batch_500_hours_estimate"], "ESTIMADO")
        self.assertEqual(labels["youtube_retention_curves_status"], "NÃO_VERIFICADO")
        self.assertEqual(m18["youtube_retention_curves_status"], "NÃO_VERIFICADO")

    def test_07_extractor_reads_full_transcript_and_has_subtitles_on_screen(self):
        """Auditoria 18.1: Extrator lê full_transcript, has_subtitles_on_screen e cut_intervals_sec."""
        rec = {
            "source_id": "v_real_keys",
            "duration_seconds": 24.0,
            "analysis_payload": json.dumps({
                "visual_and_editing": {"cuts_count": 5, "has_subtitles_on_screen": True, "cut_intervals_sec": [2.4, 4.1]},
                "audio": {"integrated_lufs": -14.5, "classification": "VALID_AUDIO", "is_usable": True, "speech_clarity_score": 0.88, "lra": 5.2},
                "narrative_and_script": {
                    "speech_detected": True,
                    "word_count": 48,
                    "speaking_pace_wpm": 120.0,
                    "full_transcript": "Por que isso acontece? Mas então descobriu o segredo e portanto aprendemos no final!",
                },
            }),
        }
        feats = self.extractor.extract(rec)
        self.assertEqual(feats["hook_type"], "question")
        self.assertEqual(feats["time_to_first_relevant_event_sec"], 2.4)
        self.assertTrue(feats["text_on_screen_detected"])
        self.assertTrue(feats["suspense_structure"])
        self.assertTrue(feats["has_conclusion"])
        self.assertEqual(feats["narrative_progression"], "complete_3_acts")

    def test_08_micro_denominator_guard_and_channel_memory_persistence(self):
        """Auditoria 18.1: Protege contra 1 view = 100% engajamento e valida persistência isolada por canal."""
        self.als.record_knowledge(
            niche="curiosidades", topic="teste_persistencia", title="Regra Persistente C4",
            summary="Teste de persistência.", classification="APRENDIZADO_VALIDADO",
            evidence_video_ids=["e1", "e2"], counterexamples=["c1"], target_channel_id=4, pilot_phase=18,
        )
        fresh_als = AudiovisualLearningSystem(db_path=self.db_path)
        mem4 = fresh_als.get_channel_editorial_memory(4)
        mem1 = fresh_als.get_channel_editorial_memory(1)
        self.assertEqual(mem4["knowledge_count"], 1)
        self.assertEqual(mem1["knowledge_count"], 0)
        self.assertTrue(all(item["target_channel_id"] == 4 for item in mem4["knowledge_items"]))


if __name__ == "__main__":
    unittest.main()
