import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
import os
import json

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_table_borders(table, color="CCCCCC", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def format_table(table, col_widths, headers, data, primary_hex="1B365D", alt_bg_hex="F8F9FA"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header Row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], primary_hex)
        set_cell_margins(hdr_cells[i], top=100, bottom=100, left=100, right=100)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in p.runs:
            run.font.name = 'Arial'
            run.font.size = Pt(9.0)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            
    # Data Rows
    for r_idx, row_data in enumerate(data):
        row_cells = table.add_row().cells
        bg_color = alt_bg_hex if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=70, bottom=70, left=100, right=100)
            p = row_cells[c_idx].paragraphs[0]
            for run in p.runs:
                run.font.name = 'Calibri'
                run.font.size = Pt(9.0)
                run.font.color.rgb = RGBColor(44, 62, 80)
                
    # Set widths
    for row in table.rows:
        for c_idx, w in enumerate(col_widths):
            row.cells[c_idx].width = Inches(w)
            
    set_table_borders(table, color="D0D7DE", sz="4")

def build_data_quality_report():
    doc = Document()
    
    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        
    PRIMARY_COLOR = RGBColor(27, 54, 93)     # Deep Navy Blue
    SECONDARY_COLOR = RGBColor(41, 128, 185) # Teal / Steel Blue
    DARK_TEXT = RGBColor(44, 62, 80)        # Dark Slate
    PRIMARY_HEX = "1B365D"
    LIGHT_BG_HEX = "F0F4F8"
    ALT_BG_HEX = "F8F9FA"
    
    # Normal style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = DARK_TEXT
    
    # Title Block
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    r_title = title_p.add_run("CAMEROON openIMIS 3.0 DATA QUALITY, RELATIONAL SCHEMA & FRAUD DETECTION AUDIT REPORT")
    r_title.font.name = 'Arial'
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = PRIMARY_COLOR
    
    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(14)
    r_sub = sub_p.add_run("Exhaustive Data Dictionary (All 13 Tables, 316 Columns), Referential Integrity, Rejection Distribution & Predictive Feature Engineering")
    r_sub.font.name = 'Arial'
    r_sub.font.size = Pt(12)
    r_sub.font.italic = True
    r_sub.font.color.rgb = SECONDARY_COLOR
    
    # Exec Metadata Box
    meta_table = doc.add_table(rows=1, cols=1)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_meta = meta_table.rows[0].cells[0]
    set_cell_background(c_meta, LIGHT_BG_HEX)
    set_cell_margins(c_meta, top=120, bottom=120, left=180, right=180)
    
    tcPr = c_meta._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="{PRIMARY_HEX}"/>'
        f'  <w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p_meta = c_meta.paragraphs[0]
    p_meta.paragraph_format.space_after = Pt(0)
    p_meta.paragraph_format.line_spacing = 1.15
    
    r_mt = p_meta.add_run("DOCUMENT METADATA & AUDIT SCOPE\n")
    r_mt.font.name = 'Arial'
    r_mt.font.size = Pt(10.5)
    r_mt.font.bold = True
    r_mt.font.color.rgb = PRIMARY_COLOR
    
    r_mb = p_meta.add_run(
        "• Target Dataset: Cameroon openIMIS Health Insurance Database (13 CSV Files in data/)\n"
        "• Total Records Ingested: 50,499,713 Rows (52.4+ Million Transaction Ledger Entries)\n"
        "• Total Schema Features: 316 Column Attributes across 13 Relational Tables | Total Disk Footprint: 12.07 GB\n"
        "• Financial Ledger Audited: 2,563,003,643 XAF Total Requested vs 1,909,992,345 XAF Total Approved (653,011,298 XAF Financial Deductions)\n"
        "• Target ML Objective: Claim Rejection Prediction, Upcoding Audit & Anomaly Detection\n"
        "• Audit Execution Date: July 2026 | System Version: openIMIS Cameroon Release 3.0"
    )
    r_mb.font.name = 'Calibri'
    r_mb.font.size = Pt(9.5)
    r_mb.font.color.rgb = DARK_TEXT
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = 'Arial'
        r.font.size = Pt(15)
        r.font.bold = True
        r.font.color.rgb = PRIMARY_COLOR
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = 'Arial'
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = SECONDARY_COLOR
        return p

    def add_p(text, bold_prefix='', italic=False):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            rb = p.add_run(bold_prefix)
            rb.font.name = 'Calibri'
            rb.font.size = Pt(10.0)
            rb.font.bold = True
            rb.font.color.rgb = PRIMARY_COLOR
        r = p.add_run(text)
        r.font.name = 'Calibri'
        r.font.size = Pt(10.0)
        r.font.italic = italic
        r.font.color.rgb = DARK_TEXT
        return p

    def add_bullet(text, bold_prefix=''):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            rb = p.add_run(bold_prefix)
            rb.font.name = 'Calibri'
            rb.font.size = Pt(10.0)
            rb.font.bold = True
            rb.font.color.rgb = PRIMARY_COLOR
        r = p.add_run(text)
        r.font.name = 'Calibri'
        r.font.size = Pt(10.0)
        r.font.color.rgb = DARK_TEXT
        return p

    # ================= SECTION 1 =================
    add_h1("1. Executive Summary & Operational Context")
    add_p("The openIMIS health insurance management platform is deployed in Cameroon to manage beneficiary coverage, health facility contracting, medical claim submission, clinical review, financial valuation, and provider reimbursement. As national health coverage scales across regional healthcare networks, automated fraud detection and claim rejection modeling are paramount to prevent revenue leakage and preserve fund solvency.")
    add_p("This report presents a thorough data quality audit, referential integrity assessment, and complete data dictionary for all 13 relational datasets in the Cameroon openIMIS database (~50.5 million records, 316 column attributes). It establishes empirical baseline distributions for claim rejections, evaluates key join paths across medical services and patient histories, and outlines 19 high-impact engineered features for machine learning deployment.")

    # ================= SECTION 2 =================
    add_h1("2. Claim Processing Lifecycle, Status Mapping & Rejection Taxonomy")
    add_p("Medical claims in openIMIS pass through a multi-stage adjudication lifecycle. The workflow transitions claims through system status codes while applying automated validation rules and manual clinical audits:")
    
    add_bullet(" The health facility enters line-item services and prices. The openIMIS system executes automated validations (active policy window, insurance ID format, service frequency limits, gender/age eligibility). If automated rules fail, the claim or service line is assigned Status 1 (REJECTED) with an automated RejectionReason code (1 to 19). If validation passes, the claim advances to Status 4 (CHECKED).", bold_prefix="Stage 1: Pre-Submission & Automated Gatekeeping: ")
    add_bullet(" Medical Counselors review medical necessity, ICD-10 diagnostic alignment, and treatment appropriateness. Claims passing clinical audit advance to Status 8 (PROCESSED). Claims failing clinical protocols are assigned Status 1 (REJECTED) with RejectionReason = -1 (Manual Clinical Rejection).", bold_prefix="Stage 2: Medical Counselor Clinical Review: ")
    add_bullet(" Financial managers evaluate approved unit prices and calculate benefit ceilings. Approved claims reach Status 16 (VALUATED) and Status 32 (PAYMENT) for disbursement.", bold_prefix="Stage 3: Financial Valuation & Payment: ")

    add_h2("2.1 System Status Code Mapping")
    hdr_s = ["Status Code", "System Constant", "Level Applied", "Functional Description & Meaning"]
    data_s = [
        ["1", "STATUS_REJECTED", "Header & Line Item", "Claim or service line item rejected entirely (0 XAF approved)"],
        ["2", "STATUS_ENTERED", "Claim Header", "Claim initially submitted into system by health facility"],
        ["4", "STATUS_CHECKED", "Claim Header", "Passed basic automated pre-submission control checks"],
        ["8", "STATUS_PROCESSED", "Claim Header", "Passed Medical Counselor clinical review"],
        ["16", "STATUS_VALUATED", "Claim Header", "Final financial valuation completed; approved for payment"],
        ["32", "STATUS_PAYMENT", "Claim Header", "Disbursement completed to health facility bank account"]
    ]
    t_s = doc.add_table(rows=1, cols=4)
    format_table(t_s, [1.0, 1.6, 1.4, 3.0], hdr_s, data_s)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    add_h2("2.2 Empirical Rejection Reason Dictionary & Distribution")
    add_p("Empirical counts and percentage shares observed across the 15,774,762 service line items in TblClaimServices.csv:")
    
    hdr_r = ["Code", "Rejection Category", "Description / Violation Rule", "Observed Count", "% Share"]
    data_r = [
        ["0.0", "Passed / Accepted", "No rejection; service item validated and accepted for payment", "12,078,452", "76.57%"],
        ["nan", "Not Evaluated", "Pending valuation, unassigned, or header-only status", "3,214,561", "20.38%"],
        ["5.0", "Automated Rule", "Frequency constraint violation (e.g., procedure repeated beyond limit)", "186,942", "1.19%"],
        ["3.0", "Automated Rule", "Not covered by active policy (policy expired, suspended, or inactive)", "160,082", "1.01%"],
        ["4.0", "Automated Rule", "Patient demographic mismatch (Sex or Age incompatibility for service)", "47,508", "0.30%"],
        ["-1.0", "Manual Clinical", "Rejected by Medical Counselor (clinical/protocol non-compliance)", "30,440", "0.19%"],
        ["10.0", "Automated Rule", "Technical or system rule constraint violation", "23,748", "0.15%"],
        ["7.0", "Automated Rule", "Invalid Insurance Number (Insuree ID not recognized in database)", "12,885", "0.08%"],
        ["2.0", "Automated Rule", "Item or Service not included in health facility contracted price list", "9,538", "0.06%"],
        ["16.0", "Automated Rule", "Maximum benefit ceiling or policy financial limit exceeded", "5,539", "0.04%"],
        ["-2.0", "Manual Admin", "Administrative rejection by system manager", "4,914", "0.03%"],
        ["9.0", "Automated Rule", "Invalid service delivery date (outside policy validity window)", "153", "< 0.01%"]
    ]
    t_r = doc.add_table(rows=1, cols=5)
    format_table(t_r, [0.8, 1.4, 2.8, 1.1, 0.9], hdr_r, data_r)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ================= SECTION 3 =================
    add_h1("3. Complete Master Dataset Inventory & Exhaustive Data Schema Dictionary")
    add_p("A rigorous audit was conducted across all 13 CSV files in the data directory. The table below summarizes the master dataset inventory:")

    add_h2("3.1 Master Dataset Inventory (13 Tables, 50.5M Rows, 316 Columns)")
    hdr_inv = ["Dataset Name", "Row Count", "Col Count", "File Size", "Primary Key", "Foreign Keys", "Description"]
    data_inv = [
        ["TblClaim.csv", "14,242,741", "56", "3,722.08 MB", "ClaimID", "Hfid, Icdid, InsureeID", "Primary medical claim header ledger"],
        ["TblClaimServices.csv", "15,774,762", "30", "1,770.86 MB", "ClaimServiceID", "ClaimID, ServiceID, PolicyID", "Line-item medical services performed"],
        ["TblClaimItems.csv", "1,728", "31", "0.17 MB", "ClaimItemID", "ClaimID, ItemID, PolicyID", "Line-item drugs & consumables issued"],
        ["TblInsuree.csv", "11,647,016", "40", "5,501.48 MB", "InsureeID", "FamilyID, Hfid", "Master beneficiary & patient registry"],
        ["TblInsureePolicy.csv", "1,239,874", "13", "135.82 MB", "InsureePolicyID", "InsureeID, PolicyId", "Insuree-to-Policy coverage bridge"],
        ["TblPolicy.csv", "1,758,198", "23", "307.86 MB", "PolicyID", "FamilyID, OfficerID, ProdID", "Insurance policy coverage terms"],
        ["TblFamilies.csv", "5,784,324", "19", "626.91 MB", "FamilyID", "InsureeID, LocationId", "Household & socio-economic profile"],
        ["TblHF.csv", "2,512", "27", "0.38 MB", "HfID", "LocationId", "Health facility master dictionary"],
        ["TblServices.csv", "27,832", "20", "5.08 MB", "ServiceID", "N/A", "Standard medical service price catalog"],
        ["TblItems.csv", "176", "19", "0.02 MB", "ItemID", "N/A", "Standard drugs/consumables catalog"],
        ["TblICDCodes.csv", "2,203", "8", "0.26 MB", "Icdid", "N/A", "ICD-10 diagnostic codes dictionary"],
        ["TblLocations.csv", "14,211", "16", "1.66 MB", "LocationId", "ParentLocationId", "Geographic administrative hierarchy"],
        ["UvwLocations.csv", "4,136", "14", "0.29 MB", "LocationId", "RegionId, DistrictId", "Flattened location hierarchy view"]
    ]
    t_inv = doc.add_table(rows=1, cols=7)
    format_table(t_inv, [1.3, 0.9, 0.6, 0.8, 1.0, 1.1, 1.3], hdr_inv, data_inv)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Load JSON schema details generated by python script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "..", "schemas", "full_schema_details.json")
    schema_data = {}
    if os.path.exists(json_path):
        with open(json_path) as fp:
            schema_data = json.load(fp)

    add_h2("3.2 Exhaustive Column Data Dictionary (All 13 Tables, 316 Attributes)")
    add_p("Below is the complete, itemized feature catalog for every column across all 13 tables in the Cameroon openIMIS database. Each attribute specifies its data type, sample non-null coverage, description, and fraud detection role:")

    # Map of column roles & descriptions for clarity
    def get_column_meta(tname, cname):
        c_upper = cname.upper()
        role = "Feature Attribute"
        if "ID" in c_upper and ("CLAIM" in c_upper or "INSUREE" in c_upper or "POLICY" in c_upper or "HF" in c_upper or "SERVICE" in c_upper or "ITEM" in c_upper or "LOCATION" in c_upper or "FAMILY" in c_upper or "ICD" in c_upper):
            if cname in ["ClaimID", "ClaimServiceID", "ClaimItemID", "InsureeID", "InsureePolicyID", "PolicyID", "FamilyID", "HfID", "ServiceID", "ItemID", "Icdid", "LocationId"]:
                role = "Primary Key"
            else:
                role = "Foreign Key / Join Key"
        elif "STATUS" in c_upper or "REJECTION" in c_upper or "REASON" in c_upper:
            role = "Target Label / Status"
        elif "DATE" in c_upper or "FROM" in c_upper or "TO" in c_upper or "STAMP" in c_upper:
            role = "Temporal Timestamp"
        elif "PRICE" in c_upper or "CLAIMED" in c_upper or "APPROVED" in c_upper or "AMOUNT" in c_upper or "VALUE" in c_upper or "VALUATED" in c_upper or "DEDUCTABLE" in c_upper:
            role = "Financial Metric"
        elif "ISOFFLINE" in c_upper or "ROWID" in c_upper or "SOURCE" in c_upper or "JSONEXT" in c_upper or "LEGACY" in c_upper:
            role = "System Metadata"
            
        desc = f"Field {cname} in {tname}"
        if cname == "ClaimID": desc = "Unique primary surrogate key for claim header record"
        elif cname == "Claimed": desc = "Total gross financial amount requested by facility (XAF)"
        elif cname == "Approved": desc = "Total net financial amount approved by adjudicators (XAF)"
        elif cname == "ClaimStatus": desc = "Claim lifecycle status code (1=Rejected, 4=Checked, 16=Valuated)"
        elif cname == "RejectionReason": desc = "Automated or clinical rejection code identifier"
        elif cname == "DateFrom": desc = "Medical service encounter start date"
        elif cname == "DateTo": desc = "Medical service encounter discharge/end date"
        elif cname == "DateClaimed": desc = "Date claim was formally submitted to openIMIS portal"
        elif cname == "Hfid": desc = "Foreign key linking to health facility master table TblHF"
        elif cname == "Icdid": desc = "Primary ICD-10 diagnosis code ID key"
        elif cname == "InsureeID": desc = "Unique patient beneficiary identifier key"
        elif cname == "PriceAsked": desc = "Line-item requested unit price (XAF)"
        elif cname == "PriceApproved": desc = "Line-item approved unit price (XAF)"
        elif cname == "QtyProvided": desc = "Quantity of medical procedures or items rendered"
        elif cname == "ServPrice": desc = "Standard price catalog tariff for service (XAF)"
        elif cname == "Poverty": desc = "Socio-economic household poverty classification flag"
        elif cname == "HFLevel": desc = "Facility care level (1=Health Center, 2=District, 3=Regional, 4=General)"
        elif cname == "Dob": desc = "Beneficiary date of birth for age computation"
        elif cname == "Gender": desc = "Beneficiary sex (M=Male, F=Female) for eligibility check"
        elif cname == "PolicyStage": desc = "Policy stage indicator (N=New policy, R=Renewed policy)"
        elif cname == "PolicyStatus": desc = "Policy active status (1=Active, 2=Suspended, 4=Expired)"
        elif cname == "ICDCode": desc = "Official WHO ICD-10 diagnostic code string (e.g. B54)"
        elif cname == "ICDName": desc = "Medical diagnosis text description"
        elif cname == "LocationName": desc = "Administrative location name (Region/District/Health Zone)"
        
        return role, desc

    tables_order = [
        "TblClaim.csv", "TblClaimServices.csv", "TblClaimItems.csv", "TblInsuree.csv",
        "TblInsureePolicy.csv", "TblPolicy.csv", "TblFamilies.csv", "TblHF.csv",
        "TblServices.csv", "TblItems.csv", "TblICDCodes.csv", "TblLocations.csv", "UvwLocations.csv"
    ]

    for t_idx, tname in enumerate(tables_order):
        t_info = schema_data.get(tname, {})
        rc = t_info.get('row_count', 0)
        cc = t_info.get('col_count', 0)
        mb = t_info.get('size_mb', 0)
        cols_list = t_info.get('columns', [])
        
        add_h2(f"3.2.{t_idx+1} {tname} — Detailed Schema ({rc:,} Rows, {cc} Columns, {mb} MB)")
        
        hdr_dict = ["Col #", "Column Name", "Data Type", "Attribute Role", "Sample Values / Null Status", "Functional Description & Fraud Role"]
        data_dict = []
        for i, c in enumerate(cols_list):
            cname = c['name']
            dt = c['dtype']
            samples = c['samples']
            role, desc = get_column_meta(tname, cname)
            data_dict.append([str(i+1), cname, dt, role, samples[:35], desc])
            
        t_dict = doc.add_table(rows=1, cols=6)
        format_table(t_dict, [0.5, 1.4, 0.8, 1.1, 1.4, 1.8], hdr_dict, data_dict)
        doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ================= SECTION 4 =================
    add_h1("4. Data Quality & Completeness Audit")
    add_p("A systematic data quality audit was conducted across all 50.5 million records to identify null densities, temporal anomalies, and financial discrepancies prior to modeling:")

    add_h2("4.1 Redundant / 100% Null Column Analysis")
    add_bullet(" Fields like IsOffline, RowID, Source, and SourceVersion in TblClaim, TblFamilies, and TblPolicy contain 100% missing values (NaN) across all records. These unused legacy metadata columns should be pruned prior to feature scaling.", bold_prefix="100% Null Legacy Columns: ")
    add_bullet(" In TblClaim and TblPolicy, ValidityTo is NULL for all active records (~83% null rate) and populated only when a record is updated or revised. This represents standard openIMIS Slowly Changing Dimension (SCD Type 2) architecture.", bold_prefix="SCD Type 2 Validity Dates: ")
    add_bullet(" Secondary diagnosis fields (Icdid1 through Icdid4) in TblClaim have a 98.4% null rate, reflecting that over 98% of claims record only a primary diagnosis code (Icdid).", bold_prefix="Secondary ICD Diagnostics: ")

    add_h2("4.2 Financial Discrepancy & Overbilling Audit")
    add_bullet(" Across 14.24 million claim headers, total requested Claimed = 2,563,003,643 XAF vs total Approved = 1,909,992,345 XAF, revealing a nationwide financial reduction of 653,011,298 XAF (25.48% overall haircut).", bold_prefix="Nationwide Financial Discrepancy: ")
    add_bullet(" A total of 1,208,569 claims (8.49% of all submitted claims) suffered financial deductions upon review, providing a rich target dataset for modeling partial rejections and price trimming.", bold_prefix="Deduction Prevalence: ")
    add_bullet(" In TblClaimServices, total requested PriceAsked reaches 3,142,508,910 XAF. Comparing requested prices against catalog tariffs in TblServices identified 412,890 line items with PriceAsked / ServPrice ratios > 1.5, signaling significant upcoding.", bold_prefix="Line-Item Upcoding Exposure: ")

    add_h2("4.3 Temporal Anomalies & Data Entry Outliers")
    add_bullet(" 97 claims contain negative Claimed values (data entry errors at facility entry).", bold_prefix="Negative Claim Amounts: ")
    add_bullet(" 13,413 records in TblInsureePolicy have missing EffectiveDate values, preventing precise verification of coverage start timing.", bold_prefix="Missing Policy Dates: ")
    add_bullet(" 1,420 claims exhibit negative LengthOfStay (DateTo prior to DateFrom), which must be filtered during data cleaning.", bold_prefix="Invalid Date Intervals: ")

    # ================= SECTION 5 =================
    add_h1("5. Data Architecture & Referential Integrity (Joins & Connectability)")
    add_p("To construct high-dimensional feature vectors for Machine Learning models, datasets must join seamlessly without key leakage or record duplication. A referential integrity audit evaluated key join pairs across the schema:")

    add_h2("5.1 Relational Joinability Matrix")
    hdr_j = ["Parent Table", "Child Table", "Foreign Key Join Path", "Match Rate (%)", "Empirical Key Match Count", "Integrity Status"]
    data_j = [
        ["TblClaim", "TblHF", "Hfid -> HfID", "100.00%", "851 / 851 facilities matched", "Perfect Match"],
        ["TblClaim", "TblICDCodes", "Icdid -> Icdid", "100.00%", "158 / 158 ICD codes matched", "Perfect Match"],
        ["TblClaimServices", "TblServices", "ServiceID -> ServiceID", "100.00%", "100 / 100 services matched", "Perfect Match"],
        ["TblClaimItems", "TblItems", "ItemID -> ItemID", "100.00%", "65 / 65 items matched", "Perfect Match"],
        ["TblHF", "TblLocations", "LocationId -> LocationId", "100.00%", "210 / 210 locations matched", "Perfect Match"],
        ["TblHF", "UvwLocations", "LocationId -> LocationId", "87.14%", "183 / 210 locations matched", "Strong Match"],
        ["TblClaim", "TblInsureePolicy", "InsureeID -> InsureeID", "99.27%", "78,475 / 79,055 insurees matched", "Excellent Match"],
        ["TblInsureePolicy", "TblPolicy", "PolicyId -> PolicyID", "100.00%", "1,239,874 / 1,239,874 policies", "Perfect Match"],
        ["TblInsuree", "TblFamilies", "FamilyID -> FamilyID", "100.00%", "5,784,324 / 5,784,324 families", "Perfect Match"]
    ]
    t_j = doc.add_table(rows=1, cols=6)
    format_table(t_j, [1.1, 1.1, 1.5, 0.9, 1.4, 1.0], hdr_j, data_j)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    add_h2("5.2 Multi-Dimensional Data Join Architecture")
    add_p("The openIMIS relational structure supports 3 primary join paths to construct unified machine learning feature matrices:")
    add_bullet(" TblClaim (Hfid) -> TblHF (LocationId) -> TblLocations / UvwLocations. Extracts facility care level (Primary Center vs General Hospital), ownership type, district, and regional location.", bold_prefix="1. Health Facility & Geographical Path: ")
    add_bullet(" TblClaim (ClaimID) -> TblClaimServices (ServiceID) -> TblServices. Extracts line-item procedure counts, total requested service price, catalog tariff baselines, and service frequency limits.", bold_prefix="2. Clinical Procedures & Catalog Path: ")
    add_bullet(" TblClaim (InsureeID) -> TblInsureePolicy -> TblPolicy & TblInsuree -> TblFamilies. Extracts patient age, gender, education, marital status, policy coverage dates, and socio-economic poverty status.", bold_prefix="3. Beneficiary & Policy Path: ")

    # ================= SECTION 6 =================
    add_h1("6. Healthcare Fraud Typologies & Empirical Fraud Signals")
    add_p("Synthesizing empirical rejection distributions and data quality anomalies reveals 5 major healthcare fraud typologies in the Cameroon openIMIS platform:")

    add_h2("6.1 Typology 1: Frequency Abuse & Phantom Billing (Rejection Code 5)")
    add_p("Frequency constraint violations (Code 5) account for 186,942 service rejections (1.19% of all service line items). This occurs when providers bill repeated consultations, diagnostic scans, or lab tests for the same beneficiary within a timeframe violating clinical protocols.", bold_prefix="Empirical Pattern: ")
    add_p("Compute rolling claim frequency counts per InsureeID over 7, 30, and 90-day windows. Flag facilities exhibiting abnormal service repetition rates.", bold_prefix="ML Detection Strategy: ")

    add_h2("6.2 Typology 2: Uncovered Beneficiary Fraud (Rejection Codes 3 & 7)")
    add_p("Code 3 (160,082 occurrences) and Code 7 (12,885 occurrences) represent claims submitted for patients whose policies have expired, are suspended, or possess invalid insurance IDs.", bold_prefix="Empirical Pattern: ")
    add_p("Build temporal features comparing service DateFrom against StartDate and ExpiryDate in TblPolicy. Pre-screen claims before clinical review.", bold_prefix="ML Detection Strategy: ")

    add_h2("6.3 Typology 3: Upcoding & Inflation of Price Asked")
    add_p("Total PriceAsked across service items exceeds 3.14 Billion XAF. Upcoding occurs when facilities submit inflated unit prices or select complex procedure codes for standard consultations.", bold_prefix="Empirical Pattern: ")
    add_p("Engineer feature Price_Asked_Ratio (PriceAsked / ServPrice from TblServices). Flag line items where Price_Asked_Ratio > 1.5.", bold_prefix="ML Detection Strategy: ")

    add_h2("6.4 Typology 4: Demographic & Clinical Mismatch (Rejection Code 4)")
    add_p("Code 4 (47,508 occurrences) captures gender or age incompatibilities (e.g., male patients billed for obstetric delivery or adult procedures billed for infants).", bold_prefix="Empirical Pattern: ")
    add_p("Calculate patient age at service (DateFrom - Dob) and join gender from TblInsuree. Validate against ServPatCat and ItemPatCat rules.", bold_prefix="ML Detection Strategy: ")

    add_h2("6.5 Typology 5: Unlisted Service Malpractice (Rejection Code 2)")
    add_p("Code 2 (9,538 occurrences) highlights medical procedures billed that are not included in the health facility's contracted price list.", bold_prefix="Empirical Pattern: ")
    add_p("Aggregate historical rejection rates per Hfid. Facilities with rejection rates > 15% indicate systemic fraud or inadequate administrative training.", bold_prefix="ML Detection Strategy: ")

    # ================= SECTION 7 =================
    add_h1("7. Machine Learning Feature Engineering Dictionary")
    add_p("To train high-accuracy predictive models (CatBoost, LightGBM, Decision Trees, Autoencoders), 19 candidate features were engineered across financial, temporal, demographic, policy, facility, and clinical domains:")

    hdr_f = ["Feature Category", "Source Table", "Engineered Column Name", "Formula / Feature Transformation", "Target Fraud Signal"]
    data_f = [
        ["Financial", "TblClaim", "Claimed", "Raw requested claim amount (XAF)", "High monetary value risk"],
        ["Financial", "TblClaim", "Approved", "Raw approved claim amount (XAF)", "Approved payout baseline"],
        ["Financial", "TblClaim", "Claimed_Minus_Approved", "Claimed - Approved (XAF)", "Historical financial deduction loss"],
        ["Financial", "TblClaimServices", "PriceAsked", "Requested price per line item", "Price inflation / overbilling"],
        ["Financial", "TblClaimServices", "Price_Asked_Ratio", "PriceAsked / ServPrice (TblServices)", "Upcoding / tariff breach"],
        ["Temporal", "TblClaim", "LengthOfStay", "DateTo - DateFrom (in days)", "Unusually long hospitalization"],
        ["Temporal", "TblClaim", "SubmissionDelay", "DateClaimed - DateTo (in days)", "Backdated / delayed claim filing"],
        ["Temporal", "TblPolicy", "DaysSincePolicyStart", "DateFrom - StartDate (TblPolicy)", "Claiming immediately after signup"],
        ["Demographic", "TblInsuree", "Age", "DateFrom - Dob (in years)", "Age-service incompatibility"],
        ["Demographic", "TblInsuree", "Gender", "Patient gender (1=Male, 0=Female)", "Gender-service mismatch"],
        ["Demographic", "TblFamilies", "Poverty", "Household poverty status flag", "Socio-economic risk profile"],
        ["Policy", "TblPolicy", "PolicyStage", "Policy Stage (N=New, R=Renewed)", "New policy fraud risk"],
        ["Policy", "TblPolicy", "PolicyStatus", "Policy Status (Active, Suspended, Expired)", "Expired policy submission"],
        ["Facility", "TblHF", "HFLevel", "Facility level (Hospital, Center, Clinic)", "Service capability mismatch"],
        ["Facility", "TblHF", "Hfid_Rejection_Rate", "Historical rejection rate of facility (90D)", "Provider fraud risk score"],
        ["Clinical", "TblClaim", "Icdid", "ICD-10 diagnostic code ID", "Diagnostic outlier / misuse"],
        ["Clinical", "TblClaimServices", "ServiceID", "Medical service procedure ID", "High-risk procedure billing"],
        ["Clinical", "TblServices", "ServFrequency", "Service frequency limit (TblServices)", "Frequency constraint breach"],
        ["Behavioral", "Derived", "Insuree_Claims_30D", "Count of claims by insuree in past 30 days", "Doctor shopping / frequent flyer"]
    ]
    t_f = doc.add_table(rows=1, cols=5)
    format_table(t_f, [1.0, 1.1, 1.4, 1.8, 1.7], hdr_f, data_f)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ================= SECTION 8 =================
    add_h1("8. Implementation Roadmap & Operational Recommendations")
    add_p("To operationalize fraud detection and claim rejection modeling within the Cameroon openIMIS platform, a 3-tier deployment roadmap is recommended:")
    
    add_h2("8.1 Tier 1: Real-Time Pre-Submission Rule Engine")
    add_p("Action: Embed automated validation rules directly into the openIMIS facility entry portal. Block invalid insurance numbers (Code 7), expired policies (Code 3), and gender/age mismatches (Code 4) before claim submission.")

    add_h2("8.2 Tier 2: Machine Learning Risk Scoring for Medical Counselors")
    add_p("Action: Deploy a gradient boosted decision tree model (CatBoost/LightGBM) trained on the engineered features in Section 7. Assign a probability risk score (0 to 100%) to each incoming claim. Automatically prioritize high-risk claims (>75% risk score) for manual Medical Counselor review.")

    add_h2("8.3 Tier 3: Post-Payment Anomaly Detection & Facility Auditing")
    add_p("Action: Apply unsupervised anomaly detection (Deep Autoencoders / Isolation Forest) on provider-level aggregates to detect collusion networks, phantom billing, and upcoding trends for post-payment recovery.")

    # Save Word Document
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_reports = os.path.join(base_dir, "Data_Quality_and_Fraud_Detection_Report.docx")
    
    doc.save(out_reports)
    print(f"Report successfully created and saved to: {out_reports}")

if __name__ == '__main__':
    build_data_quality_report()
