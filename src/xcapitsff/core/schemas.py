from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# --- Enums (mirror SQLAlchemy enums for API) ---


class RegionEnum(str, Enum):
    LATAM = "LATAM"
    IBERIA = "Iberia"


class AfinidadEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class LeadStageEnum(str, Enum):
    RAW = "raw"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    MEETING = "meeting"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class TicketStatusEnum(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# --- Lead Schemas ---


class LeadCreate(BaseModel):
    company_name: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    region: RegionEnum = RegionEnum.LATAM
    c_level: bool = False
    score_icp: float | None = None
    afinidad: AfinidadEnum = AfinidadEnum.MEDIUM
    notes: str | None = None


class LeadUpdate(BaseModel):
    company_name: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    region: RegionEnum | None = None
    c_level: bool | None = None
    score_icp: float | None = None
    afinidad: AfinidadEnum | None = None
    stage: LeadStageEnum | None = None
    notes: str | None = None
    assigned_agent: str | None = None


class LeadResponse(BaseModel):
    id: int
    company_name: str | None
    contact_name: str | None
    contact_email: str | None
    region: RegionEnum
    c_level: bool
    score_icp: float | None
    afinidad: AfinidadEnum
    stage: LeadStageEnum
    notes: str | None
    assigned_agent: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadFilter(BaseModel):
    region: RegionEnum | None = None
    c_level: bool | None = None
    afinidad: AfinidadEnum | None = None
    stage: LeadStageEnum | None = None
    score_min: float | None = None
    score_max: float | None = None


# --- Customer Schemas ---


class CustomerCreate(BaseModel):
    company_name: str
    contact_name: str
    contact_email: str
    region: RegionEnum = RegionEnum.LATAM
    plan: str | None = None
    lead_id: int | None = None


class CustomerResponse(BaseModel):
    id: int
    company_name: str
    contact_name: str
    contact_email: str
    region: RegionEnum
    plan: str | None
    lead_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Ticket Schemas ---


class TicketCreate(BaseModel):
    customer_id: int
    subject: str
    description: str
    priority: TicketPriorityEnum = TicketPriorityEnum.MEDIUM
    category: str | None = None


class TicketUpdate(BaseModel):
    status: TicketStatusEnum | None = None
    priority: TicketPriorityEnum | None = None
    category: str | None = None
    assigned_agent: str | None = None
    resolution: str | None = None


class TicketResponse(BaseModel):
    id: int
    customer_id: int
    subject: str
    description: str
    status: TicketStatusEnum
    priority: TicketPriorityEnum
    category: str | None
    assigned_agent: str | None
    resolution: str | None
    sla_deadline: datetime | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class TicketMessageCreate(BaseModel):
    sender: str
    content: str


class TicketMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender: str
    content: str
    generated_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Knowledge Base ---


class ArticleCreate(BaseModel):
    title: str
    content: str
    category: str
    tags: str | None = None


class ArticleResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    tags: str | None
    is_published: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Agent Config ---


class AgentConfigCreate(BaseModel):
    name: str
    agent_type: str
    model: str = "claude-sonnet-4-6"
    system_prompt: str
    config_json: str | None = None


class AgentConfigResponse(BaseModel):
    id: int
    name: str
    agent_type: str
    model: str
    system_prompt: str
    is_active: bool
    config_json: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Analytics ---


class SalesPipelineStats(BaseModel):
    total_leads: int
    by_stage: dict[str, int]
    by_region: dict[str, int]
    by_afinidad: dict[str, int]
    avg_score_icp: float | None
    c_level_count: int
    conversion_rate: float | None


class SupportStats(BaseModel):
    total_tickets: int
    open_tickets: int
    avg_resolution_hours: float | None
    by_priority: dict[str, int]
    by_status: dict[str, int]
    by_category: dict[str, int]
