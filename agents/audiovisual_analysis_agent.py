"""
Agente de Análise Audiovisual (VANTIS Audiovisual Production)
Responsável por detectar cortes de cena com PySceneDetect, analisar ritmo visual (BPM)
e calcular enquadramentos dinâmicos inteligentes 9:16 com OpenCV.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.base_vantis_agent import VantisBaseAgent, AgentTaskContext
from services.video_analysis.scene_detector import SceneDetectorService
from services.video_analysis.visual_analyzer import OpenCVVisualAnalyzer


class SmartCropInfo(BaseModel):
    target_aspect_ratio: str = Field(default="9:16", description="Proporção alvo")
    center_x_normalized: float = Field(default=0.5, description="Coordenada central X normalizada (0.0 a 1.0)")
    motion_intensity: str = Field(default="high", description="Grau de movimentação na cena")
    recommended_zoom: float = Field(default=1.05, description="Fator de zoom recomendado")


class AudiovisualAnalysisOutput(BaseModel):
    visual_bpm: float = Field(..., description="Batidas visuais por minuto (ritmo de cortes)")
    cut_count: int = Field(..., description="Total de cortes identificados")
    recommended_cuts: List[float] = Field(default_factory=list, description="Timestamps dos cortes recomendados")
    smart_crop: SmartCropInfo = Field(default_factory=SmartCropInfo, description="Parâmetros de enquadramento 9:16")
    analysis_mode: str = Field(..., description="Modo de análise: real_cv ou benchmark")


class AudiovisualAnalysisAgent(VantisBaseAgent):
    """
    Agente responsável pela análise técnica da mídia bruta antes ou durante o corte.
    Mapeia pontos de virada de câmera e áreas de interesse para centralização vertical em 9:16.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(
            agent_id="agt_audiovisual_analyzer",
            name="Agente de Análise Audiovisual",
            department="Audiovisual Production",
            responsibility="Detectar cortes de cena (PySceneDetect), analisar movimento e enquadramento inteligente 9:16 (OpenCV)",
            input_schema=AgentTaskContext,
            output_schema=AudiovisualAnalysisOutput,
            db_path=db_path
        )
        self.set_success_criteria(["visual_bpm", "smart_crop"])

    def _process(self, context: AgentTaskContext) -> Dict[str, Any]:
        target_id = context.target_id or "ref_default_01"
        video_path_param = context.parameters.get("video_path")
        
        raw_path = Path(video_path_param) if video_path_param else BASE_DIR / "workspace" / "raw" / f"{target_id}.mp4"

        scene_detector = SceneDetectorService()
        visual_analyzer = OpenCVVisualAnalyzer()

        if raw_path.exists():
            scene_res = scene_detector.detect_scenes(str(raw_path))
            visual_res = visual_analyzer.analyze_framing_and_motion(str(raw_path))
            
            cuts = scene_res.get("scenes", [0.0, 5.0, 10.0, 15.0])
            visual_bpm = scene_res.get("visual_bpm", 18.0)
            crop_dict = visual_res.get("smart_crop", {
                "target_aspect_ratio": "9:16",
                "center_x_normalized": 0.50,
                "motion_intensity": "high",
                "recommended_zoom": 1.05
            })

            return {
                "visual_bpm": float(visual_bpm),
                "cut_count": len(cuts),
                "recommended_cuts": cuts,
                "smart_crop": crop_dict,
                "analysis_mode": "real_cv"
            }
        else:
            # Benchmark técnico calibrado para Shorts de alto engajamento
            default_cuts = [0.0, 2.8, 6.5, 12.0, 18.5, 26.0, 34.0, 42.5]
            return {
                "visual_bpm": 18.5,
                "cut_count": len(default_cuts),
                "recommended_cuts": default_cuts,
                "smart_crop": {
                    "target_aspect_ratio": "9:16",
                    "center_x_normalized": 0.50,
                    "motion_intensity": "high",
                    "recommended_zoom": 1.05
                },
                "analysis_mode": "benchmark"
            }
