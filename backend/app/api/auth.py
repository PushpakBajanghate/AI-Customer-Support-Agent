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
