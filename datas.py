from datetime import date, datetime, time, timedelta


def resolver_data_relativa(texto: str) -> str | None:
    """Resolve 'hoje às 14h' e 'ontem às 14h'; outros formatos ficam com o LLM."""
    # Converte para minúsculas e separa o relato em palavras.
    palavras = texto.lower().split()

    # Não escolhe automaticamente entre várias referências temporais.
    quantidade_referencias = 0
    for palavra in palavras:
        # strip() remove pontuação nas extremidades somente para contar referências.
        if palavra.strip(",.;:!?()\"'") in ("hoje", "ontem", "anteontem"):
            quantidade_referencias += 1
    if quantidade_referencias != 1:
        return None

    # enumerate() entrega a posição e a palavra para consultar as duas palavras seguintes.
    for indice, palavra in enumerate(palavras):
        if palavra not in ("hoje", "ontem"):
            # Ignora esta palavra e passa para a próxima repetição do laço.
            continue

        # Precisamos de duas palavras seguintes: "às" e o horário.
        if indice + 2 >= len(palavras):
            return None
        conector = palavras[indice + 1]
        # rstrip() remove a pontuação final: "14h," vira "14h".
        horario_texto = palavras[indice + 2].rstrip(",.;:!?")
        if conector not in ("às", "as") or not horario_texto.endswith("h"):
            return None

        # Remove o "h" de "14h" e aceita apenas um ou dois dígitos de 0 a 9.
        # [:-1] seleciona o texto até antes do último caractere, descartando o h.
        numero_hora = horario_texto[:-1]
        if not (1 <= len(numero_hora) <= 2):
            return None
        if not numero_hora.isascii() or not numero_hora.isdigit():
            return None
        hora = int(numero_hora)
        if hora > 23:
            return None

        # Usa sempre a data local do computador que executa a API.
        dia = date.today()
        if palavra == "ontem":
            # Evita subtrair um dia da menor data representável pelo Python.
            if dia == date.min:
                return None
            # timedelta representa um intervalo; a subtração cuida de meses e anos.
            dia -= timedelta(days=1)

        # Aceitamos apenas horas inteiras, então os minutos são sempre zero.
        # combine() une dia e horário; strftime() formata como ano-mês-dia hora:minuto.
        return datetime.combine(dia, time(hora, 0)).strftime("%Y-%m-%d %H:%M")

    # None sinaliza que a rota deve manter a data extraída pelo LLM.
    return None
