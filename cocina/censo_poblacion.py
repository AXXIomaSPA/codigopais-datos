"""
Población censada por comuna · Censo 2024 (INE). Se corre una sola vez (la población del censo no cambia).

Descarga la base de microdatos del INE (zip con Parquet), cuenta las personas por código de comuna y escribe
datos/poblacion_comunas_censo2024.csv. Controles: el total debe ser exactamente 18.480.432 y la suma de cada región
debe coincidir con la población censada regional publicada por el INE.

Requiere pyarrow (se instala en el flujo de GitHub Actions).
"""
import collections
import csv
import io
import os
import sys
import urllib.request
import zipfile

import pyarrow.parquet as pq

URL = "https://storage.googleapis.com/bktdescargascenso2024/viv_hog_per_censo2024.zip"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "datos", "poblacion_comunas_censo2024.csv")
TOTAL = 18480432
REGIONES = {  # población censada regional, Censo 2024 (INE). Clave: código de región (2 dígitos).
    "15": 244569, "01": 369806, "02": 635416, "03": 299180, "04": 832864, "05": 1896053, "13": 7400741,
    "06": 987228, "07": 1123008, "16": 512289, "08": 1613059, "09": 1010423, "14": 398230, "10": 890284,
    "11": 100745, "12": 166537,
}


def main() -> int:
    print("Descargando microdatos del Censo 2024…")
    zpath = "/tmp/censo2024.zip"
    urllib.request.urlretrieve(URL, zpath)
    z = zipfile.ZipFile(zpath)
    nombres = [n for n in z.namelist() if n.lower().endswith(".parquet") and "persona" in n.lower()]
    print("Archivos:", z.namelist())
    if not nombres:
        print("ERROR: no se encontró el Parquet de personas"); return 1
    with z.open(nombres[0]) as fh:
        tabla = pq.read_table(io.BytesIO(fh.read()), columns=["comuna"])
    import pyarrow.compute as pc
    conteo = collections.Counter()
    for fila in pc.value_counts(tabla.column("comuna")).to_pylist():  # [{'values': 13201, 'counts': n}, ...]
        if fila["values"] is not None:
            conteo[str(int(fila["values"])).zfill(5)] += int(fila["counts"])
    total = sum(conteo.values())
    por_region = collections.Counter()
    for c, n in conteo.items():
        por_region[c[:2]] += n
    print(f"Comunas: {len(conteo)} · total: {total:,}")
    errores = []
    if total != TOTAL:
        errores.append(f"total {total} distinto de {TOTAL}")
    for r, n in REGIONES.items():
        if por_region.get(r) != n:
            errores.append(f"región {r}: {por_region.get(r)} distinto de {n}")
    if errores:
        print("ERROR:", "; ".join(errores)); return 1
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["comuna", "region", "poblacion_censada"])
        for c in sorted(conteo):
            w.writerow([c, c[:2], conteo[c]])
    print("OK: total y 16 regiones cuadran con el INE. Escrito", SALIDA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
