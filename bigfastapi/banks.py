import json
from uuid import uuid4

import fastapi
import pkg_resources
import sqlalchemy.orm as orm
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi_pagination import Page, paginate, add_pagination

from bigfastapi.db.database import get_db
from bigfastapi.models import bank_models
from bigfastapi.schemas import bank_schemas, users_schemas
from .auth_api import is_authenticated
from .models.organisation_models import is_organization_member

router = APIRouter()

BANK_DATA_PATH = pkg_resources.resource_filename('bigfastapi', 'data/')


@router.post("/banks", status_code=status.HTTP_201_CREATED, response_model=bank_schemas.BankResponse)
async def add_bank_detail(bank: bank_schemas.AddBank,
                          user: users_schemas.User = Depends(is_authenticated),
                          db: orm.Session = Depends(get_db)
                          ):
    """Creates a new bank object.
    Args:
        request: A pydantic schema that defines the room request parameters
        db (Session): The database for storing the article object
    Returns:
        HTTP_201_CREATED (new bank details added)
    Raises
        HTTP_424_FAILED_DEPENDENCY: failed to create bank object
        HTTP_403_FORBIDDEN: incomplete details
    """

    is_store_member = await is_organization_member(user_id=user.id, organization_id=bank.organisation_id, db=db)

    if not is_store_member:
        raise fastapi.HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="You are not allowed to add a bank account to this organization")

    addbank = bank_models.BankModels(id=uuid4().hex,
                                     organisation_id=bank.organisation_id,
                                     creator_id=user.id,
                                     account_number=bank.account_number,
                                     bank_name=bank.bank_name,
                                     recipient_name=bank.recipient_name,
                                     country=bank.country,
                                     sort_code=bank.sort_code,
                                     swift_code=bank.swift_code,
                                     bank_address=bank.bank_address,
                                     is_preferred=bank.is_preferred,
                                     account_type=bank.account_type,
                                     aba_routing_number=bank.aba_routing_number,
                                     iban=bank.iban,
                                     date_created=bank.date_created)

    return await bank_models.add_bank(user=user, addbank=addbank, db=db)


@router.get("/banks/organizations/{organization_id}", status_code=status.HTTP_200_OK,
            response_model=Page[bank_schemas.BankResponse])
async def get_organization_bank_accounts(organization_id: str, user: users_schemas.User = Depends(is_authenticated),
                                         db: orm.Session = Depends(get_db), page_size: int = 15,
                                         page_number: int = 1, ):
    """Fetches all available bank details in the database.
    Args:
        user: authenticates that the user is a logged in user
        db (Session): The database for storing the article object
    Returns:
        HTTP_200_OK (list of all registered bank details)
    Raises
        HTTP_424_FAILED_DEPENDENCY: failed to fetch banks
    """
    is_store_member = await is_organization_member(user_id=user.id, organization_id=organization_id, db=db)

    if not is_store_member:
        raise fastapi.HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="You are not allowed to access this resource")

    banks = db.query(bank_models.BankModels).filter_by(organisation_id=organization_id).filter_by(is_deleted=False)
    banks_list = list(map(bank_schemas.BankResponse.from_orm, banks))
    return paginate(banks_list)


@router.get("/banks/{bank_id}", status_code=status.HTTP_200_OK,
            response_model=bank_schemas.BankResponse)
async def get_single_bank(org_id: str, bank_id: str,
                          user: users_schemas.User = Depends(is_authenticated),
                          db: orm.Session = Depends(get_db)):
    """Fetches single bank detail given bank_id.
    Args:
        bank_id: a unique identifier of the bank object.
        user: authenticates that the user is a logged in user.
        db (Session): The database for storing the article object.
    Returns:
        HTTP_200_OK (bank object)
    Raises
        HTTP_424_FAILED_DEPENDENCY: failed to create bank object
        HTTP_4O4_NOT_FOUND: Bank does not exist.
    """
    bank = await bank_models.fetch_bank(user=user, id=bank_id, db=db)
    return bank_schemas.BankResponse.from_orm(bank)


@router.put("/banks/{bank_id}", status_code=status.HTTP_200_OK,
            response_model=bank_schemas.BankResponse)
async def update_bank_details(bank_id: str, bank: bank_schemas.AddBank,
                              user: users_schemas.User = Depends(is_authenticated),
                              db: orm.Session = Depends(get_db)):
    """Fetches single bank detail given bank_id.
    Args:
        bank_id: a unique identifier of the bank object.
        user: authenticates that the user is a logged in user.
        db (Session): The database for storing the article object.
    Returns:
        HTTP_200_OK (bank object)
    Raises
        HTTP_424_FAILED_DEPENDENCY: failed to create bank object
        HTTP_4O4_NOT_FOUND: Bank does not exist.
    """
    is_store_member = await is_organization_member(user_id=user.id, organization_id=bank.organisation_id, db=db)

    if not is_store_member:
        raise fastapi.HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="You are not allowed to carry out this operation")

    bank_account = await bank_models.fetch_bank(user=user, id=bank_id, db=db)
    bank_account.account_number = bank.account_number
    bank_account.bank_name = bank.bank_name
    bank_account.recipient_name = bank.recipient_name
    bank_account.country = bank.country
    bank_account.sort_code = bank.sort_code
    bank_account.swift_code = bank.swift_code
    bank_account.bank_address = bank.bank_address
    bank_account.account_type = bank.account_type
    bank_account.is_preferred = bank.is_preferred
    bank_account.aba_routing_number = bank.aba_routing_number
    bank_account.iban = bank.iban

    if bank.is_preferred:
        current_preferred_bank = db.query(bank_models.BankModels).filter_by(is_preferred=True).first()
        if current_preferred_bank is not None:
            current_preferred_bank.is_preferred = False
            db.commit()
            db.refresh(current_preferred_bank)

    return await bank_models.update_bank(addBank=bank_account, db=db)


@router.delete("/banks/{bank_id}", status_code=status.HTTP_200_OK)
async def delete_bank(bank_id: str,
                      user: users_schemas.User = Depends(is_authenticated),
                      db: orm.Session = Depends(get_db)):
    """delete a given bank of id bank_id.
    Args:
        bank_id: a unique identifier of the bank object.
        user: authenticates that the user is a logged in user.
        db (Session): The database for storing the article object.
    Returns:
        HTTP_200_OK (sucess response))
    Raises
        HTTP_424_FAILED_DEPENDENCY: failed to delete bank details
        HTTP_4O4_NOT_FOUND: Bank does not exist.
    """

    bank = await bank_models.fetch_bank(user=user, id=bank_id, db=db)
    is_store_member = await is_organization_member(user_id=user.id, organization_id=bank.organisation_id, db=db)

    if not is_store_member:
        raise fastapi.HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="You are not allowed to carry out this operation")
    bank.is_deleted = True
    db.commit()
    db.refresh(bank)
    return JSONResponse({"detail": "bank details successfully deleted"},
                        status_code=status.HTTP_200_OK)


@router.get("/banks/schema", status_code=status.HTTP_200_OK)
async def get_country_schema(country: str):
    """Fetches the schema valid for each country    .
    Args:
        country: Country whose schema structure is to be fetched.
    Returns:
        HTTP_200_OK (bank object)
    Raises: 
        HTTP_4O4_NOT_FOUND: Country not in the list of supported countries.
    """
    schema = await BV.get_country_data(country=country, info="schema")
    return {"schema": dict(schema)}


@router.get("/banks/validator", status_code=status.HTTP_200_OK)
async def validate_bank_details(country: str):
    """Fetches details needed to add bank details based on country provided.
    Args:
        country: Country whose schema structure is to be fetched.
    Returns:
        HTTP_200_OK (bank object)
    Raises
        HTTP_4O4_NOT_FOUND: Country not in the list of supported countries.
    """
    country_info = await BV.validate_supported_country(country)
    return country_info


# =================================== Bank Service =================================#


class BankValidator:

    def __init__(self) -> None:
        with open(BANK_DATA_PATH + "/bank.json") as file:
            self.country_info = json.load(file)

    async def get_country_data(self, country, info=None):
        if country not in self.country_info and info is None:
            return self.country_info["others"]
        elif country not in self.country_info:
            return self.country_info["others"][info]
        if info:
            country_info = self.country_info[country][info]
            return country_info
        return self.country_info[country]

    async def validate_supported_country(self, country):
        for data in self.country_info:
            if data == country:
                return True
        return False


BV = BankValidator()
add_pagination(router)
