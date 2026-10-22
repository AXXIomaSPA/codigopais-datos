"""
Prueba de la tabla de equivalencias de Voz vecinal sobre un mes real de órdenes de compra municipales (ChileCompra).

Uso: python3 metodo/voz-vecinal/probar_equivalencias.py oc-AAAA-M.zip metodo/voz-vecinal/equivalencias.json
El zip se descarga de https://transparenciachc.blob.core.windows.net/oc-da/AAAA-M.zip (datos abiertos, sin clave).
Muestra qué parte del gasto municipal del mes cae en cada tema, en funcionamiento general o sin clasificar.
La función clasificar() es la que usará la cocina de compras (fase 3).
"""
import zipfile, io, csv, sys, collections, json, unicodedata
EQ=json.load(open(sys.argv[2])); TEMAS=list(EQ["temas"])
def sin_tildes(t): return "".join(c for c in unicodedata.normalize("NFD", t.upper()) if unicodedata.category(c)!="Mn")
def num(x):
    try: return float((x or "0").replace(",", "."))
    except: return 0.0
def calza(rg, row, uni, nom):
    if "unidad" in rg and not any(sin_tildes(u) in uni for u in rg["unidad"]): return False
    if "excepto_unidad" in rg and any(sin_tildes(u) in uni for u in rg["excepto_unidad"]): return False
    if "n1" in rg:
        n1=rg["n1"] if isinstance(rg["n1"],list) else [rg["n1"]]
        if row["RubroN1"].strip() not in n1: return False
    if "n2" in rg and row["RubroN2"].strip() not in rg["n2"]: return False
    if "n3" in rg and row["RubroN3"].strip() not in rg["n3"]: return False
    if "palabras" in rg and not any(sin_tildes(p) in nom for p in rg["palabras"]): return False
    return True
def clasificar(row):
    uni=" "+sin_tildes(row["UnidadCompra"])+" "; nom=" "+sin_tildes(row["Nombre"]+" "+row["NombreroductoGenerico"])+" "
    for paso in ("unidad","palabras","categoria"):
        for t in TEMAS:
            for rg in EQ["temas"][t]["chilecompra"]["reglas"]:
                tipo="unidad" if "unidad" in rg else "palabras" if "palabras" in rg else "categoria"
                if tipo==paso and calza(rg,row,uni,nom): return t
    if any(calza(rg,row,uni,nom) for rg in EQ["funcionamiento_general"]): return "(funcionamiento general)"
    return "(sin clasificar)"
if __name__=="__main__":
    z=zipfile.ZipFile(sys.argv[1]); f=io.TextIOWrapper(z.open(z.infolist()[0]), encoding="latin-1", newline="")
    tot=0; por=collections.Counter(); sin=collections.Counter()
    for row in csv.DictReader(f, delimiter=";"):
        if row["sector"]!="Municipalidades" or row["monedaItem"]!="CLP": continue
        m=num(row["totalLineaNeto"]); tot+=m; t=clasificar(row); por[t]+=m
        if t=="(sin clasificar)": sin[row["RubroN1"].strip()]+=m
    for t,m in por.most_common(): print(f"{m/tot*100:5.1f}%  {t}")
    print("\nsin clasificar, por categoría:"); [print(f"   {m/tot*100:4.1f}% {k}") for k,m in sin.most_common(8)]
