# Voz vecinal · método público

Versión 1.2 · 22-10-2026

**Voz vecinal** es la sección de Código País donde las personas aportan, de forma voluntaria, lo que viven en su comuna: opiniones, experiencias, reclamos, propuestas y fotos. Esos aportes se ponen frente al gasto público.

Esta carpeta publica las reglas con que se hace ese cruce, para que cualquiera pueda revisarlas, discutirlas y corregirlas.

| Archivo | Qué contiene |
|---|---|
| `temas.json` | Los 15 temas y sus subtemas, quién es responsable de cada subtema y los 5 tipos de aporte |
| `preguntas.json` | Las preguntas cerradas: las comunes a cada tipo de aporte y las propias de cada tema |
| `equivalencias.json` | La tabla que une cada tema con el gasto en tres fuentes: órdenes de compra (ChileCompra), compras con factura de los municipios (Monitor de Gasto Municipal) y presupuesto del Estado (DIPRES) |
| `generar.py` | El origen único de los tres archivos anteriores, para que no se contradigan |
| `probar_equivalencias.py` | La prueba de la tabla sobre un mes real de compras municipales |

## Los temas

Son 15:
1. Salud
2. Educación
3. Basura y reciclaje
4. Calles y veredas
5. Plazas y áreas verdes
6. Alumbrado
7. Seguridad
8. Agua
9. Transporte
10. Vivienda y barrio
11. Apoyo social
12. Cultura y deporte
13. Animales
14. Atención municipal
15. Otro tema

**Cada subtema dice quién es responsable.** Ejemplos:
- un consultorio (CESFAM) es del municipio, pero un hospital es del Servicio de Salud;
- las micros dependen del Ministerio de Transportes;
- el agua en la ciudad está a cargo de la empresa sanitaria.

**Solo se compara la necesidad con el gasto municipal cuando el municipio es responsable**, o cuando la responsabilidad es compartida. Lo demás se muestra con el nombre de quien corresponde, sin comparación. Comparar un reclamo por un hospital con el gasto del municipio sería injusto.

## Las preguntas

Un aporte puede ser de uno o varios tipos: opinión, experiencia, reclamo, participación y fotos.

- **Preguntas comunes:** cada tipo agrega las suyas. Por ejemplo, un reclamo pregunta desde cuándo pasa, a quién afecta, si se reportó y si respondieron.
- **Preguntas del tema:** cada tema agrega una o dos propias. Por ejemplo, en salud: cuánto esperaste por la atención y si conseguiste lo que necesitabas.

Casi todo se responde con opciones cerradas, para que los aportes se puedan **comparar entre comunas y en el tiempo**. El relato libre es opcional.

## La voz: cómo le hablamos a la gente

Levantamos datos, pero la persona tiene que sentir que está en un lugar donde la escuchan, no llenando un formulario.

- **Primero el para qué:** antes de preguntar, explicamos que lo que cuente se suma a lo que viven otros vecinos y se pone al lado del gasto real del municipio, con cifras de fuentes oficiales.
- **Segunda persona y lenguaje de barrio:** "¿Cuánto tuviste que esperar?" en vez de "Tiempo de espera"; "¿Qué nota le pondrías? Del 1 al 7" en vez de una escala técnica.
- **Respuestas que no culpan:** "Todavía no", "No sabía dónde avisar", "Sentí que no serviría", "Prefiero no decir".
- **Todo es opcional menos lo mínimo:** se responde solo lo que se quiere, y se dice así.
- **Explicar cada cuidado:** si tachamos datos o no publicamos algo, decimos por qué ("para cuidarte", "para cuidar este espacio").
- **Agradecer y cerrar el ciclo:** al terminar, contamos qué pasará con su aporte y cómo seguirlo.

## Preguntas que se adaptan (versión 1.2)

Las preguntas de cada aporte se arman en este orden:
1. **La pregunta del subtema** (48 de los 60 subtemas tienen una propia). Por ejemplo, en CESFAM: "¿Qué necesitabas?". Si mide lo mismo que la del tema, la reemplaza.
2. **Las preguntas del tema.**
3. **Los bloques de lo que la persona quiere compartir** (opinión, algo que viví, un problema, una idea, fotos), sin repetir.

Si las preguntas base pasan de 8, se omiten primero "¿Cuándo la tomaste?" y después "¿Cuándo te pasó?".

**Seguimientos:** una pregunta corta aparece justo debajo de la respuesta que la activa y no cuenta para el tope. Ejemplos:
- con nota del 1 al 4: "¿Qué debería mejorar primero?";
- si todavía no avisó: "¿Qué te frenó?";
- si no le han respondido: "¿Hace cuánto avisaste?".

Están en `preguntas.json`, en las claves `por_subtema`, `seguimientos`, `tope_base` y `omitir_primero`.

Nunca se pregunta por diagnósticos ni datos que identifiquen a la persona.

## La tabla de equivalencias

Para cada tema y fuente, la tabla indica la **precisión**:
- **directa:** la fuente dice para qué se gastó;
- **aproximada:** se deduce del proveedor o de una categoría amplia;
- **sin dato:** hoy no hay fuente.

Cuando no hay dato, Código País lo dice: "lo que aún no se puede medir".

### Cómo se clasifica cada compra (ChileCompra)
Cada ítem de una orden de compra municipal pasa por cuatro pasos. En cada paso se recorren los temas en orden y gana el primero que calza, así que ningún peso se cuenta dos veces.

1. **Unidad compradora.** Si compra el Departamento de Salud, un CESFAM o una escuela, el gasto es de salud o de educación, sea lo que sea que se compró.
2. **Palabras en el nombre de la orden.** Para las obras, la categoría no dice qué se construye y el nombre sí: "plaza", "multicancha", "pavimentación", "alumbrado". Se buscan sin tildes y en mayúsculas.
3. **Categoría del producto,** con los nombres exactos de los datos abiertos de ChileCompra.
4. **Funcionamiento general.** Vehículos, combustible, oficina, limpieza de edificios o seguros son gasto real, pero no corresponden a un tema vecinal y no se comparan con necesidades.

Lo que no calza queda como **sin clasificar** y se informa su porcentaje. Nunca se reparte a la fuerza.

### Prueba con un mes real (agosto de 2026)
Órdenes de compra de las municipalidades, ítems en pesos ($218.900 millones):

| Grupo | % del gasto |
|---|---|
| Asignado a un tema | **54,0 %** (salud 12,1 · basura 11,7 · educación 8,1 · áreas verdes 6,4 · seguridad 5,5 · calles 2,3 · alumbrado 1,9 · transporte 1,5 · apoyo social 1,4 · cultura y deporte 1,3 · agua 0,7 · vivienda 0,6 · animales 0,4) |
| Funcionamiento general | 22,5 % |
| Sin clasificar | 23,5 % (10,5 % son obras cuyo nombre no dice qué se construye; 4,7 % viene sin categoría desde la fuente) |

Todos los nombres de categoría de la tabla existen en los datos de ChileCompra, y todos los rubros del Monitor de Gasto Municipal calzan con sus nombres en la fuente, escritos sin tildes como vienen.

### Límites conocidos
- **El Monitor de Gasto Municipal clasifica por el giro del proveedor, no por el destino.** Un remedio comprado a una distribuidora queda como "comercio". Por eso, para los temas, la fuente principal es ChileCompra.
- **Educación:** donde las escuelas ya pasaron a un Servicio Local de Educación Pública, ese gasto deja de ser municipal.
- **Calles y veredas:** depende de las palabras del nombre de la orden. Es una precisión aproximada.
- **Los sueldos** (médicos, profesores, guardias municipales) no pasan por órdenes de compra ni facturas.

## Cómo corregir la tabla
Se edita `generar.py`, se ejecuta `python3 metodo/voz-vecinal/generar.py` y se prueba con `probar_equivalencias.py` sobre un mes real. Cada cambio sube la versión.

Licencia: CC BY 4.0, como los demás datos de este repositorio.
