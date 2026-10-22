"""
Cocina de datos de Código País · Compras con factura de los municipios (Monitor de Gasto Municipal).

Fuente: Presupuesto Abierto (Gobierno de Chile), "Monitor de Gasto Municipal": documentos tributarios electrónicos
(facturas) emitidos al RUT de cada municipalidad y aceptados, 2017 a la fecha. API abierta:
https://api.presupuestoabierto.gob.cl/api/v1/data/municipios

IMPORTANTE: son COMPRAS CON FACTURA, no el gasto total del municipio. No incluyen sueldos, transferencias ni lo
que compran las corporaciones municipales con RUT propio. Así se rotula en el sitio.

Qué hace:
  1. Trae, para cada año, el monto y el número de facturas por comuna.
  2. Trae los rubros económicos de los proveedores (último año completo y año en curso).
  3. Ajusta a pesos del último año completo con el IPC promedio de cada año (INE).
  4. Calcula el monto por habitante (población censada 2024, INE) y compara cada comuna con las de su tramo de
     población (mediana del tramo).
  5. Solo publica si pasan los controles.

Solo biblioteca estándar. Requiere datos/poblacion_comunas_censo2024.csv (lo genera cocina/censo_poblacion.py).
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.presupuestoabierto.gob.cl/api/v1/"
INE = "https://api-calculadora.ine.cl/ServiciosCalculadoraVariacion"
UA = {"User-Agent": "CodigoPais-cocina/1.0 (+https://codigopais.cl)"}
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "salida", "municipios")
POBLACION = os.path.join(RAIZ, "datos", "poblacion_comunas_censo2024.csv")
TRAMOS = [(0, 10000, "Menos de 10 mil habitantes"), (10000, 30000, "Entre 10 y 30 mil"),
          (30000, 100000, "Entre 30 y 100 mil"), (100000, 250000, "Entre 100 y 250 mil"),
          (250000, 10 ** 9, "Más de 250 mil")]


def http_json(url: str, intentos: int = 3, timeout: int = 180):
    ultimo = None
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            ultimo = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"No se pudo consultar {url[:140]}: {ultimo}")


def consulta(**params):
    qs = urllib.parse.urlencode({k: (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
                                 for k, v in params.items()})
    return http_json(f"{API}data/municipios?{qs}")


def ipc_variacion(m: int, a_ini: int, a_fin: int) -> float | None:
    q = urllib.parse.urlencode({"mesInicio": m, "AnioInicio": a_ini, "mesTermino": m, "AnioTermino": a_fin,
                                "valor_a_ajustar": 100})
    try:
        d = http_json(f"{INE}?{q}", intentos=2, timeout=30)
        return float(d[0]["variacion_ipc"].replace("%", "").replace(" ", "").replace(".", "").replace(",", "."))
    except Exception:  # noqa: BLE001
        return None


def deflactor(anio: int, base: int) -> float | None:
    """Factor para llevar montos de 'anio' a pesos de 'base': promedio de los 12 meses de (1 + variación IPC)."""
    if anio == base:
        return 1.0
    vs = [ipc_variacion(m, anio, base) for m in range(1, 13)]
    if any(v is None for v in vs):
        return None
    return sum(1 + v / 100 for v in vs) / 12


def tramo(pob: int) -> str:
    for a, b, n in TRAMOS:
        if a <= pob < b:
            return n
    return TRAMOS[-1][2]


def capitalizar(s: str) -> str:
    s = (s or "").strip()
    if not s or s == "*":
        return "Sin rubro informado"
    s = s.lower()
    return s[0].upper() + s[1:]


def main() -> int:
    ahora = datetime.now(timezone.utc)
    if not os.path.exists(POBLACION):
        print("ERROR: falta datos/poblacion_comunas_censo2024.csv (correr cocina/censo_poblacion.py)"); return 1
    pob = {}
    with open(POBLACION, encoding="utf-8") as fh:
        for f in csv.DictReader(fh):
            pob[f["comuna"]] = int(f["poblacion_censada"])

    periodos = [int(p["periodo"]) for p in consulta(**{"distinct": ["periodo"], "order-by": ["periodo"]})]
    actual = max(periodos)
    base = actual - 1                       # último año completo
    print(f"Años disponibles: {periodos[0]}–{actual} · año base (completo): {base}")

    # 1) Monto y facturas por comuna y año
    comunas: dict = {}
    for a in periodos:
        filas = consulta(**{"group-by": ["region", "comuna"], "select": ["nombre_region", "nombre_comuna"],
                            "where": {"periodo": a}})
        for f in filas:
            c = str(f["comuna"]).zfill(5)
            d = comunas.setdefault(c, {"codigo": c, "region": str(f["region"]).zfill(2), "nombre": f["nombre_comuna"],
                                       "nombre_region": f["nombre_region"], "anios": {}})
            d["anios"][a] = {"monto": int(round(float(f["sum"]))), "facturas": int(f["count"])}
        print(f"  {a}: {len(filas)} comunas")

    # 2) Rubros (último año completo y año en curso)
    rubros = {base: {}, actual: {}}
    for a in (base, actual):
        for f in consulta(**{"group-by": ["region", "comuna", "rubro_economico"], "where": {"periodo": a}}):
            c = str(f["comuna"]).zfill(5)
            rubros[a].setdefault(c, []).append({"rubro": capitalizar(f["rubro_economico"]),
                                                "monto": int(round(float(f["sum"]))), "facturas": int(f["count"])})

    # 3) Sitio web y portal de transparencia de cada municipio
    for c, d in comunas.items():
        try:
            info = http_json(f"{API}municipalities-page-info/{d['region']}/{c}", intentos=2, timeout=30)
            d["sitio"], d["transparencia"] = info.get("url"), info.get("url_transparencia")
        except Exception:  # noqa: BLE001
            d["sitio"] = d["transparencia"] = None

    # 4) Deflactores a pesos del año base
    defl = {a: deflactor(a, base) for a in periodos if a <= base}
    print("Deflactores:", {a: (round(v, 4) if v else None) for a, v in defl.items()})

    # 5) Indicadores por comuna
    for c, d in comunas.items():
        d["poblacion"] = pob.get(c)
        d["tramo"] = tramo(d["poblacion"]) if d["poblacion"] else None
        serie = []
        for a in periodos:
            v = d["anios"].get(a)
            if not v:
                continue
            real = int(round(v["monto"] * defl[a])) if a in defl and defl[a] else None
            serie.append({"anio": a, "monto": v["monto"], "monto_real": real, "facturas": v["facturas"],
                          "parcial": a == actual})
        d["serie"] = serie
        ub = d["anios"].get(base, {}).get("monto")
        ua = d["anios"].get(base - 1, {}).get("monto")
        d["monto_base"] = ub
        d["por_habitante"] = round(ub / d["poblacion"]) if (ub and d["poblacion"]) else None
        d["variacion_real"] = ((ub / (ua * defl[base - 1])) - 1) * 100 if (ub and ua and defl.get(base - 1)) else None
        for a in (base, actual):
            lista = sorted(rubros[a].get(c, []), key=lambda x: -x["monto"])
            d[f"rubros_{a}"] = lista
    medianas = {}
    for _, _, n in TRAMOS:
        vals = [d["por_habitante"] for d in comunas.values() if d["tramo"] == n and d["por_habitante"]]
        medianas[n] = round(statistics.median(vals)) if vals else None
    for d in comunas.values():
        m = medianas.get(d["tramo"]) if d["tramo"] else None
        d["mediana_tramo"] = m
        d["vs_mediana"] = (d["por_habitante"] / m) if (m and d["por_habitante"]) else None

    # ------------------------------------------------------------ controles
    con_base = [d for d in comunas.values() if d["monto_base"]]
    sin_pob = [d["codigo"] for d in con_base if not d["poblacion"]]
    cuadra = 0
    for d in con_base:
        s = sum(r["monto"] for r in d[f"rubros_{base}"])
        if d["monto_base"] and abs(s - d["monto_base"]) <= d["monto_base"] * 0.005:
            cuadra += 1
    tot = {a: sum(d["anios"].get(a, {}).get("monto", 0) for d in comunas.values()) for a in periodos}
    controles = [
        (f"al menos 340 comunas con datos en {base}", len(con_base) >= 340, len(con_base)),
        ("todas las comunas con datos tienen población censada", len(sin_pob) <= 2, sin_pob[:5]),
        (f"los rubros suman el total de cada comuna en {base} (±0,5 %) en al menos 99 %",
         cuadra >= 0.99 * len(con_base), f"{cuadra}/{len(con_base)}"),
        (f"total {base} entre 0,7 y 1,6 veces el de {base - 1}",
         bool(tot.get(base - 1)) and 0.7 <= tot[base] / tot[base - 1] <= 1.6,
         round(tot[base] / tot[base - 1], 3) if tot.get(base - 1) else None),
        ("ningún monto anual negativo", all(v["monto"] >= 0 for d in comunas.values() for v in d["anios"].values()), None),
        ("deflactores del IPC disponibles", all(v for v in defl.values()), {a: v for a, v in defl.items() if not v}),
    ]
    for c in controles:
        print(("OK   " if c[1] else "FALLA"), c[0], "→", c[2])
    if any(not c[1] for c in controles):
        print("ERROR: no se publica. Se mantiene el último dato bueno."); return 1

    # ------------------------------------------------------------ escritura
    meta = {"generado": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"), "anio_base": base, "anio_actual": actual,
            "unidad": "pesos chilenos", "definicion": "Compras con factura: documentos tributarios electrónicos emitidos "
            "al RUT de la municipalidad y aceptados (SII). No es el gasto total del municipio: no incluye sueldos, "
            "transferencias ni compras de corporaciones municipales con RUT propio.",
            "fuentes": {"monitor": "https://presupuestoabierto.gob.cl/municipalities",
                        "organismo": "Presupuesto Abierto · Monitor de Gasto Municipal (Gobierno de Chile)",
                        "poblacion": "Población censada, Censo 2024 (INE)",
                        "ipc": "INE, api-calculadora.ine.cl (promedio anual)",
                        "metodo": "https://github.com/AXXIomaSPA/codigopais-datos#municipios"},
            "tramos": [{"nombre": n, "mediana_por_habitante": medianas[n]} for _, _, n in TRAMOS]}
    os.makedirs(os.path.join(SALIDA, "comunas"), exist_ok=True)

    def escribir(nombre, datos):
        with open(os.path.join(SALIDA, nombre), "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=1)

    indice = []
    for c in sorted(comunas):
        d = comunas[c]
        indice.append({k: d.get(k) for k in ("codigo", "nombre", "region", "nombre_region", "poblacion", "tramo",
                                             "monto_base", "por_habitante", "variacion_real", "mediana_tramo",
                                             "vs_mediana")} | {"monto_actual": d["anios"].get(actual, {}).get("monto")})
        escribir(f"comunas/{c}.json", {**meta, **{k: v for k, v in d.items() if k != "anios"}})
    escribir("indice.json", {**meta, "comunas": indice})
    nac_r = {}
    for d in comunas.values():
        for r in d[f"rubros_{base}"]:
            nac_r[r["rubro"]] = nac_r.get(r["rubro"], 0) + r["monto"]
    escribir("resumen.json", {**meta, "totales": [{"anio": a, "monto": tot[a],
                                                   "monto_real": int(round(tot[a] * defl[a])) if a in defl else None,
                                                   "parcial": a == actual} for a in periodos],
                              "rubros": sorted(({"rubro": k, "monto": v} for k, v in nac_r.items()), key=lambda x: -x["monto"])})
    escribir("control.json", {**meta, "controles": [{"control": c[0], "ok": c[1], "valor": c[2]} for c in controles]})
    print(f"Publicado: {len(indice)} comunas. Total {base}: ${tot[base] / 1e12:,.2f} billones en compras con factura.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
