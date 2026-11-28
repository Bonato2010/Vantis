# IAS — Contratos de Interface e DTOs entre Departamentos

**Versão:** 3.0  
**Status:** Especificação Técnica Formal  
**Projeto:** IAS (Intelligence & Automation System)  

Este documento define os contratos de dados estritos (schemas Pydantic / DTOs) para a comunicação entre todos os departamentos e serviços do IAS.

---

## 1. Contrato de Oportunidade de Mercado (`OpportunityDTO`)

Utilizado pelo **Departamento de Inteligência de Mercado** e submetido ao **Portal de Aprovação 1**:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class OpportunityDTO(BaseModel):
    opportunity_id: str
    source_platform: str = "youtube_shorts"
    source_url: str
    niche: str
    subniche: Optional[str] = None
    country: str = "BR"
    language: str = "pt-BR"
    title_concept: str
    context_description: str
    popularity_evidence: Dict[str, Any] = Field(
        description="Dados verificados: views, likes, comment_count ou sinais de engajamento"
    )
    competition_level: str = Field(..., pattern="^(baixo|medio|alto)$")
    monetization_potential: str = Field(..., pattern="^(baixo|medio|alto)$")
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    recommended_channel_id: int
    technical_justification: str
    status: str = Field(default="pending_review", pattern="^(pending_review|approved|rejected|needs_more_research)$")
    created_at: str
```

---

## 2. Contrato de Roteiro Original (`ScriptDTO`)

Utilizado pelo **Departamento de Roteirização** e enviado para Produção Audiovisual:

```python
class ScriptSegmentDTO(BaseModel):
    segment_index: int
    phase: str = Field(..., pattern="^(hook_3s|premissa|conflito|climax|cta)$")
    start_sec_estimated: float
    end_sec_estimated: float
    narration_text: str
    visual_cue: str
    audio_cue: Optional[str] = None

class ScriptDTO(BaseModel):
    script_id: Optional[int] = None
    channel_id: int
    opportunity_id: Optional[str] = None
    title: str
    archetype: str
    hook_3s: str
    full_script: str
    segments: List[ScriptSegmentDTO]
    recommended_duration: float = Field(..., ge=15.0, le=60.0)
    editing_style: str
    status: str = Field(default="draft", pattern="^(draft|approved|rejected)$")
    human_approved: bool = False
    approval_notes: Optional[str] = None
```

---

## 3. Contrato de Renderização Audiovisual (`RenderJobDTO`)

Utilizado pelo **Departamento Audiovisual / Edição** com o `FFmpegEngine`:

```python
class RenderJobDTO(BaseModel):
    job_id: str
    channel_id: int
    script_id: int
    raw_video_path: Optional[str] = None
    raw_audio_path: Optional[str] = None
    subtitles_ass_path: Optional[str] = None
    output_profile: str = "1080x1920_9x16_60fps"
    smart_crop_center_x: float = 0.5
    loudness_target_lufs: float = -14.0
    output_file_path: str
    gdrive_destination_folder_id: Optional[str] = None
```

---

## 4. Contrato de Aprovação e Governança (`ApprovalDecisionDTO`)

Registrado na trilha de auditoria para os Portais 1 e 2:

```python
class ApprovalDecisionDTO(BaseModel):
    approval_id: Optional[int] = None
    portal_type: str = Field(..., pattern="^(portal_1_oportunidade|portal_2_publicacao)$")
    target_id: str
    channel_id: int
    decision: str = Field(..., pattern="^(approved|rejected|paused)$")
    decided_by: str = "human_operator"
    justification_notes: Optional[str] = None
    artifact_hash: Optional[str] = None
    timestamp_utc: str
```

---

## 5. Contrato de Publicação no YouTube (`PublicationManifestDTO`)

Utilizado pelo **Departamento de Distribuição** para preparar a publicação autorizada:

```python
class PublicationManifestDTO(BaseModel):
    publication_id: Optional[int] = None
    channel_id: int
    rendered_file_path: str
    gdrive_file_id: Optional[str] = None
    youtube_channel_id: str
    title: str = Field(..., max_length=100)
    description: str
    tags: List[str]
    privacy_status: str = Field(default="private", pattern="^(private|unlisted|public)$")
    scheduled_time_utc: Optional[str] = None
    human_approval_token: str
    published_status: str = Field(default="scheduled", pattern="^(scheduled|uploading|published|failed)$")
```
