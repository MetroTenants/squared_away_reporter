import csv
from io import BytesIO, StringIO

CSV_COLS = [
    "id",
    "call_issue",
    "created_at",
    "updated_at",
    "tenant_first_name",
    "tenant_last_name",
    "tenant_phone_number",
    "tenant_email",
    "street",
    "unit_number",
    "city",
    "state",
    "zip",
    "lat",
    "lon",
    "ward",
    "landlord_first_name",
    "landlord_last_name",
    "landlord_management_company",
    "landlord_email",
    "rep_first_name",
    "rep_last_name",
    "has_lease",
    "received_lead_notice",
    "number_of_children_under_six",
    "number_of_units_in_building",
    "is_owner_occupied",
    "is_subsidized",
    "subsidy_type",
    "is_rlto",
    "is_referred_by_info",
    "is_counseled_in_spanish",
    "is_referred_to_attorney",
    "referred_to_building_organizer",
    "categories",
    "title",
    "closed",
    "resolved",
    "area_of_residence",
    "efforts_to_fix",
    "message",
    "urgency",
    "entry_availability",
    "referred_to_whom",
    "notes",
    "heard_about_mto_from",
    "materials_sent",
    "is_interested_in_membership",
    "is_interested_in_tenant_congress",
    "number_of_materials_sent",
    "is_tenant_interested_in_volunteering",
    "is_referred_to_agency",
    "is_walkin",
]

USER_PREFIXES = ["tenant", "landlord", "rep"]

ADDRESS_COLS = ["street", "unit_number", "city", "state", "zip", "lat", "lon"]

EVICTION_COLS = [
    "id",
    "created_at",
    "updated_at",
    "entry_point",
    "can_tenant_pay_rent",
    "instructions_given",
    "did_tenant_call_back",
    "did_tenant_follow_instructions",
    "outcome_description",
    "reminder_date",
    "language",
    "marital_status",
    "num_children",
    "complaints",
    "repairs_detail",
    "court_date",
    "court_time",
    "courtroom",
    "first_time_court",
    "court_experience",
    "flags",
    "household_income",
    "security_deposit_amount",
    "monthly_rent",
    "last_rent_details",
    "documentation",
    "additional_info",
    "referred_to_lcbh",
    "did_lcbh_complete_intake",
    "did_lcbh_take_case",
]


class RecordRow:
    def __init__(self, row, cols=CSV_COLS):
        self.cols = cols
        for col in self.cols:
            col_prefix = col.split("_")[0]
            if col == "call_issue":
                attr = "issue" if getattr(row, "title", None) else "call"
            elif col_prefix in USER_PREFIXES:
                attr_name = col[len(col_prefix) + 1 :]
                user_obj = getattr(row, col_prefix, None)
                if user_obj:
                    attr = getattr(user_obj, attr_name, None)
                else:
                    attr = None
            elif col == "categories":
                categories = getattr(row, "categories", [])
                attr = ", ".join([getattr(c, "name", "") for c in categories])
            elif col in ADDRESS_COLS:
                if hasattr(row, "address"):
                    attr = getattr(row.address, col, None)
                else:
                    attr = None
            else:
                attr = getattr(row, col, None)
            setattr(self, col, attr)

    def as_list(self):
        return [getattr(self, c, "") for c in self.cols]


class EvictionRecordRow(RecordRow):
    def __init__(self, row, cols=EVICTION_COLS):
        self.cols = EVICTION_COLS
        for col in self.cols:
            setattr(self, col, getattr(row, col, None))
        call = None
        if len(row.calls):
            call = sorted(row.calls, key=lambda c: c.created_at)[-1]
        call_row = RecordRow(call, cols=CSV_COLS)
        self.cols = EVICTION_COLS + [f"call_{col}" for col in CSV_COLS]
        for col in CSV_COLS:
            setattr(self, f"call_{col}", getattr(call_row, col))


class CsvExport:
    """Accepts columns and a list of lists for writing to BytesIO CSV"""

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows

    def write_rows(self):
        """Return BytesIO object with data"""
        proxy = StringIO()
        mem = BytesIO()
        writer = csv.writer(proxy)
        writer.writerow(self.cols)
        for row in self.rows:
            writer.writerow(row)
        mem.write(proxy.getvalue().encode("utf-8"))
        mem.seek(0)
        proxy.close()
        return mem
