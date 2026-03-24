"""API endpoints for Contract management."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.discovery.contracts import contract_generator

router = APIRouter(prefix="/contracts", tags=["Contracts"])


class GenerateContractRequest(BaseModel):
    client_name: str
    client_email: str
    plan: str = "pro"
    modules: list[str] = []
    term_months: int = 12
    # Custom project contract fields
    project_name: str = ""
    scope: str = ""
    total_amount: float | None = None
    currency: str = "USD"
    payment_terms: str = ""
    start_date: str | None = None
    end_date: str | None = None


@router.post("/", status_code=201)
async def generate_contract(req: GenerateContractRequest):
    # Parse dates if provided
    start_date = None
    if req.start_date:
        try:
            start_date = datetime.fromisoformat(req.start_date)
        except (ValueError, TypeError):
            pass

    end_date = None
    if req.end_date:
        try:
            end_date = datetime.fromisoformat(req.end_date)
        except (ValueError, TypeError):
            pass

    contract = contract_generator.generate(
        client_name=req.client_name,
        client_email=req.client_email,
        plan=req.plan,
        modules=req.modules,
        term_months=req.term_months,
        project_name=req.project_name,
        scope=req.scope,
        total_amount=req.total_amount,
        currency=req.currency,
        payment_terms=req.payment_terms,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "contract_id": contract.contract_id,
        "client": contract.client_name,
        "plan": contract.plan,
        "monthly": contract.monthly_amount,
        "annual": contract.annual_amount,
        "project_name": contract.project_name,
        "total_amount": contract.total_amount,
        "status": contract.status,
    }


@router.get("/{contract_id}")
async def get_contract(contract_id: str):
    contract = contract_generator.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return {
        "contract_id": contract.contract_id,
        "client": contract.client_name,
        "plan": contract.plan,
        "monthly": contract.monthly_amount,
        "annual": contract.annual_amount,
        "sla": contract.sla_uptime,
        "support": contract.support_level,
        "status": contract.status,
        "signed_at": contract.signed_at.isoformat() if contract.signed_at else None,
    }


@router.get("/{contract_id}/markdown")
async def get_contract_markdown(contract_id: str):
    contract = contract_generator.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    md = contract_generator.to_markdown(contract)
    return {"contract_id": contract_id, "markdown": md}


@router.post("/{contract_id}/sign")
async def sign_contract(contract_id: str):
    contract = contract_generator.sign_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return {"contract_id": contract_id, "status": "signed", "signed_at": contract.signed_at.isoformat()}


@router.get("/")
async def list_contracts(status: str | None = None):
    contracts = contract_generator.list_contracts(status)
    return {
        "count": len(contracts),
        "contracts": [
            {
                "contract_id": c.contract_id,
                "client": c.client_name,
                "plan": c.plan,
                "monthly": c.monthly_amount,
                "status": c.status,
            }
            for c in contracts
        ],
    }
