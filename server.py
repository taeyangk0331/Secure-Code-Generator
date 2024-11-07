import uvicorn
from fastapi import FastAPI, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from starlette.middleware.cors import CORSMiddleware
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from loguru import logger
import os
from pathlib import Path
import json
from contextlib import asynccontextmanager

# 현재 디렉토리 경로
CURRENT_DIR = Path(__file__).parent
STATIC_DIR = CURRENT_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

# 환경 변수 설정
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5059))

# 모델 경로 설정
device = 'cuda' if torch.cuda.is_available() else 'cpu'
MODEL_PATH = "/home/becreative/team_project/server/model"

# 전역 변수
model = None
tokenizer = None
is_ready = False

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_ready
    try:
        await load_model_and_data()
        create_index_html()
        is_ready = True
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        is_ready = False
    yield
    is_ready = False

# FastAPI 앱 초기화
app = FastAPI(
    title="Code Generator API",
    description="API for generating code snippets",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
origins = [
    f"http://localhost:{PORT}",
    f"http://127.0.0.1:{PORT}",
    f"http://0.0.0.0:{PORT}",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def create_index_html():
    html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Assistant</title>
    <style>
        /* 이전 스타일 유지 */
        body {
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: #1E1F1F;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        }

        .title {
            color: white;
            font-size: 24px;
            margin-bottom: 20px;
        }

        .search-container {
            width: 90%;
            max-width: 768px;
            position: relative;
            margin-bottom: 20px;
        }

        .search-box {
            width: 100%;
            min-height: 56px;
            max-height: 200px;
            padding: 16px 45px 16px 16px;
            border-radius: 8px;
            border: 1px solid #565869;
            background-color: #2A2B2D;
            color: white;
            font-size: 16px;
            outline: none;
            resize: none;
            overflow-y: hidden;
            line-height: 1.5;
        }

        .submit-arrow {
            position: absolute;
            right: 12px;
            top: 16px;
            background: none;
            border: none;
            cursor: pointer;
            padding: 8px;
        }

        .submit-arrow svg {
            width: 16px;
            height: 16px;
            fill: #ACACBE;
        }

        #response-container {
            width: 90%;
            max-width: 768px;
            margin-top: 20px;
            color: white;
            font-family: monospace;
            white-space: pre-wrap;
            padding: 10px;
            font-size: 18px;
            line-height: 1.5;
        }

        .cursor {
            display: inline-block;
            width: 2px;
            height: 1em;
            background: white;
            margin-left: 2px;
            animation: blink 1s infinite;
        }

        @keyframes blink {
            50% { opacity: 0; }
        }

        .loading {
            color: white;
            display: inline-block;
        }

        .loading::after {
            content: '';
            animation: dots 1.4s linear infinite;
        }

        @keyframes dots {
            0%   { content: ''; }
            25%  { content: '.'; }
            50%  { content: '..'; }
            75%  { content: '...'; }
            100% { content: ''; }
        }

        .error-message {
            color: #ff6b6b;
            margin-top: 10px;
            padding: 10px;
            border-radius: 4px;
            background-color: rgba(255, 107, 107, 0.1);
        }
    </style>
</head>
<body>
    <div class="title"><b>Secure Code Generator</b></div>
    <form class="search-container" id="search-form">
        <textarea 
            class="search-box" 
            placeholder="메시지" 
            aria-label="메시지 입력"
            rows="1"></textarea>
        <button type="submit" class="submit-arrow" aria-label="전송">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 20L12 4M12 4L4 12M12 4L20 12"/>
            </svg>
        </button>
    </form>
    <div id="response-container"></div>

    <script>
        const API_URL = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
        
        const textarea = document.querySelector('.search-box');
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });

        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.getElementById('search-form').dispatchEvent(new Event('submit'));
            }
        });

        async function checkApiHealth() {
            try {
                const response = await fetch(`${API_URL}/api/health`);
                if (!response.ok) throw new Error('Health check failed');
                const data = await response.json();
                console.log('Health check response:', data);  // 디버깅용 로그
                return data.status === 'healthy';
            } catch (error) {
                console.error('API health check failed:', error);
                return false;
            }
        }

        function typeWords(text, element, speed = 20) {
            const tokens = text.split(/([^A-Za-z0-9_\\n]|\\n)/g).filter(token => token.length > 0);
            let index = 0;
            element.innerHTML = '<span class="cursor"></span>';
            
            return new Promise(resolve => {
                function addWord() {
                    if (index < tokens.length) {
                        const currentText = tokens.slice(0, index + 1).join('');
                        element.innerHTML = currentText + '<span class="cursor"></span>';
                        index++;
                        setTimeout(addWord, speed);
                    } else {
                        resolve();
                    }
                }
                addWord();
            });
        }

        document.getElementById('search-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            const input = document.querySelector('.search-box');
            const responseContainer = document.getElementById('response-container');
            const query = input.value.trim();
            
            if (query) {
                responseContainer.innerHTML = '<span class="loading">생성중</span>';
                
                try {
                    const isHealthy = await checkApiHealth();
                    if (!isHealthy) {
                        throw new Error('API 서버가 응답하지 않습니다.');
                    }

                    console.log('Sending request to:', `${API_URL}/api/generate/?prompt=${encodeURIComponent(query)}`);  // 디버깅용 로그
                    
                    const response = await fetch(`${API_URL}/api/generate/?prompt=${encodeURIComponent(query)}`, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json'
                        }
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const data = await response.json();
                    console.log('Generation response:', data);  // 디버깅용 로그
                    
                    if (data.status) {
                        responseContainer.textContent = '';
                        await typeWords(data.generated_code, responseContainer);
                    } else {
                        responseContainer.innerHTML = `<div class="error-message">오류가 발생했습니다: ${data.error}</div>`;
                    }
                } catch (error) {
                    console.error('Request error:', error);  // 디버깅용 로그
                    responseContainer.innerHTML = `<div class="error-message">서버 연결 오류: ${error.message}</div>`;
                }
            }
        });

        window.addEventListener('load', async () => {
            const isHealthy = await checkApiHealth();
            if (!isHealthy) {
                document.getElementById('response-container').innerHTML = 
                    '<div class="error-message">API 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.</div>';
            }
        });
    </script>
</body>
</html>
"""
    with open(STATIC_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy" if is_ready else "initializing",
        "device": device,
        "model_loaded": model is not None,
        "tokenizer_loaded": tokenizer is not None
    }

async def load_model_and_data():
    global model, tokenizer
    logger.info("Loading model, tokenizer, and dataset...")
    try:       
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForCausalLM.from_pretrained(MODEL_PATH).to(device)
        logger.info("Model, tokenizer, and dataset loaded successfully")
        
    except Exception as e:
        logger.error(f"Error loading resources: {e}")
        raise

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse(STATIC_DIR / "index.html")

@app.post("/api/generate/")
async def generate_code_post(prompt: str = Body(..., embed=True, min_length=1, max_length=512)):
    print(prompt)
    if not is_ready:
        return {
            "status": False,
            "error": "Server is still initializing. Please try again later."
        }
        
    try:
        inputs = tokenizer(prompt, return_tensors="pt", padding="max_length", 
                         truncation=True, max_length=256, 
                         add_special_tokens=False).to(device)
        
        outputs = model(**inputs)
        logits = outputs.logits
        
        predicted_token_ids = torch.argmax(logits, dim=-1)
        generated_code = tokenizer.decode(predicted_token_ids[0], skip_special_tokens=True)
        
        return {
            "status": True,
            "generated_code": generated_code
        }
    except Exception as e:
        logger.error(f"Error generating code: {e}")
        return {
            "status": False,
            "error": str(e)
        }

@app.get("/api/generate/")
async def generate_code(prompt: str = Query(..., min_length=1, max_length=512)):
    print(prompt)
    if not is_ready:
        return {
            "status": False,
            "error": "Server is still initializing. Please try again later."
        }
        
    try:
        inputs = tokenizer(prompt, return_tensors="pt", padding="max_length", 
                         truncation=True, max_length=256, 
                         add_special_tokens=False).to(device)
        
        outputs = model(**inputs)
        logits = outputs.logits
        
        predicted_token_ids = torch.argmax(logits, dim=-1)
        generated_code = tokenizer.decode(predicted_token_ids[0], skip_special_tokens=True)
        
        
        return {
            "status": True,
            "generated_code": generated_code
        }
    
    except Exception as e:
        logger.error(f"Error generating code: {e}")
        return {
            "status": False,
            "error": str(e)
        }

if __name__ == "__main__":
    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info"
    )