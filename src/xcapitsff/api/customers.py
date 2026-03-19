"""API endpoints for Customer management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.schemas import CustomerCreate, CustomerResponse
from xcapitsff.support.tickets import create_customer, get_customer, get_customers

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("/", response_model=CustomerResponse, status_code=201)
async def api_create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    return await create_customer(
        db,
        company_name=data.company_name,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        region=data.region.value,
    )


@router.get("/", response_model=list[CustomerResponse])
async def api_list_customers(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await get_customers(db, limit, offset)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def api_get_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    customer = await get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer
