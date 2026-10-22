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
- **Gasto** = subtítulos 21 a 34 de la clasificación presupuestaria. Incluye servicio de la deuda y operaciones financieras. El 35, saldo final de caja, no es gasto.
- El **total del país** se toma del archivo nacional consolidado. Nunca se suman las partidas: el Tesoro Público traspasa el "aporte fiscal" a los ministerios y se contaría dos veces.
- Por **ministerio** se usa el archivo de partida, ya consolidado dentro de cada ministerio. Para el Tesoro Público se excluyen los subtítulos 27 y 28 (aporte fiscal).
- Cada ministerio incluye lo que transfiere a otros organismos. Por eso la suma de ministerios supera en torno a 3 % el total del país.
- El detalle por **programa** es bruto: incluye transferencias entre servicios del mismo ministerio.
- Las comparaciones con el año anterior usan el mismo mes y se expresan en pesos de hoy, con la variación oficial del IPC en 12 meses.

## Controles de calidad

Antes de publicar, la cocina verifica que:

- el total sea plausible;
- la ejecución no supere el presupuesto;
- la suma de ministerios esté entre 1,00 y 1,08 veces el total consolidado;
- la serie mensual cuadre;
- haya al menos 20 ministerios y 300 programas.

**Si un control falla, no se publica nada** y se mantiene el último dato bueno. El resultado de cada control queda en `salida/gasto/control.json`.

## Licencia

Código: MIT. Datos procesados en `salida/`: CC BY 4.0, citando a Código País y a la fuente original.
