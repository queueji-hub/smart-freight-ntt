from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO


def generate_pdf(data):

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("QUOTATION", styles["Title"]))
    elements.append(Spacer(1, 12))

    table_data = [["Description", "Price", "Currency"]]

    total = 0

    for item in data["items"]:
        table_data.append([
            item["description"],
            str(item["price"]),
            item.get("currency", "USD")
        ])
        total += float(item["price"])

    table_data.append(["TOTAL", str(total), ""])

    table = Table(table_data)
    elements.append(table)

    doc.build(elements)

    buffer.seek(0)
    return buffer