#!/usr/bin/env python3
"""
PsiqMentor V3 - Backend API (versão para deploy no Render)
Agente simulador de paciente com Transtorno de Ansiedade para treinamento médico.
Mestrado em Ensino em Saúde - CESUPA

Para rodar localmente:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="sua-chave-aqui"
    python api_server.py
"""

import json
import os
import random
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ─── Load DSM-5 Knowledge Base ───────────────────────────────────────────────
DSM5_PATH = Path(__file__).parent / "dsm5_ansiedade.json"
with open(DSM5_PATH, "r", encoding="utf-8") as f:
    DSM5_DATA = json.load(f)

TAG_CRITERIA = DSM5_DATA["transtornos_de_ansiedade"]["TAG"]

# ─── Patient Profiles (random selection per session) ─────────────────────────
PATIENT_PROFILES = [
    {
        "nome": "Márcia",
        "idade": 34,
        "genero": "feminino",
        "ocupacao": "professora de ensino fundamental",
        "estado_civil": "casada, dois filhos",
        "contexto": "Nos últimos 8 meses, Márcia tem apresentado preocupação constante com o desempenho dos filhos na escola, com as finanças da família e com a possibilidade de perder o emprego, apesar de ter estabilidade no cargo. Relata dificuldade em dormir (acorda várias vezes à noite com pensamentos sobre o futuro), tensão muscular frequente nos ombros e pescoço, fadiga constante mesmo após descanso, e irritabilidade que tem afetado seu casamento. Tem dificuldade de se concentrar nas aulas que ministra. Nega uso de substâncias.",
        "sintomas_presentes": ["C1", "C2", "C3", "C4", "C5", "C6"],
        "criterios_satisfeitos": ["A", "B", "C", "D"],
        "diagnostico_real": "Transtorno de Ansiedade Generalizada (F41.1)"
    },
    {
        "nome": "Roberto",
        "idade": 42,
        "genero": "masculino",
        "ocupacao": "gerente de banco",
        "estado_civil": "divorciado, um filho de 10 anos",
        "contexto": "Roberto procura atendimento por queixa de 'nervosismo constante' há cerca de 7 meses. Relata preocupação excessiva com praticamente tudo: o desempenho no trabalho, a saúde dos pais idosos, a educação do filho, e até questões menores como atrasos no trânsito. Sente que não consegue 'desligar' a cabeça. Apresenta inquietação motora (fica balançando as pernas, não consegue ficar sentado por muito tempo), tensão muscular (bruxismo noturno diagnosticado pelo dentista), fatigabilidade e dificuldade de concentração. Relata consumo de 4-5 cafés por dia. Nega uso de outras substâncias.",
        "sintomas_presentes": ["C1", "C2", "C3", "C5"],
        "criterios_satisfeitos": ["A", "B", "C", "D"],
        "diagnostico_real": "Transtorno de Ansiedade Generalizada (F41.1)"
    },
    {
        "nome": "Camila",
        "idade": 26,
        "genero": "feminino",
        "ocupacao": "estudante de pós-graduação em direito",
        "estado_civil": "solteira, mora sozinha",
        "contexto": "Camila relata que sempre foi 'preocupada', mas nos últimos 6 meses a situação piorou significativamente após assumir um estágio em um escritório exigente. Preocupa-se com o desempenho acadêmico, com a possibilidade de não passar na OAB, com a opinião dos supervisores e com questões financeiras. Sente-se constantemente 'no limite', com nervos à flor da pele. Tem apresentado insônia inicial (demora 2-3 horas para dormir por causa dos pensamentos), irritabilidade marcada (tem se desentendido com amigos), e tensão muscular frequente nas costas. Relata episódios de diarreia antes de situações estressantes. Nega uso de substâncias além de chá de camomila ocasional.",
        "sintomas_presentes": ["C1", "C4", "C5", "C6"],
        "criterios_satisfeitos": ["A", "B", "C", "D"],
        "diagnostico_real": "Transtorno de Ansiedade Generalizada (F41.1)"
    }
]

# ─── System Prompt for the Patient Simulation ────────────────────────────────
def build_system_prompt(profile: dict) -> str:
    now = datetime.now(ZoneInfo("America/Belem"))
    meses = ["janeiro","fevereiro","março","abril","maio","junho",
             "julho","agosto","setembro","outubro","novembro","dezembro"]
    dias_semana = ["segunda-feira","terça-feira","quarta-feira","quinta-feira",
                   "sexta-feira","sábado","domingo"]
    data_formatada = f"{dias_semana[now.weekday()]}, {now.day} de {meses[now.month-1]} de {now.year}"
    hora_formatada = f"{now.hour}:{now.minute:02d}"

    return f"""Você é um PACIENTE SIMULADO para treinamento de estudantes de Medicina em anamnese psiquiátrica.

## CONTEXTO TEMPORAL
Hoje é {data_formatada}, aproximadamente {hora_formatada} (horário de Belém). Use esta informação para responder perguntas sobre data, dia da semana, mês ou horário de forma coerente.

## SUA IDENTIDADE
- Nome: {profile['nome']}
- Idade: {profile['idade']} anos
- Gênero: {profile['genero']}
- Ocupação: {profile['ocupacao']}
- Estado civil: {profile['estado_civil']}

## SEU QUADRO CLÍNICO (NUNCA REVELE DIRETAMENTE AO ALUNO)
Você apresenta Transtorno de Ansiedade Generalizada (TAG) conforme os critérios do DSM-5-TR.

Contexto da sua história:
{profile['contexto']}

## CRITÉRIOS DSM-5 QUE VOCÊ APRESENTA
{json.dumps(TAG_CRITERIA['criterios'], ensure_ascii=False, indent=2)}

Seus sintomas do Critério C presentes: {', '.join(profile['sintomas_presentes'])}

## REGRAS DE COMPORTAMENTO

1. **SEJA NATURAL**: Responda como um paciente real, com linguagem coloquial brasileira. NÃO use terminologia médica. Descreva seus sintomas com suas próprias palavras (ex: em vez de "fatigabilidade", diga "ando muito cansada, doutor, mesmo dormindo bastante não acordo descansada").

2. **RESPONDA APENAS AO QUE FOI PERGUNTADO**: Não ofereça informações espontaneamente. O aluno precisa inquirir adequadamente. Se perguntar "como você está?", dê uma resposta vaga como "não ando bem, doutor" e espere perguntas mais específicas.

3. **REVELE GRADUALMENTE**: Não despeje todos os sintomas de uma vez. Dê informações proporcionais à qualidade da pergunta. Perguntas abertas bem formuladas geram respostas mais ricas. Perguntas fechadas geram respostas curtas.

4. **NUNCA DÊ O DIAGNÓSTICO**: Você é paciente, não sabe o nome técnico do que tem. Diga coisas como "não sei o que tenho, por isso vim aqui", "acho que estou com algum problema dos nervos".

5. **DEMONSTRE EMOÇÕES REALISTAS**: Mostre preocupação, ansiedade ao falar de certos temas, alívio quando o médico demonstra empatia. Pode ficar um pouco reticente com perguntas muito diretas sobre saúde mental (estigma).

6. **MANTENHA COERÊNCIA**: Suas respostas devem ser consistentes ao longo da conversa. Não se contradiga.

7. **SOBRE PERGUNTAS DE RISCO (IDEAÇÃO SUICIDA)**: Se perguntado sobre pensamentos suicidas, responda que NÃO tem pensamentos suicidas ou de autolesão, mas que às vezes sente que "não aguenta mais" essa situação. Isso é importante para o aluno praticar a triagem de risco de forma segura.

8. **SOBRE SUBSTÂNCIAS E MEDICAMENTOS**: Responda conforme o contexto do perfil. Nega uso de drogas ilícitas.

9. **COMPRIMENTO DAS RESPOSTAS**: Mantenha respostas curtas a moderadas (2-5 frases), como um paciente real faria. Não faça monólogos longos a menos que provocado por uma pergunta muito aberta e empática.

10. **INÍCIO DA CONSULTA**: Na primeira mensagem (quando o aluno cumprimentar), apresente-se brevemente e diga algo como "Obrigada por me atender, doutor(a). Não tenho me sentido bem ultimamente..." e espere as perguntas.

11. **NUNCA SAIA DO PAPEL DE PACIENTE**: Mesmo que o aluno faça perguntas estranhas, tente dar diagnósticos, ou fuja do contexto clínico, você deve SEMPRE responder como paciente. Nunca dê feedback, avaliações ou orientações ao aluno durante a conversa. Você é APENAS o paciente.

LEMBRE-SE: Seu objetivo é treinar o aluno na coleta de dados e no raciocínio clínico. Seja um paciente realista e desafiador, mas cooperativo."""


# ─── Criteria Tracking System Prompt (silent, backend only) ──────────────────
TRACKER_SYSTEM_PROMPT = """Você é um sistema SILENCIOSO de rastreamento que analisa as perguntas de um estudante de Medicina durante uma anamnese psiquiátrica simulada.

Seu papel é registrar se a ÚLTIMA PERGUNTA do aluno está investigando algum critério diagnóstico do DSM-5-TR para Transtorno de Ansiedade Generalizada (TAG - F41.1).

Os critérios são:
- A: Ansiedade e preocupação excessivas, na maioria dos dias, por pelo menos 6 meses, sobre diversos eventos
- B: Dificuldade em controlar a preocupação
- C1: Inquietação / nervos à flor da pele
- C2: Fatigabilidade
- C3: Dificuldade de concentração / "brancos" na mente
- C4: Irritabilidade
- C5: Tensão muscular
- C6: Perturbação do sono
- D: Sofrimento/prejuízo funcional (trabalho, social, pessoal)
- E: Exclusão de substâncias/condição médica
- F: Exclusão de outro transtorno mental
- RISCO: Triagem de risco suicida/autolesão
- EEM: Exame do Estado Mental (aparência, comportamento, humor, afeto, pensamento, sensopercepção, consciência, orientação)

Responda APENAS com um JSON válido no formato:
{
  "criterios_investigados": ["lista de códigos dos critérios que a pergunta investiga, ex: A, C1, C5"],
  "justificativa": "breve explicação"
}

Se a mensagem do aluno não investiga nenhum critério diagnóstico, retorne:
{
  "criterios_investigados": [],
  "justificativa": "mensagem não relacionada à investigação diagnóstica"
}"""


# ─── Global Interview Quality Assessment Prompt (end of session) ─────────────
QUALITY_ASSESSMENT_PROMPT = """Você é um avaliador pedagógico especializado em ensino de anamnese psiquiátrica. Analise a transcrição COMPLETA da entrevista entre um estudante de Medicina e um paciente simulado.

Avalie a qualidade PROCESSUAL da entrevista nas seguintes dimensões:

1. **Acolhimento e Rapport**: O estudante demonstrou empatia? Usou linguagem acolhedora? Construiu vínculo terapêutico? Demonstrou escuta ativa?

2. **Progressão Lógica**: A entrevista seguiu uma sequência coerente? Partiu da queixa principal para aprofundamento? Houve organização no raciocínio clínico?

3. **Exploração Temporal**: O estudante investigou há quanto tempo os sintomas existem? Investigou início, evolução, fatores de melhora/piora? Buscou estabelecer uma linha do tempo?

4. **Aprofundamento Fenomenológico**: O estudante foi além das respostas superficiais? Fez perguntas de seguimento para entender melhor os sintomas? Explorou a experiência subjetiva do paciente?

5. **Linguagem e Comunicação**: O estudante usou linguagem adequada ao paciente? Evitou jargões? Fez perguntas abertas antes de fechadas? As perguntas foram claras?

6. **Construção de Vínculo**: O estudante validou as emoções do paciente? Demonstrou interesse genuíno? O paciente pareceu confortável durante a entrevista?

Para CADA dimensão, classifique como:
- "adequado": O estudante demonstrou competência nesta dimensão
- "parcial": Houve tentativa, mas com lacunas significativas
- "insuficiente": Não houve demonstração relevante desta competência
- "não_aplicável": A entrevista foi muito curta para avaliar

Responda APENAS com um JSON válido:
{
  "acolhimento_rapport": {"classificacao": "adequado|parcial|insuficiente|não_aplicável", "observacao": "breve comentário"},
  "progressao_logica": {"classificacao": "...", "observacao": "..."},
  "exploracao_temporal": {"classificacao": "...", "observacao": "..."},
  "aprofundamento_fenomenologico": {"classificacao": "...", "observacao": "..."},
  "linguagem_comunicacao": {"classificacao": "...", "observacao": "..."},
  "construcao_vinculo": {"classificacao": "...", "observacao": "..."},
  "avaliacao_global": "breve parágrafo resumindo os pontos fortes e as áreas de melhoria do estudante nesta entrevista",
  "sugestoes_formativas": ["lista de 3-5 sugestões práticas e específicas para o estudante melhorar"]
}"""


# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(title="PsiqMentor API v3")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Anthropic()

# In-memory session store
sessions: dict = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class FinishRequest(BaseModel):
    session_id: str


@app.post("/api/start")
def start_session():
    """Start a new simulation session with a random patient profile."""
    session_id = str(uuid.uuid4())
    profile = random.choice(PATIENT_PROFILES)
    system_prompt = build_system_prompt(profile)

    sessions[session_id] = {
        "profile": profile,
        "system_prompt": system_prompt,
        "messages": [],
        "criteria_tracked": {},
        "criteria_log": [],
        "started_at": datetime.now().isoformat(),
        "finished": False,
    }

    return {
        "session_id": session_id,
        "patient_name": profile["nome"],
        "patient_age": profile["idade"],
        "patient_gender": profile["genero"],
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Send a message and get the patient's response. Tracking is silent."""
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if session["finished"]:
        raise HTTPException(status_code=400, detail="Sessão já finalizada")

    # Add user message to history
    session["messages"].append({"role": "user", "content": req.message})

    # 1. Get patient response from LLM
    patient_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=session["system_prompt"],
        messages=session["messages"],
    )
    assistant_text = patient_response.content[0].text

    # Add assistant response to history
    session["messages"].append({"role": "assistant", "content": assistant_text})

    # 2. Silent criteria tracking (backend only)
    tracking_messages = [
        {
            "role": "user",
            "content": f"Contexto da conversa até agora:\n{_format_conversation(session['messages'][:-1])}\n\nÚLTIMA PERGUNTA DO ALUNO:\n{req.message}",
        }
    ]

    try:
        tracking_response = client.messages.create(
            model="claude-haiku-4-20250414",
            max_tokens=300,
            system=TRACKER_SYSTEM_PROMPT,
            messages=tracking_messages,
        )
        tracking_text = tracking_response.content[0].text

        json_start = tracking_text.find("{")
        json_end = tracking_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            tracking_data = json.loads(tracking_text[json_start:json_end])
        else:
            tracking_data = {
                "criterios_investigados": [],
                "justificativa": "Não foi possível analisar",
            }
    except Exception:
        tracking_data = {
            "criterios_investigados": [],
            "justificativa": "Erro na análise",
        }

    # Update criteria tracking (stored silently)
    for criterio in tracking_data.get("criterios_investigados", []):
        if criterio not in session["criteria_tracked"]:
            session["criteria_tracked"][criterio] = {
                "first_asked_turn": len(session["messages"]) // 2,
            }

    session["criteria_log"].append(
        {
            "turn": len(session["messages"]) // 2,
            "student_message": req.message,
            "criteria": tracking_data.get("criterios_investigados", []),
            "justificativa": tracking_data.get("justificativa", ""),
        }
    )

    return {
        "patient_response": assistant_text,
    }


@app.post("/api/finish")
def finish_session(req: FinishRequest):
    """Finish the session and return the full formative feedback report."""
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    session["finished"] = True
    profile = session["profile"]

    # ── Criteria coverage ────────────────────────────────────────────────
    all_criteria = [
        "A", "B", "C1", "C2", "C3", "C4", "C5", "C6", "D", "E", "F", "RISCO", "EEM"
    ]
    investigated = set(session["criteria_tracked"].keys())
    missing = [c for c in all_criteria if c not in investigated]

    core_criteria = {"A", "B", "C1", "C2", "C3", "C4", "C5", "C6", "D", "E"}
    core_investigated = core_criteria.intersection(investigated)
    score_pct = round((len(core_investigated) / len(core_criteria)) * 100)

    # ── Global quality assessment ────────────────────────────────────────
    quality_assessment = _assess_interview_quality(session["messages"])

    # ── Build formative feedback ─────────────────────────────────────────
    criteria_descriptions = {
        "A": "Ansiedade e preocupação excessivas (ocorrendo na maioria dos dias, por pelo menos 6 meses, sobre diversos eventos ou atividades)",
        "B": "Dificuldade em controlar a preocupação",
        "C1": "Inquietação ou sensação de estar com os nervos à flor da pele",
        "C2": "Fatigabilidade (cansar-se com facilidade)",
        "C3": "Dificuldade de concentração ou 'brancos' na mente",
        "C4": "Irritabilidade",
        "C5": "Tensão muscular",
        "C6": "Perturbação do sono (dificuldade para iniciar/manter o sono, ou sono insatisfatório e inquieto)",
        "D": "Sofrimento clinicamente significativo ou prejuízo no funcionamento social, profissional ou em outras áreas importantes",
        "E": "A perturbação não se deve aos efeitos fisiológicos de uma substância ou a outra condição médica",
        "F": "A perturbação não é mais bem explicada por outro transtorno mental",
        "RISCO": "Triagem de risco suicida e de autolesão",
        "EEM": "Exame do Estado Mental (aparência, comportamento, humor, afeto, pensamento, sensopercepção, consciência, orientação)",
    }

    formative_tips = []
    if "RISCO" not in investigated:
        formative_tips.append("A triagem de risco suicida é obrigatória em toda avaliação psiquiátrica, mesmo em quadros de ansiedade. Pergunte diretamente sobre pensamentos de morte, desejo de morrer ou autolesão.")
    if "EEM" not in investigated:
        formative_tips.append("O Exame do Estado Mental (EEM) é parte fundamental da avaliação. Observe e descreva: aparência, comportamento, humor (relatado pelo paciente), afeto (observado por você), pensamento (forma e conteúdo), sensopercepção, consciência e orientação.")
    if "E" not in investigated:
        formative_tips.append("Sempre investigue uso de substâncias (cafeína, álcool, drogas) e condições médicas (hipotireoidismo, feocromocitoma) que possam mimetizar ou agravar sintomas de ansiedade.")
    if "F" not in investigated:
        formative_tips.append("Considere diagnósticos diferenciais: os sintomas poderiam ser melhor explicados por outro transtorno (Pânico, Fobia Social, TOC, TEPT)?")
    if "A" not in investigated:
        formative_tips.append("É essencial investigar a natureza e abrangência da preocupação: sobre quais temas o paciente se preocupa? São múltiplos? A preocupação é desproporcional?")
    if "B" not in investigated:
        formative_tips.append("Pergunte se o paciente consegue controlar a preocupação. A dificuldade de controle é um critério central do TAG.")
    if len(core_investigated) < 4:
        formative_tips.append("Utilize perguntas abertas para explorar o quadro clínico de forma mais ampla antes de partir para perguntas fechadas e direcionadas.")
    if score_pct >= 80:
        formative_tips.append("Boa cobertura dos critérios diagnósticos. Continue praticando a formulação de hipóteses diagnósticas integrando os achados da anamnese.")

    return {
        "score_pct": score_pct,
        "criteria_investigated": sorted(list(investigated)),
        "criteria_missing": missing,
        "criteria_descriptions": criteria_descriptions,
        "total_turns": len(session["messages"]) // 2,
        "diagnostico_correto": profile["diagnostico_real"],
        "quality_assessment": quality_assessment,
        "formative_tips": formative_tips,
        "criteria_log": session["criteria_log"],
    }


def _assess_interview_quality(messages: list) -> dict:
    """Assess the overall quality of the interview process."""
    if len(messages) < 4:
        return {
            "acolhimento_rapport": {"classificacao": "não_aplicável", "observacao": "Entrevista muito curta para avaliar."},
            "progressao_logica": {"classificacao": "não_aplicável", "observacao": "Entrevista muito curta para avaliar."},
            "exploracao_temporal": {"classificacao": "não_aplicável", "observacao": "Entrevista muito curta para avaliar."},
            "aprofundamento_fenomenologico": {"classificacao": "não_aplicável", "observacao": "Entrevista muito curta para avaliar."},
            "linguagem_comunicacao": {"classificacao": "não_aplicável", "observacao": "Entrevista muito curta para avaliar."},
            "construcao_vinculo": {"classificacao": "não_aplicável", "observacao": "Entrevista muito curta para avaliar."},
            "avaliacao_global": "A entrevista foi muito breve para uma avaliação processual significativa.",
            "sugestoes_formativas": ["Realize entrevistas mais longas para permitir uma avaliação adequada da qualidade processual."],
        }

    conversation_text = _format_full_conversation(messages)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=QUALITY_ASSESSMENT_PROMPT,
            messages=[{"role": "user", "content": f"TRANSCRIÇÃO DA ENTREVISTA:\n\n{conversation_text}"}],
        )
        response_text = response.content[0].text

        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            return json.loads(response_text[json_start:json_end])
    except Exception:
        pass

    return {
        "acolhimento_rapport": {"classificacao": "não_aplicável", "observacao": "Não foi possível avaliar."},
        "progressao_logica": {"classificacao": "não_aplicável", "observacao": "Não foi possível avaliar."},
        "exploracao_temporal": {"classificacao": "não_aplicável", "observacao": "Não foi possível avaliar."},
        "aprofundamento_fenomenologico": {"classificacao": "não_aplicável", "observacao": "Não foi possível avaliar."},
        "linguagem_comunicacao": {"classificacao": "não_aplicável", "observacao": "Não foi possível avaliar."},
        "construcao_vinculo": {"classificacao": "não_aplicável", "observacao": "Não foi possível avaliar."},
        "avaliacao_global": "Não foi possível realizar a avaliação processual.",
        "sugestoes_formativas": [],
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "active_sessions": len(sessions)}


def _format_conversation(messages: list) -> str:
    """Format last messages for criteria tracker."""
    lines = []
    for m in messages[-10:]:
        role = "Aluno" if m["role"] == "user" else "Paciente"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


def _format_full_conversation(messages: list) -> str:
    """Format the full conversation for quality assessment."""
    lines = []
    for m in messages:
        role = "Estudante" if m["role"] == "user" else "Paciente"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


# ─── Serve Frontend (static files) ──────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"

@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")

# Mount static files AFTER API routes
app.mount("/", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
