# DNS Performance Test Script

This Python script measures the performance of various DNS servers, including plain DNS (UDP), DNS-over-TLS (DoT), and DNS-over-HTTPS (DoH). It tests both uncached and cached responses for multiple domains and visualizes the results in a bar chart.

**Note**: The initial framework of this script was generated with assistance from Google's Gemini model and has been subsequently modified and refined based on user requirements.

## Features

*   Supports Plain DNS (UDP), DNS-over-TLS (DoT), and DNS-over-HTTPS (DoH).
*   Uses the `dnsperf` command-line tool for accurate performance measurement.
*   Measures average latency for uncached and cached DNS responses.
*   Reads DNS server lists and domain lists from external text files.
*   Generates a bar chart (`dns_performance_chart.png`) visualizing the results, sorted by uncached response time.
*   Handles `dnsperf` output parsing for different versions (specifically tested with `dnsperf 2.14.0` which outputs latency in seconds).
*   Provides progress updates in the terminal during execution.

## Prerequisites

Before running the script, ensure you have the following installed:

1.  **Python 3**: The script is written in Python 3.
2.  **`dnsperf`**: This is a command-line tool for DNS performance testing.
    *   **Installation (Linux - Debian/Ubuntu):**
        ```bash
        sudo apt-get update
        sudo apt-get install dnsperf
        ```
    *   **Installation (Linux - Fedora/CentOS):**
        ```bash
        sudo yum install dnsperf 
        # or
        sudo dnf install dnsperf
        ```
    *   **Installation (macOS - Homebrew):**
        ```bash
        brew install dnsperf
        ```
    *   Ensure `dnsperf` is in your system's PATH. You can verify by typing `dnsperf -h` in your terminal. This script has been tested with `dnsperf version 2.14.0`.
3.  **Python Packages**:
    *   `matplotlib`: For plotting the results.
    *   `numpy`: Required by `matplotlib` for numerical operations.
    Install these packages using pip:
    ```bash
    pip install matplotlib numpy
    ```

## Input Files

The script requires two text files in the same directory as the script:

1.  **`dns_servers.txt`**:
    This file contains the list of DNS servers to test. Each line should follow the format:
    `Name,Type,ServerAddressOrURL[,Port]`

    *   `Name`: A descriptive name for the DNS server (e.g., "Cloudflare-UDP", "Google-DoH"). This will be used in the chart.
    *   `Type`: The protocol type. Must be one of `plain`, `dot`, or `doh`.
    *   `ServerAddressOrURL`:
        *   For `plain` and `dot`: The IP address or hostname of the DNS server (e.g., `1.1.1.1`, `dns.google`).
        *   For `doh`: The full DoH URI (e.g., `https://cloudflare-dns.com/dns-query`).
    *   `Port` (Optional): The port number.
        *   If not specified, default ports will be assumed by `dnsperf` (53 for plain, 853 for DoT, 443 for DoH).
        *   Specify only if the server uses a non-standard port. For DoH, port information is usually part of the URL.

    **Example `dns_servers.txt`:**
    ```txt
    # Lines starting with # are comments and will be ignored.
    # Name,Type,ServerAddressOrURL[,Port]

    Cloudflare-UDP,plain,1.1.1.1
    Google-UDP,plain,8.8.8.8
    Quad9-UDP,plain,9.9.9.9
    Cloudflare-DoT,dot,1.1.1.1
    Google-DoT,dot,dns.google
    Quad9-DoT,dot,dns.quad9.net
    # AdGuard-DoT,dot,dns.adguard.com,853 # Example with explicit port for DoT
    Cloudflare-DoH,doh,https://cloudflare-dns.com/dns-query
    Google-DoH,doh,https://dns.google/dns-query
    Quad9-DoH,doh,https://dns.quad9.net/dns-query
    ```

2.  **`domains.txt`**:
    This file contains a list of domains to query for the performance test, one domain per line.

    **Example `domains.txt`:**
    ```txt
    # Lines starting with # are comments and will be ignored.
    google.com
    youtube.com
    wikipedia.org
    github.com
    amazon.com
    ```

## How to Run

1.  Save the Python script (e.g., `dns_speed_test.py`) in a directory.
2.  Create `dns_servers.txt` and `domains.txt` in the same directory and populate them with your desired servers and domains.
3.  Open your terminal or command prompt, navigate to the directory where you saved the files.
4.  Run the script using Python 3:
    ```bash
    python ./dns_speed_test.py 
    ```
    (If your script has a different name, use that name instead.)

5.  The script will print progress updates to the terminal.
6.  Upon completion, a chart image named `dns_performance_chart.png` will be saved in the same directory.

## Output

*   **Terminal Output**: Shows the server being tested, the domain being queried, and the measured latencies for uncached and cached responses. It also prints average latencies for each server.
*   **`dns_performance_chart.png`**: A bar chart image visualizing the average uncached and cached response times (in milliseconds) for each DNS server, sorted by uncached performance (lower is better).

## Notes

*   **"Uncached" vs. "Cached"**: The script assumes the first query to a domain is "uncached" and the immediately following query to the same domain is "cached". True "uncached" performance can be influenced by upstream caches (ISP, public resolvers) that are beyond the script's control.
*   **`dnsperf` Version**: This script is specifically tailored to handle the output of `dnsperf 2.14.0`, which reports latency in seconds (`Average Latency (s): ...`). If you are using a different version of `dnsperf` that outputs latency in milliseconds (`Average latency: ... ms`), the parsing logic in `parse_dnsperf_output` might need slight adjustments (though it attempts to handle both).
*   **DoH Performance**: DoH involves HTTPS, so the initial connection (including TLS handshake) can add to the latency, especially for the "uncached" query.
*   **Network Variability**: DNS performance can vary significantly based on network conditions, server load, and geographic location. For more representative results, consider running the test multiple times or from different network locations.
*   **"0.00 ms" Latency**: The script's `parse_dnsperf_output` function treats latencies of 0.00 ms (or very close to it) as a potential error and will not return a valid latency in such cases. This is because a 0.00 ms latency is unrealistic for DNS queries and often indicates a measurement issue or a server-side error.

## Troubleshooting

*   **`dnsperf` not found**: Ensure `dnsperf` is installed and its location is in your system's PATH environment variable.
*   **DoH tests fail or timeout**:
    *   Verify the DoH URI in `dns_servers.txt` is correct.
    *   Ensure your network/firewall allows outbound HTTPS connections to port 443.
    *   The script uses the `-O doh-uri=<full_uri> -s <hostname>` options for `dnsperf 2.14.0`. If you have a different `dnsperf` version, these options might need adjustment. Check `dnsperf -H` for available DoH options for your version.
*   **No chart generated**: Check for errors in the terminal output. `matplotlib` might be missing or there might have been no valid data to plot (e.g., all server tests failed).
*   **Permission denied**: Ensure the script has execute permissions (`chmod +x dns_speed_test.py`) if you are running it directly (e.g., `./dns_speed_test.py` on Linux/macOS), and write permissions in the directory to save the chart image.

## License

This script is provided as-is. You are free to use, modify, and distribute it.