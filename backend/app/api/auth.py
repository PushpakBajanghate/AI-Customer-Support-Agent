from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.schemas.auth import (
    CustomerRegisterRequest,
    CustomerLoginRequest,
    CustomerResponse,
    TokenResponse,
)
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_customer,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account"
)
def register_customer(payload: CustomerRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new customer, hashing their password before storage."""
    existing_customer = db.query(Customer).filter(Customer.email == payload.email).first()
    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A customer with this email address already exists."
        )

    hashed_pw = hash_password(payload.password)
    new_customer = Customer(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hashed_pw,
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate customer and obtain JWT token"
)
def login_customer(payload: CustomerLoginRequest, db: Session = Depends(get_db)):
    """Authenticates customer credentials and issues a signed JWT token."""
    customer = db.query(Customer).filter(Customer.email == payload.email).first()
    if not customer or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": str(customer.id), "email": customer.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "customer": customer
    }

@router.get(
    "/me",
    response_model=CustomerResponse,
    summary="Get current authenticated customer profile"
)
def get_me(current_customer: Customer = Depends(get_current_customer)):
    """
    Returns profile information of the currently authenticated customer.
    The customer_id from this authentication context will be injected into later AI agent workflows.
    """
    return current_customer


@router.get(
    "/context",
    summary="Get customer context including orders, shipments, returns, and tickets"
)
def get_customer_full_context(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """Returns the bounded relational context for the authenticated customer."""
    from app.services.conversation import load_customer_context
    return load_customer_context(db, current_customer.id)


@router.get(
    "/demo-customers",
    summary="List available customer profiles for testing"
)
def get_demo_customers(db: Session = Depends(get_db)):
    """Returns top customer profiles from database for quick profile switching."""
    customers = db.query(Customer).order_by(Customer.id).limit(10).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone
        }
        for c in customers
    ]


@router.post(
    "/demo-login/{customer_id}",
    response_model=TokenResponse,
    summary="Quick-login as a customer for testing and evaluation"
)
def demo_login(customer_id: int, db: Session = Depends(get_db)):
    """Generates a real JWT token for the specified customer ID without password typing."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found."
        )
    token = create_access_token(data={"sub": str(customer.id), "email": customer.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "customer": customer
    }
