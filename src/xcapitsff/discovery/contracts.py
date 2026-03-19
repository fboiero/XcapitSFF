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
    ) -> Contract:
        pricing = {
            "free": (0, 0),
            "pro": (99, 79 * 12),
            "enterprise": (499, 399 * 12),
        }
        monthly, annual = pricing.get(plan, (99, 79 * 12))

        sla = {"free": "99%", "pro": "99.5%", "enterprise": "99.9%"}
        support = {"free": "email", "pro": "priority", "enterprise": "dedicated_24_7"}

        contract = Contract(
            contract_id=self._next_id(),
            client_name=client_name,
            client_email=client_email,
            plan=plan,
            monthly_amount=monthly,
            annual_amount=annual,
            start_date=datetime.now(),
            term_months=term_months,
            modules_included=modules or [],
            sla_uptime=sla.get(plan, "99%"),
            support_level=support.get(plan, "standard"),
        )
        self._contracts[contract.contract_id] = contract
        return contract

    def to_markdown(self, contract: Contract) -> str:
        return f"""# Acuerdo de Servicio — XcapitSFF

## Partes
- **Proveedor:** Xcapit Software Factory
- **Cliente:** {contract.client_name} ({contract.client_email})

## Plan Contratado
- **Plan:** {contract.plan.capitalize()}
- **Monto mensual:** USD ${contract.monthly_amount}/mes
- **Monto anual:** USD ${contract.annual_amount}/año
- **Duración:** {contract.term_months} meses
- **Renovación automática:** {'Sí' if contract.auto_renew else 'No'}
- **Fecha de inicio:** {contract.start_date.strftime('%d/%m/%Y')}

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
