"""Master seed script — seeds leads, knowledge base, customers, tickets, messages, and outreach.

Idempotent: safe to run multiple times. Checks for existing data before inserting
to avoid duplicates on repeated runs.

Usage:
    PYTHONPATH=src python scripts/seed_all.py
"""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import func, select

from xcapitsff.core.database import async_session, init_db
from xcapitsff.core.models import (
    Customer,
    KnowledgeArticle,
    Lead,
    OutreachMessage,
    Ticket,
    TicketMessage,
)
from xcapitsff.core.schemas import (
    ArticleCreate,
    LeadCreate,
    TicketCreate,
    TicketMessageCreate,
    TicketPriorityEnum,
)
from xcapitsff.sales.importer import import_from_file, import_leads_bulk, parse_leads
from xcapitsff.sales.pipeline import create_lead, get_leads
from xcapitsff.support.knowledge import create_article
from xcapitsff.support.tickets import (
    add_message,
    create_customer,
    create_ticket,
)

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LEADS_SEED_FILE = DATA_DIR / "leads_seed.tsv"
KB_SEED_FILE = DATA_DIR / "knowledge_base_seed.json"


# ---------------------------------------------------------------------------
# Sample data: customers
# ---------------------------------------------------------------------------

SAMPLE_CUSTOMERS = [
    {
        "company_name": "Fintech Austral S.A.",
        "contact_name": "Mariana Gonzalez",
        "contact_email": "mariana.gonzalez@fintechaustral.com.ar",
        "region": "LATAM",
    },
    {
        "company_name": "CryptoAndes SpA",
        "contact_name": "Carlos Rojas",
        "contact_email": "carlos.rojas@cryptoandes.cl",
        "region": "LATAM",
    },
    {
        "company_name": "Inversiones del Plata S.R.L.",
        "contact_name": "Ana Belen Martinez",
        "contact_email": "abmartinez@inversionesdelplata.com.ar",
        "region": "LATAM",
    },
    {
        "company_name": "DeFi Soluciones Mexico S.A. de C.V.",
        "contact_name": "Roberto Hernandez",
        "contact_email": "roberto.hernandez@defisoluciones.mx",
        "region": "LATAM",
    },
    {
        "company_name": "Blockchain Patagonia S.A.",
        "contact_name": "Laura Fernandez",
        "contact_email": "lfernandez@blockchainpatagonia.com.ar",
        "region": "LATAM",
    },
    {
        "company_name": "NovaPay Colombia S.A.S.",
        "contact_name": "Santiago Ramirez",
        "contact_email": "santiago@novapay.co",
        "region": "LATAM",
    },
    {
        "company_name": "DigitalVault Peru S.A.C.",
        "contact_name": "Claudia Vargas",
        "contact_email": "cvargas@digitalvault.pe",
        "region": "LATAM",
    },
    {
        "company_name": "Iberica Crypto Ventures S.L.",
        "contact_name": "Alejandro Garcia",
        "contact_email": "alejandro.garcia@ibericacrypto.es",
        "region": "Iberia",
    },
    {
        "company_name": "Rio Ventures Capital S.A.",
        "contact_name": "Valentina Costa",
        "contact_email": "valentina.costa@rioventures.com.br",
        "region": "LATAM",
    },
    {
        "company_name": "Pampas Digital S.A.",
        "contact_name": "Diego Alvarez",
        "contact_email": "diego.alvarez@pampasdigital.com.ar",
        "region": "LATAM",
    },
]


# ---------------------------------------------------------------------------
# Sample data: tickets (20 total)
# ---------------------------------------------------------------------------

# 5 billing tickets
BILLING_TICKETS = [
    {
        "subject": "Me cobraron dos veces la suscripcion Pro",
        "description": (
            "Buen dia. Revise mi tarjeta y veo que me debitaron dos veces el monto "
            "del plan Pro este mes. El primer cobro fue el dia 5 y el segundo el dia 7. "
            "Necesito que me hagan el reembolso del cobro duplicado lo antes posible."
        ),
        "priority": TicketPriorityEnum.HIGH,
        "category": "billing",
    },
    {
        "subject": "Quiero cambiar mi plan de Premium a Gratuito",
        "description": (
            "Hola, necesito cancelar mi plan Premium y volver al plan Gratuito. "
            "No estoy usando las funcionalidades avanzadas y prefiero ahorrar. "
            "Como puedo hacer el downgrade?"
        ),
        "priority": TicketPriorityEnum.LOW,
        "category": "billing",
    },
    {
        "subject": "No me llega la factura mensual",
        "description": (
            "Hace dos meses que no recibo la factura de mi suscripcion por email. "
            "Necesito los comprobantes para mi contador porque tengo que presentar "
            "la declaracion de impuestos ante AFIP. Pueden reenviarlas?"
        ),
        "priority": TicketPriorityEnum.MEDIUM,
        "category": "billing",
    },
    {
        "subject": "Consulta sobre comisiones de trading",
        "description": (
            "Quisiera saber cual es la comision exacta que se cobra por operaciones "
            "de compra y venta de cripto en el plan Pro. En la app veo un porcentaje "
            "pero no coincide con lo que dice la pagina web."
        ),
        "priority": TicketPriorityEnum.LOW,
        "category": "billing",
    },
    {
        "subject": "Cargo no reconocido en mi tarjeta de credito",
        "description": (
            "URGENTE - Aparece un cargo de USD 24.99 de Xcapit en mi tarjeta de credito "
            "pero yo nunca autorice ese pago. No tengo plan Premium. Creo que puede ser "
            "un fraude. Necesito que investiguen esto inmediatamente!"
        ),
        "priority": TicketPriorityEnum.URGENT,
        "category": "billing",
    },
]

# 5 technical tickets
TECHNICAL_TICKETS = [
    {
        "subject": "La app se cierra sola cuando intento operar",
        "description": (
            "Desde la ultima actualizacion la app se cierra sola cada vez que intento "
            "hacer una operacion de compra. Tengo un iPhone 13 con iOS 17.2. "
            "Ya probe reinstalar pero sigue pasando. Error crash en pantalla de orden."
        ),
        "priority": TicketPriorityEnum.HIGH,
        "category": "technical",
    },
    {
        "subject": "Error 500 al usar la API de cotizaciones",
        "description": (
            "Hola equipo tecnico. Estoy integrando la API de Xcapit en nuestro sistema "
            "y estoy recibiendo error 500 al hacer GET /api/v1/market/prices. "
            "Antes funcionaba bien. Adjunto los logs del request."
        ),
        "priority": TicketPriorityEnum.HIGH,
        "category": "technical",
    },
    {
        "subject": "Las cotizaciones no se actualizan en la app",
        "description": (
            "Desde hace 2 horas las cotizaciones de Bitcoin y Ethereum no se actualizan "
            "en la pantalla principal. Siempre muestra el mismo precio. Ya reinicie la app "
            "y probe con WiFi y datos moviles."
        ),
        "priority": TicketPriorityEnum.MEDIUM,
        "category": "technical",
    },
    {
        "subject": "Pantalla en blanco al ingresar a la seccion Staking",
        "description": (
            "Cuando toco en la seccion de Staking me aparece una pantalla completamente "
            "en blanco. En el resto de la app funciona todo bien. Uso Android 12 en un "
            "Samsung Galaxy S21. Version de la app: 3.2.1."
        ),
        "priority": TicketPriorityEnum.MEDIUM,
        "category": "technical",
    },
    {
        "subject": "Timeout constante en la version web",
        "description": (
            "La version web de app.xcapit.com me da timeout todo el tiempo. Tarda mas "
            "de 30 segundos en cargar y muchas veces no carga. Probe en Chrome y Firefox "
            "con el mismo resultado. Mi internet funciona bien para otras paginas."
        ),
        "priority": TicketPriorityEnum.MEDIUM,
        "category": "technical",
    },
]

# 5 crypto/wallet tickets
CRYPTO_TICKETS = [
    {
        "subject": "Mi deposito de USDT no aparece en mi billetera",
        "description": (
            "Hice un deposito de 500 USDT por red TRC20 hace 6 horas y todavia no "
            "aparece en mi billetera de Xcapit. Tengo el hash de la transaccion: "
            "a1b2c3d4e5f6. El explorador de Tron muestra que la transaccion fue confirmada."
        ),
        "priority": TicketPriorityEnum.HIGH,
        "category": "crypto",
    },
    {
        "subject": "URGENTE - Me robaron los fondos de la wallet!!!",
        "description": (
            "URGENTE POR FAVOR AYUDA! Acabo de entrar a mi cuenta y mi wallet esta vacia! "
            "Tenia 2 BTC y 10.000 USDT. No hice ninguna transferencia. Creo que me "
            "hackearon la cuenta. Necesito que bloqueen todo AHORA!!! Es todo mi dinero!!!"
        ),
        "priority": TicketPriorityEnum.URGENT,
        "category": "crypto",
    },
    {
        "subject": "Consulta sobre staking de Ethereum",
        "description": (
            "Hola, tengo algunas dudas sobre el staking de ETH. Cual es el rendimiento "
            "actual? Puedo retirar antes del periodo minimo? Que pasa si baja el precio "
            "de ETH mientras esta stakeado? Gracias."
        ),
        "priority": TicketPriorityEnum.LOW,
        "category": "crypto",
    },
    {
        "subject": "Envie cripto por la red equivocada",
        "description": (
            "Cometi un error grave. Envie USDT por red ERC20 a una direccion que era BEP20 "
            "en Xcapit. Son 1.200 USDT que representan un monto importante para mi. "
            "Es posible recuperar los fondos? Estoy muy preocupado."
        ),
        "priority": TicketPriorityEnum.URGENT,
        "category": "crypto",
    },
    {
        "subject": "Transaccion de swap pendiente hace 24 horas",
        "description": (
            "Hice un swap de BTC a ETH ayer a las 14:00 y todavia aparece como pendiente. "
            "Normalmente es instantaneo. El monto es 0.5 BTC. Pueden revisar que esta "
            "pasando con la transaccion?"
        ),
        "priority": TicketPriorityEnum.HIGH,
        "category": "crypto",
    },
]

# 3 account tickets
ACCOUNT_TICKETS = [
    {
        "subject": "No puedo iniciar sesion - olvide mi contrasena",
        "description": (
            "Intente cambiar mi contrasena pero el email de recuperacion no me llega. "
            "Ya revise la carpeta de spam. Mi email registrado es carlos@ejemplo.com. "
            "Necesito acceder a mi cuenta con urgencia porque tengo operaciones abiertas."
        ),
        "priority": TicketPriorityEnum.HIGH,
        "category": "account",
    },
    {
        "subject": "Mi cuenta esta bloqueada despues de varios intentos",
        "description": (
            "Intente ingresar varias veces con la contrasena incorrecta y ahora mi cuenta "
            "esta bloqueada. Dice que tengo que esperar 30 minutos pero ya paso una hora "
            "y sigue bloqueada. Pueden desbloquearla manualmente?"
        ),
        "priority": TicketPriorityEnum.MEDIUM,
        "category": "account",
    },
    {
        "subject": "Quiero eliminar mi cuenta y descargar mis datos",
        "description": (
            "Por motivos personales quiero eliminar mi cuenta de Xcapit. Antes de eso "
            "necesito descargar todos mis datos personales y el historial de transacciones "
            "como establece la ley de proteccion de datos. Pueden guiarme?"
        ),
        "priority": TicketPriorityEnum.LOW,
        "category": "account",
    },
]

# 2 general query tickets
GENERAL_TICKETS = [
    {
        "subject": "Consulta sobre las criptomonedas disponibles",
        "description": (
            "Hola, quiero saber si tienen pensado agregar Solana (SOL) y Avalanche (AVAX) "
            "a la plataforma. Tambien me gustaria saber si ofrecen algun tipo de cartera "
            "de inversion automatica diversificada."
        ),
        "priority": TicketPriorityEnum.LOW,
        "category": "general",
    },
    {
        "subject": "Informacion sobre el programa de referidos",
        "description": (
            "Hola equipo! Me gustaria saber si Xcapit tiene un programa de referidos. "
            "Tengo varios amigos interesados en la plataforma y me gustaria saber si "
            "hay algun beneficio por recomendarlos."
        ),
        "priority": TicketPriorityEnum.LOW,
        "category": "general",
    },
]

ALL_TICKETS = BILLING_TICKETS + TECHNICAL_TICKETS + CRYPTO_TICKETS + ACCOUNT_TICKETS + GENERAL_TICKETS


# ---------------------------------------------------------------------------
# Sample data: ticket messages (2-3 per ticket)
# ---------------------------------------------------------------------------

def build_messages_for_ticket(ticket_data: dict, ticket_index: int) -> list[dict]:
    """Generate 2-3 realistic messages for a ticket."""
    messages: list[dict] = []

    # First message is always from the customer (reiterating the issue)
    customer_followups = [
        "Pueden darme una actualizacion? Necesito resolver esto pronto.",
        "Sigo esperando respuesta. Es un tema importante para mi.",
        "Hola, alguien puede ayudarme con esto?",
        "Les recuerdo que este tema sigue sin resolverse.",
        "Buen dia, hay novedades sobre mi caso?",
        "Ya pasaron varias horas y no recibo respuesta.",
        "Agradeceria una pronta respuesta, gracias.",
        "Disculpen la insistencia pero necesito una solucion.",
        "Hola de nuevo, este tema es prioritario para mi negocio.",
        "Estoy a la espera de su respuesta. Muchas gracias.",
    ]

    agent_responses = [
        (
            "Hola! Gracias por contactarnos. Ya estamos revisando tu caso. "
            "Te pedimos un poco de paciencia mientras nuestro equipo investiga."
        ),
        (
            "Buen dia! Recibimos tu consulta y la derivamos al area especializada. "
            "En breve te estaremos dando una respuesta."
        ),
        (
            "Hola! Lamentamos el inconveniente. Nuestro equipo tecnico ya esta "
            "trabajando en tu caso. Te mantendremos informado."
        ),
        (
            "Gracias por escribirnos. Entendemos la urgencia de tu caso y "
            "lo estamos priorizando. Te contactamos a la brevedad."
        ),
        (
            "Hola! Ya pudimos identificar el problema. Estamos trabajando en la "
            "solucion y esperamos resolverlo dentro de las proximas horas."
        ),
        (
            "Buen dia! Revisamos tu caso en detalle. Te enviamos los pasos a "
            "seguir para resolverlo. Por favor revisalos y contanos si te sirvieron."
        ),
        (
            "Hola! Ya escalamos tu caso al equipo senior. Dada la naturaleza del "
            "problema, necesitamos un poco mas de tiempo. Te avisamos apenas tengamos novedades."
        ),
        (
            "Gracias por la paciencia. Pudimos replicar el error que describis "
            "y nuestro equipo de desarrollo ya tiene un fix en proceso."
        ),
    ]

    # Customer message
    messages.append({
        "sender": "customer",
        "content": customer_followups[ticket_index % len(customer_followups)],
    })

    # Agent response
    messages.append({
        "sender": "agent",
        "content": agent_responses[ticket_index % len(agent_responses)],
    })

    # Some tickets get a third message (customer follow-up)
    if ticket_index % 3 == 0:
        third_messages = [
            "Perfecto, muchas gracias por la rapida respuesta. Quedo a la espera.",
            "Entendido, gracias por la informacion. Espero la solucion.",
            "Ok, gracias. Les agradezco que lo esten priorizando.",
        ]
        messages.append({
            "sender": "customer",
            "content": third_messages[ticket_index % len(third_messages)],
        })

    return messages


# ---------------------------------------------------------------------------
# Sample data: outreach messages
# ---------------------------------------------------------------------------

OUTREACH_MESSAGES = [
    {
        "channel": "email",
        "subject": "Oportunidad exclusiva de inversion automatizada para su empresa",
        "body": (
            "Hola, soy del equipo de Xcapit. Nos gustaria presentarle nuestras soluciones "
            "de inversion automatizada y gestion de activos digitales. Nuestras estrategias "
            "DeFi estan generando rendimientos consistentes para empresas lideres en LATAM."
        ),
        "status": "sent",
    },
    {
        "channel": "linkedin",
        "subject": None,
        "body": (
            "Hola! Vi tu perfil y me parecio muy interesante tu trayectoria. "
            "Lidero alianzas estrategicas en Xcapit, donde ayudamos a empresas "
            "a implementar soluciones de inversion automatizada."
        ),
        "status": "sent",
    },
    {
        "channel": "email",
        "subject": "Caso de exito: optimizacion de portafolio con Xcapit",
        "body": (
            "Hola! Queria compartirte un caso de exito reciente. Una empresa similar "
            "logro optimizar su portafolio un 35% utilizando nuestras soluciones de "
            "inversion automatizada y estrategias DeFi."
        ),
        "status": "replied",
    },
    {
        "channel": "whatsapp",
        "subject": None,
        "body": (
            "Hola! Soy del equipo de Xcapit. Queria comentarte sobre una oportunidad "
            "exclusiva de inversion automatizada. Nuestras estrategias DeFi estan "
            "generando resultados muy interesantes en la region."
        ),
        "status": "draft",
    },
    {
        "channel": "email",
        "subject": "Recursos gratuitos sobre gestion de activos digitales",
        "body": (
            "Hola! Te dejo un enlace a nuestros recursos gratuitos sobre inversion "
            "automatizada y optimizacion de portafolio. Espero que te resulten utiles. "
            "Si necesitas apoyo en esta area, no dudes en contactarnos."
        ),
        "status": "sent",
    },
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


async def seed_leads(db) -> int:
    """Seed leads from the TSV file. Returns count of imported leads."""
    if not LEADS_SEED_FILE.exists():
        print(f"  WARNING: {LEADS_SEED_FILE} not found, skipping lead import")
        return 0

    existing_count = await db.scalar(select(func.count(Lead.id))) or 0
    if existing_count > 0:
        print(f"  Leads already exist ({existing_count}), skipping TSV import")
        return existing_count

    count = await import_from_file(db, str(LEADS_SEED_FILE))
    await db.flush()
    return count


async def seed_knowledge_base(db) -> int:
    """Seed knowledge base articles from JSON. Returns count of articles."""
    if not KB_SEED_FILE.exists():
        print(f"  WARNING: {KB_SEED_FILE} not found, skipping KB seed")
        return 0

    existing_count = await db.scalar(select(func.count(KnowledgeArticle.id))) or 0
    if existing_count > 0:
        print(f"  Knowledge articles already exist ({existing_count}), skipping")
        return existing_count

    with open(KB_SEED_FILE, encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    count = 0
    for article_data in articles:
        article = KnowledgeArticle(
            title=article_data["title"],
            content=article_data["content"],
            category=article_data["category"],
            tags=article_data.get("tags"),
            is_published=True,
        )
        db.add(article)
        count += 1

    await db.flush()
    return count


async def seed_customers(db) -> int:
    """Seed sample customers. Returns count of created customers."""
    existing_count = await db.scalar(select(func.count(Customer.id))) or 0
    if existing_count > 0:
        print(f"  Customers already exist ({existing_count}), skipping")
        return existing_count

    count = 0
    for cust_data in SAMPLE_CUSTOMERS:
        customer = Customer(
            company_name=cust_data["company_name"],
            contact_name=cust_data["contact_name"],
            contact_email=cust_data["contact_email"],
            region=cust_data["region"],
        )
        db.add(customer)
        count += 1

    await db.flush()
    return count


async def seed_tickets(db) -> tuple[int, int]:
    """Seed sample tickets with messages. Returns (ticket_count, message_count)."""
    existing_tickets = await db.scalar(select(func.count(Ticket.id))) or 0
    if existing_tickets > 0:
        print(f"  Tickets already exist ({existing_tickets}), skipping")
        existing_msgs = await db.scalar(select(func.count(TicketMessage.id))) or 0
        return existing_tickets, existing_msgs

    # Get customer IDs
    result = await db.execute(select(Customer.id).order_by(Customer.id))
    customer_ids = [row[0] for row in result]

    if not customer_ids:
        print("  WARNING: No customers found, cannot create tickets")
        return 0, 0

    ticket_count = 0
    message_count = 0

    for i, ticket_data in enumerate(ALL_TICKETS):
        # Round-robin assign to customers
        customer_id = customer_ids[i % len(customer_ids)]

        ticket = Ticket(
            customer_id=customer_id,
            subject=ticket_data["subject"],
            description=ticket_data["description"],
            priority=ticket_data["priority"].value,
            category=ticket_data["category"],
        )
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        ticket_count += 1

        # Add messages for this ticket
        messages = build_messages_for_ticket(ticket_data, i)
        for msg_data in messages:
            msg = TicketMessage(
                ticket_id=ticket.id,
                sender=msg_data["sender"],
                content=msg_data["content"],
            )
            db.add(msg)
            message_count += 1

    await db.flush()
    return ticket_count, message_count


async def seed_outreach_messages(db) -> int:
    """Seed outreach messages linked to top leads. Returns count."""
    existing_count = await db.scalar(select(func.count(OutreachMessage.id))) or 0
    if existing_count > 0:
        print(f"  Outreach messages already exist ({existing_count}), skipping")
        return existing_count

    # Get top 5 leads by score
    result = await db.execute(
        select(Lead.id)
        .where(Lead.score_icp.isnot(None))
        .order_by(Lead.score_icp.desc())
        .limit(5)
    )
    top_lead_ids = [row[0] for row in result]

    if not top_lead_ids:
        print("  WARNING: No leads found, cannot create outreach messages")
        return 0

    count = 0
    for i, msg_data in enumerate(OUTREACH_MESSAGES):
        lead_id = top_lead_ids[i % len(top_lead_ids)]
        outreach = OutreachMessage(
            lead_id=lead_id,
            channel=msg_data["channel"],
            subject=msg_data["subject"],
            body=msg_data["body"],
            status=msg_data["status"],
            generated_by="outreach_composer",
        )
        db.add(outreach)
        count += 1

    await db.flush()
    return count


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------


def print_summary(
    leads_count: int,
    kb_count: int,
    customers_count: int,
    tickets_count: int,
    messages_count: int,
    outreach_count: int,
) -> None:
    """Print a comprehensive summary of seeded data."""
    print()
    print("=" * 60)
    print("  XCAPITSFF — SEED SUMMARY")
    print("=" * 60)
    print()
    print(f"  {'Leads:':<30} {leads_count:>6}")
    print(f"  {'Knowledge Articles:':<30} {kb_count:>6}")
    print(f"  {'Customers:':<30} {customers_count:>6}")
    print(f"  {'Tickets:':<30} {tickets_count:>6}")
    print(f"  {'Ticket Messages:':<30} {messages_count:>6}")
    print(f"  {'Outreach Messages:':<30} {outreach_count:>6}")
    print()
    total = leads_count + kb_count + customers_count + tickets_count + messages_count + outreach_count
    print(f"  {'TOTAL RECORDS:':<30} {total:>6}")
    print()
    print("=" * 60)
    print()
    print("  To start the API server:")
    print("    PYTHONPATH=src uvicorn xcapitsff.api.app:app --reload")
    print()
    print("  To run tests:")
    print("    PYTHONPATH=src pytest tests/ -v")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    print()
    print("=" * 60)
    print("  XCAPITSFF — MASTER SEED SCRIPT")
    print("=" * 60)
    print()

    # 1. Initialize database
    print("[1/6] Initializing database...")
    await init_db()
    print("  Database initialized.")
    print()

    async with async_session() as db:
        # 2. Seed leads
        print("[2/6] Seeding leads from TSV...")
        leads_count = await seed_leads(db)
        print(f"  Leads: {leads_count}")
        print()

        # 3. Seed knowledge base
        print("[3/6] Seeding knowledge base...")
        kb_count = await seed_knowledge_base(db)
        print(f"  Knowledge articles: {kb_count}")
        print()

        # 4. Seed customers
        print("[4/6] Seeding customers...")
        customers_count = await seed_customers(db)
        print(f"  Customers: {customers_count}")
        print()

        # 5. Seed tickets and messages
        print("[5/6] Seeding tickets and messages...")
        tickets_count, messages_count = await seed_tickets(db)
        print(f"  Tickets: {tickets_count}")
        print(f"  Messages: {messages_count}")
        print()

        # 6. Seed outreach messages
        print("[6/6] Seeding outreach messages...")
        outreach_count = await seed_outreach_messages(db)
        print(f"  Outreach messages: {outreach_count}")
        print()

        # Commit everything
        await db.commit()

    # Print summary
    print_summary(
        leads_count=leads_count,
        kb_count=kb_count,
        customers_count=customers_count,
        tickets_count=tickets_count,
        messages_count=messages_count,
        outreach_count=outreach_count,
    )


if __name__ == "__main__":
    asyncio.run(main())
