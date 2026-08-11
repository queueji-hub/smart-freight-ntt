# PHASE 23 — QUOTATION FORM REALITY AUDIT

## 1. Findings & Root Cause Analysis
- **Root Cause**: On every rerun (including validation failures), `d.get("items")` in `_quotation_form` is empty (for new mode) or populated with the pristine DB values (for edit mode). This causes `df_items` to be reconstructed, wiping out user edits in `st.data_editor`.
- **Form Variables**: Streamlit widgets use stable keys prefixed by `prefix` (e.g. `new_cust`, `edit_cust`), keeping text/number/selectbox selections safe on validation failures.
- **Numbering Protection**: The quotation number generator is nested inside `create_quotation()`, ensuring numbers are only consumed on a successful transaction insert.
