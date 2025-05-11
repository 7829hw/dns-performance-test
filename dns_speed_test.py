import subprocess
import re
import os
import time
import matplotlib.pyplot as plt
import numpy as np
import shutil
from urllib.parse import urlparse

# --- Configuration ---
DNS_SERVERS_FILE = "dns_servers.txt"
DOMAINS_FILE = "domains.txt"
OUTPUT_IMAGE_FILE = "dns_performance_chart.png"
TEMP_QUERY_FILE = "temp_dns_query.txt"  # dnsperf -d 옵션용 임시 파일
DNS_TIMEOUT_SECONDS = 5
QUERIES_PER_RUN = 1  # 캐시/비캐시 테스트를 위한 단일 쿼리

# --- Helper Functions ---


def check_dnsperf_installed():
    if not shutil.which("dnsperf"):
        print(
            "Error: dnsperf command not found. Please install and ensure it's in PATH."
        )
        return False
    return True


def read_config_file(filename):
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return None
    try:
        with open(filename, "r", encoding="utf-8") as f:
            lines = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
        if not lines:
            print(f"Warning: File '{filename}' is empty or contains only comments.")
            return []
        return lines
    except Exception as e:
        print(f"Error reading file '{filename}': {e}")
        return None


def parse_dns_server_line(line):
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 3:
        print(f"Skipping malformed server line: {line}")
        return None
    name, type_str, address = parts[0], parts[1].lower(), parts[2]
    port = None
    if type_str not in ["plain", "doh", "dot"]:
        print(f"Skipping server '{name}': Unknown type '{type_str}'.")
        return None
    if len(parts) > 3 and parts[3]:
        try:
            port = int(parts[3])
        except ValueError:
            print(f"Skipping server '{name}': Invalid port '{parts[3]}'.")
            return None
    return {"name": name, "type": type_str, "address": address, "port": port}


# !-- 여기가 최종적으로 올바르게 수정된 run_dnsperf 함수 --!
def run_dnsperf(server_info, domain_file_path):
    cmd_base = ["dnsperf"]
    cmd_options = []
    effective_timeout = DNS_TIMEOUT_SECONDS

    if server_info["type"] == "doh":
        cmd_options.extend(["-m", "doh"])
        # 1. -O doh-uri=<FULL_DOH_URI> 옵션을 사용합니다.
        cmd_options.extend(["-O", f"doh-uri={server_info['address']}"])

        # 2. -s <hostname>은 SNI(Server Name Indication) 및 내부 처리를 위해 추가합니다.
        parsed_url_for_sni = urlparse(server_info["address"])
        cmd_options.extend(["-s", parsed_url_for_sni.hostname])

        # 3. 포트 처리: config 파일 또는 URL에 명시된 포트 사용, 없으면 dnsperf 기본값.
        #    doh-uri에 포트 정보가 포함되어 있다면 dnsperf가 이를 우선할 수 있음.
        #    명시적 포트 지정이 필요한 경우를 위해 추가.
        if server_info["port"]:  # config 파일에 포트가 명시된 경우
            cmd_options.extend(["-p", str(server_info["port"])])
        elif parsed_url_for_sni.port:  # URL 자체에 포트가 명시된 경우
            cmd_options.extend(["-p", str(parsed_url_for_sni.port)])
        # 그 외에는 dnsperf가 doh-uri의 포트 또는 기본 DoH 포트(443)를 사용.

        effective_timeout = DNS_TIMEOUT_SECONDS + 7
    elif server_info["type"] == "dot":
        cmd_options.extend(["-s", server_info["address"]])
        cmd_options.extend(["-m", "dot"])
        if server_info["port"]:
            cmd_options.extend(["-p", str(server_info["port"])])
        effective_timeout = DNS_TIMEOUT_SECONDS + 5
    elif server_info["type"] == "plain":
        cmd_options.extend(["-s", server_info["address"]])
        if server_info["port"]:
            cmd_options.extend(["-p", str(server_info["port"])])

    # 공통 옵션 추가
    cmd_options.extend(
        [
            "-d",
            domain_file_path,
            "-c",
            str(QUERIES_PER_RUN),
            "-q",
            str(QUERIES_PER_RUN),
            "-Q",
            str(QUERIES_PER_RUN),
            "-t",
            str(effective_timeout),
        ]
    )

    cmd = cmd_base + cmd_options
    # DEBUG 출력을 기본적으로 활성화하여 명령어 확인
    print(f"    DEBUG: Executing: {' '.join(cmd)} (timeout: {effective_timeout}s)")

    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=effective_timeout + 2,
            check=False,
        )
        error_message = None
        if process.returncode != 0:  # dnsperf가 오류 코드로 종료
            stderr_cleaned = (
                process.stderr.strip().replace("\n", " ")
                if process.stderr
                else "No stderr output"
            )
            error_message = (
                f"dnsperf error (code {process.returncode}): {stderr_cleaned}"
            )
            # 실패 시 stderr/stdout 내용도 출력 (디버깅에 유용)
            print(
                f"    DEBUG_STDERR: {process.stderr.strip() if process.stderr else '<empty>'}"
            )
            print(
                f"    DEBUG_STDOUT: {process.stdout.strip() if process.stdout else '<empty>'}"
            )
            return None, error_message  # (결과 없음, 오류 메시지)
        return process.stdout, None  # (결과, 오류 없음)
    except subprocess.TimeoutExpired:
        timeout_msg = f"dnsperf command timed out for {server_info['name']} (after {effective_timeout}s)"
        print(f"    DEBUG: {timeout_msg}")
        return None, timeout_msg
    except Exception as e:  # 기타 예외 처리
        exc_msg = f"Exception running dnsperf for {server_info['name']}: {e}"
        print(f"    DEBUG: {exc_msg}")
        return None, exc_msg


# !-- 수정된 부분 끝 --!


def parse_dnsperf_output(output):
    if not output:
        return None
    latency = None
    # dnsperf 2.14.0은 초 단위로 출력: "Average Latency (s):  0.00818"
    match_s = re.search(r"Average Latency\s*\(s\):\s+([\d\.]+)", output)
    if match_s:
        latency = float(match_s.group(1)) * 1000  # ms로 변환
        # 0.00ms는 오류로 간주 (실제 0ms 응답은 거의 불가능)
        if latency == 0.0:
            print(
                f"    DEBUG: Latency is 0.00 ms, treating as potential error/failure."
            )
            return None
        return latency

    # 구버전 또는 다른 설정의 dnsperf는 ms 단위로 출력할 수 있음: "Average latency:  8.18 ms"
    match_ms = re.search(r"Average latency:\s+([\d\.]+)\s*ms", output, re.IGNORECASE)
    if match_ms:
        latency = float(match_ms.group(1))
        if latency == 0.0:
            print(
                f"    DEBUG: Latency is 0.00 ms, treating as potential error/failure."
            )
            return None
        return latency

    # 파싱 실패 시 디버그 메시지
    # print(f"    DEBUG: Could not parse latency. Raw dnsperf output (first 300 chars):\n---\n{output[:300].strip()}\n---") # 필요시 주석 해제
    return None


def plot_results(results_data, filename="dns_performance_chart.png"):
    if not results_data:
        print("No data to plot.")
        return
    valid_results = [r for r in results_data if r[1] is not None or r[2] is not None]
    if not valid_results:
        print("No valid data to plot after filtering (all servers might have failed).")
        return
    valid_results.sort(
        key=lambda x: (x[1] is None, x[1] if x[1] is not None else float("inf"))
    )
    server_names = [r[0] for r in valid_results]
    uncached_latencies_plot = [r[1] if r[1] is not None else 0 for r in valid_results]
    cached_latencies_plot = [r[2] if r[2] is not None else 0 for r in valid_results]
    x_indices = np.arange(len(server_names))
    bar_width = 0.35
    fig, ax = plt.subplots(figsize=(max(12, len(server_names) * 0.9), 8))
    bars1 = ax.bar(
        x_indices - bar_width / 2,
        uncached_latencies_plot,
        bar_width,
        label="Uncached (ms)",
    )
    bars2 = ax.bar(
        x_indices + bar_width / 2, cached_latencies_plot, bar_width, label="Cached (ms)"
    )
    ax.set_ylabel("Average Latency (ms)")
    ax.set_title("DNS Server Performance Comparison (Lower is better)")
    ax.set_xticks(x_indices)
    ax.set_xticklabels(server_names, rotation=45, ha="right", fontsize=9)
    ax.legend()
    for i, bar in enumerate(bars1):  # Uncached bars
        if valid_results[i][1] is not None:  # 실제 측정값이 있는 경우에만 레이블 표시
            ax.annotate(
                f"{valid_results[i][1]:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    for i, bar in enumerate(bars2):  # Cached bars
        if valid_results[i][2] is not None:  # 실제 측정값이 있는 경우에만 레이블 표시
            ax.annotate(
                f"{valid_results[i][2]:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    all_plotted_latencies = [
        l
        for r_tuple in valid_results
        for l in (r_tuple[1], r_tuple[2])
        if l is not None and l > 0
    ]
    max_y_val = max(all_plotted_latencies) if all_plotted_latencies else 0
    ax.set_ylim(0, max_y_val * 1.20 if max_y_val > 0 else 10)  # 상단 여유 20%
    fig.tight_layout()
    try:
        plt.savefig(filename, dpi=150)
        print(f"\nPerformance chart saved as '{filename}'")
    except Exception as e:
        print(f"Error saving chart: {e}")
    plt.close(fig)


def main():
    print("Starting DNS performance test...")
    if not check_dnsperf_installed():
        return
    server_lines = read_config_file(DNS_SERVERS_FILE)
    domain_lines = read_config_file(DOMAINS_FILE)
    if not server_lines or not domain_lines:
        print("Error: Missing server or domain configurations. Exiting.")
        return
    servers_to_test = [
        p for p in (parse_dns_server_line(line) for line in server_lines) if p
    ]
    if not servers_to_test:
        print("No valid DNS server configurations. Exiting.")
        return

    all_results_summary = []
    for server_info in servers_to_test:
        server_name = server_info["name"]
        port_str = f":{server_info['port']}" if server_info["port"] else ""
        print(
            f"\n[Testing Server: {server_name} ({server_info['type']} @ {server_info['address']}{port_str})]"
        )
        server_uncached_latencies, server_cached_latencies = [], []
        num_domains_to_test_this_server = len(domain_lines)

        for i, domain in enumerate(domain_lines[:num_domains_to_test_this_server]):
            print(
                f"  Querying domain ({i+1}/{num_domains_to_test_this_server}): {domain}"
            )
            try:
                with open(TEMP_QUERY_FILE, "w", encoding="utf-8") as f:
                    f.write(f"{domain} A\n")
            except Exception as e:
                print(f"    Error creating temp query file: {e}. Skipping domain.")
                continue

            print(f"    Running uncached test...", end="", flush=True)
            stdout_uncached, err_uncached = run_dnsperf(server_info, TEMP_QUERY_FILE)
            lat_uncached = parse_dnsperf_output(stdout_uncached)
            if lat_uncached is not None:
                server_uncached_latencies.append(lat_uncached)
                print(f" OK ({lat_uncached:.2f} ms)")
                print(f"    Running cached test...", end="", flush=True)
                time.sleep(0.05)
                stdout_cached, err_cached = run_dnsperf(server_info, TEMP_QUERY_FILE)
                lat_cached = parse_dnsperf_output(stdout_cached)
                if lat_cached is not None:
                    server_cached_latencies.append(lat_cached)
                    print(f" OK ({lat_cached:.2f} ms)")
                else:
                    reason = err_cached or (
                        "parse error from dnsperf output"
                        if stdout_cached
                        else "no output/error from dnsperf"
                    )
                    print(f" FAILED ({reason})")
            else:
                reason = err_uncached or (
                    "parse error from dnsperf output"
                    if stdout_uncached
                    else "no output/error from dnsperf"
                )
                print(f" FAILED ({reason})")

        if os.path.exists(TEMP_QUERY_FILE):
            try:
                os.remove(TEMP_QUERY_FILE)
            except Exception as e:
                print(f"Warning: Could not remove {TEMP_QUERY_FILE}: {e}")

        avg_uncached = (
            sum(server_uncached_latencies) / len(server_uncached_latencies)
            if server_uncached_latencies
            else None
        )
        avg_cached = (
            sum(server_cached_latencies) / len(server_cached_latencies)
            if server_cached_latencies and server_uncached_latencies
            else None
        )

        if avg_uncached is not None:
            print(
                f"  Average Uncached Latency: {avg_uncached:.2f} ms ({len(server_uncached_latencies)} queries)"
            )
        else:
            print(f"  No successful uncached queries for {server_name}.")
        if avg_cached is not None:
            print(
                f"  Average Cached Latency: {avg_cached:.2f} ms ({len(server_cached_latencies)} queries)"
            )
        elif avg_uncached is not None:
            print(f"  No successful cached queries for {server_name}.")
        all_results_summary.append((server_name, avg_uncached, avg_cached))

    if all_results_summary:
        plot_results(all_results_summary, OUTPUT_IMAGE_FILE)
    else:
        print("\nNo results to plot.")
    print("\nDNS performance test finished.")


if __name__ == "__main__":
    main()
