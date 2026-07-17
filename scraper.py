import io
import re
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from pypdf import PdfReader

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Referer": "https://finance.naver.com/",
}

# In-memory cache for stock info to prevent redundant API hits for the same stock
STOCK_CACHE = {}

def get_stock_info_and_chart(code):
    """Fetches real-time price, candlestick chart, and financial health (deficit status) from Naver Mobile API."""
    if code in STOCK_CACHE:
        return STOCK_CACHE[code]

    info = {
        "current_price": 0,
        "is_deficit": "-",
        "chart_html": "",
        "status_class": "normal",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
    }

    try:
        # 1. Fetch Price & Chart Data
        price_url = f"https://m.stock.naver.com/api/stock/{code}/price?pageSize=20&page=1"
        price_res = requests.get(price_url, headers=headers, timeout=5).json()
        price_list = price_res if isinstance(price_res, list) else price_res.get("result", [])

        if price_list:
            # Sort by date ascending
            price_list = sorted(price_list, key=lambda x: str(x.get("localTradedAt", "")))
            dates, opens, highs, lows, closes = [], [], [], [], []
            for item in price_list:
                try:
                    d = str(item.get("localTradedAt", ""))[:10]
                    c = int(str(item.get("closePrice", "0")).replace(",", ""))
                    o = int(str(item.get("openPrice", str(c))).replace(",", ""))
                    h = int(str(item.get("highPrice", str(c))).replace(",", ""))
                    l = int(str(item.get("lowPrice", str(c))).replace(",", ""))
                    dates.append(d[5:]) # MM-DD format
                    opens.append(o)
                    highs.append(h)
                    lows.append(l)
                    closes.append(c)
                except Exception:
                    continue

            if closes:
                info["current_price"] = closes[-1]
                info["chart_data"] = {
                    "dates": dates,
                    "opens": opens,
                    "highs": highs,
                    "lows": lows,
                    "closes": closes
                }
                
                # Generate simple Plotly candlestick chart
                fig = go.Figure(
                    data=[
                        go.Candlestick(
                            x=dates,
                            open=opens,
                            high=highs,
                            low=lows,
                            close=closes,
                            increasing_line_color="#ef4444",
                            increasing_fillcolor="#ef4444",
                            decreasing_line_color="#3b82f6",
                            decreasing_fillcolor="#3b82f6",
                        )
                    ]
                )
                fig.update_layout(
                    margin=dict(l=5, r=5, t=5, b=5),
                    height=140,
                    xaxis_rangeslider_visible=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(
                        showgrid=False, 
                        type="category",
                        tickfont=dict(size=9, color="#94a3b8")
                    ),
                    yaxis=dict(
                        showgrid=True, 
                        gridcolor="#f1f5f9",
                        tickfont=dict(size=9, color="#94a3b8")
                    ),
                )
                # Convert Plotly chart to raw HTML snippet
                info["chart_html"] = fig.to_html(
                    full_html=False, 
                    include_plotlyjs=False,
                    config={"displayModeBar": False}
                )
            else:
                info["chart_data"] = None
        else:
            info["chart_data"] = None

        # 2. Fetch Annual Financial Info for Deficit/Surplus check
        fin_url = f"https://m.stock.naver.com/api/stock/{code}/finance/annual"
        fin_res = requests.get(fin_url, headers=headers, timeout=5).json()
        if "financeInfo" in fin_res and "rowList" in fin_res["financeInfo"]:
            for row in fin_res["financeInfo"]["rowList"]:
                if "영업이익" in str(row.get("title", "")):
                    cols = row.get("columns", [])
                    # Look at latest annual reports backwards
                    for col in reversed(cols):
                        val_clean = re.sub(r"[^\d.-]", "", str(col.get("value", "")))
                        if val_clean and val_clean != "-" and val_clean != "":
                            try:
                                if float(val_clean) < 0:
                                    info["is_deficit"] = "🔴 적자"
                                    info["status_class"] = "deficit"
                                else:
                                    info["is_deficit"] = "🔵 흑자"
                                    info["status_class"] = "surplus"
                                break
                            except ValueError:
                                continue
                    break
    except Exception:
        pass

    STOCK_CACHE[code] = info
    return info


def extract_from_pdf_directly(pdf_url, headers):
    """Downloads research PDF and parses first 2 pages for Target Price and Opinion."""
    op = "제시없음"
    tp = 0
    try:
        if not pdf_url or pdf_url == "#":
            return op, tp
        res = requests.get(pdf_url, headers=headers, timeout=6)
        if res.status_code == 200:
            with io.BytesIO(res.content) as f:
                reader = PdfReader(f)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text() or ""
                    if len(reader.pages) > 1:
                        text += " " + (reader.pages[1].extract_text() or "")

                    # 1. Target Price extraction
                    tp_matches = re.findall(
                        r"(?:목표(?:주)?가|TP|적정주가|Target\s*Price)[^\d]{0,15}([1-9][0-9,]{3,9})",
                        text,
                        re.IGNORECASE,
                    )
                    if tp_matches:
                        for m in tp_matches:
                            val = int(m.replace(",", "").strip())
                            # Validate reasonable stock price range (exclude years)
                            if 1500 <= val <= 10000000 and val not in range(2024, 2035):
                                tp = val
                                break

                    # 2. Investment Opinion rating extraction
                    op_match = re.search(
                        r"(?:투자의견|Rating|Recommendation)\s*[:：]?\s*(?:(?:상향|하향|유지|신규)\s*[:：]?\s*)?(Buy|Strong\s*Buy|Sell|Hold|매수|강력매수|매도|중립|Outperform|Overweight|Neutral|Trading\s*Buy)",
                        text,
                        re.IGNORECASE,
                    )
                    if op_match:
                        op = op_match.group(1).upper()
    except Exception:
        pass
    return op, tp


def get_official_target_and_opinion(code, broker, date, title, full_text, current_price, pdf_link):
    """
    Attempts to fetch investment target/opinion from Naver PC Web,
    falling back to direct PDF parsing and content heuristics.
    """
    opinion = "제시없음"
    target_price = 0

    # Step 1: Look up Naver Finance Research Web Table
    try:
        url = f"https://finance.naver.com/item/research.naver?code={code}&page=1"
        res = requests.get(url, headers=HEADERS, timeout=5)
        res.encoding = "euc-kr"
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table.type_5 tr")

        for row in rows:
            tds = row.find_all("td")
            if len(tds) >= 6:
                row_broker = tds[0].text.strip()
                row_tp_str = re.sub(r"[^\d]", "", tds[1].text.strip())
                row_op = tds[2].text.strip()
                row_date = tds[4].text.strip()

                # Clean and compare broker names
                b1 = re.sub(r"(증권|투자|리서치|금융|\s)", "", broker)
                b2 = re.sub(r"(증권|투자|리서치|금융|\s)", "", row_broker)

                if (b1 and b2 and (b1 in b2 or b2 in b1)) and (date[-5:] == row_date[-5:]):
                    if row_op and row_op not in ["-", "", "N/A", "제시없음"]:
                        opinion = row_op
                    if row_tp_str.isdigit() and int(row_tp_str) > 0:
                        target_price = int(row_tp_str)
                    break
    except Exception:
        pass

    # Step 2: Fallback to direct PDF parsing if opinion/target is missing
    if target_price == 0 or opinion == "제시없음":
        pdf_op, pdf_tp = extract_from_pdf_directly(pdf_link, HEADERS)
        if target_price == 0 and pdf_tp > 0:
            target_price = pdf_tp
        if opinion == "제시없음" and pdf_op != "제시없음":
            opinion = pdf_op

    # Step 3: Fallback to detailed report summary heuristics
    if target_price == 0:
        combined_text = f"{title} {full_text}"
        tp_matches = re.findall(
            r"(?:목표(?:주)?가|목표가|TP|적정주가|Target\s*Price)[^0-9]{0,15}([1-9][0-9,]{3,9})\s*(?:원|KRW)?",
            combined_text,
            re.IGNORECASE,
        )
        if tp_matches:
            for m in tp_matches:
                val_str = m.replace(",", "").strip()
                if val_str.isdigit():
                    val = int(val_str)
                    if 1500 <= val <= 10000000 and val not in range(2024, 2035):
                        target_price = val
                        break

    if opinion == "제시없음":
        combined_text = f"{title} {full_text}"
        op_match = re.search(
            r"(?:투자의견|Rating|Opinion|Recommendation)\s*[:：]?\s*(?:(?:상향|하향|유지|신규)\s*[:：]?\s*)?(Buy|Strong\s*Buy|Sell|Hold|매수|강력매수|매도|중립|Outperform|Marketperform|Overweight|Neutral|Trading\s*Buy|비중확대|비중축소)",
            combined_text,
            re.IGNORECASE,
        )
        if op_match:
            val = op_match.group(1).upper().replace(" ", "")
            if val in ["매수", "강력매수", "BUY", "STRONGBUY"]:
                opinion = "BUY"
            elif val in ["중립", "HOLD", "NEUTRAL", "MARKETPERFORM"]:
                opinion = "HOLD"
            elif val in ["비중확대", "OUTPERFORM", "OVERWEIGHT", "TRADINGBUY"]:
                opinion = "OUTPERFORM"
            elif val in ["매도", "SELL", "UNDERPERFORM", "비중축소"]:
                opinion = "SELL"
            else:
                opinion = op_match.group(1)
        elif re.search(r"\b(Buy|매수)\b", title, re.IGNORECASE):
            opinion = "BUY (추정)"

    # Format output opinions into readable Korean labels
    if opinion in ["매수", "BUY", "Buy", "강력매수", "STRONG BUY"]:
        opinion = "BUY (매수)"
    elif opinion in ["중립", "HOLD", "Hold", "NEUTRAL"]:
        opinion = "HOLD (중립)"
    elif opinion in ["매도", "SELL", "Sell"]:
        opinion = "SELL (매도)"

    # Calculate upside potential percentage
    upside_val = None
    upside_str = "-"
    if target_price > 0 and current_price > 0:
        gap = ((target_price - current_price) / current_price) * 100
        upside_val = gap
        upside_str = f"+{gap:.1f}%" if gap > 0 else f"{gap:.1f}%"

    return opinion, target_price, upside_str, upside_val


def fetch_single_report_details(item):
    """Processes a single report's details: stock info, summary page, opinion mapping."""
    try:
        code = item["code"]
        # Fetch stock details (price, chart, surplus/deficit status)
        stock_info = get_stock_info_and_chart(code)
        item.update({
            "current_price": stock_info["current_price"],
            "is_deficit": stock_info["is_deficit"],
            "status_class": stock_info["status_class"],
            "chart_html": stock_info["chart_html"],
            "chart_data": stock_info.get("chart_data"),
        })

        # Fetch detail text
        detail_res = requests.get(item["detail_link"], headers=HEADERS, timeout=5)
        detail_res.encoding = "euc-kr"
        detail_soup = BeautifulSoup(detail_res.text, "html.parser")
        content_tag = detail_soup.find(class_="view_cnt") or detail_soup.find(class_="view_txt")
        full_text = content_tag.text.strip() if content_tag else ""
        item["summary"] = re.sub(r"\s+", " ", full_text)[:180] + "..." if full_text else "본문 요약 없음 (PDF 참조)"

        # Fetch target and opinion
        opinion, target_price, upside_str, upside_val = get_official_target_and_opinion(
            code,
            item["broker"],
            item["date"],
            item["title"],
            full_text,
            item["current_price"],
            item["pdf_link"]
        )
        item.update({
            "opinion": opinion,
            "target_price": target_price,
            "upside": upside_str,
            "upside_val": upside_val,
        })
        return item
    except Exception as e:
        # Return partial details on failure rather than crashing
        item.update({
            "current_price": item.get("current_price", 0),
            "is_deficit": item.get("is_deficit", "-"),
            "status_class": item.get("status_class", "normal"),
            "chart_html": item.get("chart_html", ""),
            "chart_data": None,
            "summary": "오류로 인해 상세 분석을 불러오지 못했습니다.",
            "opinion": "제시없음",
            "target_price": 0,
            "upside": "-",
            "upside_val": None,
        })
        return item


def fetch_all_reports(max_pages=3, max_reports=35):
    """Scrapes the Naver Research table list and fetches detailed report info concurrently."""
    reports_list = []

    # Step 1: Scrape list of reports from page tables
    for page in range(1, max_pages + 1):
        if len(reports_list) >= max_reports:
            break
        url = f"https://finance.naver.com/research/company_list.naver?page={page}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.encoding = "euc-kr"
            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("table.type_1 tr")
        except Exception:
            continue

        for row in rows:
            if len(reports_list) >= max_reports:
                break
            tds = row.find_all("td")
            if len(tds) < 6:
                continue

            try:
                stock = tds[0].text.strip()
                title_tag = tds[1].find("a")
                title = title_tag.text.strip()
                detail_link = "https://finance.naver.com/research/" + title_tag["href"]
                broker = tds[2].text.strip()
                pdf_tag = tds[3].find("a")
                pdf_link = pdf_tag["href"] if pdf_tag else "#"
                date = tds[4].text.strip()

                code = None
                stock_a = tds[0].find("a")
                if stock_a and "href" in stock_a.attrs:
                    m = re.search(r"(\d{6})", stock_a["href"])
                    if m:
                        code = m.group(1)
                if not code:
                    continue

                reports_list.append({
                    "stock": stock,
                    "code": code,
                    "title": title,
                    "detail_link": detail_link,
                    "broker": broker,
                    "pdf_link": pdf_link,
                    "date": date,
                })
            except Exception:
                continue

    # Step 2: Fetch report details concurrently
    final_reports = []
    # Using ThreadPoolExecutor for fast network-bound performance
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_report_details, report): report for report in reports_list}
        for future in as_completed(futures):
            res = future.result()
            if res:
                final_reports.append(res)

    # Sort final reports by date descending
    final_reports = sorted(final_reports, key=lambda x: x.get("date", ""), reverse=True)
    return final_reports
