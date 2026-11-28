"""
VANTIS — Script de Auditoria Forense Completa da Fase 15 (20 Shorts)
Inspeciona cada um dos 20 vídeos do piloto no banco de dados e no disco:
- Existência, tamanho, SHA256 completo de 64 caracteres
- Fluxos de vídeo e áudio via FFprobe (detecção estrita de ausência de faixa de áudio)
- Decodificabilidade total via FFmpeg e OpenCV
- Análise acústica com distinção de:
  * Áudio válido
  * Áudio silencioso / quase silencioso
  * Sem faixa de áudio
  * Falha de decodificação
- Duração nominal dos metadados vs Duração real física
- Análise de aderência editorial ao canal de destino
"""

import os
import sys
import json
import hashlib
import sqlite3
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import cv2
from services.media_processing.ffmpeg_engine import FFmpegEngine

DB_PATH = BASE_DIR / "database" / "shorts_central.db"
JSON_PATH = BASE_DIR / "docs" / "audits" / "phase15_pilot_execution_data.json"

CHANNEL_THEMES = {
    1: {"name": "Canal 01 - Futebol em 60 Segundos", "niche": "futebol_outros", "keywords": ["futebol", "gol", "lance", "drible", "jogo", "torcida", "time", "bola", "champions", "palmeiras", "madrid"]},
    2: {"name": "Canal 02 - Arquivo Sombrio (Casos Reais)", "niche": "casos_policiais", "keywords": ["misterio", "crime", "caso", "policial", "tribunal", "suspeito", "execucao", "morte", "investigacao", "assassino", "bizarro", "namibia"]},
    3: {"name": "Canal 03 - Rir para Não Chorar", "niche": "humor", "keywords": ["humor", "comedia", "pegadinha", "trolagem", "engracado", "piada", "meme", "rir", "cliente", "cachorro", "caramelo"]},
    4: {"name": "Canal 04 - Mente Curiosa & Ciência", "niche": "curiosidades", "keywords": ["curiosidade", "fato", "ciencia", "natureza", "borboleta", "sabia", "incrivel", "universo", "planeta", "historia"]},
    5: {"name": "Canal 05 - Mente Focada & Produtividade", "niche": "desenvolvimento_pessoal", "keywords": ["disciplina", "foco", "motivacao", "produtividade", "vida", "riqueza", "milionario", "habito", "mente"]}
}

def calculate_full_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def test_ffmpeg_decodability(file_path: Path, ffmpeg_bin: str) -> dict:
    cmd = [ffmpeg_bin, "-v", "error", "-i", str(file_path), "-f", "null", "-"]
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=30)
    return {
        "decodable": res.returncode == 0,
        "error_message": res.stderr.strip() if res.stderr else None
    }

def test_opencv_decodability(file_path: Path) -> dict:
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        return {"cv2_readable": False, "frame_count": 0, "fps": 0, "width": 0, "height": 0}
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Testa leitura do primeiro e último frame
    ret_first, _ = cap.read()
    if frame_count > 10:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 2)
        ret_last, _ = cap.read()
    else:
        ret_last = ret_first
    cap.release()

    return {
        "cv2_readable": ret_first and ret_last,
        "frame_count": frame_count,
        "fps": round(fps, 2) if fps else 0.0,
        "width": width,
        "height": height,
        "aspect_ratio": f"{width}:{height}"
    }

def run_forensic_audit():
    print("=" * 90)
    print("VANTIS — AUDITORIA FORENSE E RIGOROSA DOS 20 SHORTS (FASE 15.1)")
    print("Zero suposições | Integridade de arquivos | Investigação acústica e editorial")
    print("=" * 90)

    ffmpeg_engine = FFmpegEngine()
    ffmpeg_bin = ffmpeg_engine.binary_path

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM audiovisual_library WHERE id > 23 ORDER BY id ASC")
    db_rows = cur.fetchall()
    print(f"Registros encontrados no banco para o piloto da Fase 15 (IDs > 23): {len(db_rows)}")

    audit_results = []

    for idx, row in enumerate(db_rows, 1):
        vid_id = row["source_id"]
        title = row["title"]
        db_duration = row["duration_seconds"]
        db_state = row["processing_state"]
        url = row["original_url"]
        
        raw_meta = json.loads(row["raw_metadata"] or "{}")
        ch_id = raw_meta.get("target_channel_id") or 1
        meta_duration = raw_meta.get("duration")

        payload = json.loads(row["analysis_payload"] or "{}")
        phys_meta = payload.get("physical_media", {})
        audio_meta = payload.get("audio", {})
        vis_meta = payload.get("visual_and_editing", {})

        local_path_str = phys_meta.get("local_path")
        local_path = Path(local_path_str) if local_path_str else None

        print(f"\n[{idx:02d}/20] Analisando: ID {vid_id} | Canal {ch_id}")
        print(f"       Título: {title[:60]}")

        # 1. Existência física do arquivo
        file_exists = local_path is not None and local_path.exists() and local_path.is_file()
        file_size = local_path.stat().st_size if file_exists else 0
        
        # 2. Hash SHA256 completo (64 caracteres)
        full_sha256 = calculate_full_sha256(local_path) if file_exists else None
        stored_sha256 = phys_meta.get("sha256_hash")
        sha256_match = (full_sha256 == stored_sha256) if (full_sha256 and stored_sha256) else False

        # 3. Probes técnicos detalhados (Streams de vídeo e áudio)
        probe_data = ffmpeg_engine.probe_media(str(local_path)) if file_exists else {}
        real_duration = probe_data.get("duration_sec", 0.0)
        has_video_stream = probe_data.get("has_video", False)
        has_audio_stream = probe_data.get("has_audio", False)
        probe_format = probe_data.get("format", "")
        v_codec = probe_data.get("video_codec", "")
        a_codec = probe_data.get("audio_codec", "")

        # 4. Decodificabilidade
        ffmpeg_dec = test_ffmpeg_decodability(local_path, ffmpeg_bin) if file_exists else {"decodable": False, "error_message": "Arquivo ausente"}
        cv2_dec = test_opencv_decodability(local_path) if file_exists else {"cv2_readable": False}

        # 5. Investigação Acústica Forense (Dissecando -70.0 LUFS e limites)
        stored_lufs = audio_meta.get("integrated_lufs")
        audio_diagnostic = "UNKNOWN"
        measured_lufs = None

        if not file_exists:
            audio_diagnostic = "FILE_MISSING"
        elif not has_audio_stream:
            audio_diagnostic = "NO_AUDIO_TRACK"
        else:
            # Mede loudness diretamente com FFmpeg ebur128
            try:
                measured = ffmpeg_engine.measure_loudness(str(local_path))
                measured_lufs = measured.get("integrated_lufs")
                if measured_lufs is None or measured_lufs <= -69.0:
                    audio_diagnostic = "SILENT_AUDIO_TRACK"
                elif -69.0 < measured_lufs <= -24.0:
                    audio_diagnostic = "QUIET_AUDIO_TRACK"
                elif -24.0 < measured_lufs <= -10.0:
                    audio_diagnostic = "VALID_STANDARD_AUDIO"
                elif measured_lufs > -10.0:
                    audio_diagnostic = "HOT_LOUD_AUDIO"
            except Exception as e:
                audio_diagnostic = f"MEASUREMENT_FAILURE: {str(e)}"

        # 6. Auditoria Editorial de Aderência
        theme_info = CHANNEL_THEMES.get(ch_id, {})
        ch_name = theme_info.get("name", f"Canal {ch_id}")
        expected_niche = theme_info.get("niche", "geral")
        keywords = theme_info.get("keywords", [])

        title_lower = title.lower()
        keyword_hits = [kw for kw in keywords if kw in title_lower]
        
        # Critérios de inadequação editorial explícita
        editorial_verdict = "APPROVED"
        editorial_issues = []

        if ch_id == 2:
            # Canal 2 é Arquivo Sombrio (Casos Reais / Crimes / Mistérios)
            if "jeans" in title_lower or "cintura baixa" in title_lower:
                editorial_verdict = "REJECTED_OFF_TOPIC"
                editorial_issues.append("Conteúdo de moda/vestuário (Short Jeans) catalogado erroneamente no canal de crimes reais")
        elif ch_id == 4:
            # Canal 4 é Curiosidades & Ciência
            pass
        elif ch_id == 5:
            # Canal 5 é Produtividade e Foco
            pass

        if len(keyword_hits) == 0 and editorial_verdict == "APPROVED":
            editorial_issues.append("Baixa correlação lexical direta com as palavras-chave do nicho")

        # 7. Evidências do Aprendizado
        cur.execute("SELECT id, title, classification, confidence_score, evidence_video_ids FROM editorial_knowledge_library WHERE evidence_video_ids LIKE ?", (f'%"{vid_id}"%',))
        linked_knowledge = [dict(k) for k in cur.fetchall()]

        # 8. Verificação de Divergência de Duração
        dur_diff = abs(real_duration - (meta_duration or db_duration))
        dur_divergence_flag = dur_diff > 2.0  # Divergência superior a 2 segundos

        print(f"       Arquivo: {local_path.name if local_path else 'NÃO'} | {file_size:,} bytes")
        print(f"       SHA256: {full_sha256[:16] if full_sha256 else 'N/A'}... (Tam 64: {len(full_sha256) if full_sha256 else 0})")
        print(f"       Duração: Meta={meta_duration}s | Real={real_duration:.2f}s | Divergência={dur_diff:.2f}s")
        print(f"       Áudio: Track={has_audio_stream} | Stored={stored_lufs} LUFS | Measured={measured_lufs} LUFS | Diag: {audio_diagnostic}")
        print(f"       Vídeo: Decodificável={ffmpeg_dec['decodable']} | OpenCV={cv2_dec['cv2_readable']} | {cv2_dec.get('aspect_ratio')}")
        print(f"       Editorial: {editorial_verdict} (Canal {ch_id} - {ch_name})")
        if editorial_issues:
            print(f"       Alertas Editoriais: {'; '.join(editorial_issues)}")
        print(f"       Padrões Vinculados: {len(linked_knowledge)} registros")

        audit_results.append({
            "index": idx,
            "db_id": row["id"],
            "video_id": vid_id,
            "url": url,
            "title": title,
            "channel_id": ch_id,
            "channel_name": ch_name,
            "expected_niche": expected_niche,
            "file_exists": file_exists,
            "local_path": str(local_path.resolve()) if local_path and file_exists else None,
            "file_size_bytes": file_size,
            "sha256_full": full_sha256,
            "sha256_len": len(full_sha256) if full_sha256 else 0,
            "sha256_match_stored": sha256_match,
            "metadata_duration": meta_duration,
            "db_duration": db_duration,
            "real_duration": real_duration,
            "duration_divergence": round(dur_diff, 2),
            "is_short_duration_valid": 0 < real_duration <= 60.5,
            "has_video_stream": has_video_stream,
            "has_audio_stream": has_audio_stream,
            "video_codec": v_codec,
            "audio_codec": a_codec,
            "ffmpeg_decodable": ffmpeg_dec["decodable"],
            "cv2_readable": cv2_dec["cv2_readable"],
            "resolution": f"{cv2_dec.get('width')}x{cv2_dec.get('height')}",
            "aspect_ratio": cv2_dec.get("aspect_ratio"),
            "stored_lufs": stored_lufs,
            "measured_lufs": measured_lufs,
            "audio_diagnostic": audio_diagnostic,
            "editorial_verdict": editorial_verdict,
            "editorial_issues": editorial_issues,
            "linked_knowledge_count": len(linked_knowledge),
            "linked_knowledge": linked_knowledge,
            "current_db_state": db_state
        })

    conn.close()

    # Salva resultado da auditoria forense em JSON
    out_json = BASE_DIR / "docs" / "audits" / "phase15_1_forensic_evidence.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 90)
    print("RESUMO DA AUDITORIA FORENSE:")
    print("=" * 90)
    print(f"Total de Vídeos Auditados         : {len(audit_results)}")
    print(f"Arquivos Físicos Existentes       : {sum(1 for r in audit_results if r['file_exists'])} / 20")
    print(f"Hashes SHA256 com 64 caracteres   : {sum(1 for r in audit_results if r['sha256_len'] == 64)} / 20")
    print(f"Decodificáveis por FFmpeg e OpenCV: {sum(1 for r in audit_results if r['ffmpeg_decodable'] and r['cv2_readable'])} / 20")
    print(f"Duração Real <= 60.5s             : {sum(1 for r in audit_results if r['is_short_duration_valid'])} / 20")
    print(f"Com Faixa de Áudio Presente       : {sum(1 for r in audit_results if r['has_audio_stream'])} / 20")
    print(f"Áudio com -70.0 LUFS ou Silencioso: {sum(1 for r in audit_results if r['audio_diagnostic'] in ['SILENT_AUDIO_TRACK', 'NO_AUDIO_TRACK'])}")
    print(f"Aprovados Editorialmente          : {sum(1 for r in audit_results if r['editorial_verdict'] == 'APPROVED')} / 20")
    print(f"Rejeitados Editorialmente         : {sum(1 for r in audit_results if r['editorial_verdict'] != 'APPROVED')}")
    print("=" * 90)

if __name__ == "__main__":
    run_forensic_audit()
