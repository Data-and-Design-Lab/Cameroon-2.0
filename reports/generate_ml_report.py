import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import os
import shutil

doc = docx.Document()

# Set Margins
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def style_table(table, col_widths, headers, data):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header Row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], '1B365D') # Deep Navy
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=120, right=120)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in p.runs:
            run.font.name = 'Arial'
            run.font.size = Pt(9.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            
    # Data Rows
    for r_idx, row_data in enumerate(data):
        row_cells = table.add_row().cells
        bg_color = 'F8F9FA' if r_idx % 2 == 1 else 'FFFFFF'
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = row_cells[c_idx].paragraphs[0]
            for run in p.runs:
                run.font.name = 'Calibri'
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(44, 62, 80)
                
    # Set widths
    for row in table.rows:
        for c_idx, w in enumerate(col_widths):
            row.cells[c_idx].width = Inches(w)

def add_h1(text):
    h = doc.add_paragraph()
    h.paragraph_format.space_before = Pt(16)
    h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True
    r = h.add_run(text)
    r.font.name = 'Arial'
    r.font.size = Pt(16)
    r.font.bold = True
    r.font.color.rgb = RGBColor(27, 54, 93)
    return h

def add_h2(text):
    h = doc.add_paragraph()
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(4)
    h.paragraph_format.keep_with_next = True
    r = h.add_run(text)
    r.font.name = 'Arial'
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = RGBColor(41, 128, 185)
    return h

def add_h3(text):
    h = doc.add_paragraph()
    h.paragraph_format.space_before = Pt(8)
    h.paragraph_format.space_after = Pt(2)
    h.paragraph_format.keep_with_next = True
    r = h.add_run(text)
    r.font.name = 'Arial'
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = RGBColor(52, 73, 94)
    return h

def add_p(text, bold_prefix='', italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        rb = p.add_run(bold_prefix)
        rb.font.name = 'Calibri'
        rb.font.size = Pt(10.5)
        rb.font.bold = True
        rb.font.color.rgb = RGBColor(44, 62, 80)
    r = p.add_run(text)
    r.font.name = 'Calibri'
    r.font.size = Pt(10.5)
    r.font.italic = italic
    r.font.color.rgb = RGBColor(44, 62, 80)
    return p

def add_b(text, bold_prefix=''):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        rb = p.add_run(bold_prefix)
        rb.font.name = 'Calibri'
        rb.font.size = Pt(10.5)
        rb.font.bold = True
        rb.font.color.rgb = RGBColor(44, 62, 80)
    r = p.add_run(text)
    r.font.name = 'Calibri'
    r.font.size = Pt(10.5)
    r.font.color.rgb = RGBColor(44, 62, 80)
    return p

def add_callout(text, title=''):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, 'F0F4F8')
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    if title:
        rt = p.add_run(title + '\n')
        rt.font.name = 'Arial'
        rt.font.size = Pt(10.5)
        rt.font.bold = True
        rt.font.color.rgb = RGBColor(27, 54, 93)
    r = p.add_run(text)
    r.font.name = 'Calibri'
    r.font.size = Pt(10.0)
    r.font.italic = True
    r.font.color.rgb = RGBColor(44, 62, 80)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

# ================= TITLE & COVER =================
title_p = doc.add_paragraph()
title_p.paragraph_format.space_before = Pt(24)
title_p.paragraph_format.space_after = Pt(6)
title_run = title_p.add_run('MACHINE LEARNING FRAUD DETECTION & REJECTED CLAIM FRAMEWORK')
title_run.font.name = 'Arial'
title_run.font.size = Pt(22)
title_run.font.bold = True
title_run.font.color.rgb = RGBColor(27, 54, 93)

subtitle_p = doc.add_paragraph()
subtitle_p.paragraph_format.space_after = Pt(18)
sub_run = subtitle_p.add_run('Evaluation of Supervised Models, Unsupervised Anomaly Detectors, SMOTE Imbalance Handling, and SHAP Explainability for Cameroon openIMIS 3.0')
sub_run.font.name = 'Arial'
sub_run.font.size = Pt(13)
sub_run.font.italic = True
sub_run.font.color.rgb = RGBColor(41, 128, 185)

add_callout(
    'Target Dataset: Cameroon openIMIS Health Insurance Database (13 CSV Files, >52.4 Million Records)\n'
    'Evaluated Models: Supervised (CatBoost, Decision Tree, SVM) | Unsupervised (Isolation Forest, Autoencoder, HDBSCAN, LOF, DBSCAN, K-Means)\n'
    'Explainability Engine: SHAP (SHapley Additive exPlanations) | Data Imbalance Method: SMOTE & Class Weighting\n'
    'Date of Analysis: July 2026',
    'EXECUTIVE TECHNICAL SUMMARY'
)

# ================= SECTION 1 =================
add_h1('1. Architecture & Dual-Engine Strategy')
add_p('Health insurance claim fraud detection requires a hybrid approach. Because the Cameroon openIMIS platform records both historical rejected claims (known labels) and encounters new, emerging fraud schemes (unlabeled anomalies), a Dual-Engine Machine Learning Architecture is recommended:')

add_b('Trained on historical claim rejections (ClaimStatus = 1 and ClaimServiceStatus = 2). It predicts the exact probability that an incoming claim violates technical, clinical, or policy rules.', '1. Supervised Learning Engine: ')
add_b('Scans incoming claims without using historical labels to discover novel fraud typologies, phantom billing bursts, and provider collusion networks.', '2. Unsupervised Anomaly Engine: ')
add_b('Translates complex model predictions into clear, audit-ready explanations for Medical Counselors and auditors.', '3. SHAP Explainability Layer: ')

# ================= SECTION 2 =================
add_h1('2. Supervised Learning Models')
add_p('Supervised models utilize historical labels from TblClaim and TblClaimServices to predict whether future claim submissions will be rejected or fraudulent.')

add_h2('2.1 CatBoost (Categorical Gradient Boosting)')
add_p('CatBoost is an advanced gradient-boosted decision tree algorithm optimized for categorical-heavy datasets.', 'Algorithm Overview: ')
add_p('YES — Top Recommendation (Best Performance).', 'Compatibility with Cameroon Data: ')
add_p('The Cameroon database contains high-cardinality categorical features such as Hfid (851 health facilities), Icdid (158 ICD codes), ServiceID (100 procedure codes), PolicyStage (N/R), and Gender. CatBoost processes these categorical fields natively without requiring memory-intensive One-Hot Encoding, preventing target leakage and overfitting.', 'How it Works on openIMIS Data: ')
add_p('CatBoost features internal parameters scale_pos_weight = 31.3 or auto_class_weights="Balanced". When combined with SMOTE, it handles the 31:1 class imbalance effectively.', 'Data Imbalance & SMOTE Integration: ')

add_h2('2.2 Decision Tree Classifier')
add_p('Decision Trees create hierarchical IF-THEN rules by recursively partitioning feature space based on Information Gain or Gini Impurity.', 'Algorithm Overview: ')
add_p('YES — Excellent for Baseline Rules & Auditor Verification.', 'Compatibility with Cameroon Data: ')
add_p('Decision Trees mirror human decision logic (e.g., IF PriceAsked > 50,000 XAF AND DaysSincePolicyStart < 7 THEN Rejection Probability = 88%). They extract explicit rule sets that can be embedded directly into openIMIS pre-submission checks.', 'How it Works on openIMIS Data: ')
add_p('Unweighted decision trees overfit heavily toward the majority class (Accepted claims). Applying SMOTE or class_weight="balanced" forces the tree to evaluate minority class rejection patterns.', 'Data Imbalance & SMOTE Integration: ')

add_h2('2.3 Support Vector Machine (SVM)')
add_p('SVM projects input features into a high-dimensional space via Kernel Functions (RBF, Polynomial) to construct an optimal separating hyperplane.', 'Algorithm Overview: ')
add_p('YES — Applicable on sampled training subsets (requires feature scaling).', 'Compatibility with Cameroon Data: ')
add_p('SVM is effective at establishing non-linear decision boundaries between legitimate multi-service packages and artificially inflated billing bundles. However, training SVM on millions of rows is computationally intensive.', 'How it Works on openIMIS Data: ')
add_p('SVM is extremely sensitive to scale and class imbalance. Numerical features (Claimed, LengthOfStay) must be normalized using StandardScaler, and SMOTE must be applied to equalize class boundaries.', 'Data Imbalance & SMOTE Integration: ')

# ================= SECTION 3 =================
add_h1('3. Unsupervised Learning Models & Anomaly Detection')
add_p('Unsupervised models identify rare, novel, or structural anomalies in claim submissions without relying on past rejection labels.')

add_h2('3.1 Isolation Forest')
add_p('Isolation Forest isolates anomalies by randomly selecting a feature and splitting the feature values. Outliers require fewer splits to isolate than normal data points.', 'Algorithm Overview: ')
add_p('YES — Top Unsupervised Choice for Transactional Claims.', 'Compatibility with Cameroon Data: ')
add_p('Evaluates millions of records in TblClaim and TblClaimServices rapidly. Claims with unusual feature combinations (e.g. abnormal price requested for a basic consultation code) receive high anomaly scores.', 'How it Works on openIMIS Data: ')
add_p('Inherently handles class imbalance by treating rare records as positive anomalies (contamination parameter set to 3–5%).', 'Imbalance Resilience: ')

add_h2('3.2 Autoencoder (Deep Neural Network)')
add_p('An Autoencoder is a neural network trained to compress (Encoder) and reconstruct (Decoder) legitimate claim patterns. The Reconstruction Mean Squared Error (MSE) acts as the anomaly score.', 'Algorithm Overview: ')
add_p('YES — Best Deep Learning Approach for Complex Behavioral Patterns.', 'Compatibility with Cameroon Data: ')
add_p('Trained strictly on accepted claims (ClaimStatus = 16 or 4). When a fraudulent or abnormal claim is fed into the network, the reconstruction error spikes, signaling a high-risk transaction.', 'How it Works on openIMIS Data: ')
add_p('Does not require SMOTE because it is trained exclusively on normal baseline transactions.', 'Imbalance Resilience: ')

add_h2('3.3 HDBSCAN (Hierarchical Density-Based Spatial Clustering)')
add_p('HDBSCAN extends DBSCAN by extracting clusters of varying densities and identifying noise data points.', 'Algorithm Overview: ')
add_p('YES — Recommended for Provider & Facility Level Profiling.', 'Compatibility with Cameroon Data: ')
add_p('Applied to aggregate health facility features (Hfid) and officer activities (OfficerID). Facilities operating within standard clinical norms form dense clusters, while fraudulent or rogue facilities fall out as noise (-1).', 'How it Works on openIMIS Data: ')

add_h2('3.4 Local Outlier Factor (LOF)')
add_p('LOF computes the local density of a claim relative to its k-nearest neighbors. Claims in sparse local spaces receive high LOF scores.', 'Algorithm Overview: ')
add_p('YES — Ideal for Detecting Regional Price Inflation & Upcoding.', 'Compatibility with Cameroon Data: ')
add_p('Flags health facilities charging significantly above their regional peer average (from UvwLocations) for standard procedure codes.', 'How it Works on openIMIS Data: ')

add_h2('3.5 DBSCAN')
add_p('DBSCAN groups data points based on spatial density within a specified radius (eps) and minimum points (min_samples).', 'Algorithm Overview: ')
add_p('YES — Effective for Geographic & Temporal Burst Detection.', 'Compatibility with Cameroon Data: ')
add_p('Identifies suspicious temporal bursts of claims submitted from a single district or village within a short time window.', 'How it Works on openIMIS Data: ')

add_h2('3.6 K-Means Clustering')
add_p('K-Means partitions data into k centroids by minimizing within-cluster variance.', 'Algorithm Overview: ')
add_p('YES — Best for Facility & Patient Segmentation.', 'Compatibility with Cameroon Data: ')
add_p('Segments facilities into operational tiers. Claims that fall far from their cluster centroid indicate potential billing anomalies.', 'How it Works on openIMIS Data: ')

# ================= SECTION 4 =================
add_h1('4. Model Explainability & Transparency (SHAP)')
add_p('Machine learning models in healthcare insurance must provide clear justifications for audit compliance. SHAP (SHapley Additive exPlanations) uses cooperative game theory to measure feature contributions.')

add_p('When CatBoost or XGBoost assigns a 92% Rejection Risk to an incoming claim, SHAP generates an instant visual decomposition for the Medical Counselor:')
add_b('+35% Risk Contribution: PriceAsked = 120,000 XAF exceeds standard ServPrice (25,000 XAF)', 'Risk Driver 1: ')
add_b('+28% Risk Contribution: DaysSincePolicyStart = 2 days (policy newly activated)', 'Risk Driver 2: ')
add_b('+15% Risk Contribution: Insuree_Claims_30D = 8 (high claim frequency count)', 'Risk Driver 3: ')
add_b('-6% Risk Contribution: Valid ICD-10 Diagnosis code match', 'Risk Mitigation: ')

# ================= SECTION 5 =================
add_h1('5. Class Imbalance Handling Strategy (SMOTE & Scaling)')
add_p('The Cameroon dataset exhibits a 31.3 : 1 imbalance ratio for claim rejections and a 34.0 : 1 ratio for service rejections. Standard model training without adjustment will lead to severe under-detection of rejections.')

add_h2('5.1 SMOTE (Synthetic Minority Over-sampling Technique)')
add_p('SMOTE generates synthetic samples along line segments connecting k-nearest minority class neighbors (Rejected claims). This balances the training distribution without replicating identical duplicate rows.')

add_h2('5.2 Cost-Sensitive Loss Functions')
add_p('For tree-based algorithms like CatBoost, LightGBM, and Random Forest, cost-sensitive parameters (scale_pos_weight = 31.3 or class_weight="balanced") scale the loss function penalty for misclassifying minority rejection cases.')

# ================= SECTION 6 =================
add_h1('6. Comprehensive Model Comparison Matrix')
add_p('Below is the comparative evaluation matrix of all 10 algorithms for the Cameroon openIMIS fraud detection deployment:')

headers_m = ['Algorithm', 'Category', 'Imbalance Handling', 'Scalability', 'Auditor Transparency', 'Recommended Role']
data_m = [
    ['CatBoost', 'Supervised', 'Native Weighting / SMOTE', 'High (14M+ rows)', 'High (via SHAP)', 'Primary Production Classifier'],
    ['Decision Tree', 'Supervised', 'SMOTE / Class Weighting', 'High', 'Very High (Direct Rules)', 'Baseline & Rule Extraction'],
    ['SVM', 'Supervised', 'SMOTE + Scaling Required', 'Medium (Subsamples)', 'Medium', 'Specialized Boundary Classifier'],
    ['Isolation Forest', 'Unsupervised', 'Native Anomaly Score', 'High', 'Medium', 'Primary Transaction Screening'],
    ['Autoencoder', 'Unsupervised', 'Train on Normal Only', 'High (GPU Accelerated)', 'Medium (Reconstruction)', 'Complex Fraud Pattern Detector'],
    ['HDBSCAN', 'Unsupervised', 'Identifies Noise (-1)', 'Medium', 'Medium', 'Provider Collusion Detection'],
    ['Local Outlier Factor', 'Unsupervised', 'Density Evaluation', 'Medium', 'Medium', 'Regional Price Inflation Detection'],
    ['DBSCAN', 'Unsupervised', 'Identifies Noise (-1)', 'Medium', 'Medium', 'Spatiotemporal Burst Detection'],
    ['K-Means', 'Unsupervised', 'Distance to Centroid', 'High', 'High (Centroid Analysis)', 'Provider Profiling & Segmentation'],
    ['SHAP', 'Explainability', 'N/A (Explanation Engine)', 'High', 'Very High', 'Auditor Visual Justification']
]
t_m = doc.add_table(rows=1, cols=6)
style_table(t_m, [1.3, 1.1, 1.5, 1.1, 1.2, 1.5], headers_m, data_m)

# Save Report
report_dir = os.path.dirname(os.path.abspath(__file__))
out1 = os.path.join(report_dir, 'Fraud_Detection_Machine_Learning_Models_Report.docx')

doc.save(out1)

print('Machine Learning Report generated successfully at:')
print('  -', out1)
