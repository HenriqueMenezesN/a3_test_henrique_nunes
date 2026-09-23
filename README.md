# API de extração de incidentes

Aplicação para o desafio técnico de Engenharia de IA da A3Data. Recebe um relato, normaliza os espaços e utiliza um LLM local pelo Ollama para extrair `data_ocorrencia`, `local`, `tipo_incidente` e `impacto` em JSON.

O projeto usa FastAPI, Pydantic e HTTPX. O modelo padrão é `tinyllama`, sugerido no enunciado. É possível escolher outro modelo ao iniciar a API pela variável de ambiente `OLLAMA_MODEL`. O processamento não depende de serviços pagos ou de nuvem. A instalação das dependências e o download inicial do modelo exigem internet; depois, a inferência pode ser executada offline.

## Preparação no Windows / PowerShell

Tenha Python instalado (o ambiente local foi executado com Python 3.14), Ollama e, para os testes manuais, Postman.

Dentro da pasta do projeto, crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação, libere scripts apenas na sessão atual e tente novamente:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Ollama e modelo local

Instale o Ollama pela [página oficial para Windows](https://ollama.com/download/windows). Abra um novo terminal após a instalação e execute:

```powershell
ollama --version
ollama pull tinyllama
ollama list
```

O serviço deve estar disponível em `http://localhost:11434`. Se não estiver rodando, execute em outro terminal e deixe-o aberto:

```powershell
ollama serve
```

Se o endereço já estiver em uso, verifique se o aplicativo Ollama já está executando. Não é necessário iniciar uma segunda instância.

O nome configurado deve corresponder a um modelo instalado. O endereço da integração é definido em `ollama_client.py`, pela constante `OLLAMA_URL`.

## Executar a API

Com o ambiente virtual ativo, dentro da pasta do projeto:

```powershell
python -m uvicorn main:app --reload
```

A API fica em `http://127.0.0.1:8000`. Mantenha o terminal aberto. A opção `--reload` recarrega o código durante o desenvolvimento; `Ctrl+C` encerra o servidor.

### Escolher o modelo na inicialização

Sem definir `OLLAMA_MODEL`, a API usa `tinyllama`.

O modelo alternativo usado nos testes manuais foi **Llama 3.2 de 1 bilhão de parâmetros**, identificado no Ollama como **`llama3.2:1b`**. Ele também apresentou erros de extração, incluindo datas inventadas e nomes de sistemas interpretados como local; a troca de modelo não garante respostas corretas.

Para executar com esse mesmo modelo, pare a API com `Ctrl+C` e execute no mesmo PowerShell:

```powershell
ollama pull llama3.2:1b
$env:OLLAMA_MODEL = "llama3.2:1b"
python -m uvicorn main:app --reload
```

Para voltar ao TinyLlama, pare a API e execute:

```powershell
$env:OLLAMA_MODEL = "tinyllama"
python -m uvicorn main:app --reload
```

A variável vale para a sessão atual do terminal e é lida ao iniciar a aplicação. Reinicie a API após alterá-la. A escolha se aplica a todas as requisições; o corpo enviado pelo Postman continua contendo apenas `texto`. O download do modelo é uma etapa separada, realizada pelo comando `ollama pull`.

## Rotas

### GET `/health`

Retorna `200` com:

```json
{"status": "ok"}
```

Essa rota verifica que a API está respondendo; não verifica a disponibilidade do Ollama ou do modelo.

### POST `/incidentes`

Envie `Content-Type: application/json` e um corpo contendo apenas o texto do relato:

```json
{
  "texto": "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
}
```

O campo `texto` é obrigatório e aceita de 1 a 10.000 caracteres antes da normalização. Textos compostos apenas por espaços são rejeitados.

Exemplo de saída desejada, supondo que a data local do servidor seja **23/09/2026**:

```json
{
  "data_ocorrencia": "2026-09-22 14:00",
  "local": "São Paulo",
  "tipo_incidente": "Falha no servidor principal",
  "impacto": "Sistema de faturamento afetado por 2 horas"
}
```

Os quatro campos aceitam texto ou `null`. Esse exemplo representa o resultado desejado; os valores produzidos pelo LLM podem ser diferentes ou incorretos.

## Fluxo e decisões

1. A API valida a entrada com Pydantic.
2. `preprocessamento.py` remove espaços extras, tabulações e quebras de linha usando `split()` e `join()`, preservando o conteúdo.
3. `ollama_client.py` envia o relato e o prompt ao Ollama. A chamada usa um esquema JSON, `stream: false`, temperatura zero e timeout de 60 segundos no HTTPX. Esse timeout se aplica às operações de rede, não a um limite global de duração da requisição.
4. O código verifica a resposta do Ollama, converte o JSON gerado e exige exatamente os quatro campos com valores string ou `null`.
5. `datas.py` tenta calcular expressões simples de data relativa a partir do relato, substituindo o campo de data quando reconhece o formato.
6. A API retorna o objeto validado.

### Datas relativas

O cálculo Python reconhece `hoje às 14h` e `ontem às 14h`, também aceitando `as` sem acento e diferenças de maiúsculas/minúsculas. Usa sempre a data local do computador que executa a API; não existe um campo de data de referência na requisição.

O reconhecimento utiliza separação de palavras e validação da hora, sem expressões regulares. Calcula horas inteiras de `0h` a `23h`, inclusive em viradas de mês e ano. Se houver múltiplas referências relativas ou o formato não for reconhecido, mantém a extração do modelo.

Formatos com minutos (`14:30`, `9h15`), datas absolutas e outros casos continuam dependendo do LLM. A ausência de uma expressão reconhecida não força `data_ocorrencia` a ser `null`.

## Testar pelo Postman

1. Inicie o Ollama e a API.
2. No Postman, clique em **Import** e selecione `postman/a3_test.postman_collection.json`.
3. Confira a variável `base_url`, configurada como `http://127.0.0.1:8000`.
4. Execute **Health - API disponivel**.
5. Execute **Incidente - extrair dados com LLM** e confira **Body** e **Test Results**.

A collection contém essas duas requisições e a pasta **Erros - executar manualmente**, com os cenários de entrada composta apenas por espaços (`422`) e Ollama desligado (`503`). Execute os testes individualmente: a extração exige Ollama ativo, enquanto o teste de comunicação exige que ele esteja desligado e a API continue ativa. Depois desse teste, inicie o Ollama novamente.

Para testar as frases abaixo, substitua o valor de `texto` em **Body → raw → JSON** da requisição de extração. Seus testes conferem status, campos e tipos, sem exigir uma data específica. Confira manualmente a precisão dos valores. A primeira inferência pode demorar enquanto o modelo é carregado.

## Testar pelo `/docs`

1. Inicie o Ollama e a API.
2. No navegador, acesse [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), a documentação interativa da API.
3. Abra **GET /health**, clique em **Try it out** e depois em **Execute**. Confira o código `200` e `{"status": "ok"}` em **Response body**.
4. Abra **POST /incidentes** e clique em **Try it out**.
5. Em **Request body**, substitua o conteúdo pelo exemplo:

```json
{
  "texto": "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
}
```

6. Clique em **Execute** e confira o status HTTP em **Code** e o JSON retornado em **Response body**, na área **Server response**.
7. Para testar outras frases, altere o valor de `texto` em **Request body** e clique novamente em **Execute**.

O `/docs` envia requisições reais à API e mostra as respostas, mas não executa as verificações automáticas da collection do Postman. Confira manualmente os quatro campos e se os valores correspondem ao relato. A primeira inferência pode demorar enquanto o modelo é carregado.

Para testar a validação de entrada, envie `{"texto": "   "}`: o resultado esperado é `422`. Para testar uma falha de comunicação, encerre o Ollama e envie um relato válido: o resultado esperado é `503`. Depois, inicie o Ollama novamente.

## Frases adicionais

**Sem data nem local:** ambos deveriam ser `null`.

```json
{
  "texto": "Uma falha no roteador deixou o sistema de vendas sem conexão por 30 minutos."
}
```

**Com local, mas sem data:** `local` deveria identificar Recife e `data_ocorrencia` deveria ser `null`.

```json
{
  "texto": "No escritório de Recife, uma queda de energia desligou os computadores e interrompeu o atendimento por uma hora."
}
```

**Com data e hora explícitas:** observe se o modelo preserva a expressão temporal.

```json
{
  "texto": "Em 20/09/2026 às 09:30, no depósito de Curitiba, uma falha na impressora impediu a emissão de etiquetas por 45 minutos."
}
```

**Com hoje e hora inteira:** a data deve ser calculada pelo Python usando o dia local do servidor.

```json
{
  "texto": "Hoje às 10h, na filial de Salvador, uma falha no servidor de arquivos impediu o acesso aos documentos por 20 minutos."
}
```

**Sem impacto informado:** `impacto` deveria ser `null`.

```json
{
  "texto": "Foi identificada uma falha no equipamento de refrigeração da unidade de Manaus."
}
```

**Falha e consequência distintas:** o rompimento do cabo é o incidente; os terminais sem conexão são o impacto.

```json
{
  "texto": "Um rompimento no cabo de rede da unidade de Santos deixou os terminais de pagamento sem conexão por 15 minutos."
}
```

## Tratamento de erros

| Status | Situação |
| --- | --- |
| `200` | Extração retornada no formato esperado. |
| `422` | Entrada inválida, ausente, vazia ou acima do limite. |
| `502` | Erro HTTP do Ollama, JSON inválido ou estrutura de resposta incorreta. |
| `503` | Falha de comunicação com o Ollama. |
| `504` | Timeout na chamada ao Ollama. |

Exemplo de erro de comunicação:

```json
{
  "detail": "Não foi possível comunicar com o Ollama. Verifique se ele está em execução."
}
```

Para testar `422`, use **Entrada invalida - apenas espacos**. Para testar `503`, encerre o serviço Ollama e execute **Ollama desligado - falha de comunicacao**, mantendo a API ativa; depois inicie o Ollama novamente. Essas requisições verificam os respectivos códigos de erro. Fechar apenas uma conversa com o modelo não encerra o serviço.

Se receber `502` com aviso de `404`, confira `ollama list`, o modelo configurado e o endereço do serviço. Para `504`, verifique a disponibilidade de recursos e tente novamente. Erros de validação de entrada podem trazer uma lista em `detail`; os erros tratados da integração trazem uma mensagem.

## Limitações conhecidas

- Os modelos pequenos testados podem inventar datas e locais, confundir o componente que falhou com o sistema afetado e omitir detalhes do impacto.
- O esquema JSON e a validação garantem a estrutura aceita, mas não verificam a veracidade dos valores. Uma extração semanticamente incorreta pode retornar `200`.
- As regras do prompt orientam o uso de `null` para informações ausentes, mas não garantem que o modelo obedeça.
- A normalização de datas cobre apenas as expressões simples descritas acima.
- O escopo é uma execução local para avaliação. Não há autenticação, persistência de incidentes ou configuração de implantação em produção.

O enunciado prioriza integração com LLM local, boas práticas, organização e reprodutibilidade, sem avaliar a precisão das respostas. A validação deste projeto é feita manualmente pelo Postman; não há arquivos de testes automatizados na entrega atual.

## Arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `main.py` | Rotas, modelos de entrada/saída e tratamento de erros. |
| `ollama_client.py` | Prompt, configuração do modelo, chamada HTTP e validação da extração. |
| `preprocessamento.py` | Normalização de espaços. |
| `datas.py` | Cálculo simples de hoje/ontem com hora inteira. |
| `requirements.txt` | Dependências Python diretas com versões fixadas. |
| `postman/a3_test.postman_collection.json` | Requisições para testes manuais. |

Ao versionar o projeto em Git, inclua o código, este README, as dependências e a collection. Não inclua `.venv/`, ambientes antigos ou `__pycache__/`.
