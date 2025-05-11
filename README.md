# DNS 성능 측정 스크립트

이 파이썬 스크립트는 일반 DNS(UDP), DNS-over-TLS(DoT), DNS-over-HTTPS(DoH)를 포함한 다양한 DNS 서버의 성능을 측정합니다. 여러 도메인에 대해 캐시되지 않은 응답과 캐시된 응답을 모두 테스트하고, 그 결과를 막대 그래프로 시각화합니다.

**참고**: 이 스크립트의 기본 골격은 Google의 Gemini 모델에 의해 생성되었으며, 사용자의 요구사항에 맞춰 여러 차례 수정 및 개선되었습니다.

## 주요 기능

*   일반 DNS(UDP), DNS-over-TLS(DoT), DNS-over-HTTPS(DoH) 프로토콜 지원.
*   정확한 성능 측정을 위해 명령줄 도구인 `dnsperf` 사용.
*   캐시되지 않은 DNS 응답과 캐시된 DNS 응답의 평균 지연 시간 측정.
*   외부 텍스트 파일에서 DNS 서버 목록과 도메인 목록을 읽어옴.
*   측정 결과를 막대 그래프(`dns_performance_chart.png`)로 생성하여 시각화 (캐시되지 않은 응답 시간 기준 정렬).
*   다양한 `dnsperf` 버전의 출력 형식 처리 (특히 지연 시간을 초 단위로 출력하는 `dnsperf 2.14.0` 버전으로 테스트 완료).
*   실행 중 터미널에 진행 상황 업데이트 제공.

## 사전 준비 사항

스크립트를 실행하기 전에 다음 사항들이 설치되어 있는지 확인하십시오:

1.  **Python 3**: 이 스크립트는 Python 3로 작성되었습니다.
2.  **`dnsperf`**: DNS 성능 테스트를 위한 명령줄 도구입니다.
    *   **설치 (Linux - Debian/Ubuntu):**
        ```bash
        sudo apt-get update
        sudo apt-get install dnsperf
        ```
    *   **설치 (Linux - Fedora/CentOS):**
        ```bash
        sudo yum install dnsperf 
        # 또는
        sudo dnf install dnsperf
        ```
    *   **설치 (macOS - Homebrew):**
        ```bash
        brew install dnsperf
        ```
    *   `dnsperf`가 시스템의 PATH에 등록되어 있는지 확인하십시오. 터미널에서 `dnsperf -h`를 입력하여 확인할 수 있습니다. 이 스크립트는 `dnsperf 버전 2.14.0`으로 테스트되었습니다.
3.  **Python 패키지**:
    *   `matplotlib`: 결과 그래프 작성에 사용됩니다.
    *   `numpy`: `matplotlib`에서 수치 연산에 필요합니다.
    pip를 사용하여 이 패키지들을 설치하십시오:
    ```bash
    pip install matplotlib numpy
    ```

## 입력 파일

스크립트 실행 시, 스크립트와 동일한 디렉토리에 다음 두 개의 텍스트 파일이 필요합니다:

1.  **`dns_servers.txt`**:
    테스트할 DNS 서버 목록을 포함합니다. 각 줄은 다음 형식을 따라야 합니다:
    `이름,타입,서버주소또는URL[,포트]`

    *   `이름`: DNS 서버를 설명하는 이름 (예: "Cloudflare-UDP", "Google-DoH"). 그래프에 사용됩니다.
    *   `타입`: 프로토콜 타입. `plain`, `dot`, `doh` 중 하나여야 합니다.
    *   `서버주소또는URL`:
        *   `plain` 및 `dot`의 경우: DNS 서버의 IP 주소 또는 호스트 이름 (예: `1.1.1.1`, `dns.google`).
        *   `doh`의 경우: 전체 DoH URI (예: `https://cloudflare-dns.com/dns-query`).
    *   `포트` (선택 사항): 포트 번호.
        *   지정하지 않으면 `dnsperf`가 기본 포트(plain의 경우 53, DoT의 경우 853, DoH의 경우 443)를 사용합니다.
        *   서버가 비표준 포트를 사용하는 경우에만 지정합니다. DoH의 경우, 포트 정보는 대개 URL에 포함됩니다.

    **`dns_servers.txt` 예시:**
    ```txt
    # '#'으로 시작하는 줄은 주석으로 처리되어 무시됩니다.
    # 이름,타입,서버주소또는URL[,포트]

    Cloudflare-UDP,plain,1.1.1.1
    Google-UDP,plain,8.8.8.8
    Quad9-UDP,plain,9.9.9.9
    Cloudflare-DoT,dot,1.1.1.1
    Google-DoT,dot,dns.google
    Quad9-DoT,dot,dns.quad9.net
    # AdGuard-DoT,dot,dns.adguard.com,853 # DoT 포트 명시 예시
    Cloudflare-DoH,doh,https://cloudflare-dns.com/dns-query
    Google-DoH,doh,https://dns.google/dns-query
    Quad9-DoH,doh,https://dns.quad9.net/dns-query
    ```

2.  **`domains.txt`**:
    성능 테스트에 사용할 도메인 목록을 포함하며, 한 줄에 하나의 도메인을 입력합니다.

    **`domains.txt` 예시:**
    ```txt
    # '#'으로 시작하는 줄은 주석으로 처리되어 무시됩니다.
    google.com
    youtube.com
    wikipedia.org
    github.com
    naver.com
    ```

## 실행 방법

1.  파이썬 스크립트(예: `dns_speed_test.py`)를 특정 디렉토리에 저장합니다.
2.  `dns_servers.txt`와 `domains.txt` 파일을 동일한 디렉토리에 생성하고, 원하는 서버와 도메인으로 내용을 채웁니다.
3.  터미널 또는 명령 프롬프트를 열고, 파일들을 저장한 디렉토리로 이동합니다.
4.  Python 3를 사용하여 스크립트를 실행합니다:
    ```bash
    python ./dns_speed_test.py 
    ```
    (스크립트 파일명이 다를 경우, 해당 파일명으로 실행하십시오.)

5.  스크립트는 터미널에 진행 상황을 출력합니다.
6.  완료되면, `dns_performance_chart.png`라는 이름의 차트 이미지가 동일한 디렉토리에 저장됩니다.

## 출력 결과

*   **터미널 출력**: 테스트 중인 서버, 쿼리 중인 도메인, 그리고 캐시되지 않은 응답과 캐시된 응답에 대해 측정된 지연 시간을 보여줍니다. 또한 각 서버에 대한 평균 지연 시간도 출력합니다.
*   **`dns_performance_chart.png`**: 각 DNS 서버에 대한 평균 캐시되지 않은 응답 시간과 캐시된 응답 시간(밀리초 단위)을 시각화한 막대 그래프 이미지입니다. 캐시되지 않은 성능(낮을수록 좋음)을 기준으로 정렬됩니다.

## 참고 사항

*   **"캐시되지 않음" vs. "캐시됨"**: 스크립트는 도메인에 대한 첫 번째 쿼리를 "캐시되지 않음"으로, 바로 이어지는 동일한 도메인에 대한 쿼리를 "캐시됨"으로 가정합니다. 실제 "캐시되지 않음" 성능은 스크립트가 제어할 수 없는 업스트림 캐시(ISP, 공용 리졸버 등)의 영향을 받을 수 있습니다.
*   **`dnsperf` 버전**: 이 스크립트는 지연 시간을 초 단위(`Average Latency (s): ...`)로 보고하는 `dnsperf 2.14.0`의 출력을 처리하도록 특별히 조정되었습니다. 만약 지연 시간을 밀리초 단위(`Average latency: ... ms`)로 출력하는 다른 버전의 `dnsperf`를 사용하신다면, `parse_dnsperf_output` 함수의 파싱 로직을 약간 수정해야 할 수 있습니다 (현재 스크립트는 두 형식 모두 처리하려고 시도합니다).
*   **DoH 성능**: DoH는 HTTPS를 포함하므로, 특히 "캐시되지 않은" 쿼리의 경우 초기 연결(TLS 핸드셰이크 포함) 시간이 지연 시간에 추가될 수 있습니다.
*   **네트워크 변동성**: DNS 성능은 네트워크 상태, 서버 부하, 지리적 위치에 따라 크게 달라질 수 있습니다. 더 대표적인 결과를 얻으려면 테스트를 여러 번 실행하거나 다른 네트워크 위치에서 실행하는 것을 고려하십시오.
*   **"0.00 ms" 지연 시간**: 스크립트의 `parse_dnsperf_output` 함수는 0.00 ms에 가까운 비정상적으로 낮은 지연 시간을 잠재적인 오류로 간주하여 유효한 값으로 처리하지 않습니다. 이는 DNS 쿼리에서 0.00 ms 응답이 현실적으로 거의 불가능하며, 측정 오류나 서버 오류를 나타내는 경우가 많기 때문입니다.

## 문제 해결

*   **`dnsperf` 찾을 수 없음**: `dnsperf`가 설치되어 있고 해당 위치가 시스템의 PATH 환경 변수에 포함되어 있는지 확인하십시오.
*   **DoH 테스트 실패 또는 타임아웃**:
    *   `dns_servers.txt`의 DoH URI가 올바른지 확인하십시오.
    *   네트워크/방화벽이 포트 443으로의 아웃바운드 HTTPS 연결을 허용하는지 확인하십시오.
    *   이 스크립트는 `dnsperf 2.14.0`에 대해 `-O doh-uri=<full_uri> -s <hostname>` 옵션을 사용합니다. 다른 `dnsperf` 버전을 사용 중이라면 이 옵션들을 조정해야 할 수 있습니다. 사용 중인 버전에 맞는 DoH 옵션은 `dnsperf -H`를 실행하여 확인하십시오.
*   **차트 생성 안 됨**: 터미널 출력에서 오류를 확인하십시오. `matplotlib`이 누락되었거나, 그래프를 그릴 유효한 데이터가 없을 수 있습니다 (예: 모든 서버 테스트 실패).
*   **권한 거부됨**: 스크립트를 직접 실행하는 경우(예: Linux/macOS에서 `./dns_speed_test.py`), 스크립트에 실행 권한(`chmod +x dns_speed_test.py`)이 있는지, 그리고 차트 이미지를 저장할 디렉토리에 쓰기 권한이 있는지 확인하십시오.

## 라이선스

이 스크립트는 있는 그대로 제공됩니다. 자유롭게 사용, 수정 및 배포할 수 있습니다.