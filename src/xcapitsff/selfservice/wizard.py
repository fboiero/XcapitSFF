"""Setup Wizard engine for self-service onboarding."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FormField:
    """A single field inside a wizard step."""

    name: str
    label: str
    type: str  # text / email / select / multiselect / toggle / number
    required: bool = True
    options: list[str] | None = None
    default: Any = None
    help_text: str = ""


@dataclass
class WizardStep:
    """One step of the setup wizard."""

    step_id: str
    title: str
    description: str
    type: str  # form / choice / import / configure / test
    fields: list[FormField] = field(default_factory=list)
    is_completed: bool = False
    is_skippable: bool = False
    completion_action: str = ""


@dataclass
class WizardProgress:
    """Tracks a tenant's progress through the wizard."""

    tenant_id: str
    current_step: str
    completed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str | None = None
    configuration: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pre-built steps (all copy in Spanish)
# ---------------------------------------------------------------------------

def _build_steps() -> list[WizardStep]:
    """Return the ordered list of wizard steps."""

    step1 = WizardStep(
        step_id="company_profile",
        title="Perfil de tu empresa",
        description="Contanos sobre tu empresa para personalizar tu experiencia.",
        type="form",
        completion_action="/api/v1/wizard/actions/company_profile",
        fields=[
            FormField(
                name="company_name",
                label="Nombre de la empresa",
                type="text",
                required=True,
                help_text="Ingres\u00e1 el nombre legal o comercial de tu empresa.",
            ),
            FormField(
                name="industry",
                label="Industria",
                type="select",
                required=True,
                options=["fintech", "tech", "consulting", "ecommerce", "healthcare", "education", "other"],
                help_text="Seleccion\u00e1 la industria que mejor represente a tu empresa.",
            ),
            FormField(
                name="company_size",
                label="Tama\u00f1o del equipo",
                type="select",
                required=True,
                options=["1-10", "11-50", "51-200", "200+"],
                help_text="Eleg\u00ed el rango que mejor se ajuste.",
            ),
            FormField(
                name="website",
                label="Sitio web",
                type="text",
                required=False,
                help_text="URL del sitio web de tu empresa (opcional).",
            ),
            FormField(
                name="primary_market",
                label="Mercado principal",
                type="select",
                required=True,
                options=["LATAM", "Iberia", "Global"],
                help_text="Seleccion\u00e1 la regi\u00f3n principal donde oper\u00e1s.",
            ),
        ],
    )

    step2 = WizardStep(
        step_id="team_setup",
        title="Configur\u00e1 tu equipo",
        description="Invit\u00e1 a tu equipo. Pod\u00e9s agregar m\u00e1s despu\u00e9s.",
        type="form",
        completion_action="/api/v1/wizard/actions/team_setup",
        fields=[
            FormField(
                name="invite_emails",
                label="Emails del equipo",
                type="text",
                required=False,
                help_text="Invit\u00e1 a tu equipo. Pod\u00e9s agregar m\u00e1s despu\u00e9s.",
            ),
            FormField(
                name="default_role",
                label="Rol por defecto",
                type="select",
                required=True,
                options=["admin", "manager", "user"],
                default="user",
                help_text="Rol que se asignar\u00e1 a los nuevos miembros.",
            ),
        ],
    )

    step3 = WizardStep(
        step_id="sales_config",
        title="Configur\u00e1 ventas",
        description="Eleg\u00ed qu\u00e9 funcionalidades de ventas necesit\u00e1s.",
        type="configure",
        completion_action="/api/v1/wizard/actions/sales_config",
        fields=[
            FormField(
                name="use_sales",
                label="Activar m\u00f3dulo de ventas",
                type="toggle",
                required=True,
                default=True,
                help_text="Eleg\u00ed qu\u00e9 funcionalidades de ventas necesit\u00e1s.",
            ),
            FormField(
                name="scoring_model",
                label="Modelo de scoring",
                type="select",
                required=False,
                options=["basic", "advanced"],
                default="basic",
                help_text="El modelo avanzado usa m\u00e1s variables para calificar leads.",
            ),
            FormField(
                name="pipeline_stages",
                label="Etapas del pipeline",
                type="multiselect",
                required=False,
                options=[
                    "raw", "contacted", "qualified", "proposal",
                    "negotiation", "won", "lost", "churned",
                ],
                default=["raw", "contacted", "qualified", "proposal", "won", "lost"],
                help_text="Seleccion\u00e1 las etapas de tu pipeline de ventas.",
            ),
            FormField(
                name="auto_qualify",
                label="Calificaci\u00f3n autom\u00e1tica",
                type="toggle",
                required=False,
                default=False,
                help_text="Calificar leads autom\u00e1ticamente seg\u00fan el score.",
            ),
            FormField(
                name="auto_qualify_threshold",
                label="Umbral de calificaci\u00f3n",
                type="number",
                required=False,
                default=60,
                help_text="Score m\u00ednimo para calificaci\u00f3n autom\u00e1tica (0-100).",
            ),
        ],
    )

    step4 = WizardStep(
        step_id="support_config",
        title="Configur\u00e1 soporte",
        description="Configur\u00e1 c\u00f3mo quer\u00e9s manejar tickets de soporte.",
        type="configure",
        completion_action="/api/v1/wizard/actions/support_config",
        fields=[
            FormField(
                name="use_support",
                label="Activar m\u00f3dulo de soporte",
                type="toggle",
                required=True,
                default=True,
                help_text="Configur\u00e1 c\u00f3mo quer\u00e9s manejar tickets de soporte.",
            ),
            FormField(
                name="sla_enabled",
                label="Activar SLA",
                type="toggle",
                required=False,
                default=False,
                help_text="Habilit\u00e1 acuerdos de nivel de servicio.",
            ),
            FormField(
                name="default_sla_hours",
                label="SLA por defecto (horas)",
                type="number",
                required=False,
                default=24,
                help_text="Tiempo m\u00e1ximo de respuesta en horas.",
            ),
            FormField(
                name="auto_routing",
                label="Ruteo autom\u00e1tico",
                type="toggle",
                required=False,
                default=False,
                help_text="Asignar tickets autom\u00e1ticamente al agente adecuado.",
            ),
            FormField(
                name="kb_enabled",
                label="Base de conocimiento",
                type="toggle",
                required=False,
                default=True,
                help_text="Habilit\u00e1 la base de conocimiento para autoservicio.",
            ),
        ],
    )

    step5 = WizardStep(
        step_id="import_data",
        title="Import\u00e1 tus datos",
        description="Import\u00e1 leads existentes o empez\u00e1 de cero.",
        type="import",
        is_skippable=True,
        completion_action="/api/v1/wizard/actions/import_data",
        fields=[
            FormField(
                name="import_source",
                label="Fuente de importaci\u00f3n",
                type="select",
                required=False,
                options=["csv", "salesforce", "hubspot", "skip"],
                default="skip",
                help_text="Import\u00e1 leads existentes o empez\u00e1 de cero.",
            ),
            FormField(
                name="file_upload",
                label="Archivo CSV",
                type="text",
                required=False,
                help_text="Sub\u00ed tu archivo CSV con los datos a importar.",
            ),
        ],
    )

    step6 = WizardStep(
        step_id="agent_config",
        title="Agentes AI",
        description="Los agentes AI van a trabajar por vos 24/7.",
        type="configure",
        completion_action="/api/v1/wizard/actions/agent_config",
        fields=[
            FormField(
                name="enable_agents",
                label="Activar agentes AI",
                type="toggle",
                required=True,
                default=True,
                help_text="Los agentes AI van a trabajar por vos 24/7.",
            ),
            FormField(
                name="agent_tone",
                label="Tono del agente",
                type="select",
                required=False,
                options=["formal", "friendly", "professional"],
                default="professional",
                help_text="Eleg\u00ed el tono de comunicaci\u00f3n de los agentes.",
            ),
            FormField(
                name="agent_language",
                label="Idioma del agente",
                type="select",
                required=False,
                options=["es_latam", "es_iberia"],
                default="es_latam",
                help_text="Seleccion\u00e1 la variante de espa\u00f1ol.",
            ),
            FormField(
                name="auto_outreach",
                label="Outreach autom\u00e1tico",
                type="toggle",
                required=False,
                default=False,
                help_text="Permite que el agente contacte leads autom\u00e1ticamente.",
            ),
            FormField(
                name="auto_respond_tickets",
                label="Respuestas autom\u00e1ticas a tickets",
                type="toggle",
                required=False,
                default=False,
                help_text="Permite que el agente responda tickets autom\u00e1ticamente.",
            ),
        ],
    )

    step7 = WizardStep(
        step_id="integrations",
        title="Integraciones",
        description="Conect\u00e1 tus herramientas favoritas.",
        type="configure",
        is_skippable=True,
        completion_action="/api/v1/wizard/actions/integrations",
        fields=[
            FormField(
                name="crm",
                label="CRM",
                type="select",
                required=False,
                options=["none", "salesforce", "hubspot"],
                default="none",
                help_text="Conect\u00e1 tu CRM para sincronizar datos.",
            ),
            FormField(
                name="notifications",
                label="Notificaciones",
                type="multiselect",
                required=False,
                options=["email", "slack", "webhook"],
                default=["email"],
                help_text="Eleg\u00ed c\u00f3mo quer\u00e9s recibir notificaciones.",
            ),
            FormField(
                name="webhook_url",
                label="URL de webhook",
                type="text",
                required=False,
                help_text="URL para recibir eventos v\u00eda webhook (opcional).",
            ),
        ],
    )

    step8 = WizardStep(
        step_id="review_and_launch",
        title="Revis\u00e1 y lanz\u00e1",
        description="Revis\u00e1 tu configuraci\u00f3n y activ\u00e1 tu workspace.",
        type="form",
        completion_action="/api/v1/wizard/actions/launch",
        fields=[],
    )

    return [step1, step2, step3, step4, step5, step6, step7, step8]


# ---------------------------------------------------------------------------
# Wizard engine
# ---------------------------------------------------------------------------


class SetupWizard:
    """Manages the multi-step setup wizard for new tenants."""

    def __init__(self) -> None:
        self._steps: list[WizardStep] = _build_steps()
        self._step_ids: list[str] = [s.step_id for s in self._steps]
        # tenant_id -> WizardProgress
        self._progress: dict[str, WizardProgress] = {}

    # -- helpers --

    def _get_step(self, step_id: str) -> WizardStep | None:
        for s in self._steps:
            return_step = WizardStep(
                step_id=s.step_id,
                title=s.title,
                description=s.description,
                type=s.type,
                fields=list(s.fields),
                is_completed=s.is_completed,
                is_skippable=s.is_skippable,
                completion_action=s.completion_action,
            )
            if s.step_id == step_id:
                return return_step
        return None

    def _next_step_id(self, current: str) -> str | None:
        idx = self._step_ids.index(current)
        if idx + 1 < len(self._step_ids):
            return self._step_ids[idx + 1]
        return None

    def _prev_step_id(self, current: str) -> str | None:
        idx = self._step_ids.index(current)
        if idx - 1 >= 0:
            return self._step_ids[idx - 1]
        return None

    def _validate_step_data(self, step: WizardStep, data: dict[str, Any]) -> list[str]:
        """Return list of validation error messages."""
        errors: list[str] = []
        for f in step.fields:
            if f.required and f.name not in data:
                errors.append(f"El campo '{f.name}' es obligatorio.")
            if f.type == "select" and f.options and f.name in data:
                if data[f.name] not in f.options:
                    errors.append(
                        f"Valor inv\u00e1lido para '{f.name}': {data[f.name]}. "
                        f"Opciones: {', '.join(f.options)}"
                    )
            if f.type == "multiselect" and f.options and f.name in data:
                val = data[f.name]
                if isinstance(val, list):
                    for v in val:
                        if v not in f.options:
                            errors.append(
                                f"Valor inv\u00e1lido en '{f.name}': {v}. "
                                f"Opciones: {', '.join(f.options)}"
                            )
            if f.type == "number" and f.name in data:
                if not isinstance(data[f.name], (int, float)):
                    errors.append(f"El campo '{f.name}' debe ser num\u00e9rico.")
        return errors

    # -- public API --

    @property
    def steps(self) -> list[WizardStep]:
        return list(self._steps)

    def start_wizard(self, tenant_id: str) -> WizardProgress:
        """Start the wizard for a tenant."""
        progress = WizardProgress(
            tenant_id=tenant_id,
            current_step=self._step_ids[0],
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._progress[tenant_id] = progress
        return progress

    def get_current_step(self, tenant_id: str) -> WizardStep:
        """Return the current step for the tenant."""
        progress = self._progress.get(tenant_id)
        if not progress:
            raise ValueError(f"No hay wizard activo para el tenant '{tenant_id}'.")
        step = self._get_step(progress.current_step)
        if not step:
            raise ValueError(f"Step '{progress.current_step}' no encontrado.")
        # Mark completed status based on progress
        step.is_completed = step.step_id in progress.completed_steps
        return step

    def submit_step(self, tenant_id: str, step_id: str, data: dict[str, Any]) -> WizardProgress:
        """Submit data for a step and advance to the next."""
        progress = self._progress.get(tenant_id)
        if not progress:
            raise ValueError(f"No hay wizard activo para el tenant '{tenant_id}'.")
        if progress.current_step != step_id:
            raise ValueError(
                f"El paso actual es '{progress.current_step}', no '{step_id}'."
            )

        step = self._get_step(step_id)
        if not step:
            raise ValueError(f"Step '{step_id}' no encontrado.")

        # Validate
        errors = self._validate_step_data(step, data)
        if errors:
            raise ValueError("; ".join(errors))

        # Save data
        progress.configuration[step_id] = data

        # Mark completed
        if step_id not in progress.completed_steps:
            progress.completed_steps.append(step_id)

        # Advance
        next_id = self._next_step_id(step_id)
        if next_id:
            progress.current_step = next_id
        return progress

    def skip_step(self, tenant_id: str, step_id: str) -> WizardProgress:
        """Skip a skippable step."""
        progress = self._progress.get(tenant_id)
        if not progress:
            raise ValueError(f"No hay wizard activo para el tenant '{tenant_id}'.")
        if progress.current_step != step_id:
            raise ValueError(
                f"El paso actual es '{progress.current_step}', no '{step_id}'."
            )

        step = self._get_step(step_id)
        if not step:
            raise ValueError(f"Step '{step_id}' no encontrado.")

        if not step.is_skippable:
            raise ValueError(f"El paso '{step_id}' no se puede omitir.")

        if step_id not in progress.skipped_steps:
            progress.skipped_steps.append(step_id)

        next_id = self._next_step_id(step_id)
        if next_id:
            progress.current_step = next_id
        return progress

    def go_back(self, tenant_id: str) -> WizardProgress:
        """Go back one step."""
        progress = self._progress.get(tenant_id)
        if not progress:
            raise ValueError(f"No hay wizard activo para el tenant '{tenant_id}'.")

        prev_id = self._prev_step_id(progress.current_step)
        if not prev_id:
            raise ValueError("Ya est\u00e1s en el primer paso.")
        progress.current_step = prev_id
        return progress

    def get_progress(self, tenant_id: str) -> WizardProgress:
        """Return the current progress for a tenant."""
        progress = self._progress.get(tenant_id)
        if not progress:
            raise ValueError(f"No hay wizard activo para el tenant '{tenant_id}'.")
        return progress

    def complete_wizard(self, tenant_id: str) -> dict[str, Any]:
        """Finalize the wizard and apply all configuration."""
        progress = self._progress.get(tenant_id)
        if not progress:
            raise ValueError(f"No hay wizard activo para el tenant '{tenant_id}'.")

        # Check that all non-skippable steps are completed
        for step in self._steps:
            if (
                not step.is_skippable
                and step.step_id not in progress.completed_steps
                and step.step_id != "review_and_launch"
            ):
                raise ValueError(
                    f"El paso '{step.step_id}' ({step.title}) debe completarse antes de lanzar."
                )

        progress.completed_at = datetime.now(timezone.utc).isoformat()

        # Apply configuration
        applied = self.apply_configuration(tenant_id, progress.configuration)

        return {
            "status": "completed",
            "tenant_id": tenant_id,
            "completed_at": progress.completed_at,
            "configuration_applied": applied,
            "steps_completed": len(progress.completed_steps),
            "steps_skipped": len(progress.skipped_steps),
        }

    def apply_configuration(self, tenant_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """Apply the accumulated configuration to activate features and set defaults.

        In production this would call actual service layers.  Here we return
        a summary of what *would* be applied.
        """
        applied: dict[str, Any] = {
            "tenant_id": tenant_id,
            "features_enabled": [],
            "settings_applied": {},
        }

        # Company profile
        company = config.get("company_profile", {})
        if company:
            applied["settings_applied"]["company"] = {
                "name": company.get("company_name"),
                "industry": company.get("industry"),
                "size": company.get("company_size"),
                "market": company.get("primary_market"),
            }

        # Sales
        sales = config.get("sales_config", {})
        if sales.get("use_sales"):
            applied["features_enabled"].append("sales")
            applied["settings_applied"]["sales"] = {
                "scoring_model": sales.get("scoring_model", "basic"),
                "pipeline_stages": sales.get("pipeline_stages"),
                "auto_qualify": sales.get("auto_qualify", False),
                "auto_qualify_threshold": sales.get("auto_qualify_threshold", 60),
            }

        # Support
        support = config.get("support_config", {})
        if support.get("use_support"):
            applied["features_enabled"].append("support")
            applied["settings_applied"]["support"] = {
                "sla_enabled": support.get("sla_enabled", False),
                "default_sla_hours": support.get("default_sla_hours", 24),
                "auto_routing": support.get("auto_routing", False),
                "kb_enabled": support.get("kb_enabled", True),
            }

        # Agents
        agents = config.get("agent_config", {})
        if agents.get("enable_agents"):
            applied["features_enabled"].append("agents")
            applied["settings_applied"]["agents"] = {
                "tone": agents.get("agent_tone", "professional"),
                "language": agents.get("agent_language", "es_latam"),
                "auto_outreach": agents.get("auto_outreach", False),
                "auto_respond_tickets": agents.get("auto_respond_tickets", False),
            }

        # Integrations
        integrations = config.get("integrations", {})
        if integrations:
            applied["settings_applied"]["integrations"] = {
                "crm": integrations.get("crm", "none"),
                "notifications": integrations.get("notifications", ["email"]),
                "webhook_url": integrations.get("webhook_url"),
            }

        # Import
        import_data = config.get("import_data", {})
        if import_data and import_data.get("import_source") != "skip":
            applied["settings_applied"]["import"] = {
                "source": import_data.get("import_source"),
            }

        return applied
