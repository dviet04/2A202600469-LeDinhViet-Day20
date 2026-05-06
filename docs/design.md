# Design Template

## Problem

Xây dựng một research assistant nhận câu hỏi dài, tìm nguồn, phân tích và viết câu trả lời tham khảo (có citation). Hệ thống cần vừa hoạt động offline (mock) vừa có thể gọi LLM và search provider khi có key.

## Why multi-agent?

Multi-agent tách rõ trách nhiệm: `Researcher` tìm nguồn, `Analyst` đánh giá/structure claims, `Writer` biên soạn lời giải cuối cùng và `Supervisor` điều phối. So với single-agent, cách này cho: tốt hơn về coverage (citations), dễ debug do trace từng bước, và có thể dễ dàng retry/fallback cho từng worker.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Điều phối luồng, quyết định worker tiếp theo | `ResearchState` | cập nhật `route_history`, trace quyết định | Lỗi routing, vòng lặp vô hạn nếu guardrail thiếu |
| Researcher | Thực hiện tìm kiếm, thu thập `SourceDocument`, tóm tắt nghiên cứu | query | `state.sources`, `state.research_notes` | search thất bại, LLM timeout (fallback mock in local) |
| Analyst | Phân tích, trích xuất claims, chấm điểm độ tin cậy | `research_notes`, `sources` | `state.analysis_notes` | LLM failure, malformed sources |
| Writer | Tổng hợp final answer, chèn citations | `research_notes`, `analysis_notes` | `state.final_answer` | LLM failure, timeout |

## Shared state

Sử dụng `ResearchState` (src/core/state.py) với các field chính:
- `request` (ResearchQuery): input query và max_sources.
- `sources`: list[SourceDocument] lưu kết quả tìm kiếm.
- `research_notes`, `analysis_notes`, `final_answer`: các bước trung gian/đầu ra.
- `agent_results`: lưu metadata (input/output tokens) để tính cost.
- `trace`: danh sách event để debug, timing, retry info.
- `errors`: lưu lỗi runtime.
- `metrics`: chứa benchmark (latency, cost_by_agent, estimated_cost_usd, supervisor_decisions).

Mục đích: cho phép audit, benchmarking và retry/guardrail logic dựa trên state duy nhất.

## Routing policy

Supervisor đơn giản:
- Nếu chưa có `research_notes` → route `researcher`.
- Nếu đã có `research_notes` nhưng chưa có `analysis_notes` → route `analyst`.
- Nếu đã có research/analysis nhưng chưa có `final_answer` → route `writer`.
- Nếu tất cả có → `done`.

Supervisor ghi `route_history` và trace mỗi quyết định. Workflow gọi supervisor mỗi iteration và gọi worker tương ứng với retry/timeout/ fallback.

## Guardrails

- Max iterations: cấu hình `MAX_ITERATIONS` (mặc định 6).
- Timeout: `TIMEOUT_SECONDS` (mặc định 60s) — worker vượt quá xem là failure.
- Retry: `execute_with_retry` retry up to 3 attempts (configurable), fallback delays `(5s,10s,60s)`.
- Fallback: khi `APP_ENV=local` sử dụng mock results; cuối cùng trả `StudentTodoError` với message thân thiện.
- Validation: Supervisor kiểm tra `request.query` không rỗng; ghi lỗi vào `state.errors` nếu invalid.

## Benchmark plan

- Queries: chọn 3 benchmark queries representative (short factual query, multi-claim query, domain-specific query).
- Metrics: latency (wall-clock), estimated cost (token-based), token usage, citation coverage (claims with source / total claims), failure rate, supervisor decisions.
- Expected outcome: multi-agent tốn nhiều token và latency hơn baseline single-call, nhưng cải thiện citation coverage và (theo rubric) chất lượng trả lời; supervisor overhead nhỏ so với LLM cost.

Kết quả được lưu vào `reports/` và `reports/*_trace.json` để phân tích tiếp.