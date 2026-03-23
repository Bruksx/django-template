from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class SkuadConfig(BaseModel):
    host: str
    x_auth_token: Optional[str] = None
    x_auth_legal_entity_id: Optional[str] = None
    origin: Optional[str] = None
    cookie: Optional[str] = None



class RecipientAddress(BaseModel):
    country: str
    invoice_address: Optional[str] = Field(None, alias="invoiceAddress")

    class Config:
        populate_by_name = True

class GetContractByIdInput(BaseModel):
    id: str


class Recipient(BaseModel):
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    email: str
    role: str
    designation: str
    phone: Optional[str] = None
    gender: Optional[str] = None
    address: RecipientAddress

    class Config:
        populate_by_name = True


class ContractCompensation(BaseModel):
    currency_code: str = Field(..., alias="currencyCode")
    net_payable_amount: float = Field(..., alias="netPayableAmount")
    payment_frequency: str = Field(..., alias="paymentFrequency")
    criteria: str
    role: Optional[str] = None
    payment_note: Optional[str] = Field(None, alias="paymentNote")
    allowances: list[Any] = Field(default_factory=list)
    bonuses: list[Any] = Field(default_factory=list)
    end_date: Optional[str] = Field(None, alias="endDate")
    compensation_id: Optional[str] = Field(None, alias="compensationId")

    class Config:
        populate_by_name = True


class WorkInfoDetails(BaseModel):
    approval_manager: str = Field(..., alias="approvalManager")
    approval_manager_email: str = Field(..., alias="approvalManagerEmail")
    reporting_manager: str = Field(..., alias="reportingManager")
    reporting_manager_email: str = Field(..., alias="reportingManagerEmail")

    class Config:
        populate_by_name = True


class CustomTemplate(BaseModel):
    template_id: str = Field(..., alias="templateId")
    template_provider: str = Field(..., alias="templateProvider")
    is_custom: bool = Field(True, alias="isCustom")

    class Config:
        populate_by_name = True


class ProbationInput(BaseModel):
    probation_period: int = Field(..., alias="probationPeriod")
    notice_during_probation: int = Field(0, alias="noticeDuringProbation")

    class Config:
        populate_by_name = True

class ConsultantMeta(BaseModel):
    current_active_step_key: str = Field(..., alias="currentActiveStepKey")
    completed_step_keys: list[str] = Field(..., alias="completedStepKeys")
    cost_center_id: Optional[str] = Field(None, alias="costCenterId")
    service_type: Optional[str] = Field(None, alias="serviceType")
    tax: Optional[float] = None
    tds: Optional[float] = None
    has_signed_the_contract: Optional[bool] = Field(None, alias="hasSignedTheContract")

    class Config:
        populate_by_name = True


class ScopeOfWork(BaseModel):
    value: str
    name: Optional[str] = None
    type: Optional[str] = None
    path: Optional[str] = None


class PaymentContractDocument(BaseModel):
    name: str
    path: str
    type: str


class AddConsultantAorInput(BaseModel):
    is_aor: bool = Field(True, alias="isAor")
    is_payment_only: bool = Field(False, alias="isPaymentOnly")
    is_direct: bool = Field(True, alias="isDirect")
    type: str
    geography: list[str]
    recipients: list[Recipient]
    contract_compensations: list[ContractCompensation] = Field(..., alias="contractCompensations")
    meta: ConsultantMeta
    custom_template: Optional[CustomTemplate] = Field(None, alias="customTemplate")
    scope_of_work: ScopeOfWork = Field(..., alias="scopeOfWork")
    notice_period: int = Field(..., alias="noticePeriod")
    start_date: str = Field(..., alias="startDate")
    termination_date: Optional[str] = Field(None, alias="terminationDate")
    tax_residence: str = Field(..., alias="taxResidence")
    work_info_details: WorkInfoDetails = Field(..., alias="workInfoDetails")
    send_contract: bool = Field(True, alias="sendContract")
    is_draft: bool = Field(False, alias="isDraft")
    employment_type: str = Field("Consultant", alias="employmentType")

    class Config:
        populate_by_name = True

    @classmethod
    def from_json(cls, json_data: dict) -> 'AddConsultantAorInput':
        data = dict()
        meta = json_data.pop("meta",None)
        if meta:
            data["meta"] = ConsultantMeta(**meta)
        scope_of_work = json_data.pop("scope_of_work",None)
        if scope_of_work:
            data["scope_of_work"] = ScopeOfWork(**scope_of_work)
        work_info_details = json_data.pop("work_info_details",None)
        if work_info_details:
            data["work_info_details"] = WorkInfoDetails(**work_info_details)

        recipients = json_data.pop("recipients",None)
        if recipients:
            data["recipients"] = [Recipient(**r) for r in recipients]

        contract_compensations = json_data.pop("contract_compensations",None)
        if contract_compensations:
            data["contract_compensations"] = [ContractCompensation(**c) for c in contract_compensations]

        custom_template = json_data.pop("custom_template",None)
        if custom_template:
            data["custom_template"] = CustomTemplate(**custom_template)

        probation = json_data.pop("probation",None)
        if probation:
            data["probation"] = ProbationInput(**probation)

        data.update(json_data)
        return cls(**data)


class AddConsultantPayOnlyInput(AddConsultantAorInput):
    is_aor: bool = Field(False, alias="isAor")
    is_payment_only: bool = Field(True, alias="isPaymentOnly")
    payment_contract_document: Optional[PaymentContractDocument] = Field(
        None, alias="paymentContractDocument"
    )

    class Config:
        populate_by_name = True


class GetInvoiceInput(BaseModel):
    invoice_id: str


class LineItemAmount(BaseModel):
    amount: float
    currency: str


class CreateLineItemInput(BaseModel):
    type: str
    head: str
    description: str
    unit_rate: str = Field(..., alias="unitRate")
    unit: float = 1
    amount: float
    amounts: list[LineItemAmount]
    taxable: bool = True
    currency: str
    unit_criteria: str = Field(..., alias="unitCriteria")
    invoice_id: Optional[str] = Field(None, alias="invoiceId")
    tax_percentage: Optional[float] = Field(None, alias="taxPercentage")
    hsn_code: Optional[str] = Field(None, alias="hsnCode")

    class Config:
        populate_by_name = True


class CreateInvoiceInput(BaseModel):
    client_id: str = Field(..., alias="clientId")
    contract_id: str = Field(..., alias="contractId")
    period_start: str = Field(..., alias="periodStart")
    period_end: str = Field(..., alias="periodEnd")
    invoice_type: str = Field("Contractor", alias="invoiceType")
    status: str = "Draft"
    line_items: list[CreateLineItemInput] = Field(..., alias="lineItems")

    class Config:
        populate_by_name = True

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> CreateInvoiceInput:
        data["lineItems"] = [CreateLineItemInput(
            **line_item
        ) for line_item in data["lineItems"]]
        return cls(**data)


class CreatePaymentOrderInput(BaseModel):
    invoice_ids: list[str] = Field(..., alias="invoiceIds")
    credit_note_ids: list[str] = Field(default_factory=list, alias="creditNoteIds")
    payment_method: str = Field("bank_transfer", alias="paymentMethod")
    contract_id: str = Field(..., alias="contractId")

    class Config:
        populate_by_name = True


class ConfirmPaymentOrderInput(BaseModel):
    payment_order_id: str


class CancelPaymentOrderInput(BaseModel):
    payment_order_id: str
