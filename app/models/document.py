from dataclasses import dataclass

@dataclass
class DocumentElement:
    element_type : str
    content : str | None
    page_number : int
    metadata : dict

@dataclass
class Page:
    page_number : int
    width : float
    height : float
    elements : list[DocumentElement]

@dataclass
class Document:
    document_id : str
    source : str
    pages : list[Page]
    metadata : dict
