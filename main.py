from fastapi import FastAPI, HTTPException
import httpx
# BaseModel fornece validação e conversão de dados à classe; Field define regras para os campos, como tamanho mínimo e máximo.
from pydantic import BaseModel, Field
from preprocessamento import normalizar_texto
from ollama_client import extrair_dados_incidente
from datas import resolver_data_relativa

class IncidenteEntrada(BaseModel):
    texto: str = Field(min_length=1, max_length=10000)

class IncidenteSaida(BaseModel):
    data_ocorrencia: str | None = None
    local: str | None = None
    tipo_incidente: str | None = None
    impacto: str | None = None

app = FastAPI(title="API de Incidentes")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/incidentes", response_model=IncidenteSaida)
def extrair_incidente(entrada: IncidenteEntrada):
    # Acessa o texto recebido e normaliza os espaços.
    texto_normalizado = normalizar_texto(entrada.texto)

    # Rejeita textos que ficaram vazios após remover os espaços.
    if texto_normalizado == "":
        raise HTTPException(
            status_code=422,
            detail="O texto do incidente não pode conter apenas espaços.",
        )

    # try executa a extração; except transforma falhas conhecidas em erros HTTP claros.
    try:
        dados_extraidos = extrair_dados_incidente(texto_normalizado)
    except httpx.TimeoutException as erro:
        raise HTTPException(
            status_code=504,
            detail="O Ollama demorou demais para responder. Tente novamente.",
        ) from erro
    except httpx.HTTPStatusError as erro:
        if erro.response.status_code == 404:
            mensagem = "O Ollama retornou 404. Verifique o endereço e se o modelo configurado está instalado."
        else:
            mensagem = "O Ollama retornou um erro ao processar o incidente."
        raise HTTPException(status_code=502, detail=mensagem) from erro
    except httpx.RequestError as erro:
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
        dados_extraidos["data_ocorrencia"] = data_calculada

    return dados_extraidos
