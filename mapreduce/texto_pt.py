"""
Utilidades de texto en portugués compartidas por los mappers.
Hadoop Streaming distribuye este archivo a cada contenedor con la opción -files,
así que los mappers lo importan desde su directorio de trabajo.
"""
import re
import unicodedata
import zlib

# Palabras vacías del portugués. "nao" NO se elimina: la negación cambia el sentido
# ("nao chegou", "nao recomendo") y es clave para detectar quejas.
STOPWORDS = set("""
a o e as os um uma uns umas de do da dos das no na nos nas em ao aos para pra pro
por pelo pela pelos pelas com sem que se ja foi ser sao esta estao estava era sou
eu me meu minha meus minhas voce voces ele ela eles elas lhe nos isso isto esse essa
este aquele aquela mas mais muito muita bem tambem so como quando onde porque pois
ate apos entre sobre tem ter tinha teve fui vou vai ha hoje dia dias ainda agora
la aqui ai entao ou nem the of to and is it in my item produto
""".split())

# Léxico de temas (prefijos sobre texto normalizado, sin tildes).
TEMAS = {
    "entrega_atraso":     ["atras", "demor", "fora do prazo", "passou do prazo", "apos o prazo",
                           "nao chegou", "ainda nao", "nao receb", "nao foi entregue",
                           "nao entreg", "aguard", "esperand", "extravi"],
    "producto_defecto":   ["defeit", "quebrad", "danific", "nao funcion", "estragad",
                           "riscad", "amassad", "vazand"],
    "producto_diferente": ["diferente", "errad", "outro produto", "nao corresponde",
                           "trocad", "cor errada", "tamanho errado", "falsific"],
    "pedido_incompleto":  ["faltou", "falta", "faltand", "incomplet", "veio so", "veio apenas",
                           "somente um", "apenas um", "so um", "1 dos", "um dos"],
    "atencion_cliente":   ["atendiment", "contato", "respost", "reclam", "sac ", "email",
                           "e-mail", "ninguem", "descaso", "reembols", "estorno", "devolu"],
    "elogio_entrega":     ["antes do prazo", "chegou rapido", "entrega rapida", "rapidez",
                           "chegou antes", "super rapid", "dentro do prazo", "no prazo"],
    "elogio_producto":    ["otim", "excelent", "perfeit", "recomendo", "qualidade boa",
                           "boa qualidade", "adorei", "amei", "maravilh", "lindo"],
}

_RE_NO_LETRA = re.compile(r"[^a-z0-9\s-]")
_RE_ESPACIOS = re.compile(r"\s+")


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, sin signos de puntuación."""
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = _RE_NO_LETRA.sub(" ", t)
    return _RE_ESPACIOS.sub(" ", t).strip()


def tokens(texto_normalizado: str):
    return [w for w in texto_normalizado.split()
            if len(w) >= 2 and w not in STOPWORDS and not w.isdigit()]


def terminos(texto_normalizado: str):
    """Unigramas y bigramas únicos de una reseña (frecuencia documental)."""
    tk = tokens(texto_normalizado)
    uni = set(tk)
    bi = {f"{a}_{b}" for a, b in zip(tk, tk[1:])}
    return uni | bi


def temas(texto_normalizado: str):
    # Cada patrón debe empezar en un límite de palabra (" so um" no coincide con "isso um").
    t = f" {texto_normalizado} "
    return sorted(tema for tema, pats in TEMAS.items() if any(f" {p}" in t for p in pats))


def clase(score: int) -> str:
    """Clase de sentimiento a partir de la calificación (1-5 estrellas)."""
    return "NEG" if score <= 2 else ("NEU" if score == 3 else "POS")


def es_prueba(review_id: str) -> bool:
    """Partición determinística 80/20 (entrenamiento/prueba) por hash del review_id."""
    return zlib.crc32(review_id.encode()) % 5 == 0
