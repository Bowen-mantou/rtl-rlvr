# -*- coding: utf-8 -*-
"""rtl_common.py — RTL 双闸判定共享引擎（Yosys 综合 + Verilator 仿真）。

RTL-RLVR 项目的核心模块：eval_rtl.py（评估）、configs/grpo/reward_fn.py（奖励）、
build_spec_set.py --verify（数据自检）、annotate_samples.py（verifier 数据标注）
全部调用这里同一套闸门实现 —— 口径纪律：判分逻辑只有一份。

双闸语义（严格按 docs/项目设计.md 第三节/第四节）：
  ① Yosys 综合：read_verilog + hierarchy -check + synth —— 语法对不对、能否变成电路
  ② Verilator 仿真：自动生成 C++ harness，按测试向量逐拍驱动输入、检查输出
  两闸全过 = 本题对。综合失败 → 仿真闸直接判失败（不跑）。

统一数据格式（设计文档第二节的超集，新增字段已注释说明）：
  {
    "task_id": "spec50-comb-001",        # 唯一 id
    "tier": "combinational|sequential|fsm",   # 难度分桶（设计文档第二节）
    "spec": "Design an 8-bit counter ...",    # 自然语言规格（设计文档第二节）
    "header": "module counter (input clk, ...);",  # 接口契约（给模型的 prompt 含此行）
    "module": "module counter ... endmodule",      # 参考实现（设计文档第二节，SFT 用）
    "tests": [                                   # 测试向量（设计文档第二节）
        {"name": "t1", "steps": [
            {"input": {"rst": 1, "en": 0}, "expect": {"count": 0}, "clock": true},
            ...
        ]}
    ],
    "split": "train|eval",
    "detail": {...}                              # 来源元信息（可选）
  }
步骤语义：设置 input 端口值 → 若 clock=true 则给 clk 端口一个完整脉冲（0→1 上升沿）
→ eval 稳定后逐端口检查 expect。未列出的输出端口不检查；未列出的输入端口保持上一拍值。
时钟端口名必须叫 clk（本数据集约定）；无 clk 端口 = 纯组合逻辑题。
端口位宽上限 64（C++ harness 用 uint64 驱动，超限报错，不静默截断）。

仿真判分的两种模式：
  - 显式测试向量（tests 非空）：与期望值直接比较（主模式，自建 50 题用）
  - 参考 oracle（tests 为空且有参考实现 module）：候选与参考实现喂相同输入序列，
    逐拍比较输出（VerilogEval 题目没有结构化向量时用；参考实现本身先过 --verify 自检）
诚实纪律：不做任何美化数字的事 —— 失败原因（synth 日志尾部 / 第一个失败步骤）
全部保留在返回结果里。

本模块纯 Python 可跑 --selftest（离线静态自检，不需要 yosys/verilator）。

用法：
  python scripts/rtl_common.py --selftest
"""
import hashlib
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

# ---------------------------------------------------------------------------
# 常量与格式
# ---------------------------------------------------------------------------

MAX_PORT_WIDTH = 64          # 超限报错（不做静默截断）
SYNTH_TIMEOUT = 60           # 秒，单样本 yosys 超时
SIM_COMPILE_TIMEOUT = 120    # 秒，verilator 编译超时
SIM_RUN_TIMEOUT = 60         # 秒，harness 运行超时
ORACLE_MAX_COMBOS = 65536    # oracle 组合逻辑穷举上限（≤16 输入位宽）
ORACLE_RANDOM_SAMPLES = 1024
ORACLE_SEQ_CYCLES = 32

TOOL_REQUIRED_MSG = (
    "缺少 %s。安装命令：sudo apt install -y yosys verilator build-essential "
    "（gcc/make 是 verilator --build 编译 harness 的依赖）"
)

HEADER_RE = re.compile(r"module\s+(\w+)\s*\(([\s\S]*?)\)\s*;")
PORT_ITEM_RE = re.compile(
    r"(input|output|inout)\s+"
    r"(?:wire\s+|reg\s+|logic\s+)?"
    r"(?:signed\s+)?"
    r"(?:\[(\d+)\s*:\s*(\d+)\]\s*)?"
    r"(\w+)"
)
MODULE_BLOCK_RE = re.compile(r"\bmodule\s+\w+\s*\(?[\s\S]*?endmodule\b")
ANSWER_TAG_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
FENCE_RE = re.compile(r"```(?:\w+)?\s*\n(.*?)```", re.DOTALL)


class GateError(Exception):
    """闸门执行错误（工具缺失/接口解析失败等），消息对用户可读。"""


# ---------------------------------------------------------------------------
# 提示词与输出解析
# ---------------------------------------------------------------------------

def prompt_text(problem):
    """spec + 接口契约 + 格式要求 → 给模型的 prompt（评估与 GRPO 训练共用）。"""
    spec = problem["spec"]
    header = problem.get("header") or ""
    instr = ("Complete the Verilog module below. Use exactly the given module "
             "name and port list. Put the complete module code inside "
             "<answer> and </answer> tags.")
    parts = [spec]
    if header:
        parts += ["", instr, "", header]
    return "\n".join(parts)


QWEN_DEFAULT_SYSTEM = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."


def apply_qwen_chat(prompt):
    """Qwen2.5-Coder-3B-Instruct 单轮用户消息的 chat 模板（与 tokenizer 输出一致）。

    注意：Qwen2.5 模板在无 system 消息时会注入默认 system 提示词，这里硬编码了
    同一段文本，保证「数据端预格式化」与「评估端 apply_chat_template」逐字符一致。
    """
    return (f"<|im_start|>system\n{QWEN_DEFAULT_SYSTEM}<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n")


def _find_module_in(text):
    m = MODULE_BLOCK_RE.search(text)
    return m.group(0).strip() if m else None


def extract_module_strict(text):
    """奖励格式闸：只从 <answer> 标签内解析完整 module（设计文档第三节）。

    返回 module 代码或 None（无标签 / 标签内无完整 module 都算解析失败）。
    """
    m = ANSWER_TAG_RE.search(text)
    if not m:
        return None
    return _find_module_in(m.group(1))


def extract_module_lenient(text):
    """评估用宽容解析：<answer> → ```代码块``` → 全文，逐级回退找完整 module。

    与奖励闸不同：评估测的是「模型会不会写 module」本身，格式达标率单独统计。
    """
    m = ANSWER_TAG_RE.search(text)
    if m:
        code = _find_module_in(m.group(1))
        if code:
            return code
    fences = FENCE_RE.findall(text)
    if fences:
        code = _find_module_in("\n".join(fences))
        if code:
            return code
    return _find_module_in(text)


# ---------------------------------------------------------------------------
# 接口解析（ANSI 风格 module 声明）
# ---------------------------------------------------------------------------

def _strip_comments(s):
    s = re.sub(r"//[^\n]*", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    return s


def _split_top_level(s):
    """按顶层逗号切分端口列表（不处理括号嵌套——ANSI 端口列表里没有嵌套括号）。"""
    return [part.strip() for part in s.split(",") if part.strip()]


def parse_header(header):
    """解析 ANSI 风格 module 声明 → dut 描述。

    返回 {"top": str, "clk": str|None, "ports": {name: {"dir": "input"|"output", "width": int}}}
    解析失败抛 GateError（数据集错误必须报出来，不静默跳过）。
    """
    m = HEADER_RE.search(_strip_comments(header))
    if not m:
        raise GateError(f"无法解析 module 声明: {header[:120]!r}")
    top, body = m.group(1), m.group(2)
    ports = {}
    for item in _split_top_level(body):
        pm = PORT_ITEM_RE.search(item)
        if not pm:
            raise GateError(f"无法解析端口条目 {item!r}（仅支持 ANSI 风格："
                            f"input/output [width] name）")
        direction, msb, lsb, name = pm.groups()
        width = 1
        if msb is not None:
            msb, lsb = int(msb), int(lsb)
            if msb < lsb:
                raise GateError(f"端口 {name} 位宽声明倒置 [{msb}:{lsb}]")
            width = msb - lsb + 1
        if width > MAX_PORT_WIDTH:
            raise GateError(f"端口 {name} 位宽 {width} 超过上限 {MAX_PORT_WIDTH}")
        if direction == "inout":
            raise GateError(f"端口 {name} 是 inout：harness 不支持双向口，"
                            f"请改成 input/output 拆分")
        ports[name] = {"dir": direction, "width": width}
    clk = "clk" if ("clk" in ports and ports["clk"]["dir"] == "input") else None
    if not ports:
        raise GateError(f"module {top} 没有端口")
    return {"top": top, "clk": clk, "ports": ports}


def parse_module_interface(code, top_name):
    """在候选代码里找名为 top_name 的 module，解析其接口；找不到返回 None。"""
    for m in re.finditer(r"\bmodule\s+(\w+)\s*\(([\s\S]*?)\)\s*;", _strip_comments(code)):
        if m.group(1) == top_name:
            try:
                return parse_header(m.group(0))
            except GateError:
                return None
    return None


def check_interface(candidate_iface, dut):
    """候选接口 vs 期望接口。返回 mismatch 列表（空 = 一致）。

    名字/端口集/方向/位宽任何一处不一致都是接口违规 —— 仿真闸直接判失败并写明原因
    （等价于「没有实现题目要求的接口」，VerilogEval 同款口径）。
    """
    if candidate_iface is None:
        return [f"候选代码中没有名为 {dut['top']} 的 module"]
    mismatches = []
    if candidate_iface["top"] != dut["top"]:
        mismatches.append(f"module 名不一致: 期望 {dut['top']}, "
                          f"得到 {candidate_iface['top']}")
    want, got = set(dut["ports"]), set(candidate_iface["ports"])
    if want != got:
        if want - got:
            mismatches.append(f"缺少端口: {sorted(want - got)}")
        if got - want:
            mismatches.append(f"多余端口: {sorted(got - want)}")
    for name in want & got:
        w, g = dut["ports"][name], candidate_iface["ports"][name]
        if w["dir"] != g["dir"]:
            mismatches.append(f"端口 {name} 方向不一致: 期望 {w['dir']}, 得到 {g['dir']}")
        if w["width"] != g["width"]:
            mismatches.append(f"端口 {name} 位宽不一致: 期望 {w['width']}, 得到 {g['width']}")
    return mismatches


# ---------------------------------------------------------------------------
# 闸门 ①：Yosys 综合
# ---------------------------------------------------------------------------

def _which(tool):
    return shutil.which(tool)


def check_tools():
    """返回缺失工具列表；非空时评估/奖励无法运行。"""
    return [t for t in ("yosys", "verilator", "make", "g++") if not _which(t)]


def run_yosys(code, top, timeout=SYNTH_TIMEOUT):
    """闸门 ①。返回 (ok: bool, log_tail: str)。exit code 0 = 综合通过。"""
    if not _which("yosys"):
        raise GateError(TOOL_REQUIRED_MSG % "yosys")
    workdir = tempfile.mkdtemp(prefix="rtl_yosys_")
    try:
        src = os.path.join(workdir, "candidate.v")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        script = f"read_verilog {src}; hierarchy -check -top {top}; synth -top {top}"
        try:
            proc = subprocess.run(
                ["yosys", "-Q", "-T", "-p", script],
                capture_output=True, text=True, timeout=timeout, cwd=workdir)
        except subprocess.TimeoutExpired:
            return False, f"[timeout] yosys 超过 {timeout}s（工具挂死，按失败计）"
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, out[-800:]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 闸门 ②：Verilator 仿真（自动生成 C++ harness）
# ---------------------------------------------------------------------------

def _mask_literal(width):
    return "~0ULL" if width >= 64 else hex((1 << width) - 1) + "ULL"


def _fmt_value(v):
    return hex(int(v)) + "ULL"


def generate_harness(dut, tests, mode="check"):
    """根据 dut 描述 + 测试步骤生成 Verilator C++ harness 源码。

    mode="check"：逐拍检查 expect 端口，第一个失败即打印 FAIL 行并退出 1。
    mode="trace"：不检查，逐拍打印所有输出端口值（oracle 对比模式用）。
    每个 test 新建一个 DUT 实例（状态隔离，测试之间互不污染）。
    """
    top = dut["top"]
    clk = dut["clk"]
    in_ports = [n for n, p in dut["ports"].items() if p["dir"] == "input" and n != clk]
    out_ports = [n for n, p in dut["ports"].items() if p["dir"] == "output"]
    L = []

    def w(line, indent=2):
        L.append(" " * indent + line)

    w("#include <verilated.h>")
    w("#include <cstdio>")
    w("#include <cstdint>")
    w(f'#include "V{top}.h"')
    w("")
    w("int main(int argc, char** argv) {")
    w("Verilated::commandArgs(argc, argv);", 4)
    w(f"const int n_tests = {len(tests)};", 4)
    w("for (int t = 0; t < n_tests; t++) {", 4)
    w(f"V{top}* dut = new V{top};", 8)
    w("int step = 0;", 8)
    for ti, test in enumerate(tests):
        # 每个测试在自己的 DUT 实例上跑（状态隔离）；if 守卫把步骤限定在 t==ti 那次迭代
        w(f"if (t == {ti}) {{", 8)
        for si, s in enumerate(test["steps"]):
            w(f"// test {ti} '{test['name']}' step {si} (clock={bool(s.get('clock'))})", 12)
            for name, val in sorted(s.get("input", {}).items()):
                if not isinstance(name, str):
                    raise GateError(f"测试向量 {test['name']} step {si} 的输入端口名 "
                                    f"不是字符串: {name!r}（数据构造 bug）")
                if name not in dut["ports"]:
                    raise GateError(f"测试向量 {test['name']} step {si} 的输入端口 "
                                    f"{name!r} 不在 {top} 接口中")
                if dut["ports"][name]["dir"] != "input":
                    raise GateError(f"测试向量 {test['name']} step {si} 把输出端口 "
                                    f"{name!r} 当输入驱动")
                if name == clk:
                    raise GateError(f"测试向量不能用 input 驱动时钟端口 clk，"
                                    f"用 step 的 clock 字段")
                w(f"dut->{name} = {_fmt_value(s['input'][name])};", 12)
            if s.get("clock"):
                if not clk:
                    raise GateError(f"测试向量 {test['name']} step {si} 要求 clock 脉冲，"
                                    f"但 {top} 没有 clk 端口")
                w(f"dut->{clk} = 0; dut->eval(); dut->{clk} = 1; dut->eval();", 12)
            w("dut->eval();", 12)
            if mode == "check":
                for name, exp in sorted(s.get("expect", {}).items()):
                    if not isinstance(name, str):
                        raise GateError(f"测试向量 {test['name']} step {si} 的检查端口名 "
                                        f"不是字符串: {name!r}（数据构造 bug）")
                    if name not in dut["ports"]:
                        raise GateError(f"测试向量 {test['name']} step {si} 检查的端口 "
                                        f"{name!r} 不在 {top} 接口中")
                    if dut["ports"][name]["dir"] != "output":
                        raise GateError(f"测试向量 {test['name']} step {si} 把输入端口 "
                                        f"{name!r} 当输出检查")
                    w("{", 12)
                    w(f"uint64_t got = (uint64_t)(dut->{name}) & "
                      f"{_mask_literal(dut['ports'][name]['width'])};", 16)
                    w(f"if (got != {_fmt_value(exp)}) {{", 16)
                    w(f'printf("FAIL t=%d step=%d port={name} expect=%llu got=%llu\\n", '
                      f"t, step, (unsigned long long){_fmt_value(exp)}, "
                      f"(unsigned long long)got);", 20)
                    w("delete dut; return 1; }", 20)
                    w("}", 12)
            else:  # trace
                # 格式串每个 %llu 对应一个实参；实参用 ", " 连接（无尾逗号）
                vals = " ".join("%llu" for _ in out_ports)
                args = ", ".join(
                    f"(unsigned long long)((uint64_t)(dut->{n}) & "
                    f"{_mask_literal(dut['ports'][n]['width'])}),"
                    for n in out_ports)
                args = args.rstrip(",")
                w(f'printf("{vals}\\n", {args});', 12)
            w("step++;", 12)
        w("}", 8)
    w("delete dut;", 8)
    w("}", 4)
    w('printf("SIM_DONE\\n");', 4)
    w("return 0;", 4)
    w("}")
    return "\n".join(L) + "\n"


def _run_timed(cmd, timeout, cwd, what):
    """subprocess + 进程组超时（Popen 教训：timeout 只杀直接子进程，这里杀整组）。"""
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        return -1, "", f"[timeout] {what} 超过 {timeout}s（按失败计）"


def run_verilator_tests(code, dut, tests, mode="check"):
    """闸门 ② 主路径（显式测试向量）。

    返回 dict: {ok, n_pass, n_total, reason, log_tail}
      ok=True        → n_pass == n_total，全部测试通过
      ok=False       → reason 说明第一个失败点（接口不一致 / 编译错 / FAIL 行 / 超时）
    接口不一致在编译之前就被拦截（不浪费 verilator 编译时间）。
    """
    if not _which("verilator"):
        raise GateError(TOOL_REQUIRED_MSG % "verilator")
    cand = parse_module_interface(code, dut["top"])
    mismatches = check_interface(cand, dut)
    if mismatches:
        return {"ok": False, "n_pass": 0, "n_total": len(tests),
                "reason": "interface_mismatch: " + "; ".join(mismatches), "log_tail": ""}

    workdir = tempfile.mkdtemp(prefix="rtl_sim_")
    try:
        src = os.path.join(workdir, "candidate.v")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        harness = generate_harness(dut, tests, mode=mode)
        with open(os.path.join(workdir, "harness.cpp"), "w", encoding="utf-8") as f:
            f.write(harness)
        obj = os.path.join(workdir, "obj_dir")
        # 注意：Ubuntu 22.04 apt 的 Verilator 4.038 不支持 -j（4.1xx 才有），
        # 不传并行编译参数，兼容所有版本。
        # -Wno-fatal：闸门②判功能不判 lint（WIDTH 等 lint 警告不该让仿真闸
        # 挂掉——lint 是可选的行为奖励开关，单独读警告，见 reward_fn._lint_score）
        cmd = ["verilator", "--cc", "--exe", "--build", "-Wno-fatal",
               "--top-module", dut["top"], "--Mdir", obj,
               "-o", "sim_bin", "harness.cpp", "candidate.v"]
        rc, out, err = _run_timed(cmd, SIM_COMPILE_TIMEOUT, workdir, "verilator 编译")
        if rc != 0:
            return {"ok": False, "n_pass": 0, "n_total": len(tests),
                    "reason": "verilator_compile_error",
                    "log_tail": (out + err)[-800:]}
        rc, out, err = _run_timed([os.path.join(obj, "sim_bin")], SIM_RUN_TIMEOUT,
                                  workdir, "仿真运行")
        if rc != 0:
            fail_line = next((l for l in out.splitlines() if l.startswith("FAIL")), "")
            n_pass = 0
            if fail_line:
                m = re.search(r"FAIL t=(\d+)", fail_line)
                if m:
                    n_pass = int(m.group(1))  # 0..t-1 号测试已过
            return {"ok": False, "n_pass": n_pass, "n_total": len(tests),
                    "reason": fail_line or "sim_runtime_error",
                    "log_tail": (out + err)[-400:]}
        if "SIM_DONE" not in out:
            return {"ok": False, "n_pass": 0, "n_total": len(tests),
                    "reason": "sim_output_unexpected", "log_tail": out[-400:]}
        return {"ok": True, "n_pass": len(tests), "n_total": len(tests),
                "reason": "", "log_tail": ""}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 闸门 ② 备选：参考 oracle（无显式测试向量的题目，如 VerilogEval）
# ---------------------------------------------------------------------------

def _build_oracle_tests(dut, seed=42):
    """按 dut 接口生成确定性输入序列（无 expect → trace 模式）。"""
    rng = random.Random(seed)
    in_ports = [n for n, p in dut["ports"].items()
                if p["dir"] == "input" and n != dut["clk"]]
    if dut["clk"] is None:
        # 组合逻辑：位宽 ≤16 全穷举；否则随机采样 + 边界
        total_bits = sum(dut["ports"][n]["width"] for n in in_ports)
        cases = []
        if total_bits <= 16 and total_bits > 0:
            for v in range(1 << total_bits):
                inputs = {}
                pos = 0
                for n in in_ports:
                    w = dut["ports"][n]["width"]
                    inputs[n] = (v >> pos) & ((1 << w) - 1)
                    pos += w
                cases.append(inputs)
        else:
            for _ in range(ORACLE_RANDOM_SAMPLES):
                inputs = {n: rng.getrandbits(dut["ports"][n]["width"]) for n in in_ports}
                cases.append(inputs)
            cases.append({n: 0 for n in in_ports})
            cases.append({n: (1 << dut["ports"][n]["width"]) - 1 for n in in_ports})
        return [{"name": f"oracle_case_{i}",
                 "steps": [{"input": c, "expect": {}, "clock": False}]}
                for i, c in enumerate(cases)]
    # 时序逻辑：rst 两拍（有 rst 端口时）+ 随机刺激
    steps = []
    rst = "rst" if "rst" in dut["ports"] else None
    for i in range(ORACLE_SEQ_CYCLES):
        inputs = {n: rng.getrandbits(dut["ports"][n]["width"]) for n in in_ports}
        if rst is not None:
            inputs[rst] = 1 if i < 2 else 0
        steps.append({"input": inputs, "expect": {}, "clock": True})
    return [{"name": "oracle_trace", "steps": steps}]


def run_gold_oracle(candidate_code, gold_code, dut, seed=42):
    """参考 oracle 判分：候选与参考实现喂同一确定性输入序列，逐拍比较输出。

    返回 dict 同 run_verilator_tests。参考实现必须在数据准备阶段通过 --verify
    自检（build_spec_set.py --verify / clean_data.py --annotate）。
    """
    if not _which("verilator"):
        raise GateError(TOOL_REQUIRED_MSG % "verilator")
    cand = parse_module_interface(candidate_code, dut["top"])
    mismatches = check_interface(cand, dut)
    if mismatches:
        return {"ok": False, "n_pass": 0, "n_total": len(_build_oracle_tests(dut, seed)),
                "reason": "interface_mismatch: " + "; ".join(mismatches), "log_tail": ""}
    tests = _build_oracle_tests(dut, seed)
    gold_iface = parse_module_interface(gold_code, dut["top"])
    if check_interface(gold_iface, dut):
        return {"ok": False, "n_pass": 0, "n_total": len(tests),
                "reason": "gold_interface_mismatch（参考实现接口与 header 不一致，"
                          "数据集本身有问题，需先跑 --verify 修复）", "log_tail": ""}

    workdir = tempfile.mkdtemp(prefix="rtl_oracle_")
    try:
        traces = []
        for tag, code in (("cand", candidate_code), ("gold", gold_code)):
            with open(os.path.join(workdir, f"{tag}.v"), "w", encoding="utf-8") as f:
                f.write(code)
            harness = generate_harness(dut, tests, mode="trace")
            with open(os.path.join(workdir, f"harness_{tag}.cpp"), "w",
                      encoding="utf-8") as f:
                f.write(harness)
            obj = os.path.join(workdir, f"obj_{tag}")
            cmd = ["verilator", "--cc", "--exe", "--build", "-Wno-fatal",
                   "--top-module", dut["top"], "--Mdir", obj,
                   "-o", "sim_bin", f"harness_{tag}.cpp", f"{tag}.v"]
            rc, out, err = _run_timed(cmd, SIM_COMPILE_TIMEOUT, workdir,
                                      f"verilator 编译 ({tag})")
            if rc != 0:
                return {"ok": False, "n_pass": 0, "n_total": len(tests),
                        "reason": f"verilator_compile_error({tag})",
                        "log_tail": (out + err)[-800:]}
            rc, out, err = _run_timed([os.path.join(obj, "sim_bin")], SIM_RUN_TIMEOUT,
                                      workdir, f"仿真运行 ({tag})")
            if rc != 0 or "SIM_DONE" not in out:
                return {"ok": False, "n_pass": 0, "n_total": len(tests),
                        "reason": f"sim_runtime_error({tag})",
                        "log_tail": (out + err)[-400:]}
            # 逐行输出：每个 step 一行，每行是全部输出端口值
            lines = [l for l in out.splitlines() if l and "SIM_DONE" not in l]
            traces.append(lines)
        if len(traces[0]) != len(traces[1]):
            return {"ok": False, "n_pass": 0, "n_total": len(tests),
                    "reason": "oracle_trace_length_mismatch", "log_tail": ""}
        out_ports = [n for n, p in dut["ports"].items() if p["dir"] == "output"]
        step_counter = 0
        n_pass = 0
        for t_i, test in enumerate(tests):
            passed = True
            fail_step = -1
            for s_i in range(len(test["steps"])):
                if traces[0][step_counter] != traces[1][step_counter]:
                    passed = False
                    fail_step = s_i
                step_counter += 1
                if not passed:
                    break
            if passed:
                n_pass += 1
            else:
                return {"ok": False, "n_pass": n_pass, "n_total": len(tests),
                        "reason": (f"gold_oracle_mismatch test={t_i} "
                                   f"step={fail_step} ports={out_ports}"),
                        "log_tail": ""}
        return {"ok": True, "n_pass": len(tests), "n_total": len(tests),
                "reason": "", "log_tail": ""}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 双闸总入口 + 结果缓存
# ---------------------------------------------------------------------------

_CACHE = {}
_CACHE_LOCK = threading.Lock()
CACHE_ENABLED = os.environ.get("RTL_DISABLE_CACHE") != "1"


def evaluate_module(code, problem, use_oracle=True, seed=42):
    """双闸总入口。code = 候选完整 module 代码（已解析出），problem = 统一数据记录。

    返回 dict:
      {synth_ok, sim_ok, overall, n_pass, n_total, reason, synth_log, sim_log}
      overall = synth_ok and sim_ok；综合失败时不再跑仿真（sim_ok=False, n_pass=0）。
    结果按 (code, tests) 哈希缓存 —— 工具执行是确定性的，缓存只提速不改数。
    """
    dut = parse_header(problem["header"])
    tests = problem.get("tests") or []
    gold = problem.get("module") or ""

    key = hashlib.md5((
        code + "|||" + json.dumps(tests, sort_keys=True, default=str)
        + "|||" + ("oracle" if (use_oracle and not tests and gold) else "no-oracle")
        + "|||" + str(seed) + "|||" + (hashlib.md5(gold.encode()).hexdigest()
                                       if gold else "")
    ).encode("utf-8")).hexdigest()

    if CACHE_ENABLED:
        with _CACHE_LOCK:
            if key in _CACHE:
                return dict(_CACHE[key])

    result = {"synth_ok": False, "sim_ok": False, "overall": False,
              "n_pass": 0, "n_total": len(tests), "reason": "", "synth_log": "",
              "sim_log": ""}
    try:
        result["synth_ok"], result["synth_log"] = run_yosys(code, dut["top"])
        if not result["synth_ok"]:
            result["reason"] = "synth_fail"
            result["n_total"] = len(tests)
        elif tests:
            r = run_verilator_tests(code, dut, tests)
            result.update({"sim_ok": r["ok"], "n_pass": r["n_pass"],
                           "n_total": r["n_total"], "sim_log": r["log_tail"]})
            if not r["ok"]:
                result["reason"] = r["reason"]
        elif use_oracle and gold:
            r = run_gold_oracle(code, gold, dut, seed=seed)
            result.update({"sim_ok": r["ok"], "n_pass": r["n_pass"],
                           "n_total": r["n_total"], "sim_log": r["log_tail"]})
            if not r["ok"]:
                result["reason"] = r["reason"]
        else:
            result["reason"] = ("no_tests_no_gold（该题既无测试向量也无参考实现，"
                                "仿真闸无法判定，按失败计）")
        result["overall"] = result["synth_ok"] and result["sim_ok"]
    except GateError as e:
        result["reason"] = f"gate_error: {e}"
        result["synth_log"] = str(e)

    if CACHE_ENABLED:
        with _CACHE_LOCK:
            _CACHE[key] = dict(result)
    return result


# ---------------------------------------------------------------------------
# 数据加载与校验（坏行必须报错退出，不静默跳过 —— PITFALLS 教训）
# ---------------------------------------------------------------------------

REQUIRED_KEYS = ("task_id", "tier", "spec", "header", "module", "tests", "split")


def validate_problem(p, path="?"):
    """校验一条数据记录，返回错误列表（空 = 合法）。"""
    errs = []
    where = f"{path}:{p.get('task_id', '?')}"
    for k in REQUIRED_KEYS:
        if k not in p:
            errs.append(f"{where} 缺字段 {k}")
            return errs
    if p["tier"] not in ("combinational", "sequential", "fsm"):
        errs.append(f"{where} tier 非法: {p['tier']!r}")
    if p["split"] not in ("train", "eval"):
        errs.append(f"{where} split 非法: {p['split']!r}")
    if not isinstance(p["tests"], list):
        errs.append(f"{where} tests 必须是列表")
        return errs
    try:
        dut = parse_header(p["header"])
    except GateError as e:
        errs.append(f"{where} header 解析失败: {e}")
        return errs
    if not p["tests"] and not p.get("module"):
        errs.append(f"{where} 无测试向量且无参考实现，仿真闸无法判定")
    for t in p["tests"]:
        if "name" not in t or "steps" not in t or not t["steps"]:
            errs.append(f"{where} 测试 {t.get('name', '?')} 缺 name/steps")
            continue
        for si, s in enumerate(t["steps"]):
            for k in ("input", "expect"):
                if k not in s or not isinstance(s[k], dict):
                    errs.append(f"{where} 测试 {t['name']} step {si} 缺 {k}")
            for name in s.get("input", {}):
                if name not in dut["ports"]:
                    errs.append(f"{where} 测试 {t['name']} step {si} 输入端口 "
                                f"{name!r} 不在接口中")
                elif dut["ports"][name]["dir"] != "input":
                    errs.append(f"{where} 测试 {t['name']} step {si} 把输出端口 "
                                f"{name!r} 当输入")
            for name in s.get("expect", {}):
                if name not in dut["ports"]:
                    errs.append(f"{where} 测试 {t['name']} step {si} 检查端口 "
                                f"{name!r} 不在接口中")
                elif dut["ports"][name]["dir"] != "output":
                    errs.append(f"{where} 测试 {t['name']} step {si} 把输入端口 "
                                f"{name!r} 当输出检查")
            if s.get("clock") and not dut["clk"]:
                errs.append(f"{where} 测试 {t['name']} step {si} 要求时钟脉冲但 "
                            f"module 没有 clk 端口")
    return errs


def load_problems(path):
    """读统一 jsonl，全量校验；任何坏行直接抛错（不静默跳过）。"""
    problems = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                p = json.loads(line)
            except json.JSONDecodeError as e:
                raise GateError(f"{path}:{ln} JSON 解析失败: {e}（坏行必须修复，"
                                f"不允许跳过）")
            errs = validate_problem(p, f"{path}:{ln}")
            if errs:
                raise GateError("\n".join(errs))
            problems.append(p)
    return problems


# ---------------------------------------------------------------------------
# 离线自检（不需要 yosys/verilator，Windows/无卡模式可跑）
# ---------------------------------------------------------------------------

def _selftest():
    failures = []

    def check(name, cond, detail=""):
        if cond:
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name} {detail}")
            failures.append(name)

    print("== rtl_common selftest ==")
    print("-- parse_header --")
    dut = parse_header("module counter (input wire clk, input wire rst, "
                       "input wire en, output reg [7:0] count);")
    check("basic ANSI header", dut["top"] == "counter" and dut["clk"] == "clk"
          and dut["ports"]["count"] == {"dir": "output", "width": 8}
          and dut["ports"]["en"]["width"] == 1, dut)
    dut2 = parse_header("module m (input a, output b);")
    check("no clk → combinational", dut2["clk"] is None)
    check("comment stripping", parse_header(
        "module m (// input x\n input a, /* inline */ output b);")["ports"] ==
        {"a": {"dir": "input", "width": 1}, "b": {"dir": "output", "width": 1}})
    try:
        parse_header("module m (output [3:0] y, inout z);")
        check("inout rejected", False)
    except GateError:
        check("inout rejected", True)
    try:
        parse_header("module m (output [70:0] y);")
        check("width>64 rejected", False)
    except GateError:
        check("width>64 rejected", True)

    print("-- extract_module --")
    s = ("<think>ok</think>\n<answer>\n```verilog\nmodule m (input a, output b);"
         " assign b = a;\nendmodule\n```\n</answer>")
    check("strict from answer+fence", extract_module_strict(s) is not None)
    check("strict rejects no-tag", extract_module_strict(
        "module m (input a, output b); assign b = a; endmodule") is None)
    check("lenient falls back to bare", extract_module_lenient(
        "module m (input a, output b); assign b = a; endmodule") is not None)
    check("lenient returns None on garbage", extract_module_lenient(
        "no verilog here") is None)

    print("-- check_interface --")
    cand = parse_header("module counter (input clk, input rst, input en, "
                        "output reg [7:0] count);")
    check("interface match", not check_interface(cand, dut))
    bad = parse_header("module counter2 (input clk, input rst, output [3:0] count);")
    m = check_interface(bad, dut)
    check("name+port+width mismatch detected", len(m) == 3, m)
    check("missing module detected", len(check_interface(None, dut)) == 1)

    print("-- generate_harness --")
    tests = [{"name": "t1", "steps": [
        {"input": {"rst": 1, "en": 0}, "expect": {"count": 0}, "clock": True},
        {"input": {"rst": 0, "en": 1}, "expect": {"count": 1}, "clock": True}]}]
    h = generate_harness(dut, tests, mode="check")
    check("harness instantiates DUT", 'Vcounter* dut = new Vcounter;' in h)
    check("harness has expect check", 'port=count expect=' in h)
    check("harness has clock pulse", "dut->clk = 0; dut->eval(); dut->clk = 1;" in h)
    # 测试隔离：每个 test 的步骤必须包在 if (t == N) 守卫里（每测试一个全新 DUT）
    multi = [{"name": "t1", "steps": [{"input": {"rst": 1, "en": 0},
                                       "expect": {"count": 0}, "clock": True}]},
             {"name": "t2", "steps": [{"input": {"rst": 1, "en": 0},
                                       "expect": {"count": 0}, "clock": True}]}]
    h3 = generate_harness(dut, multi, mode="check")
    check("per-test isolation guards", "if (t == 0) {" in h3
          and "if (t == 1) {" in h3, h3[:200])
    check("one DUT per test iteration", h3.count("new Vcounter") == 1)
    h2 = generate_harness(dut2, [{"name": "t", "steps": [
        {"input": {"a": 1}, "expect": {"b": 1}, "clock": False}]}], mode="trace")
    check("trace mode prints outputs", "(uint64_t)(dut->b)" in h2)
    try:
        generate_harness(dut, [{"name": "t", "steps": [
            {"input": {"clk": 1}, "expect": {}, "clock": True}]}])
        check("clock as input port rejected", False)
    except GateError:
        check("clock as input port rejected", True)
    try:
        generate_harness(dut2, [{"name": "t", "steps": [
            {"input": {"a": 1}, "expect": {}, "clock": True}]}])
        check("clock pulse without clk port rejected", False)
    except GateError:
        check("clock pulse without clk port rejected", True)

    print("-- prompt_text --")
    p = {"spec": "S", "header": "module m (input a, output b);"}
    t = prompt_text(p)
    check("prompt contains spec+header+tags", "S" in t and "module m" in t
          and "<answer>" in t)
    check("qwen chat format", apply_qwen_chat("hi") ==
          f"<|im_start|>system\n{QWEN_DEFAULT_SYSTEM}<|im_end|>\n"
          f"<|im_start|>user\nhi<|im_end|>\n<|im_start|>assistant\n")

    print("-- 源码防回归 --")
    # 只扫实现部分（split 掉 selftest 自身，避免检查代码自匹配）
    impl_src = open(os.path.abspath(__file__), encoding="utf-8").read() \
        .split("def _selftest()")[0]
    check("verilator 命令无 -j2（旧版不支持）", '"-j2"' not in impl_src)
    check("verilator 命令带 -Wno-fatal", impl_src.count("-Wno-fatal") >= 2)

    print("-- load_problems (data/spec_set_50.jsonl 若存在) --")
    pset = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "data", "spec_set_50.jsonl")
    if os.path.exists(pset):
        try:
            problems = load_problems(pset)
            n_eval = sum(1 for x in problems if x["split"] == "eval")
            tiers = {}
            for x in problems:
                tiers[x["tier"]] = tiers.get(x["tier"], 0) + 1
            check(f"loaded {len(problems)} problems (tiers={tiers}, eval={n_eval})",
                  len(problems) == 54 and n_eval == 14)
        except GateError as e:
            check("spec set validates", False, str(e)[:300])
    else:
        print("  [SKIP] data/spec_set_50.jsonl 不存在（先跑 build_spec_set.py）")

    print(f"\n== selftest {'FAILED: ' + str(failures) if failures else 'ALL PASS'} ==")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
    sys.exit(1)
