# PsiqMentor V3 — Deploy no Render

Simulador de paciente com Transtorno de Ansiedade para treinamento de anamnese psiquiátrica.
Produto educacional — Mestrado em Ensino em Saúde, CESUPA.

## Novidades da V3

- **Identificação do aluno**: após sortear o paciente, o aluno preenche nome e matrícula
- **Dados no relatório**: nome e matrícula aparecem no cabeçalho do relatório (tela e PDF)
- **Avaliação processual**: 6 dimensões de qualidade da entrevista avaliadas por IA
- **Relatório formativo**: orientações pedagógicas em vez de classificação ruim/excelente
- **Tracking silencioso**: sem painel lateral durante a simulação
- **Pré-requisitos**: seção na tela inicial informando conhecimentos necessários

## Estrutura

```
psiqmentor-v3-render/
├── api_server.py          # Backend FastAPI + serve frontend
├── dsm5_ansiedade.json    # Critérios DSM-5-TR
├── requirements.txt       # Dependências Python
├── render.yaml            # Configuração do Render
├── .gitignore
├── README.md
└── static/
    └── index.html         # Frontend completo
```

## Deploy no Render (passo a passo)

### 1. Criar repositório no GitHub

1. Acesse [github.com/new](https://github.com/new) e crie um repositório (ex: `psiqmentor-v3`)
2. Pode ser público ou privado

### 2. Subir os arquivos

Você pode subir os arquivos de duas formas:

**Opção A — Pelo navegador:**
1. No GitHub, clique "uploading an existing file"
2. Arraste TODOS os arquivos e a pasta `static/` para lá
3. Clique "Commit changes"

**Opção B — Por terminal (se tiver Git instalado):**
```bash
cd psiqmentor-v3-render
git init
git add .
git commit -m "PsiqMentor V3"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/psiqmentor-v3.git
git push -u origin main
```

### 3. Obter chave da API Anthropic

1. Acesse [console.anthropic.com](https://console.anthropic.com/)
2. Crie uma conta (se não tiver)
3. Vá em "API Keys" e crie uma nova chave
4. Copie a chave (começa com `sk-ant-...`)

> **Custo estimado**: Cada simulação completa (15-20 turnos) custa aproximadamente US$ 0.05–0.10.

### 4. Deploy no Render

1. Acesse [render.com](https://render.com/) e crie uma conta
2. Clique **"New" → "Web Service"**
3. Conecte seu repositório GitHub
4. O Render vai detectar automaticamente o `render.yaml`
5. Configurações serão preenchidas automaticamente:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
6. Vá em **"Environment"** e adicione:
   - `ANTHROPIC_API_KEY` = cole sua chave `sk-ant-...`
7. Clique **"Create Web Service"**

### 5. Pronto!

Após o deploy (2-3 minutos), o Render fornecerá uma URL como:
```
https://psiqmentor-v3.onrender.com
```

Essa URL é permanente e funciona 24/7.

## Plano gratuito do Render

- O plano **Free** funciona, mas o servidor "dorme" após 15 minutos de inatividade
- A primeira requisição após dormir leva ~30 segundos para acordar
- Para uso acadêmico, isso é perfeitamente aceitável

## Modelos de IA utilizados

- **Claude Sonnet 4** — simulação do paciente e avaliação de qualidade
- **Claude Haiku 4** — rastreamento silencioso de critérios (mais econômico)
