from app.models.document import Page, Document, DocumentElement


def normalize(result, source):

    pages = []

    for azure_pages in result.pages:
        page = Page(
            page_number= azure_pages.page_number,
            width=azure_pages.width,
            height=azure_pages.height,
            elements=[]
        )

        pages.append(page)


    for azure_paras in result.paragraphs:
        pg_no = azure_paras.bounding_regions[0].page_number
        for page in pages:
            if(page.page_number == pg_no):
                doc_element = DocumentElement(
                            element_type="text",
                            content=azure_paras.content,
                            metadata = {
                                "role" :  azure_paras.role
                            },
                            page_number=pg_no
                        )
                page.elements.append(doc_element)
                

    document = Document(
        document_id=source,
        source=source,
        pages=pages,
        metadata={}
    )

    return document


