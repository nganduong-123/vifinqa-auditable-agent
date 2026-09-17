# Portfolio scope and ownership

## Maintainer

- **Dương Thị Ngân**
- GitHub: [nganduong-123](https://github.com/nganduong-123)

## Project statement

This project extends the LastDance ViFinQA Stage 2 competition repository into
a portfolio-ready, auditable financial QA application. The original commit
history is preserved and GitHub displays the upstream fork relationship.

The correct CV description is **“extended and productionized an existing
ViFinQA competition pipeline”**. It should not be described as a system written
entirely from scratch.

## Added in portfolio version 0.3.0

1. Extended the rule-based Vietnamese semantic parser with financial metrics,
   operations, year ranges, constraints and explicit ambiguity reporting.
2. Repaired the general-question pipeline so batch processing terminates,
   planner output is validated, grounding results are executed correctly and
   every request is persisted as JSONL.
3. Removed the undeclared HTTP client dependency by using the Python standard
   library with request-size, response-shape and timeout boundaries.
4. Added a responsive local web demo and JSON API that run without GPU or the
   private benchmark dataset.
5. Added a project doctor that validates the 1,012-item execution plan,
   release checksum, evidence statistics and optional artifact readiness.
6. Made the locked execution-plan checksum portable across Windows and Unix
   line endings, and enforced LF through `.gitattributes`.
7. Replaced placeholder tests and added coverage for question analysis,
   diagnostics, leakage boundaries and demo input validation.
8. Added continuous integration for Python 3.11 and 3.12.

## Suggested CV entry

### Vietnamese

**ViFinQA Auditable Financial Agent — Maintainer & AI Engineer**

- Phát triển tiếp pipeline hỏi đáp báo cáo tài chính tiếng Việt theo hướng
  evidence-first, kết hợp SQLite FTS5/BM25, LLM semantic planning và thực thi
  Pandas có kiểm soát.
- Xây dựng bộ phân tích intent cho doanh nghiệp, kỳ báo cáo, chỉ tiêu, đơn vị,
  phép toán và điều kiện; bổ sung API/demo web cùng kiểm tra độ sẵn sàng hệ thống.
- Thiết kế cơ chế audit bằng provenance, checksum, AST allowlist và replay;
  tự động hóa kiểm thử trên GitHub Actions.
- Quy mô benchmark: 1.012 câu hỏi, 5.941 evidence bindings và 2.842 bảng nguồn.

### English

**ViFinQA Auditable Financial Agent — Maintainer & AI Engineer**

- Extended an evidence-first Vietnamese financial QA pipeline combining SQLite
  FTS5/BM25 retrieval, LLM semantic planning and sandboxed Pandas execution.
- Built structured intent analysis for entities, reporting periods, metrics,
  units, operations and constraints, plus a local web demo and health API.
- Added provenance checks, cross-platform checksums, AST allowlisting, replay
  validation and GitHub Actions CI for reproducible releases.
- Worked with a 1,012-question benchmark, 5,941 evidence bindings and 2,842
  cited financial-statement tables.

## Interview explanation

The key design choice is to keep the LLM away from source numbers. It sees
number-masked labels and proposes a constrained FinancialPlan. Deterministic
code binds facts to source cells, converts units, compiles the operation DAG to
Pandas, executes it in an allowlisted environment and proves each CSV matches
the cited database table.

The benchmark's 1,012/1,012 replay rate means every submitted query executes
and reproduces its stored answer. It is separate from answer accuracy, reported
as 0.6522 in the locked release configuration.
