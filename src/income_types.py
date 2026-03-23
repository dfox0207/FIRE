from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any

def income_type_from_evnt_type(event_type: str):
    event_type = str(event_type).strip().lower()

    if event_type == "salary":
        return EarnedIncome()
    if event_type == "pension":
        return RetirementDistributionIncome()
    if event_type == "special_annuity":
        return RetirementDistributionIncome()
    if event_type == "ssa":
        return SocialSecurityIncome()   
    if event_type in {"roth_conversion", "roth_conv", "Roth Conversion"}:
        return RothConversionIncome()
    if event_type == "interest":
        return InterestIncome()
    if event_type == "qualified_dividend":
        return QualifiedDividendIncome()
    if event_type == "stcg":
        return LongTermCapitalGainIncome()
    if event_type == "ltcg":
        return LongTermCapitalGainIncome()
    if event_type in {"401k", "403b", "457b", "traditional_ira", "annuity", "pension", "tsp", "pretax"}:
        return RetirementDistributionIncome()
    if event_type in {"roth_ira", "roth_401k", "roth_tsp", "roth"}:
        return RothDistributionIncome()
    if event_type in {"brokerage"}:
        return None
    raise ValueError(f"Unknwon account_type: {event_type}")

@dataclass
class TaxResult:
    federal_ordinary_income: float = 0.0
    federal_ltcg_income: float = 0.0
    federal_qualified_dividends: float = 0.0
    social_security_income: float=0.0
    payroll_ss_wages: float = 0.0
    payroll_medicare_wages: float = 0.0
    self_employment_income: float = 0.0

    va_ordinary_income: float = 0.0

    tax_exempt_interest: float = 0.0
    excluded_income: float = 0.0

    withholding: float = 0.0

    def add(self, other: "TaxResult") -> None:
        for field_name in self.__dataclass_fields__:
            setattr(
                self,
                field_name,
                getattr(self, field_name) + getattr(other, field_name)
            )

    def __add__(self, other: "TaxResult") -> "TaxResult":

        result = TaxResult()
        for field_name in self.__dataclass_fields__:
            setattr(
                result,
                field_name,
                getattr(self, field_name) + getattr(other, field_name)
            )
        return result
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)
    
    @classmethod
    def zero(cls) -> "TaxResult":
        return cls()


class IncomeType(ABC):

    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        pass

    def is_spendable(self) -> bool:
        return True 
    
    def is_reported_income(self) -> bool:
        return True 
    
    def is_taxable_income(self) -> bool:
        return True 
    

class EarnedIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            federal_ordinary_income = amount,
            payroll_ss_wages = amount,
            payroll_medicare_wages = amount,
            va_ordinary_income = amount
        )

class SelfEmploymentIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            federal_ordinary_income = amount,
            self_employment_income = amount,
            va_ordinary_income = amount
        )

class InterestIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            federal_ordinary_income = amount,
            va_ordinary_income = amount
        )

class QualifiedDividendIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            federal_qualified_dividends=amount,
            va_ordinary_income=amount
        )

class ShortTermCapitalGainIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            federal_ordinary_income=amount,
            va_ordinary_income=amount
        )

class LongTermCapitalGainIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return  TaxResult(
            federal_ltcg_income=amount,
            va_ordinary_income=amount
        )

class RetirementDistributionIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            federal_ordinary_income=amount,
            va_ordinary_income=amount
        )

class RothConversionIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            federal_ordinary_income=amount,
            va_ordinary_income=amount 
        )
    
    def is_spendable(self) -> bool:
        return False 

    def is_reported_income(self) -> bool:
        return False

class RothDistributionIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            excluded_income=amount
        )

class SocialSecurityIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            social_security_income=amount
        )

class MunicipalBondInterestIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:
        return TaxResult(
            tax_exempt_interest=amount
        )

class CapitalAssetSaleIncome(IncomeType):
    def classify_for_tax(self, amount: float, **kwargs) -> TaxResult:

        proceeds = kwargs.get("proceeds", 0.0)
        basis = kwargs.get("basis", 0.0)
        long_term = kwargs.get("long_term", False)

        gain = max(0.0, proceeds - basis)

        if long_term:
            return TaxResult(
                federal_ltcg_income=gain,
                va_ordinary_income=gain
            )
        else:
            return TaxResult(
                federal_ordinary_income=gain,
                va_ordinary_income=gain
            )

@dataclass
class IncomeSource:

    name: str 
    income_type: "IncomeType"
    account: str | None=None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IncomeEvent:

    date: Any
    source: "IncomeSource"
    gross_amount: float = 0.0

    basis: float = 0.0
    proceeds: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)

    def tax_result(self) -> TaxResult:

        return self.source.income_type.classify_for_tax(
            amount = self.gross_amount,
            basis = self.basis,
            proceeds = self.proceeds,
            **self.metadata
        )