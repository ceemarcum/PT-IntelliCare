"""
Step 1 of the RAG: build the knowledge base (run once, and again when the sources change).

This is the notebook's loading, chunking and embedding cells. Differences from Colab:
  - PDFs are read from data/pdfs/ instead of /content/
  - the API key comes from the .env file instead of userdata.get()
  - the vector store is saved to chroma_db/ so the API can reuse it without rebuilding

Run from the Capstone_Backend folder:  py -m rag.build_index
"""
import shutil
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from langchain_community.document_loaders import PyPDFLoader, RecursiveUrlLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from rag.config import PDF_DIR, PDF_FILES, WEBSITES, CHROMA_DIR, EMBEDDING_MODEL, check_api_key

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def load_documents():
    all_documents = []

    # PDFs
    for name in PDF_FILES:
        path = PDF_DIR / name
        if not path.exists():
            print(f"Missing PDF: {path} (download it and save it there)")
            continue
        pages = PyPDFLoader(str(path)).load()
        all_documents.extend(pages)
        print(f"{name}: {len(pages)} pages")

    # Websites
    for site in WEBSITES:
        loader = RecursiveUrlLoader(url=site["url"], max_depth=2, check_response_status=True,
                                    exclude_dirs=site["exclude_dirs"])
        html_docs = loader.load()

        for doc in html_docs:
            soup = BeautifulSoup(doc.page_content, "html.parser")
            text = soup.get_text(separator="\n")
            all_documents.append(Document(page_content=text, metadata=doc.metadata))
        print(f"{site['url']}: {len(html_docs)} pages")

    for d in all_documents[-5:]:
        print(d.metadata.get("source"), len(d.page_content))

    return all_documents


def build():
    check_api_key()
    all_documents = load_documents()

    # Preprocess text/descriptions
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(all_documents)
    print(f"{len(chunks)} chunks")

    # Embeddings, saved to disk
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)     # start fresh so old chunks aren't duplicated
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    print(f"Saved the vector store to {CHROMA_DIR}")


if __name__ == "__main__":
    build()
