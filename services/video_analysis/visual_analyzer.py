"""
IAS Video Analysis - Visual Analyzer (OpenCV)
Análise visual de movimento, composição e cálculo de Smart Crop 9:16 para centralização de personagens.
"""
import os
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

class OpenCVVisualAnalyzer:
    """Análise visual assistida por OpenCV para composição vertical de Shorts."""

    def __init__(self):
        self.available = hasattr(cv2, "__version__")

    def analyze_framing_and_motion(self, video_path: str, max_frames: int = 60) -> Dict[str, Any]:
        """
        Analisa intensidade de movimento e calcula a melhor posição de corte horizontal (Smart Crop).
        """
        if not os.path.exists(video_path):
            return {"error": f"Arquivo não encontrado: {video_path}"}

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": "Não foi possível abrir o arquivo de vídeo via OpenCV"}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        step = max(1, total_frames // max_frames)
        prev_gray = None
        motion_scores = []
        x_centers = []
        representative_frames = []
        framing_changes_detected = 0
        text_edge_scores = []
        prev_cx = None

        frame_idx = 0
        while cap.isOpened() and len(motion_scores) < max_frames:
            if frame_idx % step != 0:
                if not cap.grab():
                    break
                frame_idx += 1
                continue
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Reduz para velocidade
            small = cv2.resize(gray, (320, 180))
            ts_sec = round(frame_idx / fps, 2) if fps > 0 else 0.0
            avg_brightness = round(float(np.mean(small)), 1)

            # Amostra até 5 frames representativos espaçados ao longo do vídeo
            if len(representative_frames) < 5 and (len(motion_scores) % max(1, max_frames // 5) == 0):
                representative_frames.append({
                    "frame_idx": frame_idx,
                    "timestamp_sec": ts_sec,
                    "avg_brightness": avg_brightness
                })

            # Densidade de bordas nas faixas de texto/legenda (topo e rodapé 35%)
            h_s, w_s = small.shape
            sobel_x = cv2.Sobel(small, cv2.CV_64F, 1, 0, ksize=3)
            abs_sx = np.abs(sobel_x)
            top_band = abs_sx[:int(h_s * 0.30), :]
            bot_band = abs_sx[int(h_s * 0.65):, :]
            band_edge_density = float(max(np.mean(top_band > 60), np.mean(bot_band > 60)))
            text_edge_scores.append(band_edge_density)

            # 1. Detecção de Movimento
            if prev_gray is not None:
                diff = cv2.absdiff(small, prev_gray)
                motion_val = float(np.mean(diff))
                motion_scores.append(motion_val)

                # 2. Localização do Centro de Atenção (Centro de Massa do movimento/saliência)
                thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
                moments = cv2.moments(thresh)
                if moments["m00"] > 0:
                    cx = (moments["m10"] / moments["m00"]) / 320.0 # 0.0 a 1.0 relativo
                    x_centers.append(cx)
                else:
                    cx = 0.5
                    x_centers.append(0.5)

                if (prev_cx is not None and abs(cx - prev_cx) > 0.12) or motion_val > 18.0:
                    framing_changes_detected += 1
                prev_cx = cx
            else:
                motion_scores.append(0.0)
                x_centers.append(0.5)
                prev_cx = 0.5

            prev_gray = small

            frame_idx += 1

        cap.release()

        opencv_frames_read_ok = len(motion_scores) > 0
        avg_motion = float(np.mean(motion_scores)) if motion_scores else 0.0
        avg_text_edge = float(np.mean(text_edge_scores)) if text_edge_scores else 0.0
        # Presença detectável de texto na tela via densidade de bordas de alto contraste em faixas de legenda
        text_on_screen_detected = avg_text_edge >= 0.045
        # Média ponderada do centro horizontal do sujeito (0.5 = centro exato)
        median_x = float(np.median(x_centers)) if x_centers else 0.5
        # Mantém entre 0.2 e 0.8 para evitar cortar bordas pretas
        clamped_x = max(0.25, min(0.75, median_x))

        # Enquadramento estimado
        shot_type = "Medium Shot"
        if avg_motion > 15.0:
            shot_type = "High-Energy Action / Dynamic"
        elif avg_motion < 3.0:
            shot_type = "Static Talk / Close-Up"

        # Constrói expressão de crop para FFmpeg:
        # Se clamped_x = 0.5 -> '(iw-ow)/2'
        # Se clamped_x > 0.5 (sujeito à direita) -> desloca offset x para direita
        crop_expr = f"(iw-ow)*{clamped_x:.3f}"

        return {
            "engine": f"OpenCV {cv2.__version__}",
            "opencv_frames_read_ok": opencv_frames_read_ok,
            "sampled_frames_count": len(motion_scores),
            "original_resolution": f"{orig_width}x{orig_height}",
            "aspect_ratio": round(orig_width / max(1, orig_height), 2),
            "average_motion_score": round(avg_motion, 2),
            "framing_changes_detected": framing_changes_detected,
            "representative_frames": representative_frames,
            "text_on_screen_detected": text_on_screen_detected,
            "text_edge_density_avg": round(avg_text_edge, 4),
            "text_detection_method": "opencv_sobel_band_density",
            "estimated_shot_type": shot_type,
            "recommended_crop_center_x": round(clamped_x, 3),
            "ffmpeg_crop_offset_x": crop_expr,
            "smart_crop_applied": abs(clamped_x - 0.5) > 0.05
        }

    def verify_resolution(self, video_path: str) -> Dict[str, Any]:
        """Verifica resolução e proporção vertical 9:16 do vídeo físico via OpenCV."""
        if not os.path.exists(video_path):
            return {"error": f"Arquivo não encontrado: {video_path}"}
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": "Não foi possível abrir o arquivo via OpenCV"}
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        is_vertical = h > w and w > 0
        ratio = f"{w}:{h}" if w and h else "unknown"
        return {
            "width": w,
            "height": h,
            "is_vertical_9_16": is_vertical,
            "aspect_ratio": ratio
        }
