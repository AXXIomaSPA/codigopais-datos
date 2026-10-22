"""
Cocina de datos de Código País · Presupuesto nacional (DIPRES).

Fuente: Dirección de Presupuestos, conjuntos "Ley de Presupuestos Inicial y Vigente" y
"Ejecución Presupuestaria" del Gobierno Central (Total), publicados en datos.gob.cl con licencia CC0.

Qué hace:
  1. Busca en el catálogo de datos.gob.cl el último mes publicado del año en curso.
  2. Descarga la ley y la ejecución (nacional consolidado, por partida y por programa).
  3. Arma la serie mensual, compara con el mismo mes del año anterior (en pesos de hoy, con el IPC del INE)
     y genera archivos JSON pequeños en salida/gasto/.
  4. Antes de publicar, verifica que los totales cuadren. Si un control crítico falla, no escribe nada
     y termina con error (el último dato bueno se mantiene).

Reglas de cálculo (ver FASE0-VERIFICACION-FUENTES.md):
  - Montos de origen en MILES de pesos, con punto como separador de miles. Aquí se publican en PESOS.
  - Gasto = subtítulos 21 a 34 (el 35, saldo final de caja, no es gasto).
  - El total del país sale del archivo NACIONAL consolidado; nunca de sumar partidas (el Tesoro Público
    traspasa a los ministerios el "aporte fiscal", subtítulos 27 y 28, y se contaría dos veces).
  - Por ministerio se usa el archivo de PARTIDA (ya consolidado dentro de cada ministerio); para la
    partida 50 (Tesoro Público) se excluyen los subtítulos 27 y 28.
  - El detalle por programa es bruto (incluye transferencias entre servicios del mismo ministerio).

Solo usa la biblioteca estándar de Python 3.10+.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone

CKAN = "https://datos.gob.cl/api/3/action/package_search"
ORG = "direccion_de_presupuestos"
INE = "https://api-calculadora.ine.cl/ServiciosCalculadoraVariacion"
UA = {"User-Agent": "CodigoPais-cocina/1.0 (+https://codigopais.cl)"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "salida", "gasto")


# ---------------------------------------------------------------- utilidades
def http(url: str, intentos: int = 3, timeout: int = 120) -> bytes:
    ultimo = None
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            ultimo = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"No se pudo descargar {url}: {ultimo}")


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def miles_a_pesos(x: str) -> int:
    """'203.173' (miles) → 203173000 pesos. Acepta negativos y celdas vacías."""
    x = (x or "").strip().replace(".", "").replace(",", ".")
    if not x:
        return 0
    return int(round(float(x) * 1000))


def leer_csv(b: bytes) -> list[dict]:
    texto = b.decode("utf-8-sig", errors="replace")
    filas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
    # Normaliza nombres de columnas y la moneda ("Pesos" / "PESOS").
    out = []
    for f in filas:
        g = {(k or "").strip(): (v or "").strip() for k, v in f.items()}
        g["Moneda"] = g.get("Moneda", "").upper()
        out.append(g)
    return out


def col(fila: dict, prefijo: str) -> str:
    """Devuelve la columna que empieza con el prefijo (los nombres incluyen el mes: 'Ejecución a Agosto')."""
    for k in fila:
        if sin_tildes(k).startswith(sin_tildes(prefijo)):
            return k
    raise KeyError(prefijo)


def es_gasto(sub: str) -> bool:
    return sub.isdigit() and 21 <= int(sub) <= 34


# ---------------------------------------------------------------- catálogo
def catalogo() -> list[dict]:
    paquetes, inicio = [], 0
    while True:
        q = urllib.parse.urlencode({"fq": f"organization:{ORG}", "rows": 1000, "start": inicio})
        r = json.loads(http(f"{CKAN}?{q}"))["result"]
        paquetes += r["results"]
        inicio += 1000
        if inicio >= r["count"]:
            return paquetes


PATRON = re.compile(r"^(Ejecuci[oó]n Presupuestaria|Ley de Presupuestos Inicial y Vigente) a (\w+) de (\d{4}) del Gobierno Central - Total$", re.I)


def indexar(paquetes: list[dict]) -> dict:
    """{('ejec'|'ley', año, mes): paquete}"""
    idx = {}
    for p in paquetes:
        m = PATRON.match(p.get("title", "").strip())
        if not m:
            continue
        mes = sin_tildes(m.group(2))
        if mes not in MESES:
            continue
        tipo = "ejec" if m.group(1).lower().startswith("ejec") else "ley"
        idx[(tipo, int(m.group(3)), MESES.index(mes) + 1)] = p
    return idx


def recurso(paquete: dict, nivel: str) -> dict:
    for r in paquete.get("resources", []):
        if sin_tildes(r.get("name", "")) == sin_tildes(f"A nivel {nivel}"):
            return r
    raise KeyError(f"{paquete['title']}: falta el recurso 'A nivel {nivel}'")


def bajar(paquete: dict, nivel: str) -> tuple[list[dict], str]:
    r = recurso(paquete, nivel)
    return leer_csv(http(r["url"])), r["url"]


def url_paquete(p: dict) -> str:
    return f"https://datos.gob.cl/dataset/{p['name']}"


# ---------------------------------------------------------------- IPC (INE)
def ipc_12m(anio: int, mes: int) -> float | None:
    """Variación oficial del IPC entre el mismo mes del año anterior y este (INE), en %."""
    q = urllib.parse.urlencode({"mesInicio": mes, "AnioInicio": anio - 1, "mesTermino": mes,
                                "AnioTermino": anio, "valor_a_ajustar": 100})
    try:
        d = json.loads(http(f"{INE}?{q}", intentos=2, timeout=30))
        t = d[0]["variacion_ipc"].replace("%", "").replace(" ", "").replace(".", "").replace(",", ".")
        return float(t)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- cálculo
def sumar(filas, columna, filtro):
    return sum(miles_a_pesos(f[columna]) for f in filas if filtro(f))


def pesos_gasto(f):
    return f["Moneda"] == "PESOS" and es_gasto(f["Subtítulo"])


def gasto_ministerio(f):
    return pesos_gasto(f) and not (f["Partida"] == "50" and f["Subtítulo"] in ("27", "28"))


def main() -> int:
    ahora = datetime.now(timezone.utc)
    idx = indexar(catalogo())
    anios = sorted({a for (t, a, m) in idx if t == "ejec"})
    if not anios:
        print("ERROR: no se encontraron conjuntos de ejecución en el catálogo"); return 1
    anio = anios[-1]
    meses = sorted(m for (t, a, m) in idx if t == "ejec" and a == anio and ("ley", a, m) in idx)
    if not meses:
        print(f"ERROR: {anio} no tiene ley y ejecución del mismo mes"); return 1
    mes = meses[-1]
    pe, pl = idx[("ejec", anio, mes)], idx[("ley", anio, mes)]
    print(f"Último mes publicado: {MESES[mes-1]} de {anio} (publicado {pe.get('metadata_modified','')[:10]})")

    # --- descargas del mes
    en, url_en = bajar(pe, "Nacional"); ln, url_ln = bajar(pl, "Nacional")
    ep, url_ep = bajar(pe, "Partida"); lp, url_lp = bajar(pl, "Partida")
    eg, url_eg = bajar(pe, "Programa"); lg, url_lg = bajar(pl, "Programa")
    c_ej, c_ejm = col(en[0], "Ejecución a"), col(en[0], "Ejecución de")
    c_li, c_lv = col(ln[0], "Monto Ley Inicial"), col(ln[0], "Monto Ley Vigente")

    tot_ini = sumar(ln, c_li, pesos_gasto)
    tot_vig = sumar(ln, c_lv, pesos_gasto)
    tot_eje = sumar(en, c_ej, pesos_gasto)

    # --- por tipo de gasto (subtítulo), nacional consolidado
    nombres_sub = {f["Subtítulo"]: f["Nombre Subtítulo"] for f in ln + en if pesos_gasto(f)}
    por_tipo = []
    for s in sorted(nombres_sub):
        v = sumar(ln, c_lv, lambda f, s=s: pesos_gasto(f) and f["Subtítulo"] == s)
        e = sumar(en, c_ej, lambda f, s=s: pesos_gasto(f) and f["Subtítulo"] == s)
        if v or e:
            por_tipo.append({"subtitulo": s, "nombre": nombres_sub[s].capitalize(), "vigente": v, "ejecutado": e})

    # --- serie mensual del año (ejecución del mes y acumulada)
    mensual = []
    for m in range(1, mes + 1):
        p = idx.get(("ejec", anio, m))
        if not p:
            mensual.append({"mes": m, "nombre": MESES[m-1], "ejecutado_mes": None, "acumulado": None}); continue
        fil, _ = bajar(p, "Nacional")
        mensual.append({"mes": m, "nombre": MESES[m-1],
                        "ejecutado_mes": sumar(fil, col(fil[0], "Ejecución de"), pesos_gasto),
                        "acumulado": sumar(fil, col(fil[0], "Ejecución a"), pesos_gasto)})

    # --- comparación con el mismo mes del año anterior
    comp, ant_part = None, {}
    pa = idx.get(("ejec", anio - 1, mes))
    if pa:
        an, _ = bajar(pa, "Nacional"); ap, _ = bajar(pa, "Partida")
        eje_ant = sumar(an, col(an[0], "Ejecución a"), pesos_gasto)
        c_ap = col(ap[0], "Ejecución a")
        for f in ap:
            if gasto_ministerio(f):
                ant_part[f["Partida"]] = ant_part.get(f["Partida"], 0) + miles_a_pesos(f[c_ap])
        ipc = ipc_12m(anio, mes)
        nom = (tot_eje / eje_ant - 1) * 100 if eje_ant else None
        real = ((tot_eje / (eje_ant * (1 + ipc / 100))) - 1) * 100 if (eje_ant and ipc is not None) else None
        comp = {"anio_anterior": anio - 1, "ejecutado_anterior": eje_ant, "variacion_nominal": nom,
                "ipc_12_meses": ipc, "variacion_real": real, "fuente_anterior": url_paquete(pa)}

    # --- ministerios (partidas)
    c_epa, c_lpi, c_lpv = col(ep[0], "Ejecución a"), col(lp[0], "Monto Ley Inicial"), col(lp[0], "Monto Ley Vigente")
    nombres = {f["Partida"]: f["Nombre Partida"] for f in lp + ep}
    ministerios = []
    for cod in sorted(nombres):
        ini = sumar(lp, c_lpi, lambda f, c=cod: gasto_ministerio(f) and f["Partida"] == c)
        vig = sumar(lp, c_lpv, lambda f, c=cod: gasto_ministerio(f) and f["Partida"] == c)
        eje = sumar(ep, c_epa, lambda f, c=cod: gasto_ministerio(f) and f["Partida"] == c)
        if not (vig or eje):
            continue
        ant = ant_part.get(cod)
        real = None
        if ant and comp and comp["ipc_12_meses"] is not None:
            real = ((eje / (ant * (1 + comp["ipc_12_meses"] / 100))) - 1) * 100
        ministerios.append({
            "codigo": cod, "nombre": nombres[cod].title().replace(" De ", " de ").replace(" Del ", " del ").replace(" Y ", " y "),
            "ley_inicial": ini, "vigente": vig, "ejecutado": eje,
            "porcentaje": eje / vig * 100 if vig else None,
            "ejecutado_anterior": ant, "variacion_real": real,
            "nota": "Sin el aporte fiscal que el Tesoro traspasa a los ministerios (subtítulos 27 y 28)." if cod == "50" else None,
        })
    ministerios.sort(key=lambda x: -x["vigente"])

    # --- programas por partida (bruto)
    c_egp, c_lgv = col(eg[0], "Ejecución a"), col(lg[0], "Monto Ley Vigente")
    prog = {}
    for f, c, k in [(f, c_lgv, "vigente") for f in lg] + [(f, c_egp, "ejecutado") for f in eg]:
        if not pesos_gasto(f):
            continue
        key = (f["Partida"], f["Capítulo"], f["Programa"])
        d = prog.setdefault(key, {"capitulo": f["Capítulo"], "nombre_capitulo": f["Nombre Capítulo"],
                                  "programa": f["Programa"], "nombre_programa": f["Nombre Programa"],
                                  "vigente": 0, "ejecutado": 0})
        d[k] += miles_a_pesos(f[c])

    # ---------------------------------------------------------------- controles
    suma_min = sum(m["vigente"] for m in ministerios)
    razon = suma_min / tot_vig if tot_vig else 0
    controles = [
        ("total vigente plausible (entre $50 y $300 billones)", 50e12 <= tot_vig <= 300e12, tot_vig),
        ("ejecución entre 0 % y 110 % del vigente", 0 <= tot_eje <= tot_vig * 1.10, tot_eje / tot_vig * 100 if tot_vig else None),
        ("ministerios suman entre 1,00 y 1,08 veces el total consolidado", 1.0 <= razon <= 1.08, round(razon, 4)),
        ("serie mensual: acumulado del último mes = total ejecutado", mensual[-1]["acumulado"] == tot_eje, mensual[-1]["acumulado"]),
        ("hay al menos 20 ministerios", len(ministerios) >= 20, len(ministerios)),
        ("hay al menos 300 programas", len(prog) >= 300, len(prog)),
    ]
    falla = [c for c in controles if not c[1]]
    for c in controles:
        print(("OK   " if c[1] else "FALLA"), c[0], "→", c[2])
    if falla:
        print("ERROR: no se publica. Se mantiene el último dato bueno."); return 1

    # ---------------------------------------------------------------- escritura
    fuentes = {
        "organismo": "Dirección de Presupuestos (DIPRES)",
        "licencia": "CC0 1.0 (dominio público)",
        "ejecucion": url_paquete(pe), "ley": url_paquete(pl),
        "archivos": {"ejecucion_nacional": url_en, "ley_nacional": url_ln, "ejecucion_partida": url_ep,
                     "ley_partida": url_lp, "ejecucion_programa": url_eg, "ley_programa": url_lg},
        "ipc": "Instituto Nacional de Estadísticas (INE), api-calculadora.ine.cl",
    }
    meta = {"anio": anio, "mes": mes, "mes_nombre": MESES[mes-1],
            "publicado_fuente": pe.get("metadata_modified", "")[:10],
            "generado": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"), "unidad": "pesos chilenos", "fuentes": fuentes}
    os.makedirs(os.path.join(SALIDA, "programas"), exist_ok=True)

    def escribir(nombre, datos):
        with open(os.path.join(SALIDA, nombre), "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=1)

    escribir("resumen.json", {**meta, "totales": {"ley_inicial": tot_ini, "vigente": tot_vig, "ejecutado": tot_eje,
                                                 "porcentaje": tot_eje / tot_vig * 100},
                              "por_tipo": por_tipo, "mensual": mensual, "comparacion": comp,
                              "definicion": "Gasto del Gobierno Central consolidado: subtítulos 21 a 34 (incluye servicio de la deuda y operaciones financieras), en pesos."})
    escribir("ministerios.json", {**meta, "ministerios": ministerios,
                                  "nota": "Cada ministerio incluye las transferencias que hace a otros organismos públicos; por eso la suma supera en alrededor de 3 % al total consolidado del país."})
    for cod in {k[0] for k in prog}:
        lista = sorted((v for k, v in prog.items() if k[0] == cod), key=lambda x: -x["vigente"])
        escribir(f"programas/{cod}.json", {**meta, "partida": cod, "nombre": nombres.get(cod, ""), "programas": lista,
                                           "nota": "Montos brutos: incluyen transferencias entre servicios del mismo ministerio."})
    escribir("control.json", {**meta, "controles": [{"control": c[0], "ok": c[1], "valor": c[2]} for c in controles]})
    print(f"Publicado: {len(ministerios)} ministerios, {len(prog)} programas. Total vigente ${tot_vig/1e12:,.2f} billones; ejecutado {tot_eje/tot_vig*100:.1f} %.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
