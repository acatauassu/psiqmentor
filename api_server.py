#!/usr/bin/env python3
"""
PsiqMentor V4 - Backend API
Agente simulador de pacientes com Transtornos de Ansiedade para treinamento médico.
Mestrado em Ensino em Saúde - CESUPA

V4 - Mudanças:
- 9 pacientes cobrindo todos os transtornos de ansiedade do DSM-5-TR
- Prompts dinâmicos por transtorno (sistema e tracker)
- Remoção de identificação do aluno
- Endpoints de pesquisa de satisfação (survey)
- Critério EXAMES para transtornos por substância e condição médica
"""

import csv
import hashlib
import hmac
import io
import json
import os
import random
import secrets
import time
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from anthropic import Anthropic
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

# placeholder - full content below