"""
Cocina de datos de Código País · Presupuesto nacional (DIPRES).

Fuente: Dirección de Presupuestos, conjuntos "Ley de Presupuestos Inicial y Vigente" y
"Ejecución Presupuestaria" del Gobierno Central (Total), publicados en datos.gob.cl con licencia CC0.

Qué hace:
  1. Busca en el catálogo de datos.gob.cl el último mes publicado del año en curso.
  2. Descarga la ley y la ejecución (nacional consolidado, por partida y por programa).
  3. Calcula el gasto, la serie mensual, el desglose por ministerio y programa, y la comparación con el
     mismo mes del año anterior (en pesos de hoy, con el IPC oficial del INE).
  4. Antes de publicar, verifica que todo cuadre. Si un control crítico falla, no escribe nada y termina
     con error (el último dato bueno se mantiene).

Definición de GASTO (alineada con la forma en que DIPRES separa gasto y financiamiento):
  - Gasto = subtítulos 21 a 26, 29, 31 y 33 (personal, bienes y servicios, prestaciones, transferencias,
    íntegros, otros, activos no financieros, inversión, transferencias de capital) + intereses y otros gastos
    financieros de la deuda (subtítulo 34, ítems 03 a 06).
  - NO es gasto (se informa aparte como "operaciones financieras"): adquisición de activos financieros (30),
    préstamos (32), amortización de la deuda (34.01 y 34.02) y deuda flotante (34.07: pago de obligaciones de
    años anteriores). El aporte fiscal (27 y 28) es un traspaso del Tesoro a los ministerios y tampoco se suma.

Otras reglas (ver FASE0-VERIFICACION-FUENTES.md):
  - Montos de origen en MILES, con punto como separador de miles; aquí se publican en PESOS.
  - Total del país: archivo NACIONAL consolidado (nunca sumar partidas). Los intereses se toman del archivo
    por programa (el subtítulo 34 no tiene transferencias internas: su suma cuadra con el nacional).
  - Por ministerio: archivo de PARTIDA (consolidado dentro de cada ministerio).
  - Por programa: montos brutos. La ley por programa trae subtotales: se usa el nivel más agregado.
    Sus códigos vienen sin cero inicial ("2" en vez de "02"): se normalizan.

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

GASTO_SUB = {"21", "22", "23", "24", "25", "26", "29", "31", "33"}
INTERESES = {"03", "04", "05", "06"}              # ítems del subtítulo 34 que son gasto
FINANCIERO = {"30": "Adquisición de activos financieros", "32": "Préstamos otorgados"}
DEUDA_FIN = {"01": "Amortización de la deuda interna", "02": "Amortización de la deuda externa",
             "07": "Deuda flotante (pago de obligaciones de años anteriores)"}
UMBRAL_COMPARABLE = 40.0                          # % de variación real que exige revisión editorial


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
    return int(round(float(x) * 1000)) if x else 0


def cod(x: str) -> str:
    """'2' → '02'. Los archivos de ley y de ejecución escriben los códigos distinto."""
    x = (x or "").strip()
    return x.zfill(2) if x.isdigit() else x


def leer_csv(b: bytes) -> list[dict]:
    """Lee el CSV y normaliza: columnas sin espacios, moneda en mayúsculas, códigos con dos dígitos
    y la columna del ítem siempre como 'Ítem' (en un archivo viene como 'Item')."""
    filas = csv.DictReader(io.StringIO(b.decode("utf-8-sig", errors="replace")), delimiter=";")
    out = []
    for f in filas:
        g = {(k or "").strip(): (v or "").strip() for k, v in f.items()}
        if "Item" in g and "Ítem" not in g:
            g["Ítem"] = g.pop("Item")
            g["Nombre Ítem"] = g.pop("Nombre Item", "")
        g["Moneda"] = g.get("Moneda", "").upper()
        for c in ("Partida", "Capítulo", "Programa", "Subtítulo", "Ítem"):
            if c in g:
                g[c] = cod(g[c])
        out.append(g)
    return out


def col(fila: dict, prefijo: str) -> str:
    """Columna que empieza con el prefijo (los nombres incluyen el mes: 'Ejecución a Agosto')."""
    for k in fila:
        if sin_tildes(k).startswith(sin_tildes(prefijo)):
            return k
    raise KeyError(prefijo)


def es_pesos(f) -> bool:
    return f["Moneda"] == "PESOS"


def sumar(filas, columna, filtro) -> int:
    return sum(miles_a_pesos(f[columna]) for f in filas if filtro(f))


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


PATRON = re.compile(r"^(Ejecuci[oó]n Presupuestaria|Ley de Presupuestos Inicial y Vigente) a (\w+) de (\d{4}) "
                    r"del Gobierno Central - Total$", re.I)


def indexar(paquetes: list[dict]) -> dict:
    """{('ejec'|'ley', año, mes): paquete}"""
    idx = {}
    for p in paquetes:
        m = PATRON.match(p.get("title", "").strip())
        if not m or sin_tildes(m.group(2)) not in MESES:
            continue
        tipo = "ejec" if m.group(1).lower().startswith("ejec") else "ley"
        idx[(tipo, int(m.group(3)), MESES.index(sin_tildes(m.group(2))) + 1)] = p
    return idx


_cache: dict = {}


def bajar(paquete: dict, nivel: str) -> tuple[list[dict], str]:
    for r in paquete.get("resources", []):
        if sin_tildes(r.get("name", "")) == sin_tildes(f"A nivel {nivel}"):
            if r["url"] not in _cache:
                _cache[r["url"]] = leer_csv(http(r["url"]))
            return _cache[r["url"]], r["url"]
    raise KeyError(f"{paquete['title']}: falta el recurso 'A nivel {nivel}'")


def url_paquete(p: dict) -> str:
    return f"https://datos.gob.cl/dataset/{p['name']}"


# ---------------------------------------------------------------- IPC (INE)
def ipc_12m(anio: int, mes: int) -> float | None:
    """Variación oficial del IPC entre el mismo mes del año anterior y este (INE), en %."""
    q = urllib.parse.urlencode({"mesInicio": mes, "AnioInicio": anio - 1, "mesTermino": mes,
                                "AnioTermino": anio, "valor_a_ajustar": 100})
    try:
        d = json.loads(http(f"{INE}?{q}", intentos=2, timeout=30))
        return float(d[0]["variacion_ipc"].replace("%", "").replace(" ", "").replace(".", "").replace(",", "."))
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- reglas de gasto
def gasto_sub(f) -> bool:
    return es_pesos(f) and f["Subtítulo"] in GASTO_SUB


def nivel_ley(f) -> int:
    """0 = fila del subtítulo, 1 = ítem, 2 = asignación (la ley por programa trae los tres)."""
    return 0 if not f.get("Ítem") else (1 if not f.get("Asignación") else 2)


def es_interes_ejec(f) -> bool:
    return es_pesos(f) and f["Subtítulo"] == "34" and f.get("Ítem") in INTERESES


def es_interes_ley(f) -> bool:
    return es_interes_ejec(f) and nivel_ley(f) == 1


def deuda_fin(filas, columna, ley: bool) -> dict:
    out = {}
    for it in DEUDA_FIN:
        out[it] = sumar(filas, columna, lambda f, it=it: es_pesos(f) and f["Subtítulo"] == "34" and f.get("Ítem") == it
                        and (nivel_ley(f) == 1 if ley else True))
    return out


def gasto_de_mes(paquete_ejec: dict) -> dict:
    """Gasto acumulado y del mes (nacional) para un mes cualquiera."""
    nac, _ = bajar(paquete_ejec, "Nacional")
    prg, _ = bajar(paquete_ejec, "Programa")
    c_a, c_m = col(nac[0], "Ejecución a"), col(nac[0], "Ejecución de")
    p_a, p_m = col(prg[0], "Ejecución a"), col(prg[0], "Ejecución de")
    return {"acumulado": sumar(nac, c_a, gasto_sub) + sumar(prg, p_a, es_interes_ejec),
            "mes": sumar(nac, c_m, gasto_sub) + sumar(prg, p_m, es_interes_ejec)}


def programas(lg: list[dict], c_lgv: str, eg: list[dict], c_egp: str) -> dict:
    """Ley vigente y ejecución por programa (brutos), solo con la definición de gasto."""
    prog: dict = {}

    def ficha(f):
        key = (f["Partida"], f["Capítulo"], f["Programa"])
        return prog.setdefault(key, {"capitulo": key[1], "nombre_capitulo": f["Nombre Capítulo"],
                                     "programa": key[2], "nombre_programa": f["Nombre Programa"],
                                     "vigente": 0, "ejecutado": 0})

    grupos: dict = {}
    for f in lg:
        if gasto_sub(f):
            grupos.setdefault((f["Partida"], f["Capítulo"], f["Programa"], f["Subtítulo"]), {}) \
                  .setdefault(nivel_ley(f), []).append(f)
        elif es_interes_ley(f):
            ficha(f)["vigente"] += miles_a_pesos(f[c_lgv])
    for niveles in grupos.values():
        filas = niveles[min(niveles)]
        ficha(filas[0])["vigente"] += sum(miles_a_pesos(f[c_lgv]) for f in filas)
    for f in eg:
        if gasto_sub(f) or es_interes_ejec(f):
            ficha(f)["ejecutado"] += miles_a_pesos(f[c_egp])
    return prog


def titulo(s: str) -> str:
    t = s.title()
    for a, b in ((" De ", " de "), (" Del ", " del "), (" Y ", " y "), (" La ", " la "), (" Las ", " las "),
                 (" Los ", " los "), (" E ", " e "), (" Para ", " para "), (" Por ", " por "), (" En ", " en ")):
        t = t.replace(a, b)
    return t


# ---------------------------------------------------------------- principal
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
    print(f"Último mes publicado: {MESES[mes - 1]} de {anio} (publicado {pe.get('metadata_modified', '')[:10]})")

    en, url_en = bajar(pe, "Nacional"); ln, url_ln = bajar(pl, "Nacional")
    ep, url_ep = bajar(pe, "Partida"); lp, url_lp = bajar(pl, "Partida")
    eg, url_eg = bajar(pe, "Programa"); lg, url_lg = bajar(pl, "Programa")
    c_en = col(en[0], "Ejecución a")
    c_li, c_lv = col(ln[0], "Monto Ley Inicial"), col(ln[0], "Monto Ley Vigente")
    c_ep = col(ep[0], "Ejecución a")
    c_lpi, c_lpv = col(lp[0], "Monto Ley Inicial"), col(lp[0], "Monto Ley Vigente")
    c_eg = col(eg[0], "Ejecución a")
    c_lgi, c_lgv = col(lg[0], "Monto Ley Inicial"), col(lg[0], "Monto Ley Vigente")

    # --- totales nacionales
    int_ini, int_vig, int_eje = sumar(lg, c_lgi, es_interes_ley), sumar(lg, c_lgv, es_interes_ley), sumar(eg, c_eg, es_interes_ejec)
    tot_ini = sumar(ln, c_li, gasto_sub) + int_ini
    tot_vig = sumar(ln, c_lv, gasto_sub) + int_vig
    tot_eje = sumar(en, c_en, gasto_sub) + int_eje

    # --- por tipo de gasto
    nombres_sub = {f["Subtítulo"]: f["Nombre Subtítulo"] for f in ln + en if gasto_sub(f)}
    por_tipo = []
    for s in sorted(nombres_sub):
        v = sumar(ln, c_lv, lambda f, s=s: gasto_sub(f) and f["Subtítulo"] == s)
        e = sumar(en, c_en, lambda f, s=s: gasto_sub(f) and f["Subtítulo"] == s)
        if v or e:
            por_tipo.append({"codigo": s, "nombre": nombres_sub[s].capitalize(), "vigente": v, "ejecutado": e})
    por_tipo.append({"codigo": "34.int", "nombre": "Intereses de la deuda", "vigente": int_vig, "ejecutado": int_eje})
    por_tipo.sort(key=lambda x: -x["vigente"])

    # --- operaciones financieras (aparte; no son gasto)
    financiero = []
    for s, nom in FINANCIERO.items():
        financiero.append({"codigo": s, "nombre": nom,
                           "vigente": sumar(ln, c_lv, lambda f, s=s: es_pesos(f) and f["Subtítulo"] == s),
                           "ejecutado": sumar(en, c_en, lambda f, s=s: es_pesos(f) and f["Subtítulo"] == s)})
    dv, de = deuda_fin(lg, c_lgv, True), deuda_fin(eg, c_eg, False)
    for it, nom in DEUDA_FIN.items():
        financiero.append({"codigo": f"34.{it}", "nombre": nom, "vigente": dv[it], "ejecutado": de[it]})

    # --- serie mensual
    mensual = []
    for m in range(1, mes + 1):
        p = idx.get(("ejec", anio, m))
        g = gasto_de_mes(p) if p else {"mes": None, "acumulado": None}
        mensual.append({"mes": m, "nombre": MESES[m - 1], "ejecutado_mes": g["mes"], "acumulado": g["acumulado"]})

    # --- comparación con el mismo mes del año anterior
    comp, ant_part = None, {}
    pa = idx.get(("ejec", anio - 1, mes))
    ipc = ipc_12m(anio, mes) if pa else None
    if pa:
        eje_ant = gasto_de_mes(pa)["acumulado"]
        ap, _ = bajar(pa, "Partida"); apg, _ = bajar(pa, "Programa")
        c_ap, c_apg = col(ap[0], "Ejecución a"), col(apg[0], "Ejecución a")
        for f in ap:
            if gasto_sub(f):
                ant_part[f["Partida"]] = ant_part.get(f["Partida"], 0) + miles_a_pesos(f[c_ap])
        for f in apg:
            if es_interes_ejec(f):
                ant_part[f["Partida"]] = ant_part.get(f["Partida"], 0) + miles_a_pesos(f[c_apg])
        comp = {"anio_anterior": anio - 1, "ejecutado_anterior": eje_ant,
                "variacion_nominal": (tot_eje / eje_ant - 1) * 100 if eje_ant else None,
                "ipc_12_meses": ipc,
                "variacion_real": ((tot_eje / (eje_ant * (1 + ipc / 100))) - 1) * 100 if (eje_ant and ipc is not None) else None,
                "fuente_anterior": url_paquete(pa)}

    # --- ministerios
    nombres = {f["Partida"]: f["Nombre Partida"] for f in lp + ep}
    int_part_v, int_part_i, int_part_e = {}, {}, {}
    for f in lg:
        if es_interes_ley(f):
            int_part_v[f["Partida"]] = int_part_v.get(f["Partida"], 0) + miles_a_pesos(f[c_lgv])
            int_part_i[f["Partida"]] = int_part_i.get(f["Partida"], 0) + miles_a_pesos(f[c_lgi])
    for f in eg:
        if es_interes_ejec(f):
            int_part_e[f["Partida"]] = int_part_e.get(f["Partida"], 0) + miles_a_pesos(f[c_eg])
    ministerios = []
    for c in sorted(nombres):
        ini = sumar(lp, c_lpi, lambda f, c=c: gasto_sub(f) and f["Partida"] == c) + int_part_i.get(c, 0)
        vig = sumar(lp, c_lpv, lambda f, c=c: gasto_sub(f) and f["Partida"] == c) + int_part_v.get(c, 0)
        eje = sumar(ep, c_ep, lambda f, c=c: gasto_sub(f) and f["Partida"] == c) + int_part_e.get(c, 0)
        if not (vig or eje):
            continue
        ant = ant_part.get(c)
        real = ((eje / (ant * (1 + ipc / 100))) - 1) * 100 if (ant and ant > 0 and ipc is not None) else None
        comparable = real is not None and abs(real) <= UMBRAL_COMPARABLE
        ministerios.append({
            "codigo": c, "nombre": titulo(nombres[c]),
            "ley_inicial": ini, "vigente": vig, "ejecutado": eje,
            "porcentaje": eje / vig * 100 if vig else None,
            "ejecutado_anterior": ant, "variacion_real": real, "comparable": comparable,
            "aviso": None if comparable or real is None else
            "Variación mayor a ±40 %: puede deberse a cambios de estructura (un servicio nuevo, traspasado o "
            "fusionado). Requiere revisión editorial antes de mostrarse.",
        })
    ministerios.sort(key=lambda x: -x["vigente"])

    prog = programas(lg, c_lgv, eg, c_eg)

    # ---------------------------------------------------------------- controles
    suma_min = sum(m["vigente"] for m in ministerios)
    razon = suma_min / tot_vig if tot_vig else 0
    con_ley = [p for p in prog.values() if p["vigente"] > 0]
    coinciden = sum(1 for p in con_ley if p["ejecutado"] != 0) / len(con_ley) if con_ley else 0
    fuera_rango = []
    for m in ministerios:
        bruto = sum(p["vigente"] for k, p in prog.items() if k[0] == m["codigo"])
        if m["vigente"] and not (0.98 <= bruto / m["vigente"] <= 3.5):
            fuera_rango.append(f'{m["codigo"]}:{bruto / m["vigente"]:.2f}')
    controles = [
        ("gasto vigente plausible (entre $50 y $300 billones)", 50e12 <= tot_vig <= 300e12, tot_vig),
        ("gasto ejecutado entre 0 % y 105 % del vigente", 0 <= tot_eje <= tot_vig * 1.05,
         round(tot_eje / tot_vig * 100, 2) if tot_vig else None),
        ("ministerios suman entre 1,00 y 1,08 veces el total consolidado", 1.0 <= razon <= 1.08, round(razon, 4)),
        ("serie mensual: acumulado del último mes = total ejecutado", mensual[-1]["acumulado"] == tot_eje,
         mensual[-1]["acumulado"]),
        ("ningún ministerio supera el 120 % de ejecución", all((m["porcentaje"] or 0) <= 120 for m in ministerios),
         [m["codigo"] for m in ministerios if (m["porcentaje"] or 0) > 120]),
        ("hay al menos 20 ministerios", len(ministerios) >= 20, len(ministerios)),
        ("hay al menos 300 programas", len(prog) >= 300, len(prog)),
        ("al menos 90 % de los programas con presupuesto tiene ejecución (códigos coinciden)", coinciden >= 0.90,
         round(coinciden, 3)),
        ("programas de cada ministerio suman entre 0,98 y 3,5 veces su total (Salud ronda 2,5 por FONASA)",
         not fuera_rango, fuera_rango[:5]),
    ]
    for c in controles:
        print(("OK   " if c[1] else "FALLA"), c[0], "→", c[2])
    if any(not c[1] for c in controles):
        print("ERROR: no se publica. Se mantiene el último dato bueno."); return 1

    # ---------------------------------------------------------------- escritura
    fuentes = {
        "organismo": "Dirección de Presupuestos (DIPRES)", "licencia": "CC0 1.0 (dominio público)",
        "ejecucion": url_paquete(pe), "ley": url_paquete(pl),
        "archivos": {"ejecucion_nacional": url_en, "ley_nacional": url_ln, "ejecucion_partida": url_ep,
                     "ley_partida": url_lp, "ejecucion_programa": url_eg, "ley_programa": url_lg},
        "ipc": "Instituto Nacional de Estadísticas (INE), api-calculadora.ine.cl",
        "metodo": "https://github.com/AXXIomaSPA/codigopais-datos#reglas-de-cálculo",
    }
    meta = {"anio": anio, "mes": mes, "mes_nombre": MESES[mes - 1],
            "publicado_fuente": pe.get("metadata_modified", "")[:10],
            "generado": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"), "unidad": "pesos chilenos", "fuentes": fuentes}
    os.makedirs(os.path.join(SALIDA, "programas"), exist_ok=True)

    def escribir(nombre, datos):
        with open(os.path.join(SALIDA, nombre), "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=1)

    definicion = ("Gasto del Gobierno Central consolidado: personal, bienes y servicios, prestaciones, transferencias, "
                  "inversión e intereses de la deuda. No incluye operaciones financieras (activos financieros, "
                  "préstamos, amortización de la deuda ni deuda flotante), que se informan aparte.")
    escribir("resumen.json", {**meta, "definicion": definicion,
                              "totales": {"ley_inicial": tot_ini, "vigente": tot_vig, "ejecutado": tot_eje,
                                          "porcentaje": tot_eje / tot_vig * 100},
                              "por_tipo": por_tipo, "operaciones_financieras": financiero,
                              "mensual": mensual, "comparacion": comp})
    escribir("ministerios.json", {**meta, "definicion": definicion, "ministerios": ministerios,
                                  "nota": "Cada ministerio incluye las transferencias que hace a otros organismos "
                                          "públicos; por eso la suma supera en torno a 3 % el total del país."})
    for c in sorted({k[0] for k in prog}):
        lista = sorted((v for k, v in prog.items() if k[0] == c), key=lambda x: -x["vigente"])
        escribir(f"programas/{c}.json", {**meta, "partida": c, "nombre": titulo(nombres.get(c, "")), "programas": lista,
                                         "nota": "Montos brutos: incluyen transferencias entre servicios del mismo ministerio."})
    escribir("control.json", {**meta, "controles": [{"control": c[0], "ok": c[1], "valor": c[2]} for c in controles]})
    print(f"Publicado: {len(ministerios)} ministerios, {len(prog)} programas. Gasto vigente "
          f"${tot_vig / 1e12:,.2f} billones; ejecutado {tot_eje / tot_vig * 100:.1f} %.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
