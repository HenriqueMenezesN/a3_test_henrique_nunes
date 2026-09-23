from fastapi import FastAPI, HTTPException
import httpx
# BaseModel fornece validação e conversão de dados à classe; Field define regras para os campos, como tamanho mínimo e máximo.
from pydantic import BaseModel, Field
from preprocessamento import normalizar_texto
from ollama_client import extrair_dados_incidente
from datas import resolver_data_relativa

# Define o corpo da requisição. O FastAPI valida estes limites antes de chamar a rota.
class IncidenteEntrada(BaseModel):
    texto: str = Field(min_length=1, max_length=10000)

# str | None permite texto ou ausência de valor, representada por null no JSON.
# O padrão = None preenche campos ausentes; o cliente Ollama valida sua presença antes.
class IncidenteSaida(BaseModel):
    data_ocorrencia: str | None = None
    local: str | None = None
    tipo_incidente: str | None = None
    impacto: str | None = None

# Cria a aplicação e define o título exibido na documentação /docs.
app = FastAPI(title="API de Incidentes")

@app.get("/health")
def health():
    # Confirma que a API responde, sem consultar o Ollama.
    return {"status": "ok"}

# Associa a URL à função; response_model valida e formata a saída.
@app.post("/incidentes", response_model=IncidenteSaida)
def extrair_incidente(entrada: IncidenteEntrada):
    # Acessa o texto recebido e normaliza os espaços.
    texto_normalizado = normalizar_texto(entrada.texto)

    # Rejeita textos que ficaram vazios após remover os espaços.
    if texto_normalizado == "":
        # raise interrompe a função; HTTPException define o status e a mensagem ao cliente.
        raise HTTPException(
            status_code=422,
            detail="O texto do incidente não pode conter apenas espaços.",
        )

    # try executa a extração; except transforma falhas conhecidas em erros HTTP claros.
    try:
        dados_extraidos = extrair_dados_incidente(texto_normalizado)
    except httpx.TimeoutException as erro:
        # Timeout também é RequestError, por isso deve ser tratado antes dele.
        # "from erro" preserva a causa original para diagnóstico no Python.
        raise HTTPException(
            status_code=504,
            detail="O Ollama demorou demais para responder. Tente novamente.",
        ) from erro
    except httpx.HTTPStatusError as erro:
        # Houve resposta HTTP, mas o Ollama informou falha ao atender o pedido.
        if erro.response.status_code == 404:
            mensagem = "O Ollama retornou 404. Verifique o endereço e se o modelo configurado está instalado."
        else:
            mensagem = "O Ollama retornou um erro ao processar o incidente."
        raise HTTPException(status_code=502, detail=mensagem) from erro
    except httpx.RequestError as erro:
        # Abrange falhas de comunicação, como conexão recusada com o serviço desligado.
        raise HTTPException(
            status_code=503,
            detail="Não foi possível comunicar com o Ollama. Verifique se ele está em execução.",
        ) from erro
    except ValueError as erro:
        # Inclui JSON inválido e respostas que não respeitam os campos esperados.
        raise HTTPException(
            status_code=502,
            detail="O Ollama retornou uma resposta inválida. Tente novamente.",
        ) from erro

    # Calcula a data a partir do relato, sem confiar na data inventada pelo modelo.
    data_calculada = resolver_data_relativa(texto_normalizado)
    if data_calculada is not None:
        # Substitui apenas a data reconhecida; os outros campos continuam vindo do modelo.
        dados_extraidos["data_ocorrencia"] = data_calculada

    # O FastAPI converte o dicionário Python em uma resposta JSON.
    return dados_extraidos
