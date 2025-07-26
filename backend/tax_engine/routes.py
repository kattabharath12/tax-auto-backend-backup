from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from auth.routes import get_current_user
from .calculator import TaxCalculator

router = APIRouter()

class TaxCalculationRequest(BaseModel):
    form_1040: Optional[Dict[str, Any]] = {}
    schedule_a: Optional[Dict[str, Any]] = {}
    schedule_c: Optional[Dict[str, Any]] = {}
    filing_status: str = "single"
    state: str = "CA"

class FormSaveRequest(BaseModel):
    form_type: str
    form_data: Dict[str, Any]

@router.post("/calculate")
async def calculate_taxes(
    request: TaxCalculationRequest,
    current_user = Depends(get_current_user)
):
    """Calculate taxes based on form data"""
    try:
        calculator = TaxCalculator()
        
        # Combine all form data
        combined_data = {}
        if request.form_1040:
            combined_data.update(request.form_1040)
        if request.schedule_a:
            combined_data.update(request.schedule_a)
        if request.schedule_c:
            combined_data.update(request.schedule_c)
        
        # Ensure numeric values and handle empty/null values
        for key, value in combined_data.items():
            if value is None or value == "":
                combined_data[key] = 0.0
            elif isinstance(value, str):
                try:
                    # Try to convert string to float
                    combined_data[key] = float(value.replace(',', '')) if value.replace(',', '').replace('.', '').replace('-', '').isdigit() else 0.0
                except (ValueError, AttributeError):
                    combined_data[key] = 0.0
            elif isinstance(value, (int, float)):
                combined_data[key] = float(value)
            else:
                combined_data[key] = 0.0
        
        # Calculate taxes
        result = calculator.calculate(
            form_data=combined_data,
            filing_status=request.filing_status,
            state=request.state
        )
        
        # Add additional fields expected by frontend
        federal_withholding = combined_data.get("federal_withholding", 0)
        state_withholding = combined_data.get("state_withholding", 0)
        total_withholding = federal_withholding + state_withholding
        
        result.update({
            "total_income": result.get("total_income", 0),
            "total_deductions": result.get("deductions", 0),
            "total_withholding": total_withholding,
            "federal_withholding": federal_withholding,
            "state_withholding": state_withholding,
            "refund_amount": result.get("refund", 0),
            "amount_due": max(0, result.get("tax_owed", 0) - total_withholding),
            "taxable_income": result.get("taxable_income", 0),
            "agi": result.get("total_income", 0)  # AGI same as total income for simple calc
        })
        
        return result
        
    except Exception as e:
        print(f"Tax calculation error: {e}")
        raise HTTPException(status_code=500, detail=f"Tax calculation failed: {str(e)}")

@router.post("/save-form")
async def save_form(
    request: FormSaveRequest,
    current_user = Depends(get_current_user)
):
    """Save form data (mock implementation for demo)"""
    try:
        form_type = request.form_type.upper()
        
        # In a real implementation, you would save this to the database
        # For now, just return success
        return {
            "message": f"{form_type} form saved successfully",
            "form_type": request.form_type,
            "user_email": current_user.email,
            "saved_at": "2024-01-01T00:00:00Z",
            "status": "saved"
        }
    except Exception as e:
        print(f"Save form error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save form: {str(e)}")

@router.get("/forms/{form_type}")
async def get_form_template(form_type: str):
    """Get form template with field definitions"""
    templates = {
        "1040": {
            "name": "Form 1040 - U.S. Individual Income Tax Return",
            "description": "Main tax form for individual income tax returns",
            "fields": [
                {"name": "wages", "label": "Wages, salaries, tips (W-2)", "type": "number", "required": False},
                {"name": "interest_income", "label": "Taxable interest", "type": "number", "required": False},
                {"name": "dividend_income", "label": "Ordinary dividends", "type": "number", "required": False},
                {"name": "business_income", "label": "Business income (1099-NEC)", "type": "number", "required": False},
                {"name": "federal_withholding", "label": "Federal income tax withheld", "type": "number", "required": False},
                {"name": "state_withholding", "label": "State income tax withheld", "type": "number", "required": False}
            ]
        },
        "schedule_a": {
            "name": "Schedule A - Itemized Deductions",
            "description": "Use this form to itemize deductions instead of taking the standard deduction",
            "fields": [
                {"name": "medical_expenses", "label": "Medical and dental expenses", "type": "number", "required": False},
                {"name": "state_local_taxes", "label": "State and local income taxes or sales taxes", "type": "number", "required": False},
                {"name": "mortgage_interest", "label": "Home mortgage interest", "type": "number", "required": False},
                {"name": "charitable_contributions", "label": "Gifts to charity", "type": "number", "required": False}
            ]
        },
        "schedule_c": {
            "name": "Schedule C - Profit or Loss From Business",
            "description": "Use this form to report income or loss from a business you operated",
            "fields": [
                {"name": "gross_receipts", "label": "Gross receipts or sales", "type": "number", "required": False},
                {"name": "business_expenses", "label": "Total expenses", "type": "number", "required": False},
                {"name": "home_office", "label": "Home office deduction", "type": "number", "required": False},
                {"name": "vehicle_expenses", "label": "Car and truck expenses", "type": "number", "required": False}
            ]
        },
        "w9": {
            "name": "Form W-9 - Request for Taxpayer Identification Number",
            "description": "Give this form to the requester to provide your correct TIN",
            "fields": [
                {"name": "name", "label": "Name (as shown on your income tax return)", "type": "text", "required": True},
                {"name": "business_name", "label": "Business name/disregarded entity name", "type": "text", "required": False},
                {"name": "tax_classification", "label": "Federal tax classification", "type": "select", "required": True,
                 "options": ["Individual/sole proprietor", "C Corporation", "S Corporation", "Partnership", "Trust/estate", "LLC"]},
                {"name": "address", "label": "Address (number, street, and apt. or suite no.)", "type": "text", "required": True},
                {"name": "city", "label": "City", "type": "text", "required": True},
                {"name": "state", "label": "State", "type": "text", "required": True},
                {"name": "zip_code", "label": "ZIP code", "type": "text", "required": True},
                {"name": "taxpayer_id", "label": "Taxpayer Identification Number (TIN)", "type": "text", "required": True},
                {"name": "ssn", "label": "Social Security Number", "type": "text", "required": False},
                {"name": "ein", "label": "Employer Identification Number", "type": "text", "required": False},
                {"name": "account_numbers", "label": "Account number(s) (optional)", "type": "text", "required": False},
                {"name": "requester_name", "label": "Requester's name and address", "type": "text", "required": False},
                {"name": "requester_address", "label": "Requester's address", "type": "textarea", "required": False}
            ]
        }
    }
    
    if form_type not in templates:
        raise HTTPException(status_code=404, detail=f"Form type '{form_type}' not found")
    
    return templates[form_type]

@router.get("/forms")
async def get_available_forms():
    """Get list of all available tax forms"""
    return {
        "forms": [
            {"type": "1040", "name": "Form 1040", "category": "Individual"},
            {"type": "schedule_a", "name": "Schedule A", "category": "Deductions"},
            {"type": "schedule_c", "name": "Schedule C", "category": "Business"},
            {"type": "w9", "name": "Form W-9", "category": "Information"}
        ]
    }

@router.get("/filing-status")
async def get_filing_status_options():
    """Get available filing status options"""
    return {
        "filing_statuses": [
            {"value": "single", "label": "Single"},
            {"value": "married_filing_jointly", "label": "Married Filing Jointly"},
            {"value": "married_filing_separately", "label": "Married Filing Separately"},
            {"value": "head_of_household", "label": "Head of Household"},
            {"value": "qualifying_widow", "label": "Qualifying Widow(er)"}
        ]
    }

@router.get("/states")
async def get_state_options():
    """Get available state options for tax calculation"""
    states = [
        {"value": "AL", "label": "Alabama"}, {"value": "AK", "label": "Alaska"},
        {"value": "AZ", "label": "Arizona"}, {"value": "AR", "label": "Arkansas"},
        {"value": "CA", "label": "California"}, {"value": "CO", "label": "Colorado"},
        {"value": "CT", "label": "Connecticut"}, {"value": "DE", "label": "Delaware"},
        {"value": "FL", "label": "Florida"}, {"value": "GA", "label": "Georgia"},
        {"value": "HI", "label": "Hawaii"}, {"value": "ID", "label": "Idaho"},
        {"value": "IL", "label": "Illinois"}, {"value": "IN", "label": "Indiana"},
        {"value": "IA", "label": "Iowa"}, {"value": "KS", "label": "Kansas"},
        {"value": "KY", "label": "Kentucky"}, {"value": "LA", "label": "Louisiana"},
        {"value": "ME", "label": "Maine"}, {"value": "MD", "label": "Maryland"},
        {"value": "MA", "label": "Massachusetts"}, {"value": "MI", "label": "Michigan"},
        {"value": "MN", "label": "Minnesota"}, {"value": "MS", "label": "Mississippi"},
        {"value": "MO", "label": "Missouri"}, {"value": "MT", "label": "Montana"},
        {"value": "NE", "label": "Nebraska"}, {"value": "NV", "label": "Nevada"},
        {"value": "NH", "label": "New Hampshire"}, {"value": "NJ", "label": "New Jersey"},
        {"value": "NM", "label": "New Mexico"}, {"value": "NY", "label": "New York"},
        {"value": "NC", "label": "North Carolina"}, {"value": "ND", "label": "North Dakota"},
        {"value": "OH", "label": "Ohio"}, {"value": "OK", "label": "Oklahoma"},
        {"value": "OR", "label": "Oregon"}, {"value": "PA", "label": "Pennsylvania"},
        {"value": "RI", "label": "Rhode Island"}, {"value": "SC", "label": "South Carolina"},
        {"value": "SD", "label": "South Dakota"}, {"value": "TN", "label": "Tennessee"},
        {"value": "TX", "label": "Texas"}, {"value": "UT", "label": "Utah"},
        {"value": "VT", "label": "Vermont"}, {"value": "VA", "label": "Virginia"},
        {"value": "WA", "label": "Washington"}, {"value": "WV", "label": "West Virginia"},
        {"value": "WI", "label": "Wisconsin"}, {"value": "WY", "label": "Wyoming"}
    ]
    
    return {"states": states}