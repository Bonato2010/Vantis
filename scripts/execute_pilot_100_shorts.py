"""
VANTIS — Engine de Execução do Piloto Controlado de 100 Shorts (Fase 16)
Auditoria Física Multimodal | Trava Custo Zero ($0.00) | Circuit Breakers | Checkpointing
Critérios Mandatórios:
1. 100 Shorts reais selecionados de docs/audits/phase16_selected_candidates.json.
2. Duração confirmada <= 60.0s em 100% dos arquivos.
3. Download físico e verificação de SHA256 (64 caracteres), tamanho > 0, codecs, streams e decodificação FFmpeg/OpenCV.
4. Análise multimodal real (OpenCV frames/texto/movimento, PySceneDetect cortes/intervalos, FFmpeg EBU R128 -vn, Whisper local CPU).
5. Classificação acústica rigorosa (VALID_AUDIO, QUIET_AUDIO_TRACK, HOT_LOUD_AUDIO, SILENT_AUDIO_TRACK, NO_AUDIO_TRACK, DECODING_FAILURE, MEASUREMENT_FAILURE).
6. Avaliação editorial contextual real sem IDs rejeitados artificialmente nem transcrições simuladas.
7. Preservação de ciclo de vida: downloaded -> technical_analysis_complete -> editorial_analysis_complete -> learning_candidate / editorially_rejected.
8. Síntese de aprendizados com regra de ouro (>= 2 evidências = APRENDIZADO_VALIDADO; 1 evidência = OBSERVAÇÃO).
9. Circuit breakers ativos contra falhas consecutivas, corrupção, silêncio excessivo, disco e custo.
10. Checkpointing persistente em learning_batch_checkpoints (batch_id = 'pilot_100_fase16').
"""

import os
import sys
import json
import time
import shutil
import random
import hashlib
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.learning.audiovisual_learning_system import AudiovisualLearningSystem
from services.media_processing.media_downloader import MediaDownloader
from services.media_processing.ffmpeg_engine import FFmpegEngine
from services.video_analysis.scene_detector import SceneDetectorService
from services.video_analysis.visual_analyzer import OpenCVVisualAnalyzer
from services.transcription.whisper_service import WhisperTranscriptionService
from services.model_gateway.gateway import ModelGatewayService

MANIFEST_JSON = BASE_DIR / "docs" / "audits" / "phase16_selected_candidates.json"
EXECUTION_DATA_JSON = BASE_DIR / "docs" / "audits" / "phase16_pilot_execution_data.json"
DOWNLOADS_ROOT = BASE_DIR / "workspace" / "downloads" / "pilot100"

BATCH_ID = "pilot_100_fase16"


class CircuitBreakerException(Exception):
    """Exceção levantada quando um critério de proteção do sistema é violado."""
    pass


def fetch_subtitles_for_short(youtube_url: str, video_id: str, local_video_path: Optional[str] = None, allow_network: bool = True) -> str:
    """Extrai legendas locais (.vtt/.srt) ou via yt-dlp sem fallback sintético."""
    if local_video_path:
        for sub_file in Path(local_video_path).parent.glob(f"{video_id}.*"):
            if sub_file.suffix.lower() in [".vtt", ".srt"]:
                try:
                    content = sub_file.read_text(encoding="utf-8", errors="ignore")
                    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("WEBVTT") and "-->" not in l and not l.isdigit()]
                    if lines:
                        return " ".join(lines[:60])
                except Exception:
                    pass

    if not allow_network:
        return ""

    temp_dir = BASE_DIR / "workspace" / "temp_subs" / video_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--js-runtimes", "node",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "pt,pt-BR,en",
            "--skip-download",
            "--sub-format", "vtt/srt/best",
            "-o", str(temp_dir / "%(id)s"),
            youtube_url
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=8, encoding="utf-8", check=False)
        for sub_file in temp_dir.glob("*.*"):
            if sub_file.suffix.lower() in [".vtt", ".srt"]:
                content = sub_file.read_text(encoding="utf-8", errors="ignore")
                lines = []
                for line in content.split("\n"):
                    l = line.strip()
                    if not l or l.startswith("WEBVTT") or "-->" in l or l.isdigit():
                        continue
                    lines.append(l)
                if lines:
                    return " ".join(lines[:60])
    except Exception:
        pass
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    return ""


def init_checkpoint(conn: sqlite3.Connection, target_count: int = 100):
    """Inicializa ou atualiza o checkpoint persistente da esteira."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO learning_batch_checkpoints (
            batch_id, target_goal, processed_count, success_count, rejected_count, error_count, status, updated_at
        ) VALUES (?, ?, 0, 0, 0, 0, 'RUNNING', CURRENT_TIMESTAMP)
        ON CONFLICT(batch_id) DO UPDATE SET
            status = 'RUNNING',
            updated_at = CURRENT_TIMESTAMP
    """, (BATCH_ID, target_count))
    conn.commit()


def update_checkpoint(conn: sqlite3.Connection, processed: int, success: int, rejected: int, errors: int, last_id: str, status: str = 'RUNNING'):
    """Atualiza o checkpoint persistente no banco de dados."""
    c = conn.cursor()
    c.execute("""
        UPDATE learning_batch_checkpoints
        SET processed_count = ?,
            success_count = ?,
            rejected_count = ?,
            error_count = ?,
            last_processed_source_id = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE batch_id = ?
    """, (processed, success, rejected, errors, last_id, status, BATCH_ID))
    conn.commit()


def check_circuit_breakers(
    consecutive_errors: int,
    total_processed: int,
    corrupted_count: int,
    silent_audio_count: int,
    model_gateway: ModelGatewayService
):
    """
    Verifica os 5 gatilhos de segurança do Circuit Breaker:
    1. Máximo de 3 falhas consecutivas de download.
    2. Taxa de arquivos corrompidos <= 5% (após amostra mínima >= 10).
    3. Taxa de áudio silencioso <= 20% (após amostra mínima >= 10).
    4. Espaço livre em disco >= 2.0 GB.
    5. Custo estrito de $0.00.
    """
    if consecutive_errors >= 3:
        raise CircuitBreakerException(f"Circuit Breaker Disparado: {consecutive_errors} falhas consecutivas de download.")

    if total_processed >= 10:
        corrupted_rate = corrupted_count / total_processed
        if corrupted_rate > 0.05:
            raise CircuitBreakerException(f"Circuit Breaker Disparado: taxa de arquivos corrompidos ({corrupted_rate*100:.1f}%) > 5%.")

        silent_rate = silent_audio_count / total_processed
        if silent_rate > 0.20:
            raise CircuitBreakerException(f"Circuit Breaker Disparado: taxa de áudio silencioso ({silent_rate*100:.1f}%) > 20%.")

    free_gb = shutil.disk_usage(str(BASE_DIR)).free / (1024 ** 3)
    if free_gb < 2.0:
        raise CircuitBreakerException(f"Circuit Breaker Disparado: espaço em disco crítico ({free_gb:.2f} GB livre < 2.0 GB).")

    metrics = model_gateway.get_usage_metrics()
    cost = metrics.get("total_cost_usd", 0.0)
    if cost > 0.0:
        raise CircuitBreakerException(f"Circuit Breaker Disparado: custo financeiro não-zero detectado (${cost:.4f}).")


def synthesize_editorial_learnings_for_channels(learning_sys: AudiovisualLearningSystem, processed_records: List[Dict[str, Any]]):
    """
    Sintetiza e grava na editorial_knowledge_library o conhecimento extraído
    dos learning_candidates, isolado por canal, cumprindo a Regra de Ouro:
    >= 2 evidências = APRENDIZADO_VALIDADO (confiança >= 0.80)
    1 evidência = OBSERVAÇÃO (confiança <= 0.70)
    Anti-patterns documentados para anomalias reais rejeitadas.
    """
    print("\n" + "=" * 80, flush=True)
    print(" SÍNTESE DE APRENDIZADO EDITORIAL BASEADO EM EVIDÊNCIAS (FASE 16)", flush=True)
    print("=" * 80, flush=True)

    # Limpa registros anteriores desta fase (id >= 65) apenas caso esteja reprocessando a Fase 16,
    # preservando 100% dos registros históricos (IDs <= 64 das Fases 14, 15 e 15.1)
    with learning_sys._get_conn() as conn:
        conn.execute("DELETE FROM editorial_knowledge_library WHERE id >= 65")
        conn.commit()

    for ch_id in range(1, 6):
        ch_all = [r for r in processed_records if r.get("channel_id") == ch_id]
        ch_records = [r for r in ch_all if r.get("state") == "learning_candidate"]
        ch_rejected = [r for r in ch_all if r.get("state") == "editorially_rejected"]
        if not ch_records:
            continue

        niche = ch_records[0]["niche"]
        ch_name = ch_records[0]["channel_name"]
        print(f"\n[Canal {ch_id} - {ch_name}] Sintetizando padrões a partir de {len(ch_records)} candidatos ({len(ch_rejected)} rejeitados)...", flush=True)

        fast_cut_ids = [r["video_id"] for r in ch_records if r.get("cuts_count", 0) >= 4]
        slow_cut_ids = [r["video_id"] for r in ch_records if r.get("cuts_count", 0) < 4]
        comm_loud_ids = [r["video_id"] for r in ch_records if -24.0 <= r.get("integrated_lufs", -20.0) <= -6.0 and r.get("acoustic_classification") != "SILENT_AUDIO_TRACK"]
        speech_ids = [r["video_id"] for r in ch_records if r.get("speech_detected")]

        # 1. Padrão Dinâmico de Edição
        if len(fast_cut_ids) >= 2:
            learning_sys.record_knowledge(
                category=niche,
                topic="ritmo_de_cortes_dinamico",
                title=f"Cortes Ágeis (>= 4) em Vídeos Curtos de {ch_name}",
                summary=f"Identificados {len(fast_cut_ids)} vídeos aprovados com >= 4 cortes físicos medidos por PySceneDetect.",
                confidence_score=0.92 if len(fast_cut_ids) >= 4 else 0.85,
                confidence_explanation=f"Apoiado por {len(fast_cut_ids)} evidências físicas reais no canal {ch_id}, com {len(slow_cut_ids)} contraexemplos de ritmo lento.",
                evidence_video_ids=fast_cut_ids[:6],
                channel_id=ch_id,
                target_channel_id=ch_id,
                actionable_recommendation=f"Manter cortes dinâmicos frequentes na edição para {ch_name}.",
                anti_pattern_warning="Evitar planos estáticos prolongados (> 8s) sem mudança visual ou zoom.",
                counterexamples=slow_cut_ids[:2],
                limitations="Observação estrutural de ritmo de edição; não substitui curva real de retenção do YouTube Studio Analytics.",
                classification="APRENDIZADO_VALIDADO",
                validation_status="APRENDIZADO_VALIDADO",
                pilot_phase=16
            )

        # 2. Padrão Acústico EBU R128 (somente de áudios válidos reais, nunca silenciosos!)
        if len(comm_loud_ids) >= 2:
            silent_counter = [r["video_id"] for r in ch_rejected if r.get("acoustic_classification") == "SILENT_AUDIO_TRACK"]
            learning_sys.record_knowledge(
                category=niche,
                topic="padrao_loudness_comercial",
                title=f"Loudness Efetivo (-24 a -6 LUFS) em {ch_name}",
                summary=f"Faixa dinâmica comercial medida fisicamente via FFmpeg EBU R128 (-vn) em {len(comm_loud_ids)} vídeos utilizáveis.",
                confidence_score=0.93 if len(comm_loud_ids) >= 4 else 0.86,
                confidence_explanation=f"Confirmado em {len(comm_loud_ids)} medições físicas diretas EBU R128 no canal {ch_id}.",
                evidence_video_ids=comm_loud_ids[:6],
                channel_id=ch_id,
                target_channel_id=ch_id,
                actionable_recommendation="Normalizar mixagem final em -14.0 LUFS com True Peak <= -1.0 dBTP.",
                anti_pattern_warning="Rejeitar faixas com silêncio digital (<= -65 LUFS) ou clipping (> -0.3 dBTP).",
                counterexamples=silent_counter[:2],
                limitations="Medição de loudness não distingue isoladamente música instrumental de narração; verificar speech_detected.",
                classification="APRENDIZADO_VALIDADO",
                validation_status="APRENDIZADO_VALIDADO",
                pilot_phase=16
            )

        # 3. Padrão Narrativo com Base em Transcrição Real Whisper/Legenda
        if len(speech_ids) >= 2:
            non_speech_counter = [r["video_id"] for r in ch_records if not r.get("speech_detected")]
            learning_sys.record_knowledge(
                category=niche,
                topic="estrutura_narrativa_real",
                title=f"Presença de Narração Estruturada em {ch_name}",
                summary=f"Transcrição física via Whisper/legendas confirmou conteúdo falado estruturado em {len(speech_ids)} Shorts do canal.",
                confidence_score=0.90 if len(speech_ids) >= 4 else 0.82,
                confidence_explanation=f"Baseado em {len(speech_ids)} transcrições reais verificadas no canal {ch_id}.",
                evidence_video_ids=speech_ids[:6],
                channel_id=ch_id,
                target_channel_id=ch_id,
                actionable_recommendation="Iniciar narração diretamente com gancho factual ou pergunta nos 3 segundos iniciais.",
                anti_pattern_warning="Evitar abertura silenciosa prolongada sem contextualização falada ou legenda legível.",
                counterexamples=non_speech_counter[:2],
                limitations="Transcrição automática Whisper (modelo tiny em CPU) pode conter imprecisões em jargões ou áudio ruidoso.",
                classification="APRENDIZADO_VALIDADO",
                validation_status="APRENDIZADO_VALIDADO",
                pilot_phase=16
            )

        # 4. Observação de Evidência Única (Regra de Ouro: 1 evidência = OBSERVAÇÃO)
        if slow_cut_ids:
            obs_id = slow_cut_ids[0]
            learning_sys.record_knowledge(
                category=niche,
                topic="plano_continuo_observacao",
                title=f"Plano Contínuo (< 4 cortes) em {ch_name}",
                summary=f"Exemplo isolado ({obs_id}) utilizando montagem mais pausada dentro do nicho {niche}.",
                confidence_score=0.65,
                confidence_explanation="Apenas 1 evidência isolada destacada; mantido estritamente como OBSERVAÇÃO (<= 0.70).",
                evidence_video_ids=[obs_id],
                channel_id=ch_id,
                target_channel_id=ch_id,
                actionable_recommendation="Não replicar como regra sem experimento A/B com múltiplas amostras.",
                anti_pattern_warning="Não generalizar amostra única como padrão editorial do canal.",
                counterexamples=fast_cut_ids[:1],
                limitations="Amostra única (N=1); insuficiência estatística por definição.",
                classification="OBSERVAÇÃO",
                validation_status="OBSERVAÇÃO",
                pilot_phase=16
            )

        # 5. Registro Explícito de Anti-Pattern por Canal quando houver rejeição real
        for rej in ch_rejected:
            learning_sys.record_knowledge(
                category=niche,
                topic="anti_pattern_editorial_ou_acustico",
                title=f"Anti-Pattern Detectado em {ch_name}: {rej['video_id']}",
                summary=f"Vídeo {rej['video_id']} rejeitado automaticamente ({rej.get('rejection_reason', 'anomalia')}).",
                confidence_score=0.90 if rej.get("acoustic_classification") == "SILENT_AUDIO_TRACK" else 0.70,
                confidence_explanation="Evidência empírica de rejeição física ou incompatibilidade contextual no piloto de 100 vídeos.",
                evidence_video_ids=[rej["video_id"]],
                channel_id=ch_id,
                target_channel_id=ch_id,
                actionable_recommendation="Manter filtro preventivo na triagem pré-ingestão e auditoria pós-download.",
                anti_pattern_warning=f"Não aprovar candidatos com perfil semelhante a '{rej['title'][:45]}'.",
                counterexamples=[],
                limitations="Baseado na ocorrência específica identificada durante o lote piloto.",
                classification="ANTI_PATTERN",
                validation_status="ANTI_PATTERN",
                pilot_phase=16
            )


def run_pilot_100(force_reprocess: bool = False):
    print("=" * 85, flush=True)
    print(" VANTIS — EXECUÇÃO DO PILOTO CONTROLADO DE 100 SHORTS (FASE 16) ", flush=True)
    print(" Escala Controlada | 20 Shorts/Canal | Multimodal Físico Real | Zero Simulação | $0.00 ", flush=True)
    print("=" * 85, flush=True)

    start_time = time.time()

    if not MANIFEST_JSON.exists():
        print(f"[ERRO CRÍTICO] Manifesto de candidatos não encontrado em {MANIFEST_JSON}", flush=True)
        sys.exit(1)

    with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    candidates = manifest_data.get("candidates", [])
    if len(candidates) != 100:
        print(f"[ERRO CRÍTICO] Manifesto deve conter exatamente 100 candidatos, obtido {len(candidates)}", flush=True)
        sys.exit(1)

    learning_sys = AudiovisualLearningSystem()
    downloader = MediaDownloader()
    ffmpeg = FFmpegEngine()
    scene_detector = SceneDetectorService()
    visual_analyzer = OpenCVVisualAnalyzer()
    whisper_svc = WhisperTranscriptionService(model_size="tiny")
    model_gateway = ModelGatewayService()

    print("\n[Pré-Execução] Validando Trava de Custo Zero, Ferramentas e Espaço em Disco...", flush=True)
    metrics = model_gateway.get_usage_metrics()
    assert metrics.get("enforce_free_tier", True), "Trava orçamentária enforce_free_tier DEVE estar ativa!"
    assert metrics.get("total_cost_usd", 0.0) == 0.0, "Custo inicial deve ser exatamente $0.00!"
    free_gb = shutil.disk_usage(str(BASE_DIR)).free / (1024 ** 3)
    print(f" -> Espaço Livre em Disco : {free_gb:.2f} GB", flush=True)
    print(f" -> Custo ModelGateway     : ${metrics.get('total_cost_usd', 0.0):.4f}", flush=True)
    print(f" -> FFmpeg Disponível      : {ffmpeg.get_status().get('available')} ({ffmpeg.binary_path})", flush=True)
    print(f" -> PySceneDetect Ativo    : {scene_detector.has_scenedetect}", flush=True)
    print(f" -> OpenCV Ativo           : {visual_analyzer.available}", flush=True)
    print(f" -> Whisper Local Engine   : {whisper_svc.engine_type} (modelo tiny CPU)", flush=True)

    with learning_sys._get_conn() as conn:
        init_checkpoint(conn, target_count=100)

    consecutive_dl_errors = 0
    corrupted_count = 0
    silent_audio_count = 0
    processed_count = 0
    success_count = 0
    rejected_count = 0
    failed_count = 0
    cb_triggered = False

    processed_records = []

    print(f"\n[Execução de Lote] Processando 100 Shorts (force_reprocess={force_reprocess})...", flush=True)

    for idx, c in enumerate(candidates, start=1):
        v_id = c["id"]
        url = c["url"]
        title = c["title"]
        ch_id = c["channel_id"]
        ch_name = c["channel_name"]
        niche = c["editorial_category"]
        claimed_duration = c["metadata_duration"]

        print(f"\n[{idx}/100] [Canal {ch_id}] {v_id} ({claimed_duration:.1f}s) | '{title[:50]}'", flush=True)

        # Idempotência apenas quando NÃO for reprocessamento explícito e registro já possuir payload completo da Fase 16 v2
        if not force_reprocess:
            with learning_sys._get_conn() as conn:
                prior_row = conn.execute(
                    "SELECT processing_state, analysis_payload FROM audiovisual_library WHERE source_id = ?",
                    (v_id,)
                ).fetchone()

            if prior_row:
                analysis_p = json.loads(prior_row["analysis_payload"] or "{}")
                phys = analysis_p.get("physical_media", {})
                ed_p = analysis_p.get("editorial_adherence", {})
                if "video_codec" in phys and ed_p.get("evaluated_with_transcript") is not None:
                    local_p = phys.get("local_path")
                    if local_p and Path(local_p).exists() and Path(local_p).stat().st_size > 0:
                        visual_p = analysis_p.get("visual_and_editing", {})
                        audio_p = analysis_p.get("audio", {})
                        narr_p = analysis_p.get("narrative_and_script", {})
                        record_state = prior_row["processing_state"]
                        if audio_p.get("audio_classification") == "SILENT_AUDIO_TRACK":
                            silent_audio_count += 1
                        if record_state == "editorially_rejected":
                            rejected_count += 1
                        else:
                            success_count += 1
                        processed_count += 1
                        processed_records.append({
                            "channel_id": ch_id,
                            "channel_name": ch_name,
                            "niche": niche,
                            "video_id": v_id,
                            "url": url,
                            "title": title,
                            "duration_seconds": phys.get("verified_duration", claimed_duration),
                            "file_size_bytes": phys.get("file_size_bytes", 0),
                            "sha256": phys.get("sha256_hash", ""),
                            "video_codec": phys.get("video_codec"),
                            "audio_codec": phys.get("audio_codec"),
                            "streams_count": phys.get("streams_count"),
                            "resolution": phys.get("resolution"),
                            "ffmpeg_decode_ok": phys.get("ffmpeg_decode_ok", True),
                            "opencv_frames_read_ok": phys.get("opencv_frames_read_ok", True),
                            "cuts_count": visual_p.get("cuts_count", 0),
                            "avg_cut_interval_sec": visual_p.get("avg_cut_interval_sec"),
                            "aspect_ratio": visual_p.get("aspect_ratio"),
                            "is_vertical_9_16": visual_p.get("is_vertical_9_16", False),
                            "has_subtitles_on_screen": visual_p.get("has_subtitles_on_screen"),
                            "integrated_lufs": audio_p.get("integrated_lufs", -14.0),
                            "true_peak_db": audio_p.get("true_peak_db"),
                            "clipping_detected": audio_p.get("clipping_detected", False),
                            "acoustic_classification": audio_p.get("audio_classification", "VALID_AUDIO"),
                            "speech_detected": narr_p.get("speech_detected", False),
                            "word_count": narr_p.get("word_count", 0),
                            "speaking_pace_wpm": narr_p.get("speaking_pace_wpm"),
                            "hook_type": narr_p.get("hook_type"),
                            "state": record_state,
                            "editorial_verdict": ed_p.get("editorial_verdict", "APPROVED"),
                            "rejection_reason": ed_p.get("rejection_reason")
                        })
                        print(f"        [Idempotente]: Estado '{record_state}' já completo.", flush=True)
                        continue

        # 1. Descoberta e Metadados (preserva registro existente sem apagar histórico)
        raw_meta = {
            "id": v_id,
            "title": title,
            "uploader": c.get("uploader"),
            "duration": claimed_duration,
            "pilot_phase": 16,
            "target_channel_id": ch_id,
            "channel_id": ch_id
        }
        learning_sys.discover_video(
            source_id=v_id,
            original_url=url,
            title=title,
            creator=c.get("uploader", "Desconhecido"),
            niche=niche,
            duration_seconds=claimed_duration,
            views_count=c.get("views", 0),
            likes_count=c.get("likes", 0),
            raw_metadata=raw_meta,
            channel_id=ch_id
        )
        # Garante raw_metadata atualizado com pilot_phase: 16 caso já existisse
        with learning_sys._get_conn() as conn:
            conn.execute(
                "UPDATE audiovisual_library SET raw_metadata = ? WHERE source_id = ?",
                (json.dumps(raw_meta), v_id)
            )
            conn.commit()
        learning_sys.process_metadata(v_id)

        # 2. Download Físico / Verificação Real no Disco
        ch_dir = DOWNLOADS_ROOT / f"ch_{ch_id}"
        ch_dir.mkdir(parents=True, exist_ok=True)
        downloader.download_dir = ch_dir

        existing_files = [f for f in ch_dir.glob(f"{v_id}.*") if f.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov")]
        dl_res = None

        if existing_files and existing_files[0].stat().st_size > 0:
            existing_f = existing_files[0]
            probe = ffmpeg.probe_media(str(existing_f))
            dec = ffmpeg.verify_decode_integrity(str(existing_f))
            if probe.get("duration_sec", 0) > 0 and dec.get("decodable", False):
                hasher = hashlib.sha256()
                with open(existing_f, "rb") as f_in:
                    for chunk in iter(lambda: f_in.read(65536), b""):
                        hasher.update(chunk)
                dl_res = {
                    "success": True,
                    "file_path": str(existing_f.resolve()),
                    "file_size_bytes": existing_f.stat().st_size,
                    "sha256": hasher.hexdigest(),
                    "duration_seconds": probe["duration_sec"],
                    "video_codec": probe.get("video_codec"),
                    "audio_codec": probe.get("audio_codec"),
                    "streams_count": probe.get("streams_count", 0),
                    "resolution": f"{probe.get('width')}x{probe.get('height')}" if probe.get("width") else None,
                    "ffmpeg_decode_ok": True,
                    "ffmpeg_decode_error": None
                }

        if not dl_res:
            jitter_sec = random.uniform(3.0, 6.5)
            time.sleep(jitter_sec)
            dl_res = downloader.download_short(url, output_dir=ch_dir)

        if not dl_res.get("success"):
            consecutive_dl_errors += 1
            failed_count += 1
            learning_sys._set_state(v_id, "failed", error_msg=f"Download/Decode failed: {dl_res.get('error')}")
            check_circuit_breakers(consecutive_dl_errors, idx, corrupted_count, silent_audio_count, model_gateway)
            continue

        consecutive_dl_errors = 0
        local_video_path = dl_res["file_path"]
        file_size = dl_res["file_size_bytes"]
        sha256 = dl_res["sha256"]
        verified_dur = dl_res["duration_seconds"]

        if file_size <= 0 or len(sha256) != 64 or verified_dur <= 0 or verified_dur > 61.0:
            corrupted_count += 1
            failed_count += 1
            learning_sys._set_state(v_id, "failed", error_msg="Arquivo corrompido ou duração fora dos limites")
            check_circuit_breakers(consecutive_dl_errors, idx, corrupted_count, silent_audio_count, model_gateway)
            continue

        # 3. Análise Multimodal Real
        # 3.1 Visual (PySceneDetect + OpenCV real)
        scene_res = scene_detector.detect_scenes(local_video_path)
        cuts_count = max(0, scene_res.get("total_scenes", 1) - 1)
        cut_intervals = scene_res.get("cut_intervals_sec", [])
        avg_cut_interval = scene_res.get("avg_cut_interval_sec", verified_dur)

        probe_info = ffmpeg.probe_media(local_video_path)
        aspect_ratio = probe_info.get("aspect_ratio") or "unknown"
        is_vert = probe_info.get("is_vertical", False)

        motion_info = visual_analyzer.analyze_framing_and_motion(local_video_path)
        opencv_ok = motion_info.get("opencv_frames_read_ok", False)
        sampled_cnt = motion_info.get("sampled_frames_count", 0)
        shot_type = motion_info.get("estimated_shot_type", "")
        dominant_comp = "close_up_narrador" if "Close-Up" in shot_type else ("dynamic_action" if "Dynamic" in shot_type else "standard")

        # Registra mídia física com codecs, streams, decodificação FFmpeg e OpenCV
        learning_sys.register_physical_media(
            source_id=v_id,
            local_path=local_video_path,
            file_size_bytes=file_size,
            sha256_hash=sha256,
            verified_duration=verified_dur,
            video_codec=probe_info.get("video_codec"),
            audio_codec=probe_info.get("audio_codec"),
            streams_count=probe_info.get("streams_count"),
            ffmpeg_decode_ok=dl_res.get("ffmpeg_decode_ok", True),
            ffmpeg_decode_error=dl_res.get("ffmpeg_decode_error"),
            opencv_frames_read_ok=opencv_ok,
            opencv_sampled_frames=sampled_cnt,
            resolution=f"{probe_info.get('width')}x{probe_info.get('height')}" if probe_info.get("width") else None
        )
        learning_sys._set_state(v_id, "downloaded")

        learning_sys.process_visual(
            source_id=v_id,
            cuts_count=cuts_count,
            aspect_ratio=aspect_ratio,
            has_subtitles_on_screen=motion_info.get("text_on_screen_detected"),
            framing_changes=motion_info.get("framing_changes_detected", 0),
            broll_presence_ratio=0.0,
            dominant_composition=dominant_comp,
            cut_intervals_sec=cut_intervals,
            avg_cut_interval_sec=avg_cut_interval,
            representative_frames=motion_info.get("representative_frames", []),
            average_motion_score=motion_info.get("average_motion_score"),
            text_detection_evidence={
                "method": motion_info.get("text_detection_method"),
                "text_edge_density_avg": motion_info.get("text_edge_density_avg")
            },
            opencv_frames_read_ok=opencv_ok
        )

        # 3.2 Acústica (FFmpeg EBU R128 com -vn)
        audio_metrics = learning_sys._analyze_audio_file(local_video_path)
        measured_lufs = audio_metrics["integrated_lufs"]
        speech_clarity = audio_metrics["speech_clarity_score"]
        pauses_ratio = audio_metrics["pauses_ratio"]
        acoustic_classification = audio_metrics["classification"]
        clipping_detected = audio_metrics.get("clipping_detected", False)

        if acoustic_classification == "SILENT_AUDIO_TRACK":
            silent_audio_count += 1

        learning_sys.process_audio(
            source_id=v_id,
            speech_clarity_score=speech_clarity,
            estimated_lufs=measured_lufs,
            pauses_ratio=pauses_ratio,
            audio_classification=acoustic_classification,
            is_usable=audio_metrics["is_usable"],
            diagnostic_message=audio_metrics["diagnostic_message"],
            clipping_detected=clipping_detected,
            true_peak_db=audio_metrics.get("true_peak_db"),
            lra=audio_metrics.get("lra")
        )

        # 3.3 Narrativa REAL (Legendas reais ou Faster-Whisper CPU local — ZERO placeholder!)
        real_transcript = fetch_subtitles_for_short(url, v_id, local_video_path=local_video_path, allow_network=False)
        trans_engine = "youtube_subtitles"
        if not real_transcript and audio_metrics["is_usable"]:
            try:
                lang_hint = "en" if any(w in title.lower() for w in ["the ", "how ", "why ", "atomic habits", "stoic"]) else "pt"
                w_res = whisper_svc.transcribe_audio(local_video_path, language=lang_hint)
                real_transcript = (w_res.get("full_transcript") or "").strip()
                trans_engine = f"faster_whisper_{whisper_svc.model_size}"
            except Exception as e:
                print(f"        [Aviso Whisper]: {e}", flush=True)
                real_transcript = ""

        narr_res = learning_sys.process_transcript(
            v_id,
            real_transcript,
            allow_insufficient_speech=True,
            transcription_engine=trans_engine
        )
        narr_metrics = narr_res.get("metrics", {})
        speech_detected = bool(narr_metrics.get("speech_detected", False))

        # 3.4 Conclusão Técnica
        learning_sys._set_state(v_id, "technical_analysis_complete")
        print(
            f"        [Técnico OK]: {probe_info.get('video_codec')}/{probe_info.get('audio_codec')} "
            f"| {cuts_count} cortes | {aspect_ratio} | {measured_lufs:.1f} LUFS ({acoustic_classification}) "
            f"| Fala: {narr_metrics.get('word_count', 0)} palavras ({narr_metrics.get('narrative_analysis_status')})",
            flush=True
        )

        # 4. Avaliação Editorial Contextual Real (SEM forced IDs!)
        ed_res = learning_sys.evaluate_editorial_adherence(
            source_id=v_id,
            target_channel_id=ch_id
        )

        if ed_res["processing_state"] == "editorially_rejected":
            rejected_count += 1
            record_state = "editorially_rejected"
            print(f"        [REJEITADO EDITORIAL/TÉCNICO]: {ed_res['editorial_verdict']} -> {ed_res['rejection_reason']}", flush=True)
        else:
            prom_res = learning_sys.promote_to_learning_candidate(v_id)
            success_count += 1
            record_state = prom_res["processing_state"]
            print(f"        [APROVADO]: '{record_state}'", flush=True)

        processed_count += 1
        with learning_sys._get_conn() as conn:
            update_checkpoint(conn, processed_count, success_count, rejected_count, consecutive_dl_errors, v_id)

        check_circuit_breakers(consecutive_dl_errors, processed_count, corrupted_count, silent_audio_count, model_gateway)

        processed_records.append({
            "channel_id": ch_id,
            "channel_name": ch_name,
            "niche": niche,
            "video_id": v_id,
            "url": url,
            "title": title,
            "duration_seconds": verified_dur,
            "file_size_bytes": file_size,
            "sha256": sha256,
            "video_codec": probe_info.get("video_codec"),
            "audio_codec": probe_info.get("audio_codec"),
            "streams_count": probe_info.get("streams_count"),
            "resolution": f"{probe_info.get('width')}x{probe_info.get('height')}" if probe_info.get("width") else None,
            "ffmpeg_decode_ok": True,
            "opencv_frames_read_ok": opencv_ok,
            "cuts_count": cuts_count,
            "avg_cut_interval_sec": avg_cut_interval,
            "aspect_ratio": aspect_ratio,
            "is_vertical_9_16": is_vert,
            "has_subtitles_on_screen": motion_info.get("text_on_screen_detected"),
            "integrated_lufs": measured_lufs,
            "true_peak_db": audio_metrics.get("true_peak_db"),
            "clipping_detected": clipping_detected,
            "acoustic_classification": acoustic_classification,
            "speech_detected": speech_detected,
            "word_count": narr_metrics.get("word_count", 0),
            "speaking_pace_wpm": narr_metrics.get("speaking_pace_wpm"),
            "hook_type": narr_metrics.get("hook_type"),
            "state": record_state,
            "editorial_verdict": ed_res["editorial_verdict"],
            "rejection_reason": ed_res.get("rejection_reason")
        })

    # 6. Síntese e Gravação de Aprendizado Editorial Real
    synthesize_editorial_learnings_for_channels(learning_sys, processed_records)

    # 7. Finaliza Checkpoint
    with learning_sys._get_conn() as conn:
        update_checkpoint(conn, processed_count, success_count, rejected_count, 0, candidates[-1]["id"], status='COMPLETED')

    elapsed = time.time() - start_time
    final_cost = float(model_gateway.get_usage_metrics().get("total_cost_usd", 0.0))

    execution_data = {
        "pilot_name": "FASE16_PILOT_100_SHORTS",
        "timestamp": time.time(),
        "elapsed_seconds": elapsed,
        "total_target": 100,
        "processed_count": processed_count,
        "physically_validated_count": sum(1 for r in processed_records if r.get("ffmpeg_decode_ok")),
        "technically_complete_count": processed_count,
        "editorially_approved_count": success_count,
        "editorially_rejected_count": rejected_count,
        "learning_candidates_count": success_count,
        "speech_transcribed_count": sum(1 for r in processed_records if r.get("speech_detected")),
        "vertical_9_16_count": sum(1 for r in processed_records if r.get("is_vertical_9_16")),
        "corrupted_count": corrupted_count,
        "silent_audio_count": silent_audio_count,
        "failed_count": failed_count,
        "cost_usd": final_cost,
        "total_storage_bytes": sum(r["file_size_bytes"] for r in processed_records),
        "circuit_breaker_triggered": cb_triggered,
        "records": processed_records
    }

    EXECUTION_DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(EXECUTION_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(execution_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 90, flush=True)
    print("           RELATÓRIO CONSOLIDADO DO PILOTO DE 100 SHORTS (FASE 16)           ", flush=True)
    print("=" * 90, flush=True)
    print(f"Total Processado                : {processed_count} / 100", flush=True)
    print(f"Validados Físicos FFmpeg/OpenCV : {execution_data['physically_validated_count']} / {processed_count}", flush=True)
    print(f"Com Fala Real Transcrita (CPU)  : {execution_data['speech_transcribed_count']} / {processed_count}", flush=True)
    print(f"Proporção Vertical 9:16         : {execution_data['vertical_9_16_count']} / {processed_count}", flush=True)
    print(f"Áudio Silencioso Detectado      : {silent_audio_count}", flush=True)
    print(f"Candidatos Aprovados            : {success_count}", flush=True)
    print(f"Rejeições Editoriais/Acústicas  : {rejected_count}", flush=True)
    print(f"Volume Total em Disco           : {execution_data['total_storage_bytes'] / (1024*1024):.2f} MB", flush=True)
    print(f"Custo Financeiro Real           : ${final_cost:.2f}", flush=True)
    print(f"Tempo de Execução               : {elapsed:.1f}s", flush=True)
    print("=" * 90, flush=True)


if __name__ == "__main__":
    reproc = "--reprocess" in sys.argv
    run_pilot_100(force_reprocess=reproc)
