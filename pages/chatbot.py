import os
import io
import time
import hashlib
import tempfile
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import streamlit.components.v1 as components
from openai import RateLimitError

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# =====================================================================================
# 환경 설정 (.env에서 API Key 로드)
# =====================================================================================
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. 프로젝트의 .env 파일을 확인하세요.")
    st.stop()

CHROMA_PERSIST_DIR = "./chroma_cache"


# =====================================================================================
# 파일 로더 (행 개수 추적 메타데이터 추가)
# =====================================================================================
def load_tabular_as_docs(file_name: str, file_bytes: bytes) -> list[Document]:
    """CSV나 Parquet 파일을 읽어 텍스트로 변환하고, 묶인 행의 개수를 기록합니다."""
    ext = os.path.splitext(file_name)[-1].lower()
    file_buffer = io.BytesIO(file_bytes)
    
    if ext == ".csv":
        try:
            df = pd.read_csv(file_buffer, encoding="utf-8")
        except UnicodeDecodeError:
            file_buffer.seek(0)
            df = pd.read_csv(file_buffer, encoding="cp949")
    elif ext == ".parquet":
        df = pd.read_parquet(file_buffer)
    else:
        return []

    df = df.fillna("")
    docs = []
    
    # 대용량 데이터를 100행씩 잘라서 문서 조각으로 생성
    batch_size = 100
    for i in range(0, len(df), batch_size):
        chunk_df = df.iloc[i : i + batch_size]
        content = f"[출처: {file_name} | 행 {i+1}~{min(i+batch_size, len(df))}]\n" + chunk_df.to_csv(index=False)
        
        # 진행률 표시를 위해 해당 조각이 몇 개의 행을 포함하는지 메타데이터에 저장
        docs.append(
            Document(
                page_content=content, 
                metadata={"source": file_name, "num_rows": len(chunk_df)}
            )
        )
    
    return docs

def load_single_file(file_name: str, file_bytes: bytes) -> list[Document]:
    ext = os.path.splitext(file_name)[-1].lower()
    
    if ext in [".csv", ".parquet"]:
        return load_tabular_as_docs(file_name, file_bytes)

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    try:
        if ext == ".pdf":
            loader = PyPDFLoader(tmp_path)
        elif ext in [".txt", ".md"]:
            loader = TextLoader(tmp_path, encoding="utf-8")
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")

        raw_docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        split_docs = text_splitter.split_documents(raw_docs)

        for doc in split_docs:
            doc.page_content = f"[출처: {file_name}]\n" + doc.page_content
            # 텍스트 문서/PDF는 1조각을 1행(단위)으로 간주
            doc.metadata["source"] = file_name
            doc.metadata["num_rows"] = 1
            
        return split_docs
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# =====================================================================================
# RAG 파이프라인 (실시간 행 단위 진행률 표시)
# =====================================================================================
@st.cache_resource(show_spinner=False)
def build_rag_system(files_payload: tuple[tuple[str, bytes], ...]):
    embedding = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
    combined_hash = hashlib.md5(b"".join(b for _, b in files_payload)).hexdigest()[:12]
    collection_name = f"rag_store_{combined_hash}"

    vectordb = Chroma(
        collection_name=collection_name,
        embedding_function=embedding,
        persist_directory=CHROMA_PERSIST_DIR
    )

    existing_count = vectordb._collection.count()
    if existing_count == 0:
        st.info("💡 대용량 파일은 초기 학습에 수 분이 소요될 수 있습니다. 완료 후에는 즉시 로드됩니다.")
        
        # 파일 텍스트 추출
        all_documents = []
        for f_name, f_bytes in files_payload:
            all_documents.extend(load_single_file(f_name, f_bytes))
            
        # 전체 행(조각) 개수 계산
        total_rows = sum(doc.metadata.get("num_rows", 1) for doc in all_documents)
        processed_rows = 0

        progress_bar = st.progress(0, text=f"데이터 준비 완료. 총 {total_rows:,}개 행(데이터) 학습을 시작합니다...")

        # 100개 문서 조각 단위로 묶어서 벡터 DB에 전송
        batch_size = 100
        for i in range(0, len(all_documents), batch_size):
            batch_docs = all_documents[i : i + batch_size]
            
            while True:
                try:
                    vectordb.add_documents(batch_docs)
                    break
                except RateLimitError:
                    st.toast("⏳ OpenAI 요청 한도 도달. 20초 대기 후 자동으로 이어서 학습합니다...", icon="⚠️")
                    time.sleep(20)

            # 현재 배치에 포함된 실제 행 개수 누적
            processed_rows += sum(doc.metadata.get("num_rows", 1) for doc in batch_docs)
            
            # 퍼센트 계산 및 프로그레스 바 업데이트
            pct = min(100, int((processed_rows / total_rows) * 100))
            progress_bar.progress(pct, text=f"총 {total_rows:,}개 행 중 {processed_rows:,}개 행 학습 중... ⏳ ({pct}%)")

        progress_bar.progress(100, text=f"✅ 총 {total_rows:,}개 행 학습이 성공적으로 완료되었습니다!")

    retriever = vectordb.as_retriever(search_kwargs={"k": 4})

    template = """당신은 주어진 문서를 바탕으로 질문에 답변하는 AI 어시스턴트입니다.
주어진 검색 결과(Context)를 바탕으로 답변하고, 참조한 출처(파일명과 행 번호 등)를 함께 안내하세요.
검색 결과에 없는 내용이라면 추측하지 말고 답변할 수 없다고 하세요.

{context}

Question: {question}
Answer:
"""
    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    answer_chain = prompt | llm | StrOutputParser()

    return retriever, answer_chain


def get_rag_response(retriever, answer_chain, input_text: str):
    docs = retriever.invoke(input_text)
    context = "\n\n".join(doc.page_content for doc in docs)
    result = answer_chain.invoke({"context": context, "question": input_text})
    return result.strip()

def get_general_response(input_text: str):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    return llm.invoke(input_text).content


# =====================================================================================
# 챗봇 UI (항상 활성화)
# =====================================================================================
st.subheader("데이터 분석 AI 챗봇")

st.markdown('<div id="top"></div>', unsafe_allow_html=True)
st.page_link("pages/home.py", label="홈으로 돌아가기", icon="🏠")
st.markdown("<br>", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "데이터 파일을 업로드해주세요 (다중 선택 가능 | CSV, Parquet, PDF, TXT)",
    type=["csv", "parquet", "pdf", "txt"],
    accept_multiple_files=True
)

if "messages" not in st.session_state:
    st.session_state.messages = []

retriever, answer_chain = None, None
if uploaded_files:
    current_file_names = sorted([f.name for f in uploaded_files])

    if st.session_state.get("uploaded_file_names") != current_file_names:
        st.session_state.uploaded_file_names = current_file_names
        st.session_state.messages = []

    files_payload = tuple((f.name, f.getvalue()) for f in uploaded_files)
    retriever, answer_chain = build_rag_system(files_payload)
    st.caption(f"📚 현재 학습된 파일 ({len(uploaded_files)}개): " + ", ".join(current_file_names))
else:
    st.info("💡 파일을 업로드하지 않으면 일반적인 AI 챗봇으로 동작합니다.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("질문을 입력해주세요..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("답변을 생성하고 있습니다..."):
            if retriever and answer_chain:
                bot_message = get_rag_response(retriever, answer_chain, user_input)
            else:
                bot_message = get_general_response(user_input)
                
        st.markdown(bot_message)

    st.session_state.messages.append({"role": "assistant", "content": bot_message})

if st.button("대화 초기화"):
    st.session_state.messages = []
    st.rerun()