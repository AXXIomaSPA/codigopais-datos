"""
Voz vecinal · método público (etapa A).

Genera los tres archivos del método a partir de este único origen, para que no se contradigan:
  temas.json          taxonomía de temas y subtemas, con quién es responsable de cada subtema
  preguntas.json      preguntas cerradas: comunes por tipo de aporte y propias de cada tema
  equivalencias.json  tabla tema ↔ gasto (ChileCompra, Monitor de Gasto Municipal y Presupuesto/DIPRES)

Uso: python3 metodo/voz-vecinal/generar.py
"""
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
VERSION = "1.2 · 22-10-2026"

# ---------------------------------------------------------------- responsables
# Quién decide y paga cada cosa. Solo se compara con el gasto municipal lo que es responsabilidad del municipio.
RESPONSABLES = {
    "municipio": "Municipalidad",
    "servicio_salud": "Servicio de Salud (hospitales, Ministerio de Salud)",
    "slep": "Servicio Local de Educación Pública (donde ya se traspasaron las escuelas)",
    "serviu": "SERVIU y Ministerio de Vivienda",
    "mop": "Ministerio de Obras Públicas",
    "sanitaria": "Empresa sanitaria (agua y alcantarillado urbano)",
    "electrica": "Empresa distribuidora eléctrica",
    "policias": "Carabineros y PDI",
    "mtt": "Ministerio de Transportes",
    "gore": "Gobierno Regional",
    "compartido": "Compartido entre varias instituciones",
}

# ---------------------------------------------------------------- tipos de aporte y preguntas comunes
TIPOS = [
    {"id": "opinion", "nombre": "Mi opinión", "para": "Decirnos qué te parece un servicio o una decisión", "icono": "estrella"},
    {"id": "experiencia", "nombre": "Algo que viví", "para": "Contarnos lo que te pasó", "icono": "conversacion"},
    {"id": "reclamo", "nombre": "Un problema", "para": "Avisarnos de algo que debería solucionarse", "icono": "alerta"},
    {"id": "participacion", "nombre": "Una idea", "para": "Proponer algo o sumarte a una iniciativa del barrio", "icono": "manos"},
    {"id": "fotos", "nombre": "Fotos", "para": "Mostrarnos cómo se ve", "icono": "camara"},
]

ALCANCE = ["A mí", "A mi familia", "A mi cuadra o edificio", "A mi barrio", "A toda la comuna"]

COMUNES = {
    "opinion": [
        {"id": "valoracion", "pregunta": "¿Qué nota le pondrías? Del 1 al 7, como en el colegio", "tipo": "escala",
         "opciones": ["1", "2", "3", "4", "5", "6", "7"]},
        {"id": "motivo", "pregunta": "¿Qué es lo que más te importó?", "tipo": "una",
         "opciones": ["La calidad", "Lo que hay que esperar", "Cómo te trataron", "Que no llega a todos", "Lo que cuesta", "La información que te dieron"]},
    ],
    "experiencia": [
        {"id": "cuando", "pregunta": "¿Cuándo te pasó?", "tipo": "una",
         "opciones": ["Esta semana", "Este mes", "En los últimos 6 meses", "Hace más de 6 meses"]},
        {"id": "alcance", "pregunta": "¿A quiénes les afecta?", "tipo": "una", "opciones": ALCANCE},
    ],
    "reclamo": [
        {"id": "desde", "pregunta": "¿Hace cuánto tiempo pasa?", "tipo": "una",
         "opciones": ["Menos de 1 mes", "De 1 a 6 meses", "De 6 a 12 meses", "Más de 1 año"]},
        {"id": "alcance", "pregunta": "¿A quiénes les afecta?", "tipo": "una", "opciones": ALCANCE},
        {"id": "reportado", "pregunta": "¿Alcanzaste a avisarle a alguien?", "tipo": "una",
         "opciones": ["Sí, al municipio", "Sí, a otra institución", "Todavía no", "No sabía dónde avisar"]},
        {"id": "respuesta", "pregunta": "¿Y te respondieron?", "tipo": "una", "si": {"reportado": ["Sí, al municipio", "Sí, a otra institución"]},
         "opciones": ["Sí, y se solucionó", "Sí, pero sigue igual", "No me han respondido", "Estoy esperando"]},
    ],
    "participacion": [
        {"id": "propuesta", "pregunta": "¿Cómo es tu idea?", "tipo": "una",
         "opciones": ["Mejorar algo que ya existe", "Algo nuevo para el barrio", "Una actividad entre vecinos", "Sumarme a algo que ya existe"]},
        {"id": "beneficia", "pregunta": "¿A quiénes ayudaría?", "tipo": "varias",
         "opciones": ["Niños y jóvenes", "Personas mayores", "Personas con discapacidad", "Familias", "Todo el barrio", "Toda la comuna"]},
        {"id": "sumarse", "pregunta": "¿Te gustaría ayudar a que se haga?", "tipo": "una", "opciones": ["Sí, cuenten conmigo", "Tal vez", "Por ahora no"]},
    ],
    "fotos": [
        {"id": "muestra", "pregunta": "¿Qué nos muestra tu foto?", "tipo": "una",
         "opciones": ["El problema", "El lugar", "Un documento", "Algo que ya mejoró"]},
        {"id": "cuando_foto", "pregunta": "¿Cuándo la tomaste?", "tipo": "una",
         "opciones": ["Hoy", "Esta semana", "Este mes", "Antes"]},
    ],
}

# ---------------------------------------------------------------- temas
# Cada subtema dice quién es responsable. Las preguntas propias se suman a las comunes del tipo elegido.
ESPERA = ["El mismo día", "Menos de 1 semana", "De 1 a 4 semanas", "De 1 a 3 meses", "Más de 3 meses", "Todavía no me atienden"]

TEMAS = [
    {"id": "salud", "nombre": "Salud", "icono": "corazon", "describe": "Consultorios, urgencias, horas, remedios y postas",
     "subtemas": [
         {"id": "cesfam", "nombre": "Consultorio o CESFAM", "responsable": "municipio"},
         {"id": "urgencia_primaria", "nombre": "Urgencia primaria (SAPU o SAR)", "responsable": "municipio"},
         {"id": "farmacia", "nombre": "Farmacia o remedios", "responsable": "municipio"},
         {"id": "posta_rural", "nombre": "Posta rural", "responsable": "municipio"},
         {"id": "hospital", "nombre": "Hospital", "responsable": "servicio_salud"},
         {"id": "especialista", "nombre": "Especialista o lista de espera", "responsable": "servicio_salud"},
     ],
     "preguntas": [
         {"id": "espera", "pregunta": "¿Cuánto tuviste que esperar?", "tipo": "una", "opciones": ESPERA},
         {"id": "obtuvo", "pregunta": "¿Pudiste resolver lo que necesitabas?", "tipo": "una", "opciones": ["Sí", "En parte", "Todavía no"]},
     ]},
    {"id": "educacion", "nombre": "Educación", "icono": "libro", "describe": "Escuelas, liceos, jardines y transporte escolar",
     "subtemas": [
         {"id": "escuela_municipal", "nombre": "Escuela o liceo municipal", "responsable": "municipio"},
         {"id": "escuela_slep", "nombre": "Escuela de un Servicio Local (SLEP)", "responsable": "slep"},
         {"id": "jardin", "nombre": "Jardín infantil o sala cuna", "responsable": "compartido"},
         {"id": "transporte_escolar", "nombre": "Transporte escolar", "responsable": "municipio"},
         {"id": "infraestructura", "nombre": "Estado del edificio", "responsable": "compartido"},
     ],
     "preguntas": [
         {"id": "nivel", "pregunta": "¿De qué nivel nos hablas?", "tipo": "una", "opciones": ["Sala cuna o jardín", "Básica", "Media", "Adultos"]},
         {"id": "problema", "pregunta": "¿Qué es lo que más te preocupa?", "tipo": "una",
          "opciones": ["Faltan profesores o clases", "Infraestructura", "Convivencia o seguridad", "Transporte", "Alimentación", "Otro"]},
     ]},
    {"id": "basura", "nombre": "Basura y reciclaje", "icono": "basurero", "describe": "Retiro de basura, microbasurales y reciclaje",
     "subtemas": [
         {"id": "retiro", "nombre": "Retiro de basura domiciliaria", "responsable": "municipio"},
         {"id": "microbasural", "nombre": "Microbasural", "responsable": "municipio"},
         {"id": "voluminosos", "nombre": "Retiro de escombros o voluminosos", "responsable": "municipio"},
         {"id": "reciclaje", "nombre": "Reciclaje", "responsable": "municipio"},
     ],
     "preguntas": [
         {"id": "frecuencia", "pregunta": "¿Cada cuánto pasa el camión por tu calle?", "tipo": "una",
          "opciones": ["Más de 2 veces por semana", "1 o 2 veces por semana", "Menos de 1 vez por semana", "No pasa", "No sé"]},
     ]},
    {"id": "calles", "nombre": "Calles y veredas", "icono": "camino", "describe": "Baches, veredas, pavimentos y señalización",
     "subtemas": [
         {"id": "baches", "nombre": "Baches o calles en mal estado", "responsable": "municipio"},
         {"id": "veredas", "nombre": "Veredas", "responsable": "municipio"},
         {"id": "sin_pavimento", "nombre": "Calle sin pavimentar", "responsable": "compartido"},
         {"id": "senalizacion", "nombre": "Señales, semáforos o lomos de toro", "responsable": "municipio"},
         {"id": "accesibilidad", "nombre": "Accesibilidad (rampas, pasos)", "responsable": "municipio"},
         {"id": "carretera", "nombre": "Carretera o ruta", "responsable": "mop"},
     ],
     "preguntas": [
         {"id": "riesgo", "pregunta": "¿Crees que alguien podría accidentarse?", "tipo": "una", "opciones": ["Sí, es peligroso", "Un poco", "No"]},
     ]},
    {"id": "areas_verdes", "nombre": "Plazas y áreas verdes", "icono": "arbol", "describe": "Plazas, parques, árboles y juegos",
     "subtemas": [
         {"id": "mantencion", "nombre": "Mantención de plazas o parques", "responsable": "municipio"},
         {"id": "arbolado", "nombre": "Árboles y poda", "responsable": "municipio"},
         {"id": "juegos", "nombre": "Juegos o máquinas de ejercicio", "responsable": "municipio"},
         {"id": "faltan", "nombre": "Faltan áreas verdes", "responsable": "compartido"},
     ],
     "preguntas": [
         {"id": "estado", "pregunta": "¿Cómo la ves hoy?", "tipo": "una", "opciones": ["Bien cuidada", "Más o menos", "Descuidada", "Abandonada", "No hay"]},
     ]},
    {"id": "alumbrado", "nombre": "Alumbrado", "icono": "ampolleta", "describe": "Luminarias apagadas o calles oscuras",
     "subtemas": [
         {"id": "apagada", "nombre": "Luminaria apagada", "responsable": "municipio"},
         {"id": "oscura", "nombre": "Calle o pasaje oscuro", "responsable": "municipio"},
         {"id": "cortes", "nombre": "Cortes de luz en las casas", "responsable": "electrica"},
     ],
     "preguntas": [
         {"id": "luminarias", "pregunta": "¿Cuántas luces faltan?", "tipo": "una", "opciones": ["Una", "Varias en la cuadra", "Todo el sector"]},
     ]},
    {"id": "seguridad", "nombre": "Seguridad", "icono": "escudo", "describe": "Prevención, patrullaje, cámaras y espacios inseguros",
     "subtemas": [
         {"id": "seguridad_municipal", "nombre": "Seguridad municipal (patrullaje, cámaras)", "responsable": "municipio"},
         {"id": "espacio_inseguro", "nombre": "Espacio inseguro (sitio eriazo, sin luz)", "responsable": "municipio"},
         {"id": "delitos", "nombre": "Delitos en el sector", "responsable": "policias"},
         {"id": "convivencia", "nombre": "Ruidos y convivencia vecinal", "responsable": "municipio"},
     ],
     "preguntas": [
         {"id": "horario", "pregunta": "¿En qué momento te sientes menos seguro?", "tipo": "una", "opciones": ["De día", "Al atardecer", "De noche", "Siempre"]},
         {"id": "denuncia", "pregunta": "¿Pudiste hacer una denuncia?", "tipo": "una", "opciones": ["Sí", "No", "Sentí que no serviría"]},
     ]},
    {"id": "agua", "nombre": "Agua", "icono": "gota", "describe": "Agua potable, alcantarillado, camiones aljibe y lluvias",
     "subtemas": [
         {"id": "aljibe", "nombre": "Camión aljibe", "responsable": "municipio"},
         {"id": "apr", "nombre": "Agua potable rural (APR)", "responsable": "compartido"},
         {"id": "red_urbana", "nombre": "Agua o alcantarillado en la ciudad", "responsable": "sanitaria"},
         {"id": "aguas_lluvia", "nombre": "Inundaciones y aguas lluvia", "responsable": "compartido"},
     ],
     "preguntas": [
         {"id": "acceso", "pregunta": "¿Cómo te llega el agua?", "tipo": "una",
          "opciones": ["Normal", "Con cortes seguidos", "Solo por camión aljibe", "No me llega"]},
     ]},
    {"id": "transporte", "nombre": "Transporte", "icono": "bus", "describe": "Micros, paraderos, ciclovías y conectividad",
     "subtemas": [
         {"id": "paraderos", "nombre": "Paraderos", "responsable": "compartido"},
         {"id": "recorridos", "nombre": "Recorridos y frecuencia de micros", "responsable": "mtt"},
         {"id": "transporte_municipal", "nombre": "Transporte municipal o rural", "responsable": "municipio"},
         {"id": "ciclovias", "nombre": "Ciclovías", "responsable": "compartido"},
     ],
     "preguntas": [
         {"id": "espera_micro", "pregunta": "¿Cuánto esperas normalmente la micro?", "tipo": "una",
          "opciones": ["Menos de 10 minutos", "De 10 a 30 minutos", "Más de 30 minutos", "No hay transporte"]},
     ]},
    {"id": "vivienda", "nombre": "Vivienda y barrio", "icono": "casa", "describe": "Campamentos, subsidios, condominios sociales",
     "subtemas": [
         {"id": "campamento", "nombre": "Campamento o toma", "responsable": "compartido"},
         {"id": "subsidio", "nombre": "Subsidio o postulación", "responsable": "serviu"},
         {"id": "condominio", "nombre": "Condominio o block social", "responsable": "compartido"},
         {"id": "emergencia", "nombre": "Vivienda dañada por emergencia", "responsable": "compartido"},
     ],
     "preguntas": [
         {"id": "situacion", "pregunta": "¿Cómo vives hoy?", "tipo": "una",
          "opciones": ["En casa propia", "Arrendando", "De allegado", "En un campamento", "Prefiero no decir"]},
     ]},
    {"id": "apoyo_social", "nombre": "Apoyo social", "icono": "mano", "describe": "Personas mayores, discapacidad, cuidados y ayudas",
     "subtemas": [
         {"id": "personas_mayores", "nombre": "Personas mayores", "responsable": "municipio"},
         {"id": "discapacidad", "nombre": "Personas con discapacidad", "responsable": "compartido"},
         {"id": "cuidados", "nombre": "Cuidados (quien cuida a otro)", "responsable": "compartido"},
         {"id": "ayudas", "nombre": "Ayudas sociales y Registro Social de Hogares", "responsable": "municipio"},
     ],
     "preguntas": [
         {"id": "atencion_social", "pregunta": "¿Cómo te atendieron en el municipio?", "tipo": "una",
          "opciones": ["Bien", "Más o menos", "Mal", "No me atendieron", "Todavía no he ido"]},
     ]},
    {"id": "cultura_deporte", "nombre": "Cultura y deporte", "icono": "balon", "describe": "Canchas, talleres, bibliotecas y eventos",
     "subtemas": [
         {"id": "canchas", "nombre": "Canchas y recintos deportivos", "responsable": "municipio"},
         {"id": "talleres", "nombre": "Talleres y actividades", "responsable": "municipio"},
         {"id": "bibliotecas", "nombre": "Bibliotecas y centros culturales", "responsable": "municipio"},
         {"id": "eventos", "nombre": "Eventos y fiestas", "responsable": "municipio"},
     ],
     "preguntas": [
         {"id": "uso", "pregunta": "¿Lo usas o te gustaría usarlo?", "tipo": "una", "opciones": ["Lo uso", "Lo usaría si mejora", "No lo usaría"]},
     ]},
    {"id": "animales", "nombre": "Animales", "icono": "huella", "describe": "Perros callejeros, esterilización y tenencia responsable",
     "subtemas": [
         {"id": "callejeros", "nombre": "Perros o gatos en la calle", "responsable": "municipio"},
         {"id": "esterilizacion", "nombre": "Esterilización y vacunas", "responsable": "municipio"},
         {"id": "plagas", "nombre": "Plagas (ratones, palomas)", "responsable": "municipio"},
     ],
     "preguntas": [
         {"id": "cantidad", "pregunta": "¿Cuántos animales ves en tu sector?", "tipo": "una", "opciones": ["Pocos", "Varios", "Muchos", "Andan en jaurías"]},
     ]},
    {"id": "municipio", "nombre": "Atención municipal", "icono": "edificio", "describe": "Trámites, atención, transparencia y participación",
     "subtemas": [
         {"id": "tramites", "nombre": "Trámites y permisos", "responsable": "municipio"},
         {"id": "atencion", "nombre": "Atención en el municipio", "responsable": "municipio"},
         {"id": "transparencia", "nombre": "Información y transparencia", "responsable": "municipio"},
         {"id": "participacion_vecinal", "nombre": "Participación y juntas de vecinos", "responsable": "municipio"},
     ],
     "preguntas": [
         {"id": "canal", "pregunta": "¿Cómo hiciste el trámite?", "tipo": "una", "opciones": ["En persona", "Por teléfono", "Por internet", "No pude hacerlo"]},
     ]},
    {"id": "otro", "nombre": "Otro tema", "icono": "mas", "describe": "Algo que no está en la lista",
     "subtemas": [{"id": "otro", "nombre": "Otro", "responsable": "compartido"}],
     "preguntas": []},
]

# ---------------------------------------------------------------- preguntas por subtema (versión 1.2)
# Una por subtema, solo si aporta algo que la del tema no cubre. "reemplaza": la pregunta del tema que deja de hacerse.
def _q(id, pregunta, opciones, tipo="una", reemplaza=None):
    d = {"id": "sub_" + id, "pregunta": pregunta, "tipo": tipo, "opciones": opciones}
    if reemplaza:
        d["reemplaza"] = reemplaza
    return d

POR_SUBTEMA = {
    "salud": {
        "cesfam": _q("cesfam", "¿Qué necesitabas?", ["Una hora con médico", "Un control o examen", "Remedios", "Atención dental", "Otra cosa"]),
        "urgencia_primaria": _q("urgencia", "¿A qué hora fuiste?", ["En la mañana", "En la tarde", "En la noche", "De madrugada"]),
        "farmacia": _q("farmacia", "¿Encontraste el remedio que necesitabas?", ["Sí", "Solo algunos", "No había", "No sabía que existía la farmacia municipal"]),
        "posta_rural": _q("posta", "¿Cada cuánto viene el médico o la ronda?", ["Todas las semanas", "Cada dos semanas", "Una vez al mes o menos", "No sé"]),
        "hospital": _q("hospital", "¿Qué estás esperando?", ["Una consulta con especialista", "Una cirugía", "Un examen", "Prefiero no decir"]),
        "especialista": _q("lista_espera", "¿Hace cuánto estás en lista de espera?", ["Menos de 6 meses", "De 6 a 12 meses", "De 1 a 2 años", "Más de 2 años"], reemplaza="espera"),
    },
    "educacion": {
        "jardin": _q("cupo", "¿Conseguiste cupo?", ["Sí", "Estoy en lista de espera", "No", "Todavía no he postulado"]),
        "transporte_escolar": _q("viaje", "¿Cuánto demora el viaje?", ["Menos de 30 minutos", "De 30 a 60 minutos", "Más de 1 hora", "No hay transporte"]),
        "infraestructura": _q("arreglo", "¿Qué necesita arreglo?", ["Baños", "Techos o goteras", "Calefacción", "Patios", "Accesos para personas con discapacidad", "Otro"], tipo="varias"),
    },
    "basura": {
        "microbasural": _q("tamano", "¿Qué tan grande es?", ["Unas pocas bolsas", "Un montón", "Ocupa media calle o más"]),
        "voluminosos": _q("voluminosos", "¿Sabías que el municipio retira voluminosos?", ["Sí, y lo pedí", "Sí, pero no lo pedí", "No sabía"]),
        "reciclaje": _q("reciclaje", "¿Tienes un punto de reciclaje cerca?", ["A menos de 5 cuadras", "Más lejos", "No hay", "No sé"]),
    },
    "calles": {
        "baches": _q("dano", "¿Qué tan grande es el daño?", ["Un bache", "Varios en la cuadra", "Toda la calle"]),
        "veredas": _q("paso", "¿Se puede pasar con coche o silla de ruedas?", ["Sí", "Con dificultad", "No"]),
        "sin_pavimento": _q("casas", "¿Cuántas casas hay en esa calle?", ["Menos de 10", "De 10 a 50", "Más de 50"]),
        "senalizacion": _q("falta_senal", "¿Qué falta?", ["Un semáforo", "Un paso de cebra", "Una señal", "Un lomo de toro", "Otra cosa"]),
        "accesibilidad": _q("dificil", "¿Para quiénes es difícil pasar?", ["Personas en silla de ruedas", "Personas mayores", "Coches de guagua", "Personas ciegas", "Para todos"], tipo="varias"),
    },
    "areas_verdes": {
        "mantencion": _q("falta_mant", "¿Qué es lo que más falta?", ["Riego", "Corte de pasto", "Limpieza", "Luz", "Bancas o basureros"]),
        "arbolado": _q("arbol", "¿Qué pasa con el árbol?", ["Necesita poda", "Está seco o podría caerse", "Rompe la vereda", "Faltan árboles"]),
        "faltan": _q("plaza_cerca", "¿A cuánto queda la plaza más cercana?", ["A menos de 5 cuadras", "De 5 a 10 cuadras", "A más de 10 cuadras"]),
    },
    "alumbrado": {
        "apagada": _q("cruce", "¿Está en un cruce o en un paradero?", ["Sí", "No", "No sé"]),
        "oscura": _q("inseguro_noche", "¿Te sientes insegura o inseguro pasando por ahí de noche?", ["Sí", "A veces", "No"]),
        "cortes": _q("cortes_luz", "¿Cada cuánto se corta la luz?", ["Una vez al mes o menos", "Varias veces al mes", "Todas las semanas"]),
    },
    "seguridad": {
        "seguridad_municipal": _q("patrullaje", "¿Has visto patrullaje municipal en tu sector?", ["Seguido", "A veces", "Nunca", "No sabía que existía"]),
        "espacio_inseguro": _q("por_que_inseguro", "¿Qué lo hace inseguro?", ["Poca luz", "Un sitio abandonado", "Consumo de drogas o alcohol", "Basura", "Otra cosa"]),
        "delitos": _q("situacion_delito", "¿Qué tipo de situación?", ["Robos", "Asaltos", "Venta de drogas", "Disparos", "Prefiero no decir"]),
        "convivencia": _q("conflicto", "¿Qué está pasando?", ["Ruidos molestos", "Fiestas", "Peleas entre vecinos", "Animales", "Otra cosa"]),
    },
    "agua": {
        "aljibe": _q("alcanza", "¿El agua que te llega te alcanza?", ["Sí", "Menos de la que necesito", "Muy poca", "No me llega"]),
        "apr": _q("apr", "¿Cómo funciona tu APR?", ["Bien", "Con cortes", "El agua llega en mal estado", "No hay APR"]),
        "aguas_lluvia": _q("lluvia", "¿Qué pasa cuando llueve?", ["Se inunda la calle", "Entra agua a las casas", "Se cortan los caminos", "Otra cosa"]),
    },
    "transporte": {
        "paraderos": _q("paradero", "¿Cómo es tu paradero?", ["Tiene techo y asiento", "Solo un letrero", "No hay paradero"]),
        "transporte_municipal": _q("uso_transporte", "¿Para qué lo usas?", ["Ir al consultorio", "Ir al colegio", "Hacer trámites", "Ir a trabajar", "Otra cosa"]),
        "ciclovias": _q("bicicleta", "¿Usarías bicicleta si hubiera una ciclovía segura?", ["Sí", "Tal vez", "No"]),
    },
    "vivienda": {
        "campamento": _q("familias", "¿Cuántas familias viven ahí?", ["Menos de 20", "De 20 a 100", "Más de 100", "No sé"]),
        "subsidio": _q("etapa", "¿En qué etapa estás?", ["Postulando", "Esperando el resultado", "Tengo el subsidio, pero no la vivienda", "Otra"]),
        "condominio": _q("problema_condominio", "¿Cuál es el problema principal?", ["Filtraciones", "Espacios comunes", "Seguridad", "Administración", "Otro"]),
        "emergencia": _q("dano_vivienda", "¿Cómo quedó tu vivienda?", ["Con daño leve", "Con daño grave", "No se puede vivir en ella"]),
    },
    "apoyo_social": {
        "personas_mayores": _q("necesita_mayor", "¿Qué es lo que más necesita?", ["Compañía", "Cuidados", "Ayuda con trámites", "Atención de salud", "Alimentación"], tipo="varias"),
        "discapacidad": _q("barrera", "¿Qué es lo más difícil?", ["Moverse por la comuna", "Acceder a servicios", "Encontrar trabajo", "Conseguir apoyos o ayudas técnicas"]),
        "cuidados": _q("horas_cuidado", "¿Cuántas horas al día cuidas a otra persona?", ["Menos de 4", "De 4 a 8", "Más de 8"]),
        "ayudas": _q("tramite_social", "¿Qué trámite o ayuda?", ["Registro Social de Hogares", "Una ayuda social", "Una pensión o bono", "Otro"]),
    },
    "cultura_deporte": {
        "canchas": _q("cancha", "¿Cómo está la cancha?", ["Bien", "Más o menos", "Mal", "No hay"]),
        "talleres": _q("talleres_para", "¿Para quiénes faltan talleres?", ["Niños", "Jóvenes", "Adultos", "Personas mayores"], tipo="varias"),
    },
    "animales": {
        "esterilizacion": _q("hora_esterilizacion", "¿Pudiste conseguir hora?", ["Sí", "Estoy esperando", "No hay operativos", "No sabía que existían"]),
        "plagas": _q("plaga", "¿Qué plaga?", ["Ratones", "Palomas", "Cucarachas", "Otra"]),
    },
    "municipio": {
        "tramites": _q("tramite", "¿Qué trámite?", ["Permiso de circulación", "Patente", "Permiso de edificación", "Certificados", "Otro"]),
        "transparencia": _q("encontro_info", "¿Encontraste la información que buscabas?", ["Sí", "En parte", "No"]),
        "participacion_vecinal": _q("junta", "¿Tu junta de vecinos está activa?", ["Sí", "Poco", "No", "No sé"]),
    },
}

# ---------------------------------------------------------------- seguimientos según la respuesta (versión 1.2)
# Aparecen justo debajo de la respuesta que los activa ("si"). "reemplaza": la pregunta que deja de hacerse cuando aparece.
MEJORAR = ["La calidad", "Lo que hay que esperar", "Cómo te tratan", "Que llegue a todos", "La información"]
SEGUIMIENTOS = [
    {"id": "mejorar", "pregunta": "¿Qué debería mejorar primero?", "tipo": "una", "opciones": MEJORAR,
     "si": {"valoracion": ["1", "2", "3", "4"]}, "reemplaza": "motivo"},
    {"id": "funciona", "pregunta": "¿Qué es lo que mejor funciona?", "tipo": "una", "opciones": MEJORAR,
     "si": {"valoracion": ["5", "6", "7"]}, "reemplaza": "motivo"},
    {"id": "pedido_hace", "pregunta": "¿Hace cuánto lo pediste?", "tipo": "una", "opciones": ["Menos de 1 mes", "De 1 a 6 meses", "Más de 6 meses"],
     "si": {"espera": ["Todavía no me atienden"]}},
    {"id": "freno", "pregunta": "¿Qué te frenó?", "tipo": "una", "opciones": ["No sabía dónde", "Pensé que no serviría", "No tuve tiempo", "Me da miedo que haya represalias"],
     "si": {"reportado": ["Todavía no"]}},
    {"id": "avisado_hace", "pregunta": "¿Hace cuánto avisaste?", "tipo": "una", "opciones": ["Menos de 1 mes", "De 1 a 3 meses", "Más de 3 meses"],
     "si": {"respuesta": ["No me han respondido"]}},
    {"id": "por_que_no_serviria", "pregunta": "¿Por qué lo sentiste?", "tipo": "una", "opciones": ["Otras veces no pasó nada", "Queda lejos", "Miedo a represalias", "Otro"],
     "si": {"denuncia": ["Sentí que no serviría"]}},
    {"id": "sin_agua_desde", "pregunta": "¿Desde cuándo?", "tipo": "una", "opciones": ["Menos de 1 semana", "De 1 a 4 semanas", "Más de 1 mes"],
     "si": {"acceso": ["No me llega"]}},
    {"id": "avisame", "pregunta": "¿Te avisamos si otros vecinos proponen lo mismo?", "tipo": "una", "opciones": ["Sí", "No"],
     "si": {"sumarse": ["Sí, cuenten conmigo"]}, "requiere_cuenta_si": "Sí"},
]
# Comportamientos sin pregunta: "No sabía dónde avisar" → al final se muestra dónde avisar; "Prefiero no decir" → no se insiste.
AL_FINAL = {"mostrar_donde_avisar_si": {"reportado": ["No sabía dónde avisar"], "freno": ["No sabía dónde"]}}
TOPE_BASE = 8
OMITIR_PRIMERO = ["cuando_foto", "cuando"]

# ---------------------------------------------------------------- equivalencias con el gasto
# Los rubros del Monitor de Gasto Municipal se escriben tal como vienen en la fuente (sin tildes).
# precision: "directa" (la fuente dice para qué se gasta), "aproximada" (lo deduce del proveedor o de un rubro amplio),
# "sin_dato" (hoy no hay fuente). Las reglas de ChileCompra se aplican sobre cada ítem de una orden de compra.
# unidad: palabras en el nombre de la unidad compradora (por ejemplo "Departamento de Salud").
# n1, n2, n3: categorías de producto de ChileCompra (nombres exactos de los datos abiertos); n1 puede ser una lista.
# palabras: palabras en el nombre de la orden de compra; se usan solo cuando la categoría es demasiado amplia.
UNIDAD_SALUD = ["SALUD", "CESFAM", "CECOSF", "SAPU", "SAR", "CONSULTORIO", "DESAMU", "POSTA"]
UNIDAD_EDUCACION = ["EDUCACION", "EDUCACIÓN", "DAEM", "DEM ", "LICEO", "ESCUELA", "COLEGIO", "JARDIN", "JARDÍN"]

# Obras: la categoría no dice qué se construye; el nombre de la orden sí ("mejoramiento plaza", "multicancha").
# Las palabras se comparan sin tildes y en mayúsculas.
OBRAS = ["Servicios de construcción y mantenimiento", "Artículos para estructuras, obras y construcciones"]

# Funcionamiento general del municipio: gasto real, pero que no corresponde a un tema vecinal.
FUNCIONAMIENTO = [
    {"n1": "Servicios de limpieza industrial", "n2": ["Servicios de limpieza"]},
    {"n1": "Vehículos y equipamiento en general"},
    {"n1": "Combustibles, lubricantes y anticorrosivos"},
    {"n1": "Productos de papel"},
    {"n1": "Productos impresos y publicaciones"},
    {"n1": "Equipos, accesorios y suministros de oficina"},
    {"n1": "Tecnologías de la información, telecomunicaciones y radiodifusión"},
    {"n1": "Servicios profesionales, administrativos y consultorías de gestión empresarial"},
    {"n1": "Servicios basados en ingeniería, ciencias sociales y tecnología de la información"},
    {"n1": "Servicios financieros, pensiones y seguros"},
    {"n1": "Servicios editoriales, de diseño, publicidad, gráficos y artistas"},
    {"n1": "Muebles y mobiliario"},
    {"n1": "Equipos y suministros de limpieza"},
    {"n1": "Herramientas y maquinaria en general"},
    {"n1": "Maquinaria para construcción y edificación"},
    {"n1": "Equipamiento para manejo y estiba de materiales"},
]

EQUIVALENCIAS = {
    "salud": {
        "chilecompra": {"precision": "directa", "reglas": [
            {"n1": OBRAS, "palabras": ["CESFAM", "CECOSF", "POSTA", "SAPU", "CONSULTORIO"]},
            {"unidad": UNIDAD_SALUD},
            {"n1": "Medicamentos y productos farmacéuticos"},
            {"n1": "Equipamiento y suministros médicos"},
            {"n1": "Salud, servicios sanitarios y alimentación", "n2": ["Medicina y servicios de salud", "Servicios para el cuidado de la salud de las personas", "Prevención y control de enfermedades"]},
        ]},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Actividades de atencion de la salud humana y de asistencia social"],
                              "nota": "Solo facturas; los remedios comprados a distribuidoras quedan como comercio y los sueldos de los CESFAM no aparecen."},
        "presupuesto_estado": {"precision": "directa", "partidas": ["16"], "nota": "Ministerio de Salud; incluye el aporte para atención primaria municipal."},
    },
    "educacion": {
        "chilecompra": {"precision": "directa", "reglas": [
            {"n1": OBRAS, "palabras": ["ESCUELA", "LICEO", "COLEGIO", "JARDIN INFANTIL", "SALA CUNA"]},
            {"unidad": UNIDAD_EDUCACION},
            {"n1": "Educación, formación, entrenamiento y capacitación"},
            {"n1": "Instrumentos musicales, juegos, juguetes, artesanías y materiales educativos"},
        ]},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Enseñanza"]},
        "presupuesto_estado": {"precision": "directa", "partidas": ["09"]},
        "nota": "En las comunas donde las escuelas ya pasaron a un Servicio Local de Educación Pública, ese gasto deja de ser municipal.",
    },
    "basura": {
        "chilecompra": {"precision": "directa", "reglas": [
            {"n1": "Servicios de limpieza industrial", "n2": ["Eliminación y tratamiento de desechos", "Limpieza de residuos o desechos tóxicos y peligrosos"]},
            {"n1": "Servicios medioambientales"},
        ]},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Suministro de agua; evacuacion de aguas residuales; gestion de desechos y descontaminacion"],
                              "nota": "El rubro mezcla basura con agua; en la práctica municipal es casi todo basura."},
        "presupuesto_estado": {"precision": "sin_dato", "partidas": []},
    },
    "calles": {
        "chilecompra": {"precision": "aproximada", "reglas": [
            {"n1": "Artículos para estructuras, obras y construcciones", "n2": ["Pavimento para carreteras y caminos"]},
            {"n1": OBRAS,
             "palabras": ["PAVIMENT", "VEREDA", "BACHE", "CALZADA", "ACERA", "ASFALT", "CALLE", "PASAJE", "SOLERA", "SENALETICA", "SENALIZACION", "DEMARCACION", "RESALTO", "LOMO DE TORO", "CAMINO", "AVENIDA", "PUENTE", "PASARELA", "CICLOVIA"]},
        ], "nota": "La categoría de construcción no separa calles de edificios; se usan palabras del nombre de la orden."},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Construccion"], "nota": "Mezcla calles, edificios y obras."},
        "presupuesto_estado": {"precision": "directa", "partidas": ["18", "12"], "nota": "Vivienda (pavimentos participativos) y Obras Públicas (vialidad)."},
    },
    "areas_verdes": {
        "chilecompra": {"precision": "directa", "reglas": [
            {"n1": OBRAS, "palabras": ["PLAZA", "PARQUE", "AREA VERDE", "AREAS VERDES", "ARBOLADO"]},
            {"n1": "Servicios agrícolas, pesqueros, forestales y relacionados con la fauna", "n2": ["Horticultura"]},
            {"n1": "Artículos para plantas y animales", "n2": ["Semillas, bulbos y almácigos", "Abonos y herbicidas", "Productos de floricultura y silvicultura"]},
            {"n1": "Equipos, suministros y accesorios deportivos y recreativos", "n2": ["Equipos y suministros de recreación, parques infantiles, natación y de spa"]},
        ]},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Agricultura; ganaderia; silvicultura y pesca"]},
        "presupuesto_estado": {"precision": "sin_dato", "partidas": []},
    },
    "alumbrado": {
        "chilecompra": {"precision": "directa", "reglas": [
            {"n1": OBRAS, "palabras": ["ALUMBRADO", "LUMINARIA", "POSTES"]},{"n1": "Artículos eléctricos y de iluminación"}]},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Suministro de electricidad; gas; vapor y aire acondicionado"],
                              "nota": "Incluye las cuentas de luz del alumbrado público y de los edificios municipales."},
        "presupuesto_estado": {"precision": "sin_dato", "partidas": []},
    },
    "seguridad": {
        "chilecompra": {"precision": "directa", "reglas": [
            {"n1": OBRAS, "palabras": ["CAMARAS", "TELEVIGILANCIA", "TELE VIGILANCIA"]},
            {"n1": "Servicios de defensa nacional, orden público y seguridad", "n2": ["Orden público y seguridad", "Seguridad y protección personal"]},
            {"n1": "Equipos y suministros de defensa, orden público, protección y seguridad", "n2": ["Seguridad y control público", "Seguridad, vigilancia y detección", "Protección contra incendios"]},
        ]},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Actividades de servicios administrativos y de apoyo"],
                              "nota": "Los guardias están en este rubro, pero junto con otros servicios de apoyo."},
        "presupuesto_estado": {"precision": "directa", "partidas": ["32", "05"]},
    },
    "agua": {
        "chilecompra": {"precision": "aproximada", "reglas": [
            {"n1": OBRAS, "palabras": ["ALCANTARILLADO", "AGUA POTABLE", "AGUAS LLUVIA", "COLECTOR", "APR "]},
            {"n1": "Servicios agrícolas, pesqueros, forestales y relacionados con la fauna", "n2": ["Desarrollo y vigilancia de recursos hidráulicos"]},
            {"n1": "Equipamiento para el acondicionamiento, distribución y filtrado de fluidos"},
            {"n1": "Servicios de transporte, almacenaje y correo", "palabras": ["ALJIBE", "AGUA POTABLE"]},
        ]},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Suministro de agua; evacuacion de aguas residuales; gestion de desechos y descontaminacion"]},
        "presupuesto_estado": {"precision": "directa", "partidas": ["12"], "nota": "Obras Públicas: agua potable rural y aguas lluvia."},
    },
    "transporte": {
        "chilecompra": {"precision": "aproximada", "reglas": [
            {"n1": "Servicios de transporte, almacenaje y correo", "n2": ["Transporte de pasajeros"], "excepto_unidad": UNIDAD_EDUCACION},
        ]},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Transporte y almacenamiento"]},
        "presupuesto_estado": {"precision": "directa", "partidas": ["19"]},
    },
    "vivienda": {
        "chilecompra": {"precision": "aproximada", "reglas": [
            {"n1": OBRAS, "palabras": ["VIVIENDA", "CAMPAMENTO", "CONDOMINIO"]},
            {"n1": "Artículos para estructuras, obras y construcciones", "n2": ["Estructuras prefabricadas"]},
            {"n1": "Servicios de construcción y mantenimiento", "n3": ["Construcción residencial"]},
        ]},
        "monitor_municipal": {"precision": "sin_dato", "rubros": []},
        "presupuesto_estado": {"precision": "directa", "partidas": ["18"]},
    },
    "apoyo_social": {
        "chilecompra": {"precision": "aproximada", "reglas": [
            {"n1": "Organizaciones y consultorías políticas, demográficas, económicas, sociales y de administración pública", "n2": ["Ayuda y asistencia humanitaria", "Desarrollo social, demográfico y comunitario"]},
            {"n1": "Servicios de cuidado personal y domésticos"},
        ]},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Actividades de atencion de la salud humana y de asistencia social"]},
        "presupuesto_estado": {"precision": "directa", "partidas": ["21"]},
    },
    "cultura_deporte": {
        "chilecompra": {"precision": "directa", "reglas": [
            {"n1": OBRAS, "palabras": ["MULTICANCHA", "CANCHA", "ESTADIO", "GIMNASIO", "BIBLIOTECA", "CENTRO CULTURAL", "SKATEPARK"]},
            {"n1": "Equipos, suministros y accesorios deportivos y recreativos"},
            {"n1": "Servicios de Viajes, alimentación, alojamiento y entretenimiento", "n2": ["Entretenimiento", "Artes interpretativas", "Deportes comerciales"]},
            {"n1": "Servicios básicos y de información pública", "n2": ["Bibliotecas y otros centros de información pública"]},
        ]},
        "monitor_municipal": {"precision": "directa", "rubros": ["Actividades artisticas; de entretenimiento y recreativas"]},
        "presupuesto_estado": {"precision": "directa", "partidas": ["29", "26"]},
    },
    "animales": {
        "chilecompra": {"precision": "directa", "reglas": [
            {"n1": "Servicios agrícolas, pesqueros, forestales y relacionados con la fauna", "n2": ["Servicios de ganadería"]},
            {"n1": "Artículos para plantas y animales", "n2": ["Artículos para mascotas", "Alimento para animales", "Productos para el control de plagas", "Casas y jaulas para animales"]},
        ]},
        "monitor_municipal": {"precision": "sin_dato", "rubros": []},
        "presupuesto_estado": {"precision": "sin_dato", "partidas": []},
    },
    "municipio": {
        "chilecompra": {"precision": "sin_dato", "reglas": [],
                        "nota": "El gasto en atención y trámites está dentro de 'funcionamiento general' y no se puede separar."},
        "monitor_municipal": {"precision": "aproximada", "rubros": ["Informacion y comunicaciones", "Actividades profesionales; cientificas y tecnicas"]},
        "presupuesto_estado": {"precision": "sin_dato", "partidas": []},
    },
    "otro": {"chilecompra": {"precision": "sin_dato", "reglas": []}, "monitor_municipal": {"precision": "sin_dato", "rubros": []},
             "presupuesto_estado": {"precision": "sin_dato", "partidas": []}},
}

REGLAS_GENERALES = [
    "Orden de aplicación para cada ítem de compra: 1) unidad compradora, 2) palabras en el nombre, 3) categoría del producto, 4) funcionamiento general. En cada paso se recorren los temas en el orden de la lista y gana el primero que calza; así ningún peso se cuenta dos veces.",
    "La regla por unidad compradora (salud, educación) tiene prioridad sobre la categoría del producto: un camión aljibe comprado por el Departamento de Salud cuenta como salud.",
    "Solo se compara la necesidad con el gasto municipal en los subtemas cuyo responsable es el municipio o es compartido; los demás se muestran sin comparación y con el nombre del responsable.",
    "Cada comparación muestra su precisión: directa, aproximada o sin dato. Sin dato, Coddy dice 'lo que aún no se puede medir'.",
    "Las palabras se buscan en el nombre de la orden y del producto, sin tildes y en mayúsculas.",
    "Lo que no es un tema vecinal (vehículos, combustible, oficina, limpieza de edificios, seguros) se agrupa como 'funcionamiento general' y no se compara con necesidades.",
    "Lo que no calza con ninguna regla queda como 'sin clasificar' y se informa su porcentaje: nunca se reparte a la fuerza.",
    "La tabla es pública y se corrige con evidencia; cada cambio cambia la versión.",
]


def main():
    temas = {"version": VERSION, "responsables": RESPONSABLES, "tipos_de_aporte": TIPOS,
             "temas": [{k: v for k, v in t.items() if k != "preguntas"} for t in TEMAS]}
    preguntas = {"version": VERSION, "comunes_por_tipo": COMUNES,
                 "por_tema": {t["id"]: t["preguntas"] for t in TEMAS},
                 "por_subtema": POR_SUBTEMA, "seguimientos": SEGUIMIENTOS, "al_final": AL_FINAL,
                 "tope_base": TOPE_BASE, "omitir_primero": OMITIR_PRIMERO,
                 "orden": "Primero la pregunta del subtema, luego las del tema (sin las que el subtema reemplaza) y después los bloques de cada tipo de aporte elegido, sin repetir. Si pasan del tope, se omiten en el orden de omitir_primero. Cada seguimiento aparece justo después de la pregunta que lo activa y no cuenta para el tope.",
                 "nota": "Al aporte se le hacen la pregunta de su subtema, las de su tema y las comunes de cada tipo elegido; los seguimientos aparecen según la respuesta."}
    ids = [t["id"] for t in TEMAS]
    todos = {q["id"] for v in COMUNES.values() for q in v} | {q["id"] for t in TEMAS for q in t["preguntas"]}
    for tid, subs in POR_SUBTEMA.items():
        validos = {x["id"] for t in TEMAS if t["id"] == tid for x in t["subtemas"]}
        for sid, q in subs.items():
            assert sid in validos, (tid, sid)
            assert q["id"] not in todos, q["id"]
            todos.add(q["id"])
    for sg in SEGUIMIENTOS:
        assert all(k in todos for k in sg["si"]), sg["id"]
        assert sg["id"] not in todos, sg["id"]
        todos.add(sg["id"])
    assert set(ids) == set(EQUIVALENCIAS), "cada tema necesita su fila de equivalencias"
    for t in TEMAS:
        for s in t["subtemas"]:
            assert s["responsable"] in RESPONSABLES, s
    equivalencias = {"version": VERSION, "reglas_generales": REGLAS_GENERALES,
                     "unidades": {"salud": UNIDAD_SALUD, "educacion": UNIDAD_EDUCACION},
                     "funcionamiento_general": FUNCIONAMIENTO,
                     "temas": {i: EQUIVALENCIAS[i] for i in ids}}
    for nombre, datos in (("temas.json", temas), ("preguntas.json", preguntas), ("equivalencias.json", equivalencias)):
        with open(os.path.join(AQUI, nombre), "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=1)
        print("escrito", nombre)


if __name__ == "__main__":
    main()
