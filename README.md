# codigopais-datos

**Cocina de datos de [Código País](https://codigopais.cl).** Aquí se descargan, verifican y procesan los datos públicos que usa la sección *¿En qué se gasta la plata?*. El método es abierto: cualquiera puede revisar cómo se calcula cada cifra.

## Qué hay

| Carpeta | Contenido |
|---|---|
| `cocina/` | Scripts que descargan y procesan cada fuente (solo biblioteca estándar de Python). |
| `salida/gasto/` | Resultados en JSON que lee el sitio: `resumen.json`, `ministerios.json`, `programas/<partida>.json` y `control.json` (resultado de los controles de calidad). |
| `.github/workflows/` | Automatización diaria (GitHub Actions). |

## Fuentes

| Dato | Fuente | Licencia |
|---|---|---|
| Ley de Presupuestos y ejecución del Gobierno Central | Dirección de Presupuestos (DIPRES), en [datos.gob.cl](https://datos.gob.cl/organization/direccion_de_presupuestos) | CC0 1.0 |
| IPC (para comparar en pesos de hoy) | Instituto Nacional de Estadísticas (INE) | Datos públicos |

Próximamente: gasto municipal (Presupuesto Abierto), compras públicas (ChileCompra) y población por comuna (Censo 2024).

## Reglas de cálculo

- Los archivos de origen vienen en **miles de pesos**; aquí se publican en **pesos**.
- **Gasto** = personal (21), bienes y servicios (22), prestaciones de seguridad social (23), transferencias corrientes (24), íntegros (25), otros gastos corrientes (26), activos no financieros (29), iniciativas de inversión (31), transferencias de capital (33) e **intereses de la deuda** (34, ítems 03 a 06).
- **No es gasto**, y se informa aparte como *operaciones financieras*: adquisición de activos financieros (30), préstamos (32), amortización de la deuda (34.01 y 34.02) y deuda flotante (34.07, pago de obligaciones de años anteriores). Mezclarlas con el gasto infla la cifra. Por ejemplo, en 2026 el Tesoro invirtió $5 billones en activos financieros con un presupuesto de $0,3 billones.
- El aporte fiscal (27 y 28) es un traspaso del Tesoro a los ministerios y no se suma. El 35, saldo final de caja, tampoco es gasto.
- El **total del país** se toma del archivo nacional consolidado. Nunca se suman las partidas: el Tesoro Público traspasa el "aporte fiscal" a los ministerios y se contaría dos veces.
- Por **ministerio** se usa el archivo de partida, ya consolidado dentro de cada ministerio. Para el Tesoro Público se excluyen los subtítulos 27 y 28 (aporte fiscal).
- Cada ministerio incluye lo que transfiere a otros organismos. Por eso la suma de ministerios supera en torno a 3 % el total del país.
- El detalle por **programa** es bruto: incluye transferencias entre servicios del mismo ministerio.
- El archivo de la ley por programa trae subtotales por subtítulo y además el desglose por ítem. Se usa solo el nivel más agregado, para no sumar dos veces. Sus códigos vienen sin cero inicial ("2" en vez de "02") y se normalizan.
- Las comparaciones con el año anterior usan el mismo mes y se expresan en pesos de hoy, con la variación oficial del IPC en 12 meses.
- Si la variación real de un ministerio supera ±40 %, se marca como *no comparable* (`comparable: false`) y requiere revisión editorial antes de mostrarse: suele deberse a servicios nuevos, traspasados o fusionados. Por ejemplo, el Ministerio de Seguridad Pública se creó en 2025.

## Controles de calidad

Antes de publicar, la cocina verifica que:

- el total sea plausible;
- la ejecución no supere el presupuesto;
- la suma de ministerios esté entre 1,00 y 1,08 veces el total consolidado;
- la serie mensual cuadre;
- ningún ministerio supere el 120 % de ejecución;
- haya al menos 20 ministerios y 300 programas;
- al menos el 90 % de los programas con presupuesto tenga ejecución (los códigos de ley y ejecución coinciden);
- los programas de cada ministerio sumen entre 0,98 y 3,5 veces su total. Salud ronda 2,5, porque FONASA transfiere a los Servicios de Salud.

**Si un control falla, no se publica nada** y se mantiene el último dato bueno. El resultado de cada control queda en `salida/gasto/control.json`.

## Licencia

Código: MIT. Datos procesados en `salida/`: CC BY 4.0, citando a Código País y a la fuente original.
