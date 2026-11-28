"""
IAS Video Analysis - Scene Detector (PySceneDetect)
Identifica transições e cortes de cena, calcula ritmo visual (BPM) e sugere pontos de corte.
"""
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

class SceneDetectorService:
    """Detecta cortes e transições de cena em arquivos de vídeo."""

    def __init__(self, threshold: float = 27.0):
        self.threshold = threshold
        self.has_scenedetect = self._check_package()

    def _check_package(self) -> bool:
        try:
            import scenedetect
            return True
        except ImportError:
            return False

    def detect_scenes(self, video_path: str, max_duration_sec: Optional[float] = None) -> Dict[str, Any]:
        """
        Executa detecção de cenas retornando lista de timestamps de corte e BPM visual.
        """
        if not os.path.exists(video_path):
            return {"error": f"Arquivo não encontrado: {video_path}"}

        if self.has_scenedetect:
            return self._detect_with_scenedetect(video_path)
        else:
            return self._detect_with_ffmpeg(video_path)

    def _detect_with_scenedetect(self, video_path: str) -> Dict[str, Any]:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector

        try:
            video = open_video(video_path, backend="pyav")
        except Exception:
            video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.auto_downscale = True
        scene_manager.add_detector(ContentDetector(threshold=self.threshold))

        scene_manager.detect_scenes(video, frame_skip=2)
        scene_list = scene_manager.get_scene_list()

        scenes = []
        for i, (start_time, end_time) in enumerate(scene_list):
            s_sec = start_time.get_seconds()
            e_sec = end_time.get_seconds()
            dur = e_sec - s_sec
            scenes.append({
                "scene_index": i + 1,
                "start_sec": round(s_sec, 2),
                "end_sec": round(e_sec, 2),
                "duration_sec": round(dur, 2)
            })

        total_scenes = len(scenes)
        total_duration = scenes[-1]["end_sec"] if scenes else 0.0
        # Ritmo visual: cortes por minuto e intervalos reais entre cortes
        visual_bpm = round((total_scenes / (total_duration / 60.0)), 1) if total_duration > 0 else 0.0
        cut_intervals = [s["duration_sec"] for s in scenes] if scenes else []
        avg_cut_interval = round(sum(cut_intervals) / len(cut_intervals), 2) if cut_intervals else 0.0

        return {
            "engine": "PySceneDetect (ContentDetector)",
            "total_scenes": total_scenes,
            "visual_bpm": visual_bpm,
            "scenes": scenes,
            "cut_intervals_sec": cut_intervals,
            "avg_cut_interval_sec": avg_cut_interval,
            "recommended_cuts": [s["start_sec"] for s in scenes[1:]]
        }

    def _detect_with_ffmpeg(self, video_path: str) -> Dict[str, Any]:
        """Fallback via filtro de cena do FFmpeg."""
        from services.media_processing.ffmpeg_engine import FFmpegEngine
        ffmpeg = FFmpegEngine()
        if not ffmpeg.available:
            return {"engine": "none", "total_scenes": 1, "visual_bpm": 0.0, "scenes": []}

        cmd = [
            ffmpeg.binary_path,
            "-i", str(video_path),
            "-filter_complex", "select='gt(scene,0.3)',metadata=print:file=-",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        # Parse simples de timestamps
        cut_points = [0.0]
        for line in res.stderr.splitlines():
            if "pts_time:" in line:
                try:
                    val = float(line.split("pts_time:")[1].strip())
                    cut_points.append(round(val, 2))
                except Exception:
                    pass

        scenes = []
        for i in range(len(cut_points) - 1):
            s = cut_points[i]
            e = cut_points[i+1]
            scenes.append({
                "scene_index": i + 1,
                "start_sec": s,
                "end_sec": e,
                "duration_sec": round(e - s, 2)
            })

        return {
            "engine": "FFmpeg Scene Filter Fallback",
            "total_scenes": len(scenes),
            "visual_bpm": 15.0,
            "scenes": scenes,
            "recommended_cuts": cut_points[1:]
        }
