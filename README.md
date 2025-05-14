# YouTube Shorts Generator

Reddit의 인기 게시물을 기반으로 YouTube Shorts를 자동으로 생성하는 에이전트입니다.

## 주요 기능

- Reddit API를 통한 인기 게시물 수집
- LLM을 활용한 콘텐츠 스크립트 생성
- TTS를 통한 음성 생성
- 이미지와 음성을 결합한 비디오 생성

## 설치 방법

### 방법 1: Python venv 사용

1. 저장소 클론
```bash
git clone [repository-url]
cd shorts-generator
```

2. 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows의 경우:
venv\Scripts\activate
# macOS/Linux의 경우:
source venv/bin/activate
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 방법 2: Conda 사용

1. 저장소 클론
```bash
git clone [repository-url]
cd shorts-generator
```

2. Conda 환경 생성 및 활성화
```bash
# Conda 환경 생성
conda env create -f environment.yml

# Conda 환경 활성화
conda activate shorts-generator
```

## 환경 변수 설정

### 1. Reddit API 설정
Reddit API를 사용하기 위해서는 다음 환경 변수를 설정해야 합니다. 프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# Reddit API 설정
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=python:shorts-generator:v1.0 (by /u/your_username)
```

Reddit API 자격 증명을 얻으려면:
1. https://www.reddit.com/prefs/apps 에서 새 앱을 생성하세요
2. 앱 유형을 "script"로 선택하세요
3. 생성된 client_id와 client_secret을 `.env` 파일에 복사하세요
4. user_agent는 "python:shorts-generator:v1.0 (by /u/your_username)" 형식으로 설정하세요

## 사용 방법

1. 설정 파일 수정
`config.yaml`에서 원하는 설정을 변경

2. 에이전트 실행
```bash
python main.py
```

## 프로젝트 구조

```
shorts-generator/
├── src/
│   ├── reddit/
│   │   ├── collector.py
│   │   └── parser.py
│   ├── content/
│   │   ├── generator.py
│   │   └── tts.py
│   ├── video/
│   │   ├── editor.py
│   │   └── renderer.py
│   └── utils/
│       ├── logger.py
│       └── config.py
├── config/
│   └── config.yaml
├── output/
│   ├── images/
│   ├── audio/
│   └── videos/
├── requirements.txt
├── environment.yml
└── README.md
```

## 라이선스

MIT License 