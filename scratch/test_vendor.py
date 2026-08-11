import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import init_database
from managers.vendor_manager import create_vendor

with patch("psycopg2.connect", side_effect=Exception("Forced SQLite Fallback")):
    mock_secrets = MagicMock()
    mock_secrets.get.side_effect = lambda k, default=None: "development" if k == "APP_ENV" else default
    with patch("streamlit.secrets", mock_secrets):
        init_database()
        v_id = create_vendor({
            "vendor_code": "V-QA-22",
            "legal_name": "Carrier Transporter Test",
            "tax_id": "TAX-V-22",
            "country": "TH",
            "currency": "THB"
        }, {"id": 1, "username": "qa_runner"})
        print("Vendor creation returned:", v_id)
