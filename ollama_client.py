import json
import os
import httpx

# Endereço do serviço local que executa o modelo; é separado da nossa API na porta 8000.
OLLAMA_URL = "http://localhost:11434/api/generate"
# Lê o modelo definido ao iniciar a API; se não houver, usa TinyLlama.
# strip() remove espaços; o "or" usa o padrão também quando a variável está vazia.
MODELO = os.getenv("OLLAMA_MODEL", "tinyllama").strip() or "tinyllama"

def extrair_dados_incidente(texto: str) -> dict:
    # A f-string insere o relato recebido em {texto} nas instruções enviadas ao modelo.
    prompt = f"""
    Extraia as informações do incidente abaixo.

    Retorne somente um JSON com:
    data_ocorrencia, local, tipo_incidente e impacto.

    Quando uma informação não estiver presente, use null.

    Incidente:
    {texto}
    """

    # JSON Schema descreve a estrutura solicitada, mas não garante valores verdadeiros.
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
        # Os campos devem existir, mesmo quando seu valor é null.
        "required": [
            "data_ocorrencia",
            "local",
            "tipo_incidente",
            "impacto",
        ],
        # Solicita que o modelo não acrescente campos fora do esquema.
        "additionalProperties": False,
    }

    dados_requisicao = {
        "model": MODELO,
        "prompt": prompt,
        "format": formato_saida,
        # Recebe a resposta completa, em vez de vários fragmentos durante a geração.
        "stream": False,
        "options": {
            # Reduz a aleatoriedade da geração; não garante uma extração correta.
            "temperature": 0,
        },
    }

    # Envia o dicionário como JSON. Erros de rede são tratados pela rota em main.py.
    resposta = httpx.post(
        OLLAMA_URL,
        json=dados_requisicao,
        # Limita a espera nas operações de rede, não a duração total da requisição.
        timeout=60.0,
    )

    # Gera HTTPStatusError se o status HTTP não indicar sucesso.
    resposta.raise_for_status()

    # Converte o JSON externo do serviço, que contém metadados e o campo response.
    dados_ollama = resposta.json()
    # Verifica o envelope da API antes de acessar a resposta do modelo.
    if not isinstance(dados_ollama, dict):
        raise ValueError("A resposta do Ollama deve ser um objeto JSON.")
    if "error" in dados_ollama or dados_ollama.get("done") is False:
        raise ValueError("O Ollama não concluiu a geração.")
    if not isinstance(dados_ollama.get("response"), str):
        raise ValueError("O Ollama não retornou o campo response como texto.")

    # O JSON gerado pelo modelo ainda é uma string dentro do JSON externo do Ollama.
    resposta_modelo = dados_ollama["response"]
    # loads() converte essa string em dados Python; JSON malformado gera ValueError.
    dados_extraidos = json.loads(resposta_modelo)

    # JSON válido não basta: precisamos dos quatro campos, com texto ou null.
    if not isinstance(dados_extraidos, dict):
        raise ValueError("A extração deve ser um objeto JSON.")
    # set() compara os nomes dos campos sem depender da ordem em que vieram.
    if set(dados_extraidos) != set(formato_saida["required"]):
        raise ValueError("A extração não contém exatamente os campos esperados.")
    # No Python, o null do JSON é convertido em None.
    for valor in dados_extraidos.values():
        if valor is not None and not isinstance(valor, str):
            raise ValueError("Cada campo extraído deve conter texto ou null.")

    return dados_extraidos
