"""
FastKwan - Traditional Chinese Medicine (TCM) API
A FastAPI-based service for TCM syndrome differentiation, lifestyle recommendations,
and prescription suggestions using AI and vector search.
"""

import os
import re
from contextlib import asynccontextmanager

import cohere
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from openai import OpenAI
from pinecone import Pinecone
from pydantic import BaseModel
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "evidgpt")

if not all([OPENAI_API_KEY, PINECONE_API_KEY, COHERE_API_KEY, MONGODB_URI]):
    raise ValueError(
        "Missing required environment variables. "
        "Please check .env.example and set all required variables."
    )

openai_client = OpenAI(api_key=OPENAI_API_KEY)
co = cohere.Client(COHERE_API_KEY)

pc = Pinecone(api_key=PINECONE_API_KEY)
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
vectorstore = PineconeVectorStore(
    index=pc.Index(PINECONE_INDEX_NAME), embedding=embeddings
)

mongo_client = MongoClient(MONGODB_URI, server_api=ServerApi("1"))
db = mongo_client["cmedai"]
collection = db["教科书"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    yield
    mongo_client.close()


app = FastAPI(
    title="FastKwan",
    description="Traditional Chinese Medicine (TCM) AI API",
    version="1.0.0",
    lifespan=lifespan,
)


class Query(BaseModel):
    """Query model for TCM requests."""

    query: str


class SyndromeResponse(BaseModel):
    """Response model for syndrome differentiation."""

    result: str


class LifestyleResponse(BaseModel):
    """Response model for lifestyle recommendations."""

    病名: str
    预防与调摄: str


class PrescriptionResponse(BaseModel):
    """Response model for prescription suggestions."""

    results: dict


@app.post("/syndrome", response_model=SyndromeResponse)
def syndrome(query: Query):
    """
    Perform TCM syndrome differentiation based on patient symptoms.
    Uses NER to extract symptoms, then vector search and reranking to find similar syndromes.
    """
    try:
        ner_completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """為症狀進行NER, 请只按例子output NER的内容，不需要症状NER以外任何东西

            例子：
            input
            - 患者最近情况好一点了，已经转阴。
            - 患者在日本时自己发烧，回香港后看中医。
            - 中医给患者开的中药可以舒缓症状，有抗病毒功效。
            - 患者有些痰，喉咙有点干，胃口正常，睡眠质量好。
            - 患者咳嗽两天，有些感冒，鼻塞、鼻水倒流，喉嚨有些痛和乾，有痰黏著喉嚨，大便正常，睡眠六至七个小时，舌头有点红，吃过炸鸡。
            - 中医师会给患者开药治疗感冒
output：
            痰，喉嚨干，感冒，鼻塞，咳嗽""",
                },
                {
                    "role": "user",
                    "content": query.query,
                },
            ],
        )

        ner_output = ner_completion.choices[0].message.content

        retrieved_docs = vectorstore.similarity_search(
            query=ner_output, k=30, namespace="syndromes"
        )
        retriever_texts = [doc.page_content for doc in retrieved_docs]

        if not retriever_texts:
            return SyndromeResponse(result="No matching syndromes found.")

        response = co.rerank(
            model="rerank-multilingual-v2.0",
            query=ner_output,
            documents=retriever_texts,
            top_n=5,
        )

        retriever_texts = [f"{doc.document['text']}" for doc in response.results]
        combined_text = " ".join(retriever_texts)

        reranked_texts = re.sub(
            r"(症狀: .*?)\s*(證型: .*?證)\s*", r"\2\n\1\n\n", combined_text
        )

        return SyndromeResponse(result=reranked_texts)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


@app.post("/lifestyle")
def lifestyle(query: Query):
    """
    Retrieve lifestyle and prevention recommendations for a given disease.
    """
    try:
        pipeline = [
            {
                "$search": {
                    "index": "diseaseName",
                    "autocomplete": {"query": query.query, "path": "病名"},
                }
            },
            {"$limit": 1},
            {"$project": {"_id": 0, "病名": 1, "预防与调摄": 1}},
        ]
        result = list(collection.aggregate(pipeline))

        if not result:
            raise HTTPException(status_code=404, detail="Disease not found")

        return result[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


@app.post("/prescription")
def prescription(query: Query):
    """
    Suggest prescriptions based on patient symptoms.
    Uses NER to extract symptoms, then vector search and reranking to find relevant prescriptions.
    """
    try:
        ner_completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """為症狀進行NER, 请只按例子output NER的内容，不需要症状NER以外任何东西

            例子：
            input
            - 患者最近情况好一点了，已经转阴。
            - 患者在日本时自己发烧，回香港后看中医。
            - 中医给患者开的中药可以舒缓症状，有抗病毒功效。
            - 患者有些痰，喉咙有点干，胃口正常，睡眠质量好。
            - 患者咳嗽两天，有些感冒，鼻塞、鼻水倒流，喉嚨有些痛和乾，有痰黏著喉嚨，大便正常，睡眠六至七个小时，舌头有点红，吃过炸鸡。
            - 中医师会给患者开药治疗感冒
output：
            痰，喉嚨干，感冒，鼻塞，咳嗽""",
                },
                {
                    "role": "user",
                    "content": query.query,
                },
            ],
        )

        ner_output = ner_completion.choices[0].message.content

        retrieved_docs = vectorstore.similarity_search(
            query=ner_output, k=50, namespace="fangji"
        )
        retriever_texts = [doc.page_content for doc in retrieved_docs]

        if not retriever_texts:
            return {"results": [], "message": "No matching prescriptions found"}

        response = co.rerank(
            model="rerank-multilingual-v2.0",
            query=ner_output,
            documents=retriever_texts,
            top_n=5,
        )

        results = [
            {
                "text": doc.document.get("text", ""),
                "index": doc.index,
                "relevance_score": doc.relevance_score,
            }
            for doc in response.results
        ]

        return {"results": results}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


@app.get("/")
def root():
    """Root endpoint - API health check."""
    return {"message": "FastKwan TCM API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
