"""
VANTIS — Motor de Roteiros Completos & Validador Editorial Automático (Fase 24)
Elimina roteiros de template superficial, reforça as 5 identidades editoriais
isoladas e valida completude, repetições, fontes, duração e licenciamento antes da aprovação humana.
"""
import re
from typing import Any, Dict, List, Optional

from services.production.asset_intelligence import VERIFIED_LICENSE_STATUSES

VALID_CLASSIFICATIONS = (
    "EDITORIALLY_READY",
    "SCRIPT_NEEDS_REVISION",
    "ASSETS_INCOMPLETE",
    "REFERENCE_INSUFFICIENT",
    "BLOCKED",
)

# Fatos editoriais verificáveis para os 10 temas do piloto (sem invenção ou sensacionalismo)
CURATED_TOPIC_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "A regra esquecida do impedimento que decidiu uma semifinal": {
        "hook": "Quase todo torcedor acha que o impedimento depende só do último zagueiro, mas a regra oficial exige dois adversários à frente da linha da bola!",
        "context": "Na Regra 11 da IFAB, a posição de impedimento compara o atacante ao penúltimo adversário — normalmente o goleiro conta como o último, o que mascara a regra real.",
        "development": "Quando o goleiro sai da área para disputar um cruzamento ou escanteio e fica atrás do atacante, apenas um zagueiro sobre a linha do gol não evita o impedimento.",
        "climax": "Em lances de bola parada nos minutos finais de mata-mata, gols aparentemente legais já foram anulados exatamente porque o goleiro havia avançado além da linha da bola.",
        "closing": "Antes de reclamar da bandeira ou do VAR no próximo escanteio, conte sempre onde está o goleiro.",
        "cta": "Você já viu um gol anulado assim? Comenta qual jogo te marcou.",
        "sources": ["IFAB Laws of the Game — Law 11 (Offside)"],
        "fact_note": "Baseado na redação oficial da Regra 11 da IFAB; sem citar partida específica não verificada.",
    },
    "Por que goleiros mudaram o posicionamento nos pênaltis modernos": {
        "hook": "Por décadas o goleiro ficava estático no centro do gol antes do apito; hoje muitos saltam ou ajustam a base centímetros antes da batida — por quê?",
        "context": "Desde a atualização da Regra 14 da IFAB e a fiscalização rigorosa do VAR, pelo menos um pé precisa tocar ou estar alinhado à linha do gol no momento do chute.",
        "development": "Sem poder dar dois passos à frente para fechar o ângulo, os preparadores passaram a treinar leitura de quadril do batedor, pé de apoio e micro-passos laterais de impulso.",
        "climax": "O resultado é uma troca clara: menos adiantamentos punidos pelo VAR e mais decisões baseadas em tempo de reação e leitura biomecânica.",
        "closing": "A regra limitou o avanço físico, mas aumentou o peso da análise de dados nos pênaltis.",
        "cta": "Qual goleiro atual melhor lê pênaltis na sua opinião?",
        "sources": ["IFAB Laws of the Game — Law 14 (The Penalty Kick)"],
        "fact_note": "Baseado na Regra 14 da IFAB sobre posicionamento do goleiro na linha.",
    },
    "O detalhe cronológico que revelou a contradição de um álibi real": {
        "hook": "Em investigações criminais reais, um álibi raramente cai por uma grande mentira — ele costuma ruir por uma diferença de poucos minutos entre dois registros independentes.",
        "context": "Quando peritos cruzam horários de câmeras urbanas, registros de antenas de telefonia e comprovantes eletrônicos, cada evento deixa uma marca temporal objetiva.",
        "development": "Se o relato afirma deslocamento contínuo em horário fixo, basta um registro de passagem ou transação incompatível com a distância física para abrir contradição verificável.",
        "climax": "É importante separar fato de especulação: a inconsistência de horário não prova culpa isoladamente, mas invalida a versão inicial e redireciona a perícia técnica.",
        "closing": "Na investigação documentada, a linha do tempo comparada vale mais do que qualquer suposição dramática.",
        "cta": "Você prefere casos explicados passo a passo com foco na perícia? Conta nos comentários.",
        "sources": ["Princípios de cronologia forense e cadeia de custódia digital"],
        "fact_note": "Análise metodológica de álibis sem inventar nomes de vítimas ou processos reais não anexados.",
    },
    "Como a perícia de vestígios resolveu um caso arquivado há décadas": {
        "hook": "Vestígios preservados em cadeia de custódia por vinte ou trinta anos podem responder hoje perguntas que a tecnologia da época não conseguia ler.",
        "context": "Casos arquivados antigos frequentemente dependiam apenas de análise sanguínea básica ou impressões parciais, insuficientes para individualização.",
        "development": "Com o avanço de técnicas modernas de extração de DNA em amostras degradadas e comparação automatizada de padrões, materiais guardados corretamente voltaram a gerar pistas objetivas.",
        "climax": "A virada não vem de palpite: depende integralmente da integridade da coleta original — sem cadeia de custódia íntegra, o exame perde valor probatório.",
        "closing": "Preservar a prova sem contaminação no dia um é o que permite justiça décadas depois.",
        "cta": "Salva este resumo e comenta se quer mais explicações sobre perícia real.",
        "sources": ["Manual de Cadeia de Custódia e Genética Forense"],
        "fact_note": "Explicação factual do papel da cadeia de custódia em casos arquivados, sem casos fictícios.",
    },
    "Quando a reunião online de segunda-feira dura mais que o projeto": {
        "hook": "Segunda-feira, nove da manhã: alguém diz 'vai ser só um alinhamento rápido de dez minutos' — e cinquenta minutos depois ninguém ainda abriu a planilha.",
        "context": "Todo mundo entra na chamada com câmera desligada e cara de quem só queria resolver um item simples antes do café esfriar.",
        "development": "Aos quinze minutos já tem três telas compartilhadas ao mesmo tempo. Aos trinta, alguém pergunta 'peraí, qual era o objetivo mesmo?' e volta tudo para a estaca zero.",
        "climax": "No minuto quarenta e cinco vem a frase clássica: 'vamos marcar outra call amanhã para fechar o que decidimos hoje' — ou seja, a tarefa virou só o convite da próxima reunião.",
        "closing": "Se a reunião durou mais que o trabalho em si, o único entregável da manhã foi cansaço em alta definição.",
        "cta": "Marca aqui quem sempre diz 'é coisa rápida' na segunda-feira.",
        "sources": ["Observação de humor cotidiano corporativo (roteiro original)"],
        "fact_note": "Conteúdo humorístico ficcional cotidiano, sem afirmações factuais externas.",
    },
    "A diferença entre o que você planejou no domingo e a realidade da terça": {
        "hook": "No domingo à noite você escreve uma lista digna de atleta olímpico; na terça às dez da manhã você já está negociando com você mesmo só para responder dois e-mails.",
        "context": "No domingo o seu eu do futuro tem energia infinita, zero preguiça e acorda às seis da manhã sorrindo.",
        "development": "Segunda começa bem até o primeiro imprevisto. Na terça, você abre a agenda, olha seis tarefas urgentes e decide que organizar a mesa já conta como produtividade extrema.",
        "climax": "A grande virada da terça-feira é perceber que o planejamento do domingo não falhou por falta de método — ele só esqueceu de avisar que a semana tinha trânsito e sono.",
        "closing": "Planejar no domingo é fácil; difícil é sobreviver à terça sem pedir férias da própria agenda.",
        "cta": "Qual item da sua lista de domingo sobrevive até terça?",
        "sources": ["Observação de humor cotidiano (roteiro original)"],
        "fact_note": "Conteúdo humorístico ficcional cotidiano.",
    },
    "Por que o céu noturno é escuro mesmo com bilhões de estrelas": {
        "hook": "Se o universo tem bilhões de estrelas brilhando em todas as direções, por que o céu da noite não é completamente claro como o dia?",
        "context": "Essa pergunta ficou conhecida como Paradoxo de Olbers: em um universo infinito, eterno e estático, qualquer linha de visão deveria terminar na superfície de uma estrela.",
        "development": "A resposta junta duas evidências observacionais: o universo tem uma idade finita de cerca de 13,8 bilhões de anos, então a luz de regiões distantes demais ainda não chegou até nós; além disso, a expansão cósmica estica a luz antiga para o infravermelho.",
        "climax": "Portanto, a escuridão noturna não é vazio sem sentido — ela é uma pista direta de que o universo teve um começo e está em expansão.",
        "closing": "Cada noite escura que você observa é uma evidência física da história cósmica.",
        "cta": "Salva essa curiosidade e comenta qual outro paradoxo você quer ver explicado aqui.",
        "sources": ["NASA / ESA — Cosmologia observacional e Paradoxo de Olbers"],
        "fact_note": "Explicação científica consolidada sobre idade finita do universo e desvio para o vermelho cosmológico.",
    },
    "Como o cérebro preenche pontos cegos sem você perceber": {
        "hook": "Você tem um ponto cego real em cada olho neste exato segundo — e mesmo assim não enxerga nenhum buraco preto na sua frente.",
        "context": "Onde o nervo óptico deixa a retina não existem fotorreceptores; por isso, nenhuma luz captada exatamente ali vira sinal visual direto.",
        "development": "Para evitar falhas na percepção contínua, o córtex visual usa o outro olho e as texturas vizinhas para interpolar cor, linha e padrão ao redor do ponto cego.",
        "climax": "Ou seja, parte do que você chama de 'ver com os próprios olhos' é na verdade uma reconstrução estatística feita em tempo real pelo cérebro.",
        "closing": "Enxergar não é apenas gravar uma câmera — é interpretar o mundo continuamente.",
        "cta": "Já fez o teste simples do ponto cego com papel? Comenta se quiser que eu mostre.",
        "sources": ["Neurociência visual — anatomia do disco óptico e preenchimento perceptual"],
        "fact_note": "Fenômeno anatômico e perceptual amplamente documentado em neurociência.",
    },
    "A armadilha dos micro-objetivos que destrói seu bloco de foco": {
        "hook": "Dividir demais uma tarefa pode parecer organização, mas transformar um trabalho de trinta minutos em quinze micro-tarefas destrói sua concentração.",
        "context": "Cada vez que você para para riscar um item minúsculo e escolher o próximo, o cérebro paga um custo de troca de contexto.",
        "development": "Em vez de criar vinte etapas microscópicas, defina apenas um resultado concreto por bloco de foco e deixe o checklist secundário para depois.",
        "climax": "A mudança prática é imediata: menos decisões intermediárias durante o bloco significam mais tempo contínuo em execução profunda.",
        "closing": "Organize antes de começar; durante o bloco, execute uma única entrega clara.",
        "cta": "Qual tarefa hoje você pode simplificar em um único bloco de entrega?",
        "sources": ["Princípios práticos de gestão de atenção e redução de custo de troca de contexto"],
        "fact_note": "Estratégia prática de produtividade sem promessas irreais.",
    },
    "Como usar blocos de 25 minutos sem cair em fadiga decisória": {
        "hook": "O bloco de 25 minutos falha quando você gasta os primeiros cinco minutos decidindo o que fazer e os últimos cinco olhando para o relógio.",
        "context": "A técnica Pomodoro funciona como temporizador, mas não resolve sozinha a indecisão de qual tarefa merece prioridade.",
        "development": "O ajuste prático é preparar a primeira ação física na noite anterior ou antes de ligar o cronômetro: arquivo aberto, título pronto e meta única definida.",
        "climax": "Quando o timer começa com zero atrito inicial, os 25 minutos viram ritmo de execução em vez de negociação mental.",
        "closing": "Defina a próxima ação visível antes de apertar o play.",
        "cta": "Testa isso no seu próximo bloco hoje e conta como foi.",
        "sources": ["Técnica Pomodoro combinada com preparação prévia de tarefa única"],
        "fact_note": "Recomendação prática e acionável de rotina.",
    },
}


def clean_accidental_repetitions(text: str) -> str:
    """Remove repetições acidentais consecutivas de palavras (ex.: 'quando Quando')."""
    if not text:
        return ""
    cleaned = re.sub(r"\b([A-Za-zÀ-ú0-9]+)\s+\1\b", r"\1", text, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def build_complete_script(
    channel_id: int,
    theme: str,
    target_duration_sec: float,
    channel_identity: Dict[str, Any],
    mem_ctx: Dict[str, Any],
    ref_info: Dict[str, Any],
) -> Dict[str, Any]:
    """Constrói roteiro completo adaptado à identidade do canal, sem campos None ou templates crus."""
    theme = clean_accidental_repetitions(theme)
    curated = CURATED_TOPIC_KNOWLEDGE.get(theme)

    limitations: List[str] = []
    if curated:
        hook = clean_accidental_repetitions(curated["hook"])
        context = clean_accidental_repetitions(curated["context"])
        development = clean_accidental_repetitions(curated["development"])
        climax = clean_accidental_repetitions(curated["climax"])
        closing = clean_accidental_repetitions(curated["closing"])
        cta = clean_accidental_repetitions(curated["cta"])
        sources = list(curated["sources"])
        fact_note = curated["fact_note"]
    else:
        # Não inventa fatos externos quando tema livre não possui base factual anexada
        if channel_id in (1, 2, 4):
            limitations.append(
                f"Tema '{theme}' sem fonte factual específica anexada; recomenda-se revisão humana de fontes antes de gravar."
            )
        if channel_id == 1:
            hook = f"Em {theme}, o detalhe decisivo acontece antes mesmo da jogada principal chamar atenção na transmissão."
            context = f"Para entender {theme}, é preciso olhar o posicionamento e o contexto tático que antecedem o lance."
            development = "Quando a marcação ajusta a linha um segundo tarde demais, o espaço se abre e muda o controle da partida."
            climax = "A virada tática mostra como uma escolha simples altera toda a leitura do jogo."
            closing = "No futebol de alto nível, detalhe de posicionamento decide o placar."
            cta = "Qual lance recente lembra essa situação? Comenta abaixo."
        elif channel_id == 2:
            hook = f"No estudo sobre {theme}, um detalhe documental discreto muda a interpretação inicial do caso."
            context = "Separando estritamente fatos registrados de hipóteses não confirmadas, a cronologia aponta uma lacuna objetiva."
            development = "Ao comparar registros independentes de tempo e local, percebe-se onde a narrativa inicial não se sustenta."
            climax = "Sem especulação gratuita, a evidência técnica mostra por que a revisão documental é decisiva."
            closing = "Investigar com rigor exige distinguir o que está provado do que ainda é hipótese."
            cta = "Comenta se você acompanha análises focadas em perícia e documentos."
        elif channel_id == 3:
            hook = f"Sabe quando {theme} começa parecendo uma ideia genial e em dez segundos vira motivo de riso?"
            context = "Na teoria tudo parecia simples, organizado e sem chance de dar errado."
            development = "Bastou colocar o plano em prática para a expectativa bater de frente com a realidade cotidiana."
            climax = "E no fim você descobre que o maior imprevisto era exatamente o plano original."
            closing = "Se não deu para resolver na hora, pelo menos rendeu uma boa história."
            cta = "Já passou por algo parecido? Conta nos comentários."
        elif channel_id == 4:
            hook = f"Você já se perguntou qual mecanismo real explica {theme} sem mistério exagerado?"
            context = "À primeira vista o fenômeno parece contraintuitivo, mas segue princípios físicos e observacionais claros."
            development = "Quando analisamos escala, tempo e evidências diretas, cada peça do comportamento se conecta de forma lógica."
            climax = "O ponto mais fascinante é que a explicação simples continua fiel aos dados medidos."
            closing = "Entender o porquê muda a forma como observamos o cotidiano."
            cta = "Salva este vídeo e sugere o próximo tema científico nos comentários."
        else:
            hook = f"Em {theme}, o gargalo raramente é falta de vontade — quase sempre é atrito logo no primeiro minuto."
            context = "Quando você começa sem definir uma única entrega concreta, a atenção se fragmenta rápido."
            development = "Separe o próximo bloco para uma ação visível única, com início e fim claros, antes de abrir notificações."
            climax = "Menos decisões paralelas durante a execução geram mais avanço real em menos tempo."
            closing = "Clareza antes de começar vale mais que listas intermináveis."
            cta = "Qual ação única você vai priorizar hoje? Escreve abaixo."

        sources = (
            [f"Referência estrutural: {ref_info['source_id']}"]
            if ref_info.get("status") == "REAL_REFERENCE_VERIFIED"
            else []
        )
        fact_note = (
            "Roteiro estruturado sem fatos externos inventados; fontes adicionais pendentes de confirmação humana."
            if limitations
            else "Roteiro estruturado conforme identidade isolada do canal."
        )

    full_narration = clean_accidental_repetitions(f"{hook} {context} {development} {climax} {closing} {cta}")
    word_count = len(full_narration.split())
    estimated_wpm = 140.0 if channel_id in (1, 3, 4) else 128.0
    estimated_spoken_sec = round((word_count / estimated_wpm) * 60.0, 1)

    return {
        "hook": hook,
        "context": context,
        "development": development,
        "climax": climax,
        "closing": closing,
        "cta": cta,
        "full_narration": full_narration,
        "word_count": word_count,
        "estimated_spoken_sec": estimated_spoken_sec,
        "sources": sources,
        "fact_vs_speculation_note": fact_note,
        "limitations": limitations,
        "narrative_progression": channel_identity["narrative_structure"],
        "retention_moments": [
            {"at_sec": round(target_duration_sec * 0.1, 1), "technique": channel_identity["hook_style"]},
            {"at_sec": round(target_duration_sec * 0.5, 1), "technique": "Virada / clímax com prova ou quebra de expectativa"},
            {"at_sec": round(target_duration_sec * 0.85, 1), "technique": "Fechamento coerente + CTA contextualizado"},
        ],
        "originality_note": "Roteiro original específico do canal, sem cópia literal de terceiros e sem invenção factual.",
    }


class EditorialValidator:
    """Validador editorial automático antes da aprovação humana."""

    PLACEHOLDER_PATTERNS = (
        (r"\{theme\}", re.IGNORECASE),
        (r"\bTODO\b", 0),
        (r"\bTBD\b", 0),
        (r"\blorem ipsum\b", re.IGNORECASE),
        (r"\bplaceholder\b", re.IGNORECASE),
    )

    def validate_package(self, pkg_row: Dict[str, Any]) -> Dict[str, Any]:
        content = pkg_row.get("package") or {}
        script = content.get("script") or {}
        av = content.get("audiovisual_plan") or {}
        audio = content.get("audio_plan") or {}
        scenes = av.get("scenes") or []
        channel_id = int(pkg_row.get("channel_id") or 0)
        target_dur = float(pkg_row.get("target_duration_sec") or 35.0)

        failures: List[str] = []
        warnings: List[str] = []
        checks: Dict[str, bool] = {}

        # 1. Texto completo e ausência de campos None
        required_fields = ("hook", "context", "development", "climax", "closing", "cta")
        missing_fields = [f for f in required_fields if not str(script.get(f) or "").strip()]
        narration = str(audio.get("narration_text") or script.get("full_narration") or "").strip()
        checks["complete_script_no_none"] = len(missing_fields) == 0 and len(narration) >= 40
        if not checks["complete_script_no_none"]:
            failures.append(f"Roteiro incompleto ou campos vazios/None: {missing_fields or ['narration_text']}.")

        # 2. Ausência de placeholders
        combined_text = " ".join(str(script.get(f) or "") for f in required_fields) + " " + narration
        has_placeholder = any(re.search(pat, combined_text, flags) for pat, flags in self.PLACEHOLDER_PATTERNS)
        checks["no_placeholders"] = not has_placeholder
        if has_placeholder:
            failures.append("Texto contém placeholders não resolvidos.")

        # 3. Ausência de repetições acidentais consecutivas
        rep_match = re.search(r"\b([A-Za-zÀ-ú0-9]+)\s+\1\b", combined_text, re.IGNORECASE)
        checks["no_accidental_repetitions"] = rep_match is None
        if rep_match:
            failures.append(f"Repetição acidental detectada: '{rep_match.group(0)}'.")

        # 4. Coerência entre roteiro e cenas
        checks["script_scene_coherence"] = len(scenes) >= 4 and all(
            bool(str(s.get("visual_description") or "").strip()) for s in scenes
        )
        if not checks["script_scene_coherence"]:
            failures.append("Plano audiovisual sem cenas suficientes ou sem descrição visual.")

        # 5. Duração estimada compatível
        scene_sum = sum(float(s.get("estimated_duration_sec") or 0.0) for s in scenes)
        checks["duration_compatible"] = 10.0 <= scene_sum <= 65.0 and abs(scene_sum - target_dur) <= 10.0
        if not checks["duration_compatible"]:
            failures.append(f"Duração das cenas ({scene_sum:.1f}s) incompatível com alvo ({target_dur:.1f}s).")

        # 6. Fontes registradas quando necessárias (Canais 1, 2, 4)
        sources = script.get("sources") or []
        requires_sources = channel_id in (1, 2, 4)
        checks["sources_verified_when_required"] = (not requires_sources) or len(sources) > 0
        if not checks["sources_verified_when_required"]:
            failures.append(f"Canal {channel_id} exige fontes ou referência registrada no roteiro.")

        # 7. Assets atribuídos ou pendências identificadas
        needed_scenes = [s.get("scene_index") for s in scenes if s.get("media_asset_status") != "ASSET_READY" or not s.get("asset_path")]
        checks["all_assets_assigned"] = len(needed_scenes) == 0 and len(scenes) > 0
        if not checks["all_assets_assigned"]:
            warnings.append(f"{len(needed_scenes)} cena(s) ainda aguardando mídia verificável (ASSET_NEEDED): {needed_scenes}.")

        # 8. Direitos de utilização verificados
        unverified_licenses = [
            s.get("scene_index") for s in scenes
            if s.get("asset_path") and s.get("license_status") not in VERIFIED_LICENSE_STATUSES
        ]
        checks["usage_rights_verified"] = len(unverified_licenses) == 0
        if unverified_licenses:
            failures.append(f"Cenas com mídia sem licença verificada (LICENSE_UNVERIFIED/RESTRICTED): {unverified_licenses}.")

        # 9. Adequação ao canal e isolamento de memória
        mems = content.get("applied_memories") or []
        cross_channel = [m for m in mems if m.get("origin_channel_id") not in (None, channel_id)]
        checks["channel_isolation_and_fit"] = len(cross_channel) == 0
        if cross_channel:
            failures.append("Contaminação cruzada de memória entre canais detectada.")

        # Classificação explícita
        script_ok = (
            checks["complete_script_no_none"]
            and checks["no_placeholders"]
            and checks["no_accidental_repetitions"]
            and checks["script_scene_coherence"]
            and checks["duration_compatible"]
            and checks["channel_isolation_and_fit"]
        )
        if not checks["usage_rights_verified"] or not checks["channel_isolation_and_fit"]:
            classification = "BLOCKED"
        elif not checks["sources_verified_when_required"]:
            classification = "REFERENCE_INSUFFICIENT"
        elif not script_ok:
            classification = "SCRIPT_NEEDS_REVISION"
        elif not checks["all_assets_assigned"]:
            classification = "ASSETS_INCOMPLETE"
        else:
            classification = "EDITORIALLY_READY"

        total_checks = len(checks)
        passed_checks = sum(1 for v in checks.values() if v)
        score = round((passed_checks / total_checks) * 100.0, 1)

        return {
            "package_id": pkg_row.get("id"),
            "version": pkg_row.get("version", 1),
            "classification": classification,
            "quality_score": score,
            "passed": classification == "EDITORIALLY_READY",
            "checks": checks,
            "failures": failures,
            "warnings": warnings,
            "score_note": "Pontuação explicável baseada em critérios técnicos/editoriais; não substitui revisão humana.",
        }
