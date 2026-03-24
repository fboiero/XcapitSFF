"""Contract Generator — create service agreements from proposals.

Generates a standard service agreement document from the proposal data,
ready for client signature.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Contract:
    contract_id: str
    client_name: str
    client_email: str
    plan: str
    monthly_amount: float
    annual_amount: float
    start_date: datetime
    term_months: int = 12
    auto_renew: bool = True
    modules_included: list[str] = field(default_factory=list)
    sla_uptime: str = "99.9%"
    support_level: str = "standard"
    created_at: datetime = field(default_factory=datetime.now)
    signed_at: datetime | None = None
    status: str = "draft"  # draft, sent, signed, active, cancelled
    # Custom project contract fields
    project_name: str = ""
    scope: str = ""
    total_amount: float | None = None
    currency: str = "USD"
    payment_terms: str = ""
    end_date: datetime | None = None


class ContractGenerator:
    """Generates contracts from proposals."""

    def __init__(self):
        self._contracts: dict[str, Contract] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"CTR-{self._counter:06d}"

    def generate(
        self,
        client_name: str,
        client_email: str,
        plan: str,
        modules: list[str] | None = None,
        term_months: int = 12,
        # NEW: Custom project contract fields
        project_name: str = "",
        scope: str = "",
        total_amount: float | None = None,
        currency: str = "USD",
        payment_terms: str = "",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Contract:
        pricing = {
            "free": (0, 0),
            "pro": (99, 99 * 12),
            "enterprise": (499, 499 * 12),
        }

        # Use custom total_amount if provided, otherwise use plan pricing
        if total_amount is not None:
            monthly = total_amount / max(term_months, 1)
            annual = total_amount
        else:
            monthly, annual = pricing.get(plan, (99, 99 * 12))

        sla = {"free": "99%", "pro": "99.5%", "enterprise": "99.9%"}
        support = {"free": "email", "pro": "priority", "enterprise": "dedicated_24_7"}

        contract = Contract(
            contract_id=self._next_id(),
            client_name=client_name,
            client_email=client_email,
            plan=plan,
            monthly_amount=monthly,
            annual_amount=annual,
            start_date=start_date or datetime.now(),
            term_months=term_months,
            modules_included=modules or [],
            sla_uptime=sla.get(plan, "99%"),
            support_level=support.get(plan, "standard"),
            # Set custom project contract fields
            project_name=project_name,
            scope=scope,
            total_amount=total_amount,
            currency=currency,
            payment_terms=payment_terms,
            end_date=end_date,
        )
        self._contracts[contract.contract_id] = contract
        return contract

    def to_markdown(self, contract: Contract) -> str:
        # Determine if showing project-specific or plan pricing
        if contract.total_amount:
            # Project-specific contract
            pricing_section = f"""## Detalles del Proyecto
- **Nombre del proyecto:** {contract.project_name}
- **Alcance:** {contract.scope}
- **Monto total:** {contract.currency} ${contract.total_amount:,.2f}
- **Monto mensual (distribuido):** {contract.currency} ${contract.monthly_amount:,.2f}/mes
- **Condiciones de pago:** {contract.payment_terms}
- **Fecha de inicio:** {contract.start_date.strftime('%d/%m/%Y')}
- **Fecha de finalización:** {contract.end_date.strftime('%d/%m/%Y') if contract.end_date else 'Por definir'}
- **Duración:** {contract.term_months} meses"""
        else:
            # Standard plan-based contract
            pricing_section = f"""## Plan Contratado
- **Plan:** {contract.plan.capitalize()}
- **Monto mensual:** USD ${contract.monthly_amount}/mes
- **Monto anual:** USD ${contract.annual_amount}/año
- **Duración:** {contract.term_months} meses
- **Renovación automática:** {'Sí' if contract.auto_renew else 'No'}
- **Fecha de inicio:** {contract.start_date.strftime('%d/%m/%Y')}"""

        return f"""# Acuerdo de Servicio — XcapitSFF

## Partes
- **Proveedor:** Xcapit Software Factory
- **Cliente:** {contract.client_name} ({contract.client_email})

{pricing_section}

## Módulos Incluidos
{chr(10).join(f'- {m}' for m in contract.modules_included) if contract.modules_included else '- Todos los módulos del plan seleccionado'}

## Nivel de Servicio (SLA)
- **Disponibilidad garantizada:** {contract.sla_uptime}
- **Soporte:** {contract.support_level}
- **Tiempo de respuesta:** {'4 horas' if contract.plan == 'enterprise' else '24 horas' if contract.plan == 'pro' else '48 horas'}

## Términos Generales
1. Los datos son propiedad exclusiva del Cliente.
2. El Cliente puede exportar todos sus datos en cualquier momento.
3. El servicio puede cancelarse con 30 días de preaviso.
4. Los precios se mantienen fijos durante el período contratado.
5. Las actualizaciones del software están incluidas sin costo adicional.

## Protección de Datos
- Cumplimiento GDPR y regulaciones locales aplicables
- Datos almacenados en infraestructura segura
- Encriptación en tránsito y en reposo
- Backups diarios automáticos

## Firmas

Proveedor: _________________________ Fecha: _________

Cliente: _________________________ Fecha: _________

---
*Documento generado automáticamente por XcapitSFF*
*Contrato ID: {contract.contract_id}*
"""

    def get_contract(self, contract_id: str) -> Contract | None:
        return self._contracts.get(contract_id)

    def sign_contract(self, contract_id: str) -> Contract | None:
        contract = self._contracts.get(contract_id)
        if not contract:
            return None
        contract.signed_at = datetime.now()
        contract.status = "signed"
        return contract

    def list_contracts(self, status: str | None = None) -> list[Contract]:
        contracts = list(self._contracts.values())
        if status:
            contracts = [c for c in contracts if c.status == status]
        return contracts


# Singleton
contract_generator = ContractGenerator()
