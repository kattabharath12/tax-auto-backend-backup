class TaxCalculator:
    def calculate(self, form_data, filing_status="single", state="CA"):
        # This is a mock calculation for demo purposes.
        # In production, use IRS/state rules and real tax logic.
        wages = float(form_data.get("wages", 0))
        business_income = float(form_data.get("business_income", 0))
        federal_withholding = float(form_data.get("federal_withholding", 0))
        gross_receipts = float(form_data.get("gross_receipts", 0))
        business_expenses = float(form_data.get("business_expenses", 0))
        home_office = float(form_data.get("home_office", 0))
        deductions = float(form_data.get("medical_expenses", 0)) + \
                     float(form_data.get("state_local_taxes", 0)) + \
                     float(form_data.get("mortgage_interest", 0)) + \
                     float(form_data.get("charitable_contributions", 0))
        total_income = wages + business_income + gross_receipts - business_expenses - home_office
        taxable_income = max(total_income - deductions, 0)
        # Simple flat tax for demo
        tax_owed = taxable_income * 0.18
        refund = max(federal_withholding - tax_owed, 0)
        return {
            "total_income": total_income,
            "deductions": deductions,
            "taxable_income": taxable_income,
            "tax_owed": tax_owed,
            "federal_withholding": federal_withholding,
            "refund": refund
        }