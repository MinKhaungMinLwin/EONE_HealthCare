"""API client for communicating with the backend."""
import json
import os
import time as time
from typing import Dict, Generator, List, Union

import requests
import streamlit as st

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_SECRET_KEY", None)
HEADERS = {}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

def get_examples(language: str) -> dict:
    """
    Since main.py doesn't have an endpoint for examples, 
    we return the static list of your 11 questions here.
    """
    # 11 Questions List
    questions = [
        "저번달과 비교해서 신환대비 재진 비율 알려줘",
        "입원환자 비율 증감율 보여주고 앞으로 비율 증감에대해서 예측해줘",
        "내과 홍길동 의사에 환자 증감 보여줘",
        "환자수 증감수가 제일 낮은 과와 환자수가 제일 적은과 데이터 보여줘",
        "신규 환자의 지역을 랭킹순으로 알려줘",
        "과별로 나이와 성별 환자수 비율 알려줘 (cf. 과 = 진료과)",
        "보험 유형별 외래 입원 별로 비율 보여주고 자보 및 산재 수를 통하여 환자유치 방향을 알려줘",
        "예약부도율이 제일 낮은 과와 제일 높은과 보여줘",
        "병상가동율이 제일높은 병동과 낮은 병동 보여주고 병동가동율을 높이는 방향을 알려줘",
        "신환 환자 유치를 위한 제일 효율적인 지역은 어디인지 알려주고 환자 유치 방향을 알려줘",
        "환자현황을 통하여 환자유입을 위한 개선 방향과 병원의 효율적인 관리에 대하여 알려줘"
    ]
    
    # Return structure matching what Chat.py expects
    return {
        "categories": {
            "hospital_stats": {
                "name": "Hospital Statistics",
                "explanation": "MySQL 데이터베이스를 사용하여 환자 흐름 및 병원 효율성을 분석합니다. Analyze patient flow and hospital efficiency from MySQL Database.",
                "questions": questions
            }
        }
    }

def send_chat_message(messages: List[Dict[str, str]],
                      stream: bool = False) -> Union[str, Generator[str, None, None]]:
    """
    Send chat message to main.py
    """
    url = f"{BASE_URL}/chat"
    
    # Payload matching main.py's ChatRequest model
    payload = {
        "messages": messages
    }

    try:
        # Note: Your main.py doesn't support streaming (SSE) yet.
        # So we send a normal request, but if the UI wants a stream,
        # we fake a generator to keep Chat.py happy.
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # main.py returns {"role": "assistant", "content": "..."}
        answer = data.get("content", "No response content.")

        if stream:
            # Generator that yields the whole answer at once
            for word in answer.split(" "):
                yield word + " "
                time.sleep(0.01)  # Simulate streaming delay
        else:
            return answer

    except Exception as e:
        error_msg = f"Error connecting to backend: {e}"
        if stream:
            yield error_msg
        else:
            return error_msg
        

def _handle_regular_response(payload: dict) -> str:
    """Handle non-streaming response"""
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            headers=HEADERS,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data.get("content", "Don't get the answer.")
    except Exception as e:
        return f"Error when call to API: {e}"


def _handle_stream_response(payload: dict) -> Generator[str, None, None]:
    """Handle streaming response with SSE"""
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            stream=True,
            headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Authorization': f'Bearer {API_KEY}',
            }
        )
        response.raise_for_status()
        response.encoding = 'utf-8'

        # Process SSE stream
        for line in response.iter_lines(decode_unicode=True):
            if line:
                # SSE format: "data: {json_content}"
                if line.startswith("data: "):
                    data_content = line[6:]  # Remove "data: " prefix

                    # Check for end of stream
                    if data_content.strip() == "[DONE]":
                        break

                    try:
                        # Parse JSON chunk
                        chunk_data = json.loads(data_content)

                        # Extract content from chunk
                        if (chunk_data.get("choices") and
                                len(chunk_data["choices"]) > 0 and
                                chunk_data["choices"][0].get("delta") and
                                chunk_data["choices"][0]["delta"].get("content")):
                            content = chunk_data["choices"][0]["delta"]["content"]
                            if isinstance(content, bytes):
                                content = content.decode('utf-8')
                            yield content

                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue

    except Exception as e:
        yield f"Error when streaming API: {e}"
