"""Assistant Personality — consistent voice and tone across all interactions.

Defines how the assistant communicates: greeting styles, response templates,
error messages, and contextual responses — all in natural Argentine Spanish.
"""

import random
from dataclasses import dataclass


@dataclass
class PersonalityConfig:
    name: str
    tone: str  # friendly, professional, casual
    language: str  # es_latam, es_iberia
    use_emojis: bool
    use_vos: bool  # Argentine "vos" vs standard "tú"


DEFAULT_PERSONALITY = PersonalityConfig(
    name="Sofi",
    tone="friendly",
    language="es_latam",
    use_emojis=True,
    use_vos=True,
)


# === Greetings ===

GREETINGS = [
    "¡Hola! 👋 Soy {name}, tu asistente. ¿En qué te puedo ayudar?",
    "¡Buenas! Soy {name}. Estoy acá para lo que necesites.",
    "¡Hola! ¿Cómo estás? Soy {name}, tu copiloto en XcapitSFF.",
]

GREETINGS_RETURNING = [
    "¡Hola de nuevo! 👋 ¿En qué seguimos?",
    "¡Volviste! ¿Qué necesitás hoy?",
    "¡Buenas! ¿Cómo puedo ayudarte ahora?",
]


# === Acknowledgments ===

ACK_POSITIVE = [
    "¡Listo! ✅",
    "¡Hecho! 👍",
    "¡Perfecto!",
    "¡Dale! Ya lo hice.",
    "¡Genial! Acá está:",
]

ACK_WORKING = [
    "Dejame buscar eso...",
    "Un segundo, ya lo traigo...",
    "Buscando...",
]

ACK_CREATED = [
    "Creado exitosamente. Acá tenés los detalles:",
    "¡Listo! Se creó correctamente:",
    "Ya está creado:",
]


# === Error responses ===

ERROR_NOT_FOUND = [
    "No encontré lo que buscás. ¿Querés intentar con otros términos?",
    "Mmm, no hay resultados para eso. Probá con otra búsqueda.",
]

ERROR_GENERAL = [
    "Ups, algo salió mal. ¿Podés intentar de nuevo?",
    "Hubo un error procesando tu pedido. Intentá de nuevo.",
]

ERROR_UNKNOWN_INTENT = [
    "No estoy segura de lo que necesitás. ¿Podés decirlo de otra forma?",
    "No entendí bien. Probá con algo como 'ver leads' o 'crear ticket'.",
    "Mmm, no capté eso. Escribí 'ayuda' para ver todo lo que puedo hacer.",
]


# === Contextual transitions ===

TRANSITIONS = {
    "after_create_lead": [
        "¿Querés calificarlo?",
        "¿Componemos un outreach para este lead?",
        "¿Vemos el pipeline?",
    ],
    "after_list_leads": [
        "¿Querés ver el kanban?",
        "¿Filtramos por algún criterio?",
        "¿Componemos outreach para los hot?",
    ],
    "after_create_ticket": [
        "¿Querés que busque artículos de KB relacionados?",
        "¿Vemos cómo quedó clasificado?",
        "¿Respondemos al ticket?",
    ],
    "after_dashboard": [
        "¿Querés ver los leads hot?",
        "¿Vemos las predicciones del pipeline?",
        "¿Revisamos los tickets pendientes?",
    ],
    "after_outreach": [
        "¿Lo enviamos?",
        "¿Generamos una variante A/B?",
        "¿Vemos el siguiente lead?",
    ],
}


# === Help categories ===

HELP_TEXT = """
**¿Qué puedo hacer?** Acá va un resumen:

📊 **Ventas**
• "Crear lead" — nuevo prospecto
• "Ver leads" / "Kanban" — pipeline
• "Leads hot" — leads de alto potencial
• "Calificar leads" — scoring automático
• "Componer outreach" — mensajes de venta
• "Crear campaña" — campaña de outreach
• "Predicciones" — forecast del pipeline

🎫 **Soporte**
• "Crear ticket" — nuevo caso
• "Ver tickets" — lista de tickets
• "Tickets urgentes" — prioridad alta
• "Buscar en KB" — knowledge base

📈 **Analytics**
• "Dashboard" — vista general
• "Analytics" — métricas detalladas
• "Health score" — salud del workspace
• "Reportes" — generar reporte

⚙️ **Sistema**
• "Configurar" — ajustes
• "Importar" / "Exportar" — datos
• "Ayuda" — esta pantalla

💡 **Tip:** También podés usar Ctrl+K para búsqueda rápida
"""


def get_greeting(is_returning: bool = False) -> str:
    pool = GREETINGS_RETURNING if is_returning else GREETINGS
    return random.choice(pool).format(name=DEFAULT_PERSONALITY.name)


def get_ack(ack_type: str = "positive") -> str:
    pool = {"positive": ACK_POSITIVE, "working": ACK_WORKING, "created": ACK_CREATED}
    return random.choice(pool.get(ack_type, ACK_POSITIVE))


def get_error(error_type: str = "general") -> str:
    pool = {
        "not_found": ERROR_NOT_FOUND,
        "general": ERROR_GENERAL,
        "unknown": ERROR_UNKNOWN_INTENT,
    }
    return random.choice(pool.get(error_type, ERROR_GENERAL))


def get_transition(context: str) -> list[str]:
    return TRANSITIONS.get(context, [])


def get_help() -> str:
    return HELP_TEXT
