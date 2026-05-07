# 서울 날씨 알림 봇

매일 아침 7시(KST)에 서울 날씨를 분석해 텔레그램으로 한국어 알림을 보내는 봇입니다.  
날씨 데이터를 기반으로 옷차림 추천, 대기질 안내, 우산 알림을 포함한 메시지를 자동 전송합니다.

---

## 기능

- 현재 기온, 체감 온도, 날씨 상태 안내
- 어제 기온과 비교 (One Call API 3.0 구독 시)
- 오늘 강수 예보 및 우산 알림
- 대기질(PM2.5, PM10) 안내 및 마스크 착용 여부 추천 (한국 환경부 기준)
- 기온별 옷차림 자동 추천

---

## 메시지 예시

```
🌤 5월 7일 (목) 오늘의 날씨

📊 기온: 18°C (어제보다 2°C ⬆️ 따뜻해짐)
☔ 강수: 오후 3시경 비 예보 (확률 70%)
😷 대기질
   - 미세먼지(PM10): 보통 (45㎍/㎥)
   - 초미세먼지(PM2.5): 좋음 (12㎍/㎥)

👔 옷차림 추천
- 긴팔 셔츠
- 우산 챙기기 필수!
```

---

## 필요한 API 키 발급 방법

### 1. OpenWeatherMap API 키
1. [https://openweathermap.org](https://openweathermap.org) 회원가입
2. 프로필 → **My API keys** 메뉴에서 키 복사
3. 무료 플랜으로도 현재 날씨, 예보, 대기질 사용 가능
4. **어제 날씨 비교 기능**: [One Call API 3.0](https://openweathermap.org/api/one-call-3) 구독 필요  
   (무료 1,000 calls/day 제공, 신용카드 등록 후 구독 활성화)

### 2. 텔레그램 봇 토큰 & 채팅 ID
1. 텔레그램에서 `@BotFather` 검색 → `/newbot` 명령으로 봇 생성
2. 발급된 **Bot Token** 복사
3. 본인 채팅 ID 확인: `@userinfobot`에 아무 메시지 전송 → ID 확인

---

## 로컬 테스트

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 파일 생성 (.gitignore에 포함되어 있어 커밋되지 않음)
cp .env.example .env
# .env 파일을 열어 각 값 입력

# 4. 실행
python weather_bot.py
```

---

## GitHub Actions 자동 실행 설정

1. 이 저장소를 GitHub에 push
2. 저장소 → **Settings** → **Secrets and variables** → **Actions**
3. 아래 3개 시크릿을 각각 **New repository secret**으로 추가:

| Secret 이름 | 값 |
|---|---|
| `OPENWEATHER_API_KEY` | OpenWeatherMap API 키 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅 ID |

4. 설정 완료 후 매일 오전 7시(KST)에 자동으로 텔레그램 알림이 전송됩니다.
5. **수동 실행**: Actions 탭 → `매일 아침 날씨 알림` → **Run workflow**

---

## 파일 구조

```
weather_bot/
├── weather_bot.py                      # 메인 봇 스크립트
├── requirements.txt                    # Python 의존성
├── .env.example                        # 환경변수 예시 (값 없음)
├── .github/
│   └── workflows/
│       └── daily-weather.yml          # GitHub Actions 워크플로우
├── .gitignore                          # .env 등 제외 목록
└── README.md                           # 이 파일
```
