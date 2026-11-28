"""
VANTIS Intelligent Autonomous Agent Base Architecture
Define o contrato fundamental, máquina de estados, telemetria SQLite e governança
para todos os agentes operacionais especializados da plataforma.
"""
import time
import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Type, Tuple, Union
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError

BASE_DIR = Path(__file__).resolve().parent.parent
from database.db import get_db_connection

logger = logging.getLogger("VantisAgent")


class AgentState(str, Enum):
    """Estados formais de execução de um agente VANTIS."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class AgentTaskContext(BaseModel):
    """Contexto de entrada fornecido a um agente durante a execução de uma tarefa."""
    task_id: str = Field(..., description="Identificador único da tarefa na plataforma")
    channel_id: Optional[int] = Field(default=1, description="ID do canal associado (para isolamento editorial)")
    niche: str = Field(default="geral", description="Nicho de atuação do conteúdo")
    target_id: Optional[str] = Field(default="", description="ID ou URL do vídeo/áudio ou referência")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parâmetros adicionais específicos da tarefa")
    human_approval_token: Optional[str] = Field(default=None, description="Token de aprovação humana para portas críticas")


class AgentExecutionResult(BaseModel):
    """Contrato de saída padronizado para qualquer agente operacional VANTIS."""
    agent_id: str = Field(..., description="ID único do agente executor")
    agent_name: str = Field(..., description="Nome do agente")
    department: str = Field(..., description="Departamento operacional")
    status: AgentState = Field(..., description="Estado final da execução")
    execution_time_ms: float = Field(default=0.0, description="Tempo total de execução em milissegundos")
    data: Dict[str, Any] = Field(default_factory=dict, description="Payload de dados resultantes")
    error_message: Optional[str] = Field(default=None, description="Mensagem de erro em caso de falha")
    success_criteria_met: bool = Field(default=True, description="Indica se todos os critérios de sucesso foram atingidos")
    flags: List[str] = Field(default_factory=list, description="Sinalizações ou advertências operacionais")


class VantisBaseAgent(ABC):
    """
    Classe base para todos os Agentes Operacionais Inteligentes VANTIS.
    Fornece:
    - Validação de entrada e saída por Pydantic
    - Máquina de estados (IDLE -> RUNNING -> SUCCESS / ERROR)
    - Persistência estruturada em SQLite (tabela agent_execution_logs)
    - Verificação declarativa de critérios de sucesso
    - Isolamento editorial estrito por canal
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        department: str,
        responsibility: str,
        input_schema: Type[BaseModel] = AgentTaskContext,
        output_schema: Optional[Type[BaseModel]] = None,
        db_path: Optional[str] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.department = department
        self.responsibility = responsibility
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.state = AgentState.IDLE
        self.db_path = Path(db_path) if db_path else BASE_DIR / "database" / "shorts_central.db"
        self.success_criteria: List[str] = []

    def set_success_criteria(self, criteria: List[str]):
        """Define os critérios de sucesso verificáveis pós-execução."""
        self.success_criteria = criteria

    def run(self, context: Union[AgentTaskContext, Dict[str, Any]]) -> AgentExecutionResult:
        """
        Executa o ciclo de vida completo do agente com validação, telemetria e auditoria.
        """
        t0 = time.time()
        self.state = AgentState.RUNNING

        # 1. Normalização e Validação do Contexto de Entrada
        if isinstance(context, dict):
            try:
                task_ctx = self.input_schema(**context)
            except ValidationError as ve:
                elapsed_ms = (time.time() - t0) * 1000
                self.state = AgentState.ERROR
                err_msg = f"Falha de validação de entrada no agente {self.agent_id}: {ve}"
                logger.error(err_msg)
                self._record_log(
                    task_id=context.get("task_id", "unknown"),
                    channel_id=context.get("channel_id"),
                    inputs=context,
                    outputs={},
                    elapsed_ms=elapsed_ms,
                    error=err_msg,
                    success_met=False
                )
                return AgentExecutionResult(
                    agent_id=self.agent_id,
                    agent_name=self.name,
                    department=self.department,
                    status=AgentState.ERROR,
                    execution_time_ms=elapsed_ms,
                    error_message=err_msg,
                    success_criteria_met=False
                )
        else:
            task_ctx = context

        task_id = getattr(task_ctx, "task_id", "unknown")
        channel_id = getattr(task_ctx, "channel_id", 1)

        # 2. Execução do Processamento Específico
        try:
            raw_output = self._process(task_ctx)
            
            # Validação do Contrato de Saída (se definido)
            if self.output_schema:
                try:
                    if isinstance(raw_output, dict):
                        validated = self.output_schema(**raw_output)
                        raw_output = validated.model_dump()
                except ValidationError as ve:
                    raise ValueError(f"Contrato de saída inválido para {self.agent_id}: {ve}")

            # 3. Verificação dos Critérios de Sucesso
            success_met, flags = self.verify_criteria(raw_output)
            elapsed_ms = (time.time() - t0) * 1000
            self.state = AgentState.SUCCESS if success_met else AgentState.ERROR

            # 4. Registro de Auditoria Operacional no SQLite
            self._record_log(
                task_id=task_id,
                channel_id=channel_id,
                inputs=task_ctx.model_dump() if hasattr(task_ctx, "model_dump") else dict(task_ctx),
                outputs=raw_output,
                elapsed_ms=elapsed_ms,
                error=None if success_met else "Critérios de sucesso não foram totalmente atendidos",
                success_met=success_met
            )

            return AgentExecutionResult(
                agent_id=self.agent_id,
                agent_name=self.name,
                department=self.department,
                status=self.state,
                execution_time_ms=elapsed_ms,
                data=raw_output,
                success_criteria_met=success_met,
                flags=flags
            )

        except Exception as e:
            elapsed_ms = (time.time() - t0) * 1000
            self.state = AgentState.ERROR
            err_msg = f"Erro operacional em {self.name} ({self.agent_id}): {str(e)}"
            logger.exception(err_msg)

            # Executa fallback se implementado
            fallback_data = self._handle_fallback(task_ctx, e)
            
            self._record_log(
                task_id=task_id,
                channel_id=channel_id,
                inputs=task_ctx.model_dump() if hasattr(task_ctx, "model_dump") else dict(task_ctx),
                outputs=fallback_data or {},
                elapsed_ms=elapsed_ms,
                error=err_msg,
                success_met=False
            )

            return AgentExecutionResult(
                agent_id=self.agent_id,
                agent_name=self.name,
                department=self.department,
                status=AgentState.ERROR,
                execution_time_ms=elapsed_ms,
                data=fallback_data or {},
                error_message=err_msg,
                success_criteria_met=False,
                flags=[f"FALLBACK_TRIGGERED: {type(e).__name__}"]
            )

    @abstractmethod
    def _process(self, context: AgentTaskContext) -> Dict[str, Any]:
        """Lógica central de processamento operacional a ser implementada por cada agente."""
        pass

    def verify_criteria(self, output_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Verifica os critérios de sucesso declarados sobre o output gerado.
        Pode ser sobrescrito para validações de alta precisão.
        """
        flags = []
        if not self.success_criteria:
            return True, flags

        all_met = True
        for criterion in self.success_criteria:
            if criterion not in output_data or output_data[criterion] is None:
                all_met = False
                flags.append(f"MISSING_CRITERION: {criterion}")
            elif isinstance(output_data[criterion], bool) and not output_data[criterion]:
                all_met = False
                flags.append(f"CRITERION_FAILED: {criterion}")

        return all_met, flags

    def _handle_fallback(self, context: AgentTaskContext, exception: Exception) -> Optional[Dict[str, Any]]:
        """Hook opcional para recuperação graciosa de falhas."""
        return None

    def _record_log(
        self,
        task_id: str,
        channel_id: Optional[int],
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        elapsed_ms: float,
        error: Optional[str],
        success_met: bool
    ):
        """Grava log de auditoria operacional na tabela agent_execution_logs."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO agent_execution_logs (
                        agent_id, agent_name, department, task_id, channel_id,
                        status, inputs_json, outputs_json, execution_time_ms,
                        error_message, success_criteria_met
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.agent_id,
                    self.name,
                    self.department,
                    task_id,
                    channel_id,
                    self.state.value,
                    json.dumps(inputs, ensure_ascii=False, default=str),
                    json.dumps(outputs, ensure_ascii=False, default=str),
                    round(elapsed_ms, 2),
                    error,
                    1 if success_met else 0
                ))
                conn.commit()
        except Exception as log_err:
            logger.warning(f"Não foi possível salvar log do agente {self.agent_id}: {log_err}")
