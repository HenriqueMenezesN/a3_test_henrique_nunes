# Recebe uma string e devolve o texto com os espaços normalizados.
def normalizar_texto(texto: str) -> str:
    # split() separa as palavras por espaços, tabulações e quebras de linha.
    # join() reúne as partes com um único espaço, eliminando também espaços nas extremidades.
    return " ".join(texto.split())