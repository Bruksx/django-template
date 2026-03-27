import json

import requests

from services.payroll.skaud.schema import GetContractByIdInput, AddConsultantAorInput, \
    GetInvoiceInput, CreateInvoiceInput, CreatePaymentOrderInput, ConfirmPaymentOrderInput, \
    CancelPaymentOrderInput, SkuadConfig

CONTRACT_FRAGMENT = """
fragment ContractOutputV3FragmentFields on ContractOutputV3 {
  id type isExpat
  recipients { id firstName middleName lastName email role isSigned isCreator legalEntityId userId designation legalEntity { firstName lastName companyName __typename } __typename }
  endClientEntity { id firstName lastName companyName __typename }
  clientId
  sdInvoice { endClientConractId clientBillingCurrency invoices { id failureMsg status __typename } __typename }
  contractStatusInfo { displayStatus { value label color __typename } contractStatus __typename }
  offBoardingDetails { typeOfTermination terminationDate terminationReason offboardingAdditionalNotes offboardingPayableLeaveBalance offboardingAdditionalBonusCurrency offboardingAdditionalBonus __typename }
  taxResidence contractName cid
  contractCompensations { id compensationBreakdown { component comments metric paymentFrequency amountYoy amount category meta { name __typename } startDate __typename } nextPaymentDate paymentNote netPayableAmount currencyCode lastPaymentDate paymentFrequency criteria startDate __typename }
  noticePeriod vendorId isAor
  clientEntity { id companyName firstName lastName __typename }
  meta { jobDescription workStartTime workEndTime contractModificationsReason isDeviceProvided isInsuranceProvided taxInformation serviceType costCenter { id name __typename } contractModificationsReason backGroundJob { asyncTaskInfo { taskType taskStatus contractId __typename } __typename } __typename }
  specialClause
  probation { probationPeriod noticeDuringProbation probationStatus __typename }
  contractTemplate { id pandaDocId templateId templateProvider name __typename }
  startDate shouldShowMarkPrimaryButton
  contractCsmInfo { psm { userId __typename } payrollChecker { userId __typename } employeeCare { userId __typename } payDay __typename }
  __typename
}
"""


class SkuadService:
    def __init__(self, config: SkuadConfig):
        self.config = config
        self._base_url = f"{config.host}/graphql"
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h = {
            "content-type": "application/json",
            "x-auth-legal-entity-id": self.config.x_auth_legal_entity_id,
        }
        if self.config.x_auth_token:
            h["x-api-token"] = self.config.x_auth_token
        if self.config.origin:
            h["origin"] = self.config.origin
        return h

    def _post(self, payload: dict) -> dict:
        response = requests.post(
            self._base_url,
            headers=self._headers(),
            data=json.dumps(payload),
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Token
    # ------------------------------------------------------------------

    def get_contract_by_id(self, data: GetContractByIdInput) -> dict:
        return self._post(
            {
                "query": CONTRACT_FRAGMENT + """
                    query contractById($id: String!) {
                      contractById(id: $id) { ...ContractOutputV3FragmentFields __typename }
                    }
                """,
                "variables": {"id": data.id},
            }
        )

    def add_consultant_aor(self, data: AddConsultantAorInput) -> dict:
        return self._post(
            {
                "query": CONTRACT_FRAGMENT + """
                    mutation createConsultantContractV3($createContractInput: CreateConsultantContractInputV3!) {
                      createConsultantContractV3(createContractInput: $createContractInput) { ...ContractOutputV3FragmentFields __typename }
                    }
                """,
                "variables": {"createContractInput": data.model_dump(by_alias=True, exclude_none=True)},
            }
        )

    def get_invoice(self, data: GetInvoiceInput) -> dict:
        return self._post(
            {
                "query": """
                    query invoice($invoiceId: String!) {
                      invoice(invoiceId: $invoiceId) { id invoiceNumber invoiceType status displayStatus amount currency periodStart periodEnd invoiceDate dueDate __typename }
                    }
                """,
                "variables": {"invoiceId": data.invoice_id},
            }
        )

    def create_invoice(self, data: CreateInvoiceInput, client=True) -> dict:
        if client:
            query = """
                    mutation createInvoiceClient($createInvoiceInput: CreateInvoiceInputDto!) {
                      createInvoiceClient(createInvoiceInput: $createInvoiceInput) { id }
                    }
                """
        else:
            query = """
                    mutation createInvoiceConsultant($createInvoiceInput: CreateInvoiceInputDto!) {
                      createInvoiceConsultant(createInvoiceInput: $createInvoiceInput) { id }
                    }
                """
        return self._post(
            {
                "query": query,
                "variables": {
                    "createInvoiceInput": data.model_dump(by_alias=True, exclude_none=True)
                },
            }
        )

    def create_payment_order(self, data: CreatePaymentOrderInput) -> dict:
        return self._post(
            {
                "query": """
                    mutation createPaymentOrder($createCustomerPaymentOrderInput: CreatePaymentOrderDto!) {
                      createPaymentOrder(createCustomerPaymentOrderInput: $createCustomerPaymentOrderInput) {
                        data { orderId message success paymentMethod paymentReferenceNumber __typename }
                        __typename
                      }
                    }
                """,
                "variables": {
                    "createCustomerPaymentOrderInput": data.model_dump(
                        by_alias=True, exclude_none=True
                    )
                },
            }
        )

    def confirm_payment_order(self, data: ConfirmPaymentOrderInput) -> dict:
        return self._post(
            {
                "query": """
                    mutation confirmPaymentOrder($paymentOrderId: String!) {
                      confirmPaymentOrder(paymentOrderId: $paymentOrderId) { id status __typename }
                    }
                """,
                "variables": {"paymentOrderId": data.payment_order_id},
            },
            use_cookie=True,
        )

    def cancel_payment_order(self, data: CancelPaymentOrderInput) -> dict:
        return self._post(
            {
                "query": """
                    mutation cancelPaymentOrder($paymentOrderId: String!) {
                      cancelPaymentOrder(paymentOrderId: $paymentOrderId) { id status __typename }
                    }
                """,
                "variables": {"paymentOrderId": data.payment_order_id},
            },
            use_cookie=True,
        )