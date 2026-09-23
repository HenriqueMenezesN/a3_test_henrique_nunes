import json
import os
import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
# Lê o modelo definido ao iniciar a API; se não houver, usa TinyLlama.
MODELO = os.getenv("OLLAMA_MODEL", "tinyllama").strip() or "tinyllama"

def extrair_dados_incidente(texto: str) -> dict:
    prompt = f"""
    Extraia as informações do incidente abaixo.

    Retorne somente um JSON com:
    data_ocorrencia, local, tipo_incidente e impacto.

    Quando uma informação não estiver presente, use null.

    Incidente:
    {texto}
    """

    formato_saida = {
        "type": "object",
        "properties": {
            "data_ocorrencia": {
                "type": ["string", "null"],
            },
            "local": {
                "type": ["string", "null"],
            },
            "tipo_incidente": {
                "type": ["string", "null"],
            },
            "impacto": {
                "type": ["string", "null"],
            },
        },
        "required": [
            "data_ocorrencia",
            "local",
            "tipo_incidente",
            "impacto",
        ],
        "additionalProperties": False,
    }

    dados_requisicao = {
        "model": MODELO,
        "prompt": prompt,
        "format": formato_saida,
        "stream": False,
        "options": {
            "temperature": 0,
        },
    }

    resposta = httpx.post(
        OLLAMA_URL,
        json=dados_requisicao,
        timeout=60.0,
    )

    resposta.raise_for_status()

    dados_ollama = resposta.json()
    # Verifica o envelope da API antes de acessar a resposta do modelo.
    if not isinstance(dados_ollama, dict):
        raise ValueError("A resposta do Ollama deve ser um objeto JSON.")
    if "error" in dados_ollama or dados_ollama.get("done") is False:
        raise ValueError("O Ollama não concluiu a geração.")
    if not isinstance(dados_ollama.get("response"), str):
        raise ValueError("O Ollama não retornou o campo response como texto.")

    resposta_modelo = dados_ollama["response"]
    dados_extraidos = json.loads(resposta_modelo)

    # JSON válido não basta: precisamos dos quatro campos, com texto ou null.
    if not isinstance(dados_extraidos, dict):
        raise ValueError("A extração deve ser um objeto JSON.")
    if set(dados_extraidos) != set(formato_saida["required"]):
        raise ValueError("A extração não contém exatamente os campos esperados.")
    for valor in dados_extraidos.values():
        if valor is not None and not isinstance(valor, str):
            raise ValueError("Cada campo extraído deve conter texto ou null.")

    return dados_extraidos
