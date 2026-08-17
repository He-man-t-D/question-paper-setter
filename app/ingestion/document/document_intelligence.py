import os
import json
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from app.ingestion.document.normalizer import normalize

from dotenv import load_dotenv

load_dotenv()

DI_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
DI_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

credential = AzureKeyCredential(DI_KEY)


client = DocumentIntelligenceClient(
    endpoint=DI_ENDPOINT,
    credential=credential
)

result = dict()

with open(r'D:\DataScienceClass\Projects\question-paper-setter\data\raw\tables.pdf', "rb") as f:
    poller = client.begin_analyze_document(
        "prebuilt-layout",
        body=f
    )

    result = poller.result()

    data = result.as_dict()

    with open(
        r"D:\DataScienceClass\Projects\question-paper-setter\data\processed\tables.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


normalized_data = normalize(result, "gmail.pdf")

print("Document:", normalized_data.document_id)
print("Source:", normalized_data.source)
print("Number of pages:", len(normalized_data.pages))

for page in normalized_data.pages:
    print(
        "Page:", page.page_number,
        "Width:", page.width,
        "Height:", page.height,
        "Elements:", len(page.elements)
    )


