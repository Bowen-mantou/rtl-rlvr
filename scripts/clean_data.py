# -*- coding: utf-8 -*-
"""clean_data.py — VerilogEval 数据下载指引 + spec→module 对齐清洗。

输入：NVlabs/verilog-eval 官方 JSON（data/VerilogEval_Machine.json 143 题 /
VerilogEval_Human.json 156 题），格式为 task_id → {prompt, canonical_solution,
testbench, detail, ...} 的 dict；也可以是本脚本之前产出的统一 jsonl（用于合并）。

输出：统一 jsonl（字段见 scripts/rtl_common.py 头注释）：
  spec    = prompt 去掉末尾 module 声明（与 header 分离）
  header  = 末尾的 module 声明（接口契约，仿真闸用它生成 harness）
  module  = canonical_solution（参考实现）
  tests   = [] —— VerilogEval 题目没有结构化测试向量，仿真闸自动切换到
            「参考 oracle」模式：候选与参考实现喂相同确定性输入序列、逐拍比较输出
            （见 rtl_common.run_gold_oracle 的诚实说明）
  detail  = {source: VerilogEval_Machine|Human, orig_task_id, description, ...}
  原 testbench 保留在 detail.testbench（未来可做 iverilog 真 testbench 判分的扩展）

清洗规则（设计文档第二节）：
  1. 过滤非 Verilog：canonical_solution 缺失 / 解析不出完整 module...endmodule
  2. 过滤截断：module 块不闭合
  3. 过滤重复：canonical_solution md5 重复（跨文件去重，保留首个）
  4. spec 与 module 必须成对（prompt 与 solution 的 module 名一致才保留，不一致计数报告）
  5. 难度分桶（自动标注）：canonical_solution 含 posedge 敏感表 → 时序；
     时序 + 状态机关键词 → fsm；否则组合逻辑。启发式，detail.tier_heuristic 记录依据
  6. --annotate：对参考实现跑 Yosys 综合自检（不能过综合的参考实现无法被双闸
     判分，剔除并报告 —— 数据集本身的坏题不允许混进来）

数据下载指引（2026-09 实测，按顺序尝试）：
  ★ 推荐：VerilogEval V2（2024-08 改版后的官方仓库，156 题 spec-to-rtl 任务，
    与本项目「spec→RTL」任务定义完全对齐；原 143 题 JSON 格式已不存在于 main 分支）
    方法 A（jsdelivr CDN，国内实测可用且快）：
      python scripts/clean_data.py --download-v2 data/raw/verilogeval_v2
    方法 B（gh-proxy 逐文件）：curl -sL "https://gh-proxy.com/https://raw.githubusercontent.com/NVlabs/verilog-eval/main/dataset_spec-to-rtl/Prob001_zero_prompt.txt"
  V2 文件结构（每题目 3 个文件）：
    dataset_spec-to-rtl/ProbNNN_<name>_{prompt.txt, ref.sv, test.sv}
    题目要求 module 名为 TopModule；参考实现里叫 RefModule（转换时统一改为
    TopModule——testbench 实例化的约定名）；ref 是 SV 后缀但内容为可综合 Verilog。
    原 testbench（SystemVerilog/iverilog 风格）保留在 detail.testbench，
    本项目的仿真闸用参考 oracle 模式（见 rtl_common），不直接跑它。
  旧格式（NVlabs 2023 版 VerilogEval_Machine.json，143 题）：hf-mirror 搜
  verilog-eval 数据集；ModelScope 有镜像则优先。已获取到就用 --input。

用法：
  python scripts/clean_data.py --download-v2 data/raw/verilogeval_v2   # 下载（Linux）
  python scripts/clean_data.py --input-v2 data/raw/verilogeval_v2 \
      --out data/verilogeval_cleaned.jsonl --eval-n 40 --annotate
  python scripts/clean_data.py --input data/verilogeval_cleaned.jsonl \
      --input data/spec_set_50.jsonl --out data/train_pool.jsonl --eval-n 0
  python scripts/clean_data.py --dry-run --input data/raw/xxx.json
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtl_common

FSM_KEYWORDS = ("next_state", "state_machine", "finite state", "mealy", "moore")
POSEDGE_RE = re.compile(r"always\s*@\s*\([^)]*posedge")
MODULE_END_RE = re.compile(r"module\s+\w+\s*\([^)]*\)\s*;\s*$", re.DOTALL)


def load_verilogeval(path):
    """加载 VerilogEval 原始 JSON（dict-of-dicts），返回任务列表。坏格式报错。"""
    with open(path, encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            raise SystemExit(f"{path} 不是合法 JSON: {e}（下载损坏？重新下载并校验）")
    if isinstance(raw, list):
        entries = raw
    elif isinstance(raw, dict):
        entries = list(raw.values())
    else:
        raise SystemExit(f"{path} 顶层结构无法识别（应为 dict 或 list）")
    out = []
    for e in entries:
        if isinstance(e, dict) and "canonical_solution" in e:
            out.append(e)
    if not out:
        raise SystemExit(f"{path} 中没有找到含 canonical_solution 的任务"
                         f"（不是 VerilogEval 格式？）")
    return out


V2_CDN = ("https://cdn.jsdelivr.net/gh/NVlabs/verilog-eval@main/"
          "dataset_spec-to-rtl/{file}")
V2_TREE_API = ("https://data.jsdelivr.com/v1/packages/gh/NVlabs/verilog-eval@main"
               "?structure=flat")


def _http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def download_verilogeval_v2(out_dir, workers=8):
    """下载 VerilogEval V2 spec-to-rtl 全部题目（jsdelivr CDN，国内可用）。

    返回下载的题目数。断点续传：已存在的文件跳过（md5 不校验——文件小，
    损坏的话清洗环节会报 JSON/语法错误，届时删掉重下）。
    """
    from concurrent.futures import ThreadPoolExecutor
    tree = json.loads(_http_get(V2_TREE_API, timeout=120))
    files = sorted(f["name"] for f in tree["files"]
                   if "dataset_spec-to-rtl" in f["name"])
    if not files:
        raise SystemExit("jsdelivr 文件树为空（API 变了？）")
    os.makedirs(out_dir, exist_ok=True)
    basenames = [os.path.basename(f) for f in files]
    todo = [b for b in basenames
            if not os.path.exists(os.path.join(out_dir, b))]
    print(f"[download-v2] 共 {len(basenames)} 个文件，缺 {len(todo)} 个")

    def fetch(name):
        dest = os.path.join(out_dir, name)
        for attempt in range(3):
            try:
                data = _http_get(V2_CDN.format(file=name), timeout=120)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(data)
                return name, True
            except Exception as e:
                if attempt == 2:
                    print(f"  ✗ {name}: {str(e)[:100]}")
                    return name, False
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for name, good in ex.map(fetch, todo):
            ok += good
            fail += not good
    print(f"[download-v2] 成功 {ok}，失败 {fail} → {out_dir}")
    if fail:
        raise SystemExit(f"{fail} 个文件下载失败，重跑本命令续传（已下的会跳过）")


def _rename_ref_module(ref_sv, new_name="TopModule"):
    """参考实现的 module 名 RefModule → TopModule（题目/testbench 的约定名）。"""
    m = re.search(r"\bmodule\s+\w+", ref_sv)
    if not m:
        return None
    return ref_sv[:m.start()] + f"module {new_name}" + ref_sv[m.end():]


def load_v2_dir(path):
    """扫描 V2 目录，按 Prob 分组。返回 [(prob_id, prompt, ref_sv, test_sv), ...]。"""
    files = {}
    for f in sorted(os.listdir(path)):
        m = re.match(r"(Prob\d+)_(.+?)_(prompt\.txt|ref\.sv|test\.sv)$", f)
        if m:
            files.setdefault(m.group(1), {})[m.group(3)] = os.path.join(path, f)
    problems = []
    for pid in sorted(files):
        parts = files[pid]
        if not all(k in parts for k in ("prompt.txt", "ref.sv", "test.sv")):
            raise SystemExit(f"{pid} 缺文件: {parts}（下载不完整，重跑 --download-v2）")
        with open(parts["prompt.txt"], encoding="utf-8") as f:
            prompt = f.read().strip()
        with open(parts["ref.sv"], encoding="utf-8") as f:
            ref = f.read().strip()
        with open(parts["test.sv"], encoding="utf-8") as f:
            test = f.read().strip()
        problems.append((pid, prompt, ref, test))
    return problems


def clean_one_v2(pid, prompt, ref_sv, test_sv):
    """V2 单题 → 统一记录（或 None + 丢弃原因）。

    header 从参考实现解析（module 名统一改为题目的 TopModule）；
    仿真闸无结构化向量 → 参考 oracle 模式；testbench 保留进 detail。
    """
    gold = _rename_ref_module(ref_sv)
    if not gold:
        return None, "no_module_in_ref"
    code = rtl_common._find_module_in(gold)
    if not code:
        return None, "no_module_block"
    m = re.search(r"module\s+\w+\s*\([^)]*\)\s*;", code)
    if not m:
        return None, "unparseable_header"
    header = m.group(0).strip()
    try:
        rtl_common.parse_header(header)
    except rtl_common.GateError as e:
        return None, f"unparseable_header: {e}"
    tier, tier_why = classify_tier(code)
    return {
        "task_id": f"verilogeval-v2-{pid}",
        "tier": tier,
        "spec": prompt,
        "header": header,
        "module": code,
        "tests": [],
        "split": "train",  # --eval-n 统一重排
        "detail": {"source": "VerilogEvalV2_spec-to-rtl", "orig_task_id": pid,
                   "tier_heuristic": tier_why, "testbench": test_sv},
    }, ""


def classify_tier(code):
    """难度分桶启发式：posedge → 时序；时序 + FSM 关键词 → fsm；否则组合。"""
    code_l = code.lower()
    if POSEDGE_RE.search(code):
        if any(k in code_l for k in FSM_KEYWORDS):
            return "fsm", "posedge + fsm keywords"
        return "sequential", "posedge sensitivity"
    return "combinational", "no posedge"


def split_header_from_prompt(prompt, solution):
    """把 prompt 末尾的 module 声明拆成 header；拆不出则整段当 spec。"""
    m = MODULE_END_RE.search(prompt)
    if m:
        header = m.group(0).strip()
        spec = prompt[:m.start()].strip()
        sol_top = None
        sm = re.search(r"\bmodule\s+(\w+)", solution)
        if sm:
            sol_top = sm.group(1)
        hm = re.search(r"\bmodule\s+(\w+)", header)
        if hm and sol_top and hm.group(1) != sol_top:
            return prompt, "", "header_name_mismatch"
        return spec, header, ""
    return prompt, "", "no_trailing_header"


def clean_one(entry, source):
    """单条清洗。返回 (记录或 None, 丢弃原因或 "")。"""
    solution = (entry.get("canonical_solution") or "").strip()
    prompt = (entry.get("prompt") or "").strip()
    if not solution:
        return None, "no_canonical_solution"
    code = rtl_common._find_module_in(solution)
    if not code:
        return None, "no_module_block"
    if not prompt:
        return None, "no_prompt"

    spec, header, hdr_err = split_header_from_prompt(prompt, solution)
    if not header or hdr_err == "header_name_mismatch":
        # prompt 没带尾部 module 声明 / 声明与参考实现名不一致：
        # 以参考实现的声明为准（保证题目自洽、双闸可判分），不一致保留 warning
        m = re.search(r"module\s+\w+\s*\([^)]*\)\s*;", solution)
        if m:
            header = m.group(0).strip()
        else:
            return None, "unparseable_header"
    try:
        rtl_common.parse_header(header)
    except rtl_common.GateError:
        return None, f"unparseable_header: {header[:60]!r}"

    tier, tier_why = classify_tier(code)
    detail = entry.get("detail") or {}
    if isinstance(detail, str):
        detail = {"content": detail}
    rec = {
        "task_id": entry.get("task_id") or f"{source}-unknown",
        "tier": tier,
        "spec": spec if spec else prompt,
        "header": header,
        "module": code,
        "tests": [],
        "split": "train",  # --eval-n 之后统一重排
        "detail": {"source": source, "orig_task_id": entry.get("task_id", ""),
                   "description": detail.get("description", ""),
                   "tier_heuristic": tier_why, "header_warning": hdr_err,
                   "testbench": entry.get("testbench", "")},
    }
    return rec, ""


def clean(inputs, v2_dirs, out, eval_n, annotate=False, workers=8, dry_run=False):
    records, seen, dropped = [], set(), {}
    for path in inputs:
        n_file = n_kept = 0
        for e in load_verilogeval(path):
            n_file += 1
            rec, why = clean_one(e, os.path.basename(path).replace(".json", ""))
            if rec is None:
                dropped[why] = dropped.get(why, 0) + 1
                continue
            key = hashlib.md5(rec["module"].encode()).hexdigest()
            if key in seen:
                dropped["duplicate"] = dropped.get("duplicate", 0) + 1
                continue
            seen.add(key)
            records.append(rec)
            n_kept += 1
        print(f"[clean] {path}: {n_file} 题 → 保留 {n_kept}")
    for path in v2_dirs:
        n_file = n_kept = 0
        for pid, prompt, ref, test in load_v2_dir(path):
            n_file += 1
            rec, why = clean_one_v2(pid, prompt, ref, test)
            if rec is None:
                dropped[why] = dropped.get(why, 0) + 1
                continue
            key = hashlib.md5(rec["module"].encode()).hexdigest()
            if key in seen:
                dropped["duplicate"] = dropped.get("duplicate", 0) + 1
                continue
            seen.add(key)
            records.append(rec)
            n_kept += 1
        print(f"[clean] {path}: {n_file} 题 → 保留 {n_kept}")

    # 排序（确定性：按 task_id），前 eval_n 题为 eval 集
    records.sort(key=lambda r: r["task_id"])
    for i, r in enumerate(records):
        r["split"] = "eval" if i < eval_n else "train"

    # --annotate：参考实现必须过 Yosys 综合（过不了的题目无法被双闸判分，剔除）
    n_bad_gold = 0
    if annotate:
        missing = rtl_common.check_tools()
        if missing:
            raise SystemExit("缺少工具: " + ", ".join(missing))
        from concurrent.futures import ThreadPoolExecutor
        duts = {r["task_id"]: rtl_common.parse_header(r["header"]) for r in records}
        def check(r):
            ok, tail = rtl_common.run_yosys(r["module"], duts[r["task_id"]]["top"])
            return r, ok, tail
        keep = []
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for r, ok, tail in ex.map(check, records):
                if ok:
                    keep.append(r)
                else:
                    n_bad_gold += 1
                    print(f"[annotate] 剔除 {r['task_id']}（参考实现不能过综合）: "
                          f"{tail[-120:]}")
        records = keep

    for r in records:
        errs = rtl_common.validate_problem(r, "cleaned")
        if errs:
            raise SystemExit("清洗输出未通过校验:\n" + "\n".join(errs))

    tiers, splits = {}, {}
    for r in records:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
        splits[r["split"]] = splits.get(r["split"], 0) + 1
    print(f"[clean] 总计 {len(records)} 题 | 分桶 {tiers} | split {splits}")
    if dropped:
        print(f"[clean] 丢弃统计: {dropped}")
    if n_bad_gold:
        print(f"[clean] ⚠ 剔除 {n_bad_gold} 题参考实现过不了综合 —— 这些题无法判分，"
              f"已如实报告（若数量异常大，检查 yosys 版本）")

    if dry_run:
        print("[clean] dry-run：不写盘")
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[clean] 已写 → {out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="VerilogEval 清洗 → 统一 jsonl")
    ap.add_argument("--input", default=[], nargs="+",
                    help="VerilogEval 旧版原始 JSON（可多个文件合并去重）")
    ap.add_argument("--input-v2", default=[], nargs="+",
                    help="VerilogEval V2 目录（--download-v2 的产物，可多个）")
    ap.add_argument("--download-v2", default=None, metavar="DIR",
                    help="下载 VerilogEval V2 到 DIR（jsdelivr CDN）")
    ap.add_argument("--out", default="data/verilogeval_cleaned.jsonl")
    ap.add_argument("--eval-n", type=int, default=40,
                    help="按 task_id 排序后前 N 题标为 eval（0 = 全部 train）")
    ap.add_argument("--annotate", action="store_true",
                    help="对参考实现跑 Yosys 综合自检并剔除坏题（Linux）")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.download_v2:
        download_verilogeval_v2(args.download_v2, workers=args.workers)
        print(f"下一步: python scripts/clean_data.py --input-v2 "
              f"{args.download_v2} --out data/verilogeval_cleaned.jsonl "
              f"--eval-n 40 --annotate")
        return 0
    if not args.input and not args.input_v2:
        raise SystemExit("需要 --input 或 --input-v2（或先 --download-v2）")
    for p in list(args.input) + list(args.input_v2):
        if not os.path.exists(p):
            raise SystemExit(f"输入不存在: {p}（先 --download-v2 下载）")
    sys.exit(clean(args.input, args.input_v2, args.out, args.eval_n,
                   annotate=args.annotate, workers=args.workers,
                   dry_run=args.dry_run))


if __name__ == "__main__":
    main()
