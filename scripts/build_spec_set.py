# -*- coding: utf-8 -*-
"""build_spec_set.py — 自建 50 题 RTL spec 集（组合 20 / 时序 20 / 状态机 10）。

设计文档第十一节风险预案 1：VerilogEval 数据获取受限时，手工构造 50 题 spec 集
（规格描述 + 参考实现 + 测试向量）。本脚本确定性生成（固定随机种子，可重复）。

输出：data/spec_set_50.jsonl（字段见 scripts/rtl_common.py 头注释，设计文档第二节超集）
  - 50 题分三档：combinational 20 / sequential 20 / fsm 10
  - 10 题标记 split=eval（分层抽取：4 组合 + 4 时序 + 2 状态机），40 题 split=train
  - 测试向量的期望值全部由 Python 镜像仿真计算（与参考实现同一份行为规格），
    参考实现本身必须先在 --verify 里过自己的双闸 —— 这是数据集的诚信底线

诚实说明（写进 detail.family）：
  - 题目按电路家族参数化生成（如 4 种计数器是同族变体），面试叙事时如实说明
  - UART/SPI 为教学简化版（16× 过采样保持真实技术点，波特率/校验位等工程细节省略）

用法：
  python scripts/build_spec_set.py                 # 生成 data/spec_set_50.jsonl
  python scripts/build_spec_set.py --out X.jsonl   # 自定义输出
  python scripts/build_spec_set.py --verify        # Linux 上双闸自检参考实现
  python scripts/build_spec_set.py --verify --problems X.jsonl
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtl_common

R = random.Random(20260920)  # 固定种子：每次生成完全一致

OUT_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "data", "spec_set_50.jsonl")

EVAL_TASK_IDS = {
    "spec50-comb-001", "spec50-comb-010", "spec50-comb-014", "spec50-comb-019",
    "spec50-seq-001", "spec50-seq-004", "spec50-seq-011", "spec50-seq-013",
    "spec50-fsm-001", "spec50-fsm-003",
    # 2026-09-21 扩充：FSM 评估集 2→6 题（E3 后补的泛化测试，三模型均未见）
    "spec50-fsm-011", "spec50-fsm-012", "spec50-fsm-013", "spec50-fsm-014",
}


def mask(v, w):
    return v & ((1 << w) - 1)


# ---------------------------------------------------------------------------
# 测试构造助手
# ---------------------------------------------------------------------------

def ct(name, cases, clock=False):
    """组合测试：cases = [(input_dict, expect_dict), ...]，一个 test 一组向量。"""
    return {"name": name,
            "steps": [{"input": i, "expect": e, "clock": clock} for i, e in cases]}


def st(name, steps):
    """时序测试：steps = [(input_dict, expect_dict), ...]，每步一个时钟脉冲。"""
    return {"name": name,
            "steps": [{"input": i, "expect": e, "clock": True} for i, e in steps]}


def comb_rand(in_ports, widths, expect_fn, n=32):
    """随机 + 全 0/全 1 边界组合用例。"""
    cases = []
    for _ in range(n):
        inputs = {p: R.getrandbits(widths[p]) for p in in_ports}
        cases.append((inputs, expect_fn(inputs)))
    zero = {p: 0 for p in in_ports}
    ones = {p: mask(-1, widths[p]) for p in in_ports}
    cases.append((zero, expect_fn(zero)))
    cases.append((ones, expect_fn(ones)))
    return cases


def P(tid, tier, spec, header, ref, tests, family):
    return {"task_id": tid, "tier": tier, "spec": spec, "header": header,
            "module": ref, "tests": tests,
            "split": "eval" if tid in EVAL_TASK_IDS else "train",
            "detail": {"family": family, "source": "self-built"}}


# ===========================================================================
# 组合逻辑（20 题）
# ===========================================================================

def comb_001_adder4():
    hdr = ("module adder4 (input [3:0] a, input [3:0] b, input cin, "
           "output [3:0] sum, output cout);")
    ref = ("module adder4 (input [3:0] a, input [3:0] b, input cin, "
           "output [3:0] sum, output cout);\n"
           "  assign {cout, sum} = a + b + cin;\n"
           "endmodule\n")
    cases = []
    for v in range(512):  # 4+4+1 = 9 输入位 → 全穷举
        a, b, cin = (v >> 5) & 0xF, (v >> 1) & 0xF, v & 1
        t = a + b + cin
        cases.append(({"a": a, "b": b, "cin": cin},
                      {"sum": t & 0xF, "cout": t >> 4}))
    half = len(cases) // 2
    return P("spec50-comb-001", "combinational",
             "Design a 4-bit full adder. It adds two 4-bit unsigned numbers a and b "
             "plus a 1-bit carry-in cin, producing a 4-bit sum and a 1-bit carry-out.",
             hdr, ref, [ct("exhaust_lo", cases[:half]),
                        ct("exhaust_hi", cases[half:])], "arithmetic")


def comb_002_adder8():
    hdr = ("module adder8 (input [7:0] a, input [7:0] b, output [8:0] sum);")
    ref = ("module adder8 (input [7:0] a, input [7:0] b, output [8:0] sum);\n"
           "  assign sum = a + b;\n"
           "endmodule\n")
    exp = lambda i: {"sum": (i["a"] + i["b"]) & 0x1FF}
    edges = [(0, 0), (255, 255), (0, 255), (255, 0), (128, 127), (1, 254), (100, 155)]
    e_cases = [({"a": a, "b": b}, exp({"a": a, "b": b})) for a, b in edges]
    r_cases = comb_rand(["a", "b"], {"a": 8, "b": 8}, exp, n=32)
    return P("spec50-comb-002", "combinational",
             "Design an 8-bit adder. It adds two 8-bit unsigned numbers a and b and "
             "produces a 9-bit sum (the extra bit is the carry-out).",
             hdr, ref, [ct("edges", e_cases), ct("rand", r_cases)], "arithmetic")


def comb_003_sub8():
    hdr = ("module sub8 (input [7:0] a, input [7:0] b, output [7:0] diff, "
           "output borrow);")
    ref = ("module sub8 (input [7:0] a, input [7:0] b, output [7:0] diff, "
           "output borrow);\n"
           "  assign {borrow, diff} = {1'b0, a} - b;\n"
           "endmodule\n")
    exp = lambda i: {"diff": (i["a"] - i["b"]) & 0xFF,
                     "borrow": 1 if i["a"] < i["b"] else 0}
    edges = [(0, 1), (1, 0), (0, 0), (255, 255), (255, 1), (1, 255), (128, 128)]
    e_cases = [({"a": a, "b": b}, exp({"a": a, "b": b})) for a, b in edges]
    r_cases = comb_rand(["a", "b"], {"a": 8, "b": 8}, exp, n=32)
    return P("spec50-comb-003", "combinational",
             "Design an 8-bit subtractor. It computes a minus b for two 8-bit "
             "unsigned numbers, producing an 8-bit difference and a 1-bit borrow "
             "flag (borrow is 1 when a is smaller than b).",
             hdr, ref, [ct("edges", e_cases), ct("rand", r_cases)], "arithmetic")


def comb_004_cmp8():
    hdr = ("module cmp8 (input [7:0] a, input [7:0] b, output eq, output lt, "
           "output gt);")
    ref = ("module cmp8 (input [7:0] a, input [7:0] b, output eq, output lt, "
           "output gt);\n"
           "  assign eq = (a == b);\n"
           "  assign lt = (a < b);\n"
           "  assign gt = (a > b);\n"
           "endmodule\n")
    exp = lambda i: {"eq": int(i["a"] == i["b"]), "lt": int(i["a"] < i["b"]),
                     "gt": int(i["a"] > i["b"])}
    edges = [(0, 0), (0, 1), (1, 0), (255, 255), (127, 128), (255, 0)]
    e_cases = [({"a": a, "b": b}, exp({"a": a, "b": b})) for a, b in edges]
    r_cases = comb_rand(["a", "b"], {"a": 8, "b": 8}, exp, n=32)
    return P("spec50-comb-004", "combinational",
             "Design an 8-bit comparator. It compares two 8-bit unsigned numbers "
             "a and b and produces three mutually exclusive flags: eq (a equals b), "
             "lt (a is less than b) and gt (a is greater than b).",
             hdr, ref, [ct("edges", e_cases), ct("rand", r_cases)], "compare")


def comb_005_mux2():
    hdr = ("module mux2 (input [7:0] a, input [7:0] b, input sel, output [7:0] out);")
    ref = ("module mux2 (input [7:0] a, input [7:0] b, input sel, output [7:0] out);\n"
           "  assign out = sel ? b : a;\n"
           "endmodule\n")
    exp = lambda i: {"out": i["b"] if i["sel"] else i["a"]}
    cases = [({"a": x, "b": y, "sel": s}, exp({"a": x, "b": y, "sel": s}))
             for x, y in [(0, 255), (255, 0), (0xAA, 0x55), (1, 2)] for s in (0, 1)]
    r_cases = comb_rand(["a", "b", "sel"], {"a": 8, "b": 8, "sel": 1}, exp, n=24)
    return P("spec50-comb-005", "combinational",
             "Design an 8-bit 2-to-1 multiplexer. When sel is 0 it outputs a; when "
             "sel is 1 it outputs b.",
             hdr, ref, [ct("edges", cases), ct("rand", r_cases)], "mux")


def comb_006_mux4():
    hdr = ("module mux4 (input [7:0] a, input [7:0] b, input [7:0] c, "
           "input [7:0] d, input [1:0] sel, output [7:0] out);")
    ref = ("module mux4 (input [7:0] a, input [7:0] b, input [7:0] c, "
           "input [7:0] d, input [1:0] sel, output [7:0] out);\n"
           "  assign out = (sel == 2'd0) ? a : (sel == 2'd1) ? b :\n"
           "                (sel == 2'd2) ? c : d;\n"
           "endmodule\n")
    exp = lambda i: {"out": [i["a"], i["b"], i["c"], i["d"]][i["sel"]]}
    vals = [1, 2, 4, 8]
    cases = [({"a": vals[0], "b": vals[1], "c": vals[2], "d": vals[3], "sel": s},
              exp({"a": vals[0], "b": vals[1], "c": vals[2], "d": vals[3], "sel": s}))
             for s in range(4)]
    r_cases = comb_rand(["a", "b", "c", "d", "sel"],
                        {"a": 8, "b": 8, "c": 8, "d": 8, "sel": 2}, exp, n=24)
    return P("spec50-comb-006", "combinational",
             "Design an 8-bit 4-to-1 multiplexer. sel selects which of the four "
             "8-bit inputs a, b, c, d is passed to out (0->a, 1->b, 2->c, 3->d).",
             hdr, ref, [ct("each_sel", cases), ct("rand", r_cases)], "mux")


def comb_007_prio():
    hdr = ("module prio_encoder (input [7:0] in, output reg [2:0] code, "
           "output valid);")
    ref = ("module prio_encoder (input [7:0] in, output reg [2:0] code, "
           "output valid);\n"
           "  always @(*) begin\n"
           "    code = 3'd0;\n"
           "    if (in[7]) code = 3'd7; else if (in[6]) code = 3'd6;\n"
           "    else if (in[5]) code = 3'd5; else if (in[4]) code = 3'd4;\n"
           "    else if (in[3]) code = 3'd3; else if (in[2]) code = 3'd2;\n"
           "    else if (in[1]) code = 3'd1; else if (in[0]) code = 3'd0;\n"
           "  end\n"
           "  assign valid = |in;\n"
           "endmodule\n")
    def exp(i):
        v = i["in"]
        code = 0
        for b in range(8):
            if (v >> b) & 1:
                code = b
        return {"code": code, "valid": 1 if v else 0}
    cases = [(0, {"code": 0, "valid": 0}),
             (1, {"code": 0, "valid": 1}),
             (0x80, {"code": 7, "valid": 1}),
             (0x55, {"code": 6, "valid": 1}),  # 最高置位 = bit6 (0x55 = 0101_0101)
             (0xFF, {"code": 7, "valid": 1})]
    r_cases = comb_rand(["in"], {"in": 8}, exp, n=32)
    return P("spec50-comb-007", "combinational",
             "Design an 8-to-3 priority encoder. It outputs the index of the "
             "highest-priority set bit (bit 7 has the highest priority, bit 0 the "
             "lowest). valid is 1 when at least one bit is set.",
             hdr, ref, [ct("edges", [( {"in": v}, e) for v, e in cases]),
                        ct("rand", r_cases)], "encoder")


def comb_008_decoder38():
    hdr = ("module decoder38 (input [2:0] in, input en, output [7:0] out);")
    ref = ("module decoder38 (input [2:0] in, input en, output [7:0] out);\n"
           "  assign out = en ? (8'b1 << in) : 8'b0;\n"
           "endmodule\n")
    exp = lambda i: {"out": (1 << i["in"]) if i["en"] else 0}
    cases = [({"in": k, "en": 0}, {"out": 0}) for k in range(8)]
    cases += [({"in": k, "en": 1}, {"out": 1 << k}) for k in range(8)]
    return P("spec50-comb-008", "combinational",
             "Design a 3-to-8 decoder with an active-high enable. When en is 1, "
             "out[in] is 1 and all other bits are 0. When en is 0, out is all zeros.",
             hdr, ref, [ct("all", cases)], "decoder")


def comb_009_parity8():
    hdr = ("module parity8 (input [7:0] data, output parity);")
    ref = ("module parity8 (input [7:0] data, output parity);\n"
           "  assign parity = ^data;\n"
           "endmodule\n")
    exp = lambda i: {"parity": bin(i["data"]).count("1") % 2}
    cases = [(0, 0), (1, 1), (3, 0), (0xFF, 0), (0xAA, 0), (0x55, 0), (0x80, 1),
             (0x81, 0)]
    r_cases = comb_rand(["data"], {"data": 8}, exp, n=24)
    return P("spec50-comb-009", "combinational",
             "Design an 8-bit odd parity generator. parity is 1 when the number "
             "of 1 bits in data is odd.",
             hdr, ref, [ct("edges", [({"data": v}, {"parity": e}) for v, e in cases]),
                        ct("rand", r_cases)], "arithmetic")


def comb_010_alu4():
    hdr = ("module alu4 (input [3:0] a, input [3:0] b, input [2:0] op, "
           "output reg [3:0] result);")
    ref = ("module alu4 (input [3:0] a, input [3:0] b, input [2:0] op, "
           "output reg [3:0] result);\n"
           "  always @(*) case (op)\n"
           "    3'd0: result = a + b;\n"
           "    3'd1: result = a - b;\n"
           "    3'd2: result = a & b;\n"
           "    3'd3: result = a | b;\n"
           "    3'd4: result = a ^ b;\n"
           "    3'd5: result = (a < b) ? 4'd1 : 4'd0;\n"
           "    3'd6: result = (a == b) ? 4'd1 : 4'd0;\n"
           "    default: result = ~a;\n"
           "  endcase\n"
           "endmodule\n")
    def exp(i):
        a, b, op = i["a"], i["b"], i["op"]
        if op == 0:
            r = a + b
        elif op == 1:
            r = a - b
        elif op == 2:
            r = a & b
        elif op == 3:
            r = a | b
        elif op == 4:
            r = a ^ b
        elif op == 5:
            r = 1 if a < b else 0
        elif op == 6:
            r = 1 if a == b else 0
        else:
            r = ~a
        return {"result": r & 0xF}
    cases = [({"a": a, "b": b, "op": op}, exp({"a": a, "b": b, "op": op}))
             for op in range(8) for a, b in [(0, 0), (15, 15), (3, 5), (5, 3)]]
    r_cases = comb_rand(["a", "b", "op"], {"a": 4, "b": 4, "op": 3}, exp, n=40)
    return P("spec50-comb-010", "combinational",
             "Design a 4-bit ALU. op selects the operation: 0=add, 1=subtract, "
             "2=bitwise and, 3=bitwise or, 4=bitwise xor, 5=set if a<b (1 else 0), "
             "6=set if a==b (1 else 0), 7=bitwise not of a. All results are 4 bits.",
             hdr, ref, [ct("ops_edges", cases), ct("rand", r_cases)], "alu")


def comb_011_barrel8():
    hdr = ("module barrel8 (input [7:0] data, input [2:0] amt, input dir, "
           "output [7:0] out);")
    ref = ("module barrel8 (input [7:0] data, input [2:0] amt, input dir, "
           "output [7:0] out);\n"
           "  assign out = dir ? (data >> amt) : (data << amt);\n"
           "endmodule\n")
    exp = lambda i: {"out": (i["data"] >> i["amt"]) if i["dir"]
                     else ((i["data"] << i["amt"]) & 0xFF)}
    cases = [({"data": d, "amt": a, "dir": s}, exp({"data": d, "amt": a, "dir": s}))
             for d in (1, 0x80, 0x55, 0xFF) for a in range(8) for s in (0, 1)]
    return P("spec50-comb-011", "combinational",
             "Design an 8-bit barrel shifter. It shifts data by amt positions: "
             "dir=0 shifts left (zeros fill the low bits), dir=1 shifts right "
             "(zeros fill the high bits).",
             hdr, ref, [ct("all", cases)], "shifter")


def comb_012_gray_enc():
    hdr = ("module gray_enc (input [3:0] bin, output [3:0] gray);")
    ref = ("module gray_enc (input [3:0] bin, output [3:0] gray);\n"
           "  assign gray = bin ^ (bin >> 1);\n"
           "endmodule\n")
    exp = lambda i: {"gray": i["bin"] ^ (i["bin"] >> 1)}
    cases = [({"bin": v}, exp({"bin": v})) for v in range(16)]
    return P("spec50-comb-012", "combinational",
             "Design a 4-bit binary-to-Gray code converter. Each Gray output bit "
             "is the XOR of the corresponding binary bit with the bit above it.",
             hdr, ref, [ct("exhaust", cases)], "code_conv")


def comb_013_gray_dec():
    hdr = ("module gray_dec (input [3:0] gray, output [3:0] bin);")
    ref = ("module gray_dec (input [3:0] gray, output [3:0] bin);\n"
           "  assign bin[3] = gray[3];\n"
           "  assign bin[2] = gray[3] ^ gray[2];\n"
           "  assign bin[1] = gray[3] ^ gray[2] ^ gray[1];\n"
           "  assign bin[0] = gray[3] ^ gray[2] ^ gray[1] ^ gray[0];\n"
           "endmodule\n")
    def exp(i):
        g = i["gray"]
        b3 = (g >> 3) & 1
        b2 = b3 ^ ((g >> 2) & 1)
        b1 = b2 ^ ((g >> 1) & 1)
        b0 = b1 ^ (g & 1)
        return {"bin": (b3 << 3) | (b2 << 2) | (b1 << 1) | b0}
    cases = [({"gray": v}, exp({"gray": v})) for v in range(16)]
    return P("spec50-comb-013", "combinational",
             "Design a 4-bit Gray-to-binary converter. bin[3] equals gray[3], and "
             "each lower bit is the XOR of the corresponding gray bit with the "
             "converted bit above it.",
             hdr, ref, [ct("exhaust", cases)], "code_conv")


def comb_014_bcd_add():
    hdr = ("module bcd_add (input [3:0] a, input [3:0] b, input cin, "
           "output [3:0] sum, output cout);")
    ref = ("module bcd_add (input [3:0] a, input [3:0] b, input cin, "
           "output [3:0] sum, output cout);\n"
           "  wire [4:0] t = a + b + cin;\n"
           "  assign cout = (t > 9);\n"
           "  assign sum = cout ? (t - 10) : t[3:0];\n"
           "endmodule\n")
    cases = []
    # 只穷举合法 BCD 输入（a,b ≤ 9）：输入约定就是 BCD 数字，
    # 非法输入下 t-10 会溢出 4 位（参考实现不保证非法输入的行为）
    for a in range(10):
        for b in range(10):
            for cin in (0, 1):
                t = a + b + cin
                cases.append(({"a": a, "b": b, "cin": cin},
                              {"sum": (t - 10) if t > 9 else t,
                               "cout": 1 if t > 9 else 0}))
    half = len(cases) // 2
    return P("spec50-comb-014", "combinational",
             "Design a single-digit BCD adder. It adds two BCD digits a and b "
             "plus carry-in cin, producing a BCD sum digit and carry-out. When the "
             "binary result exceeds 9, add the decimal correction (subtract 10 and "
             "set cout).",
             hdr, ref, [ct("exhaust_lo", cases[:half]),
                        ct("exhaust_hi", cases[half:])], "arithmetic")


def comb_015_popcount16():
    hdr = ("module popcount16 (input [15:0] data, output reg [4:0] count);")
    ref = ("module popcount16 (input [15:0] data, output reg [4:0] count);\n"
           "  integer i;\n"
           "  always @(*) begin\n"
           "    count = 5'd0;\n"
           "    for (i = 0; i < 16; i = i + 1) count = count + data[i];\n"
           "  end\n"
           "endmodule\n")
    exp = lambda i: {"count": bin(i["data"]).count("1")}
    cases = [(0, 0), (0xFFFF, 16), (0x8000, 1), (0x5555, 8), (0xAAAA, 8)]
    r_cases = comb_rand(["data"], {"data": 16}, exp, n=32)
    return P("spec50-comb-015", "combinational",
             "Design a population counter. It counts the number of 1 bits in the "
             "16-bit input data and outputs the count.",
             hdr, ref, [ct("edges", [({"data": v}, {"count": e}) for v, e in cases]),
                        ct("rand", r_cases)], "bit_count")


def comb_016_therm3():
    hdr = ("module therm3 (input [2:0] in, output [6:0] out);")
    ref = ("module therm3 (input [2:0] in, output [6:0] out);\n"
           "  assign out = (7'd1 << in) - 7'd1;\n"
           "endmodule\n")
    exp = lambda i: {"out": (1 << i["in"]) - 1}
    cases = [({"in": v}, exp({"in": v})) for v in range(8)]
    return P("spec50-comb-016", "combinational",
             "Design a 3-to-7 thermometer encoder. The number of 1 bits in out "
             "equals the value of in (out is all zeros for in=0 and all ones for "
             "in=7).",
             hdr, ref, [ct("exhaust", cases)], "encoder")


def comb_017_neg8():
    hdr = ("module neg8 (input [7:0] a, output [7:0] neg);")
    ref = ("module neg8 (input [7:0] a, output [7:0] neg);\n"
           "  assign neg = ~a + 8'd1;\n"
           "endmodule\n")
    exp = lambda i: {"neg": (-i["a"]) & 0xFF}
    cases = [(0, 0), (1, 255), (255, 1), (128, 128), (0x55, 0xAB)]
    r_cases = comb_rand(["a"], {"a": 8}, exp, n=24)
    return P("spec50-comb-017", "combinational",
             "Design an 8-bit two's complement negator. neg is the two's "
             "complement of a (equivalent to 0 minus a in 8-bit arithmetic).",
             hdr, ref, [ct("edges", [({"a": v}, {"neg": e}) for v, e in cases]),
                        ct("rand", r_cases)], "arithmetic")


def comb_018_mul4():
    hdr = ("module mul4 (input [3:0] a, input [3:0] b, output [7:0] prod);")
    ref = ("module mul4 (input [3:0] a, input [3:0] b, output [7:0] prod);\n"
           "  assign prod = a * b;\n"
           "endmodule\n")
    cases = [({"a": a, "b": b}, {"prod": a * b}) for a in range(16) for b in range(16)]
    half = len(cases) // 2
    return P("spec50-comb-018", "combinational",
             "Design a 4-bit unsigned multiplier. It multiplies two 4-bit numbers "
             "a and b and produces the 8-bit product.",
             hdr, ref, [ct("exhaust_lo", cases[:half]),
                        ct("exhaust_hi", cases[half:])], "arithmetic")


def comb_019_absdiff8():
    hdr = ("module absdiff8 (input [7:0] a, input [7:0] b, output [7:0] diff);")
    ref = ("module absdiff8 (input [7:0] a, input [7:0] b, output [7:0] diff);\n"
           "  assign diff = (a >= b) ? (a - b) : (b - a);\n"
           "endmodule\n")
    exp = lambda i: {"diff": abs(i["a"] - i["b"]) & 0xFF}
    edges = [(0, 0), (0, 255), (255, 0), (100, 150), (255, 254), (1, 1)]
    e_cases = [({"a": a, "b": b}, exp({"a": a, "b": b})) for a, b in edges]
    r_cases = comb_rand(["a", "b"], {"a": 8, "b": 8}, exp, n=32)
    return P("spec50-comb-019", "combinational",
             "Design an 8-bit absolute difference circuit. diff is the absolute "
             "value of a minus b.",
             hdr, ref, [ct("edges", e_cases), ct("rand", r_cases)], "arithmetic")


def comb_020_maj3():
    hdr = ("module maj3 (input a, input b, input c, output y);")
    ref = ("module maj3 (input a, input b, input c, output y);\n"
           "  assign y = (a & b) | (b & c) | (a & c);\n"
           "endmodule\n")
    exp = lambda i: {"y": 1 if (i["a"] + i["b"] + i["c"]) >= 2 else 0}
    cases = [({"a": (v >> 2) & 1, "b": (v >> 1) & 1, "c": v & 1},
              exp({"a": (v >> 2) & 1, "b": (v >> 1) & 1, "c": v & 1}))
             for v in range(8)]
    return P("spec50-comb-020", "combinational",
             "Design a 3-input majority voter. y is 1 when at least two of the "
             "three inputs a, b, c are 1.",
             hdr, ref, [ct("exhaust", cases)], "logic")


# ===========================================================================
# 时序逻辑（20 题）
# ===========================================================================

def seq_001_counter8():
    hdr = ("module counter8 (input clk, input rst, input en, "
           "output reg [7:0] count);")
    ref = ("module counter8 (input clk, input rst, input en, "
           "output reg [7:0] count);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) count <= 8'd0;\n"
           "    else if (en) count <= count + 8'd1;\n"
           "  end\n"
           "endmodule\n")
    t1 = st("t_reset", [({"rst": 1, "en": 1}, {"count": 0}),
                        ({"rst": 0, "en": 0}, {"count": 0}),
                        ({"rst": 0, "en": 0}, {"count": 0})])
    t2 = st("t_count5", [({"rst": 1, "en": 0}, {"count": 0})] +
            [({"rst": 0, "en": 1}, {"count": k}) for k in range(1, 6)])
    t3 = st("t_wrap", [({"rst": 1, "en": 0}, {"count": 0})] +
            [({"rst": 0, "en": 1}, {"count": k}) for k in range(1, 256)] +
            [({"rst": 0, "en": 1}, {"count": 0})])
    t4 = st("t_en_gate", [({"rst": 1, "en": 0}, {"count": 0}),
                          ({"rst": 0, "en": 1}, {"count": 1}),
                          ({"rst": 0, "en": 1}, {"count": 2}),
                          ({"rst": 0, "en": 0}, {"count": 2}),
                          ({"rst": 0, "en": 0}, {"count": 2}),
                          ({"rst": 0, "en": 1}, {"count": 3})])
    return P("spec50-seq-001", "sequential",
             "Design an 8-bit up counter with synchronous reset and enable. On "
             "each clock edge, if rst is 1 the count goes to 0; otherwise if en is "
             "1 the count increments by 1 (wrapping from 255 back to 0).",
             hdr, ref, [t1, t2, t3, t4], "counter")


def seq_002_load_counter8():
    hdr = ("module load_counter8 (input clk, input rst, input load, "
           "input [7:0] data, output reg [7:0] count);")
    ref = ("module load_counter8 (input clk, input rst, input load, "
           "input [7:0] data, output reg [7:0] count);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) count <= 8'd0;\n"
           "    else if (load) count <= data;\n"
           "    else count <= count + 8'd1;\n"
           "  end\n"
           "endmodule\n")
    t1 = st("t_reset_run", [({"rst": 1, "load": 0, "data": 0}, {"count": 0}),
                            ({"rst": 0, "load": 0, "data": 0}, {"count": 1}),
                            ({"rst": 0, "load": 0, "data": 0}, {"count": 2}),
                            ({"rst": 0, "load": 0, "data": 0}, {"count": 3})])
    t2 = st("t_load", [({"rst": 1, "load": 0, "data": 0}, {"count": 0}),
                       ({"rst": 0, "load": 1, "data": 100}, {"count": 100}),
                       ({"rst": 0, "load": 0, "data": 0}, {"count": 101}),
                       ({"rst": 0, "load": 1, "data": 0}, {"count": 0}),
                       ({"rst": 0, "load": 1, "data": 255}, {"count": 255})])
    t3 = st("t_rst_priority", [({"rst": 0, "load": 1, "data": 7}, {"count": 7}),
                               ({"rst": 1, "load": 1, "data": 7}, {"count": 0})])
    return P("spec50-seq-002", "sequential",
             "Design an 8-bit counter with synchronous reset and parallel load. "
             "On each clock edge: if rst is 1 the count goes to 0; else if load is "
             "1 the count becomes data; otherwise it increments by 1.",
             hdr, ref, [t1, t2, t3], "counter")


def seq_003_bcd_counter():
    hdr = ("module bcd_counter (input clk, input rst, input en, "
           "output reg [3:0] count, output tc);")
    ref = ("module bcd_counter (input clk, input rst, input en, "
           "output reg [3:0] count, output tc);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) count <= 4'd0;\n"
           "    else if (en) count <= (count == 4'd9) ? 4'd0 : count + 4'd1;\n"
           "  end\n"
           "  assign tc = (count == 4'd9);\n"
           "endmodule\n")
    t1 = st("t_cycle", [({"rst": 1, "en": 0}, {"count": 0, "tc": 0})] +
            [({"rst": 0, "en": 1}, {"count": k, "tc": 1 if k == 9 else 0})
             for k in range(1, 10)] +
            [({"rst": 0, "en": 1}, {"count": 0, "tc": 0}),
             ({"rst": 0, "en": 1}, {"count": 1, "tc": 0})])
    t2 = st("t_en_gate", [({"rst": 1, "en": 0}, {"count": 0, "tc": 0}),
                          ({"rst": 0, "en": 1}, {"count": 1, "tc": 0}),
                          ({"rst": 0, "en": 0}, {"count": 1, "tc": 0}),
                          ({"rst": 0, "en": 0}, {"count": 1, "tc": 0}),
                          ({"rst": 0, "en": 1}, {"count": 2, "tc": 0})])
    return P("spec50-seq-003", "sequential",
             "Design a BCD decade counter. On each clock edge with en=1, count "
             "increments and wraps from 9 back to 0. tc (terminal count) is 1 "
             "whenever count equals 9.",
             hdr, ref, [t1, t2], "counter")


def seq_004_updown8():
    hdr = ("module updown8 (input clk, input rst, input en, input up, "
           "output reg [7:0] count);")
    ref = ("module updown8 (input clk, input rst, input en, input up, "
           "output reg [7:0] count);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) count <= 8'd0;\n"
           "    else if (en) count <= up ? count + 8'd1 : count - 8'd1;\n"
           "  end\n"
           "endmodule\n")
    t1 = st("t_up", [({"rst": 1, "en": 0, "up": 0}, {"count": 0}),
                     ({"rst": 0, "en": 1, "up": 1}, {"count": 1}),
                     ({"rst": 0, "en": 1, "up": 1}, {"count": 2}),
                     ({"rst": 0, "en": 1, "up": 1}, {"count": 3})])
    t2 = st("t_down_wrap", [({"rst": 1, "en": 0, "up": 0}, {"count": 0}),
                            ({"rst": 0, "en": 1, "up": 0}, {"count": 255}),
                            ({"rst": 0, "en": 1, "up": 0}, {"count": 254}),
                            ({"rst": 0, "en": 1, "up": 1}, {"count": 255}),
                            ({"rst": 0, "en": 1, "up": 1}, {"count": 0})])
    t3 = st("t_gate", [({"rst": 1, "en": 0, "up": 0}, {"count": 0}),
                       ({"rst": 0, "en": 0, "up": 1}, {"count": 0}),
                       ({"rst": 0, "en": 1, "up": 0}, {"count": 255}),
                       ({"rst": 0, "en": 0, "up": 0}, {"count": 255})])
    return P("spec50-seq-004", "sequential",
             "Design an 8-bit up/down counter with synchronous reset and enable. "
             "When en is 1, count increments if up is 1 and decrements if up is 0 "
             "(wrapping in both directions).",
             hdr, ref, [t1, t2, t3], "counter")


def seq_005_lfsr4():
    hdr = ("module lfsr4 (input clk, input rst, input en, output [3:0] state);")
    ref = ("module lfsr4 (input clk, input rst, input en, output [3:0] state);\n"
           "  reg [3:0] s;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) s <= 4'd1;\n"
           "    else if (en) s <= {s[2:0], s[3] ^ s[2]};\n"
           "  end\n"
           "  assign state = s;\n"
           "endmodule\n")
    seq = [1]
    for _ in range(16):
        s = seq[-1]
        seq.append(((s << 1) & 0xF) | (((s >> 3) & 1) ^ ((s >> 2) & 1)))
    # 15 拍完整周期后回到 1；再多走一拍应进入下一周期的开头（seq[16] = 2）
    t1 = st("t_period", [({"rst": 1, "en": 0}, {"state": 1})] +
            [({"rst": 0, "en": 1}, {"state": seq[k]}) for k in range(1, 16)] +
            [({"rst": 0, "en": 1}, {"state": seq[16]})])
    t2 = st("t_gate_reseed", [({"rst": 1, "en": 0}, {"state": 1}),
                              ({"rst": 0, "en": 1}, {"state": 2}),
                              ({"rst": 0, "en": 0}, {"state": 2}),
                              ({"rst": 1, "en": 0}, {"state": 1}),
                              ({"rst": 0, "en": 1}, {"state": 2})])
    return P("spec50-seq-005", "sequential",
             "Design a 4-bit LFSR (linear feedback shift register) with feedback "
             "polynomial x^4+x^3+1. On reset the state seeds to 1. On each enabled "
             "clock edge the state shifts left and the new low bit is the XOR of "
             "the two highest bits.",
             hdr, ref, [t1, t2], "lfsr")


def seq_006_shifter8():
    hdr = ("module shifter8 (input clk, input rst, input en, input dir, "
           "input sin, output reg [7:0] q);")
    ref = ("module shifter8 (input clk, input rst, input en, input dir, "
           "input sin, output reg [7:0] q);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) q <= 8'd0;\n"
           "    else if (en) q <= dir ? {sin, q[7:1]} : {q[6:0], sin};\n"
           "  end\n"
           "endmodule\n")
    # dir=1：sin 从高位进入，右移；dir=0：sin 从低位进入，左移
    t1 = st("t_shift_right", [({"rst": 1, "en": 0, "dir": 0, "sin": 0}, {"q": 0}),
                              ({"rst": 0, "en": 1, "dir": 1, "sin": 1}, {"q": 0x80}),
                              ({"rst": 0, "en": 1, "dir": 1, "sin": 0}, {"q": 0x40}),
                              ({"rst": 0, "en": 1, "dir": 1, "sin": 1}, {"q": 0xA0}),
                              ({"rst": 0, "en": 1, "dir": 1, "sin": 1}, {"q": 0xD0})])
    t2 = st("t_shift_left", [({"rst": 1, "en": 0, "dir": 0, "sin": 0}, {"q": 0}),
                             ({"rst": 0, "en": 1, "dir": 0, "sin": 1}, {"q": 0x01}),
                             ({"rst": 0, "en": 1, "dir": 0, "sin": 0}, {"q": 0x02}),
                             ({"rst": 0, "en": 1, "dir": 0, "sin": 1}, {"q": 0x05}),
                             ({"rst": 0, "en": 1, "dir": 0, "sin": 1}, {"q": 0x0B})])
    t3 = st("t_gate", [({"rst": 1, "en": 0, "dir": 0, "sin": 0}, {"q": 0}),
                       ({"rst": 0, "en": 1, "dir": 0, "sin": 1}, {"q": 1}),
                       ({"rst": 0, "en": 0, "dir": 0, "sin": 1}, {"q": 1}),
                       ({"rst": 0, "en": 0, "dir": 0, "sin": 0}, {"q": 1})])
    return P("spec50-seq-006", "sequential",
             "Design an 8-bit bidirectional shift register. On each enabled clock "
             "edge: if dir is 1, shift right with sin entering the most significant "
             "bit; if dir is 0, shift left with sin entering the least significant "
             "bit.",
             hdr, ref, [t1, t2, t3], "shift_reg")


def seq_007_piso8():
    hdr = ("module piso8 (input clk, input rst, input load, input [7:0] data, "
           "input shift_en, output sout);")
    ref = ("module piso8 (input clk, input rst, input load, input [7:0] data, "
           "input shift_en, output sout);\n"
           "  reg [7:0] sr;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) sr <= 8'd0;\n"
           "    else if (load) sr <= data;\n"
           "    else if (shift_en) sr <= {sr[6:0], 1'b0};\n"
           "  end\n"
           "  assign sout = sr[7];\n"
           "endmodule\n")
    t1 = st("t_piso", [({"rst": 1, "load": 0, "data": 0, "shift_en": 0}, {"sout": 0}),
                       ({"rst": 0, "load": 1, "data": 0xA5, "shift_en": 0}, {"sout": 1}),
                       ({"rst": 0, "load": 0, "data": 0, "shift_en": 1}, {"sout": 0}),
                       ({"rst": 0, "load": 0, "data": 0, "shift_en": 1}, {"sout": 1}),
                       ({"rst": 0, "load": 0, "data": 0, "shift_en": 1}, {"sout": 0}),
                       ({"rst": 0, "load": 0, "data": 0, "shift_en": 1}, {"sout": 0}),
                       ({"rst": 0, "load": 0, "data": 0, "shift_en": 1}, {"sout": 1})])
    t2 = st("t_load_priority", [({"rst": 1, "load": 0, "data": 0, "shift_en": 0},
                                 {"sout": 0}),
                                ({"rst": 0, "load": 1, "data": 0x80, "shift_en": 1},
                                 {"sout": 1}),
                                ({"rst": 0, "load": 0, "data": 0, "shift_en": 1},
                                 {"sout": 0})])
    return P("spec50-seq-007", "sequential",
             "Design an 8-bit parallel-in serial-out shift register. When load is "
             "1 the register captures data; otherwise when shift_en is 1 it shifts "
             "left one bit (zero fills the low bit). sout is always the current "
             "most significant bit.",
             hdr, ref, [t1, t2], "shift_reg")


def seq_008_sipo8():
    hdr = ("module sipo8 (input clk, input rst, input en, input sin, "
           "output reg [7:0] q);")
    ref = ("module sipo8 (input clk, input rst, input en, input sin, "
           "output reg [7:0] q);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) q <= 8'd0;\n"
           "    else if (en) q <= {q[6:0], sin};\n"
           "  end\n"
           "endmodule\n")
    bits = [1, 0, 1, 0, 0, 1, 0, 1]  # 0xA5 LSB first
    qs = []
    q = 0
    for b in bits:
        q = ((q << 1) & 0xFF) | b
        qs.append(q)
    t1 = st("t_sipo", [({"rst": 1, "en": 0, "sin": 0}, {"q": 0}),
                       ({"rst": 0, "en": 0, "sin": bits[0]}, {"q": 0})] +
            [({"rst": 0, "en": 1, "sin": b}, {"q": qv})
             for b, qv in zip(bits, qs)])
    return P("spec50-seq-008", "sequential",
             "Design an 8-bit serial-in parallel-out shift register. On each "
             "enabled clock edge the register shifts left and captures sin into "
             "the least significant bit. q is the current register contents.",
             hdr, ref, [t1], "shift_reg")


def seq_009_acc8():
    hdr = ("module acc8 (input clk, input rst, input en, input [7:0] data, "
           "output reg [15:0] acc);")
    ref = ("module acc8 (input clk, input rst, input en, input [7:0] data, "
           "output reg [15:0] acc);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) acc <= 16'd0;\n"
           "    else if (en) acc <= acc + data;\n"
           "  end\n"
           "endmodule\n")
    t1 = st("t_acc", [({"rst": 1, "en": 0, "data": 0}, {"acc": 0}),
                      ({"rst": 0, "en": 1, "data": 10}, {"acc": 10}),
                      ({"rst": 0, "en": 1, "data": 20}, {"acc": 30}),
                      ({"rst": 0, "en": 1, "data": 30}, {"acc": 60}),
                      ({"rst": 0, "en": 0, "data": 99}, {"acc": 60})])
    t2 = st("t_wide", [({"rst": 1, "en": 0, "data": 0}, {"acc": 0}),
                       ({"rst": 0, "en": 1, "data": 250}, {"acc": 250}),
                       ({"rst": 0, "en": 1, "data": 250}, {"acc": 500}),
                       ({"rst": 0, "en": 1, "data": 250}, {"acc": 750}),
                       ({"rst": 1, "en": 1, "data": 250}, {"acc": 0})])
    return P("spec50-seq-009", "sequential",
             "Design a 16-bit accumulator. On each enabled clock edge it adds the "
             "8-bit data to the 16-bit acc register (so repeated additions do not "
             "overflow). Synchronous reset clears acc to 0.",
             hdr, ref, [t1, t2], "datapath")


def seq_010_ram16x8():
    hdr = ("module ram16x8 (input clk, input we, input [3:0] addr, "
           "input [7:0] wdata, output [7:0] rdata);")
    ref = ("module ram16x8 (input clk, input we, input [3:0] addr, "
           "input [7:0] wdata, output [7:0] rdata);\n"
           "  reg [7:0] mem [0:15];\n"
           "  always @(posedge clk) begin\n"
           "    if (we) mem[addr] <= wdata;\n"
           "  end\n"
           "  assign rdata = mem[addr];\n"
           "endmodule\n")
    mem = {}
    steps = []
    # 写入 0xAA 到 0 号地址并立刻读回（异步读）
    steps.append(({"clk": 0, "we": 1, "addr": 0, "wdata": 0xAA}, {"rdata": 0xAA}))
    mem[0] = 0xAA
    for a, v in [(1, 0x11), (2, 0x22), (15, 0xFF)]:
        steps.append(({"clk": 0, "we": 1, "addr": a, "wdata": v}, {"rdata": v}))
        mem[a] = v
    # 无写使能时读不改
    for a in (0, 1, 2, 15):
        steps.append(({"clk": 0, "we": 0, "addr": a, "wdata": 0}, {"rdata": mem[a]}))
    # 覆盖写 0 号地址
    steps.append(({"clk": 0, "we": 1, "addr": 0, "wdata": 0x55}, {"rdata": 0x55}))
    mem[0] = 0x55
    steps.append(({"clk": 0, "we": 0, "addr": 0, "wdata": 0}, {"rdata": 0x55}))
    # clk 不是数据端口——测试向量里只驱动 we/addr/wdata（clk 由 harness 驱动）
    # 注意：seq 测试助手会给每步加时钟脉冲，这里手工构造（无 clk 输入字段）
    tests = [{"name": "t_ram", "steps": [
        {"input": {k: v for k, v in i.items() if k != "clk"},
         "expect": e, "clock": True} for i, e in steps]}]
    return P("spec50-seq-010", "sequential",
             "Design a 16-word by 8-bit synchronous-write RAM. When we is 1, the "
             "data on wdata is written to mem[addr] at the clock edge. Reading is "
             "asynchronous: rdata always reflects mem[addr].",
             hdr, ref, tests, "memory")


def seq_011_fifo8x8():
    hdr = ("module fifo8x8 (input clk, input rst, input push, input pop, "
           "input [7:0] din, output [7:0] dout, output full, output empty);")
    ref = ("module fifo8x8 (input clk, input rst, input push, input pop, "
           "input [7:0] din, output [7:0] dout, output full, output empty);\n"
           "  reg [7:0] mem [0:7];\n"
           "  reg [3:0] count;\n"
           "  reg [2:0] wp, rp;\n"
           "  wire do_push = push & ~full;\n"
           "  wire do_pop  = pop  & ~empty;\n"
           "  assign full  = (count == 8);\n"
           "  assign empty = (count == 0);\n"
           "  assign dout  = mem[rp];\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin count <= 4'd0; wp <= 3'd0; rp <= 3'd0; end\n"
           "    else begin\n"
           "      if (do_push) begin mem[wp] <= din; wp <= wp + 3'd1; end\n"
           "      if (do_pop) rp <= rp + 3'd1;\n"
           "      if (do_push & ~do_pop) count <= count + 4'd1;\n"
           "      else if (do_pop & ~do_push) count <= count - 4'd1;\n"
           "    end\n"
           "  end\n"
           "endmodule\n")

    def fifo_sim(ops):
        """ops = [(push, pop, din)] → 每步后 (dout, full, empty)"""
        mem, count, wp, rp = {}, 0, 0, 0
        out = []
        for push, pop, din in ops:
            full = count == 8
            empty = count == 0
            do_push = push and not full
            do_pop = pop and not empty
            if do_push:
                mem[wp] = din
                wp = (wp + 1) & 7
            if do_pop:
                rp = (rp + 1) & 7
            if do_push and not do_pop:
                count += 1
            elif do_pop and not do_push:
                count -= 1
            out.append((mem.get(rp, 0), int(count == 8), int(count == 0)))
        return out

    def mk(ops):
        return st("t", [({"rst": 1, "push": 0, "pop": 0, "din": 0},
                         {"dout": 0, "full": 0, "empty": 1})] +
                  [({"rst": 0, "push": p, "pop": q, "din": d},
                    {"dout": dout, "full": f, "empty": e})
                   for (p, q, d), (dout, f, e) in zip(ops, fifo_sim(ops))])

    t1 = mk([(1, 0, 0x11), (1, 0, 0x22), (1, 0, 0x33),
             (0, 1, 0), (0, 1, 0), (0, 1, 0)])
    t1["name"] = "t_basic"
    t2 = mk([(1, 0, k) for k in range(8)] + [(1, 0, 99), (0, 1, 0)])
    t2["name"] = "t_full"
    t3 = mk([(1, 0, 0xA5), (1, 1, 0x5A), (0, 0, 0), (0, 1, 0), (0, 1, 0)])
    t3["name"] = "t_simul_push_pop"
    t4 = mk([(1, 0, k) for k in range(8)] + [(0, 1, 0)] * 8 + [(1, 0, 0xAA)])
    t4["name"] = "t_wrap"
    return P("spec50-seq-011", "sequential",
             "Design an 8-deep 8-bit FIFO. push writes din into the FIFO (ignored "
             "when full), pop removes the oldest entry (ignored when empty). dout "
             "always shows the oldest entry, full and empty are status flags. "
             "Synchronous reset clears all entries.",
             hdr, ref, [t1, t2, t3, t4], "memory")


def seq_012_clkdiv10():
    hdr = ("module clkdiv10 (input clk, input rst, output clk_out);")
    ref = ("module clkdiv10 (input clk, input rst, output clk_out);\n"
           "  reg [3:0] cnt;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) cnt <= 4'd0;\n"
           "    else cnt <= (cnt == 4'd9) ? 4'd0 : cnt + 4'd1;\n"
           "  end\n"
           "  assign clk_out = (cnt < 5);\n"
           "endmodule\n")
    # rst 拍 cnt=0（clk_out=1）；下一拍 cnt=1（clk_out=1）；随后 cnt 从 2 走到 13
    # （cnt 是 0-9 循环计数器，10 起按取模回绕）
    cnt_seq = [1 if (c % 10) < 5 else 0 for c in range(2, 14)]
    t1 = st("t_div10", [({"rst": 1}, {"clk_out": 1}),
                        ({"rst": 0}, {"clk_out": 1})] +
            [({"rst": 0}, {"clk_out": c}) for c in cnt_seq])
    t2 = st("t_rst_mid", [({"rst": 1}, {"clk_out": 1}),
                          ({"rst": 0}, {"clk_out": 1}),
                          ({"rst": 0}, {"clk_out": 1}),
                          ({"rst": 0}, {"clk_out": 1}),
                          ({"rst": 1}, {"clk_out": 1}),
                          ({"rst": 0}, {"clk_out": 1})])
    return P("spec50-seq-012", "sequential",
             "Design a divide-by-10 clock divider. clk_out is high for 5 clock "
             "cycles and low for 5 clock cycles (50 percent duty cycle). "
             "Synchronous reset restarts the count.",
             hdr, ref, [t1, t2], "clk_divider")


def seq_013_pulse_stretch4():
    hdr = ("module pulse_stretch4 (input clk, input rst, input pulse, "
           "output stretched);")
    ref = ("module pulse_stretch4 (input clk, input rst, input pulse, "
           "output stretched);\n"
           "  reg [2:0] cnt;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) cnt <= 3'd0;\n"
           "    else if (pulse) cnt <= 3'd4;\n"
           "    else if (cnt > 0) cnt <= cnt - 3'd1;\n"
           "  end\n"
           "  assign stretched = pulse | (cnt > 0);\n"
           "endmodule\n")

    def sim(pulses):
        cnt, out = 0, []
        for p in pulses:
            cnt = 4 if p else (cnt - 1 if cnt > 0 else 0)
            out.append(1 if (p or cnt > 0) else 0)
        return out

    p = [1, 0, 0, 0, 0, 0]
    e = sim(p)
    t1 = st("t_stretch", [({"rst": 1, "pulse": 0}, {"stretched": 0})] +
            [({"rst": 0, "pulse": v}, {"stretched": s}) for v, s in zip(p, e)])
    p2 = [1, 0, 1, 0, 0, 0, 0, 0]
    e2 = sim(p2)
    t2 = st("t_retrigger", [({"rst": 1, "pulse": 0}, {"stretched": 0})] +
            [({"rst": 0, "pulse": v}, {"stretched": s}) for v, s in zip(p2, e2)])
    t3 = st("t_none", [({"rst": 1, "pulse": 0}, {"stretched": 0}),
                       ({"rst": 0, "pulse": 0}, {"stretched": 0}),
                       ({"rst": 0, "pulse": 0}, {"stretched": 0})])
    return P("spec50-seq-013", "sequential",
             "Design a pulse stretcher. A 1-cycle pulse on the pulse input makes "
             "stretched stay high for 4 clock cycles (the cycle the pulse arrives "
             "plus the following 3 cycles). A new pulse while stretched is high "
             "restarts the count.",
             hdr, ref, [t1, t2, t3], "timing")


def seq_014_counter8_tc():
    hdr = ("module counter8_tc (input clk, input rst, input en, input [7:0] max, "
           "output reg [7:0] count, output tc);")
    ref = ("module counter8_tc (input clk, input rst, input en, input [7:0] max, "
           "output reg [7:0] count, output tc);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) count <= 8'd0;\n"
           "    else if (en) count <= (count == max) ? 8'd0 : count + 8'd1;\n"
           "  end\n"
           "  assign tc = (count == max);\n"
           "endmodule\n")
    t1 = st("t_mod5", [({"rst": 1, "en": 0, "max": 4}, {"count": 0, "tc": 0}),
                       ({"rst": 0, "en": 1, "max": 4}, {"count": 1, "tc": 0}),
                       ({"rst": 0, "en": 1, "max": 4}, {"count": 2, "tc": 0}),
                       ({"rst": 0, "en": 1, "max": 4}, {"count": 3, "tc": 0}),
                       ({"rst": 0, "en": 1, "max": 4}, {"count": 4, "tc": 1}),
                       ({"rst": 0, "en": 1, "max": 4}, {"count": 0, "tc": 0})])
    t2 = st("t_mod2", [({"rst": 1, "en": 0, "max": 1}, {"count": 0, "tc": 0}),
                       ({"rst": 0, "en": 1, "max": 1}, {"count": 1, "tc": 1}),
                       ({"rst": 0, "en": 1, "max": 1}, {"count": 0, "tc": 0}),
                       ({"rst": 0, "en": 1, "max": 1}, {"count": 1, "tc": 1})])
    t3 = st("t_max_change", [({"rst": 1, "en": 0, "max": 2}, {"count": 0, "tc": 0}),
                             ({"rst": 0, "en": 1, "max": 2}, {"count": 1, "tc": 0}),
                             ({"rst": 0, "en": 1, "max": 9}, {"count": 2, "tc": 0}),
                             ({"rst": 0, "en": 1, "max": 9}, {"count": 3, "tc": 0})])
    return P("spec50-seq-014", "sequential",
             "Design an 8-bit counter with a programmable terminal count. When "
             "count reaches the max input, the next enabled clock edge wraps it to "
             "0. tc is 1 whenever count equals max.",
             hdr, ref, [t1, t2, t3], "counter")


def seq_015_ring4():
    hdr = ("module ring4 (input clk, input rst, input en, output reg [3:0] q);")
    ref = ("module ring4 (input clk, input rst, input en, output reg [3:0] q);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) q <= 4'b0001;\n"
           "    else if (en) q <= {q[0], q[3:1]};\n"
           "  end\n"
           "endmodule\n")
    t1 = st("t_rotate", [({"rst": 1, "en": 0}, {"q": 1}),
                         ({"rst": 0, "en": 1}, {"q": 8}),
                         ({"rst": 0, "en": 1}, {"q": 4}),
                         ({"rst": 0, "en": 1}, {"q": 2}),
                         ({"rst": 0, "en": 1}, {"q": 1}),
                         ({"rst": 0, "en": 1}, {"q": 8})])
    t2 = st("t_gate", [({"rst": 1, "en": 0}, {"q": 1}),
                       ({"rst": 0, "en": 0}, {"q": 1}),
                       ({"rst": 0, "en": 0}, {"q": 1}),
                       ({"rst": 0, "en": 1}, {"q": 8}),
                       ({"rst": 1, "en": 1}, {"q": 1})])
    return P("spec50-seq-015", "sequential",
             "Design a 4-bit ring counter. It starts as 0001 after reset and on "
             "each enabled clock edge the single 1 bit rotates to the next "
             "position (0001 -> 1000 -> 0100 -> 0010 -> 0001).",
             hdr, ref, [t1, t2], "counter")


def seq_016_johnson4():
    hdr = ("module johnson4 (input clk, input rst, output reg [3:0] q);")
    ref = ("module johnson4 (input clk, input rst, output reg [3:0] q);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) q <= 4'd0;\n"
           "    else q <= {~q[0], q[3:1]};\n"
           "  end\n"
           "endmodule\n")
    seq = [0, 8, 12, 14, 15, 7, 3, 1, 0]
    t1 = st("t_cycle", [({"rst": 1}, {"q": 0}),
                        ({"rst": 0}, {"q": 8}),
                        ({"rst": 0}, {"q": 12}),
                        ({"rst": 0}, {"q": 14}),
                        ({"rst": 0}, {"q": 15}),
                        ({"rst": 0}, {"q": 7}),
                        ({"rst": 0}, {"q": 3}),
                        ({"rst": 0}, {"q": 1}),
                        ({"rst": 0}, {"q": 0}),
                        ({"rst": 0}, {"q": 8})])
    return P("spec50-seq-016", "sequential",
             "Design a 4-bit Johnson counter (twisted ring counter). Each clock "
             "edge shifts the register right and feeds the complement of the last "
             "bit back into the first bit, giving an 8-state cycle: "
             "0000 -> 1000 -> 1100 -> 1110 -> 1111 -> 0111 -> 0011 -> 0001 -> 0000.",
             hdr, ref, [t1], "counter")


def seq_017_counter4_arst():
    hdr = ("module counter4_arst (input clk, input rst, output reg [3:0] count);")
    ref = ("module counter4_arst (input clk, input rst, output reg [3:0] count);\n"
           "  always @(posedge clk or posedge rst) begin\n"
           "    if (rst) count <= 4'd0;\n"
           "    else count <= count + 4'd1;\n"
           "  end\n"
           "endmodule\n")
    # 异步复位：rst=1 无需时钟脉冲立即清零
    t1 = [{"name": "t_async_rst", "steps": [
        {"input": {"rst": 0}, "expect": {"count": 1}, "clock": True},
        {"input": {"rst": 0}, "expect": {"count": 2}, "clock": True},
        {"input": {"rst": 1}, "expect": {"count": 0}, "clock": False},
        {"input": {"rst": 0}, "expect": {"count": 1}, "clock": True},
        {"input": {"rst": 0}, "expect": {"count": 2}, "clock": True},
        {"input": {"rst": 0}, "expect": {"count": 3}, "clock": True}]}]
    t2 = st("t_wrap", [({"rst": 1}, {"count": 0}),
                       ({"rst": 0}, {"count": 1}),
                       ({"rst": 0}, {"count": 2}),
                       ({"rst": 0}, {"count": 3}),
                       ({"rst": 0}, {"count": 4}),
                       ({"rst": 0}, {"count": 5})])
    return P("spec50-seq-017", "sequential",
             "Design a 4-bit free-running counter with active-high ASYNCHRONOUS "
             "reset. The count increments on every clock edge and wraps at 15. "
             "A rising edge on rst clears the count immediately, without waiting "
             "for a clock edge.",
             hdr, ref, t1 + [t2], "counter")


def seq_018_counter4_cout():
    hdr = ("module counter4_cout (input clk, input rst, input en, "
           "output reg [3:0] count, output reg cout);")
    ref = ("module counter4_cout (input clk, input rst, input en, "
           "output reg [3:0] count, output reg cout);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin count <= 4'd0; cout <= 1'b0; end\n"
           "    else if (en) begin\n"
           "      count <= count + 4'd1;\n"
           "      cout <= (count == 4'd15);\n"
           "    end\n"
           "  end\n"
           "endmodule\n")
    # cout 在 count==15 的那一拍打一拍脉冲（count 已回到 0）
    steps = [({"rst": 1, "en": 0}, {"count": 0, "cout": 0})]
    steps += [({"rst": 0, "en": 1}, {"count": k, "cout": 0}) for k in range(1, 16)]
    steps += [({"rst": 0, "en": 1}, {"count": 0, "cout": 1}),
              ({"rst": 0, "en": 1}, {"count": 1, "cout": 0})]
    t1 = st("t_wrap_cout", steps)
    t2 = st("t_en_gate", [({"rst": 1, "en": 0}, {"count": 0, "cout": 0}),
                          ({"rst": 0, "en": 1}, {"count": 1, "cout": 0}),
                          ({"rst": 0, "en": 0}, {"count": 1, "cout": 0}),
                          ({"rst": 0, "en": 0}, {"count": 1, "cout": 0})])
    return P("spec50-seq-018", "sequential",
             "Design a 4-bit counter with an overflow pulse. On the clock edge "
             "where count wraps from 15 back to 0, cout goes high for exactly one "
             "cycle. cout stays 0 when en is 0.",
             hdr, ref, [t1, t2], "counter")


def seq_019_sat_counter4():
    hdr = ("module sat_counter4 (input clk, input rst, input en, input up, "
           "output reg [3:0] count);")
    ref = ("module sat_counter4 (input clk, input rst, input en, input up, "
           "output reg [3:0] count);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) count <= 4'd0;\n"
           "    else if (en) begin\n"
           "      if (up) count <= (count == 4'd15) ? 4'd15 : count + 4'd1;\n"
           "      else count <= (count == 4'd0) ? 4'd0 : count - 4'd1;\n"
           "    end\n"
           "  end\n"
           "endmodule\n")
    t1 = st("t_saturate_top", [({"rst": 1, "en": 0, "up": 0}, {"count": 0}),
                               ({"rst": 0, "en": 1, "up": 1}, {"count": 1}),
                               ({"rst": 0, "en": 1, "up": 1}, {"count": 2})] +
            [({"rst": 0, "en": 1, "up": 1}, {"count": k}) for k in range(3, 16)] +
            [({"rst": 0, "en": 1, "up": 1}, {"count": 15}),
             ({"rst": 0, "en": 1, "up": 1}, {"count": 15}),
             ({"rst": 0, "en": 1, "up": 1}, {"count": 15})])
    t2 = st("t_saturate_bottom", [({"rst": 1, "en": 0, "up": 0}, {"count": 0}),
                                  ({"rst": 0, "en": 1, "up": 0}, {"count": 0}),
                                  ({"rst": 0, "en": 1, "up": 1}, {"count": 1}),
                                  ({"rst": 0, "en": 1, "up": 1}, {"count": 2}),
                                  ({"rst": 0, "en": 1, "up": 0}, {"count": 1}),
                                  ({"rst": 0, "en": 1, "up": 0}, {"count": 0}),
                                  ({"rst": 0, "en": 1, "up": 0}, {"count": 0})])
    return P("spec50-seq-019", "sequential",
             "Design a 4-bit saturating up/down counter. It counts up or down on "
             "enabled clock edges, but instead of wrapping it SATURATES: it stays "
             "at 15 when counting up past 15 and stays at 0 when counting down "
             "past 0.",
             hdr, ref, [t1, t2], "counter")


def seq_020_edge_detect():
    hdr = ("module edge_detect (input clk, input rst, input sig, output reg pulse);")
    ref = ("module edge_detect (input clk, input rst, input sig, output reg pulse);\n"
           "  reg prev;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin prev <= 1'b0; pulse <= 1'b0; end\n"
           "    else begin\n"
           "      prev <= sig;\n"
           "      pulse <= sig & ~prev;\n"
           "    end\n"
           "  end\n"
           "endmodule\n")
    sigs = [0, 0, 1, 1, 1, 0, 0]
    prev, pulses = 0, []
    for s in sigs:
        pulses.append(1 if (s and not prev) else 0)
        prev = s
    t1 = st("t_rising", [({"rst": 1, "sig": 0}, {"pulse": 0}),
                         ({"rst": 0, "sig": 0}, {"pulse": 0})] +
            [({"rst": 0, "sig": s}, {"pulse": p}) for s, p in zip(sigs, pulses)])
    # 复位后 prev=0，所以第一个 sig=1 本身就是上升沿（pulse=1）；
    # 随后的 1→0 下降沿不产生脉冲，0→1 再产生
    t2 = st("t_rising_falling", [({"rst": 1, "sig": 0}, {"pulse": 0}),
                                 ({"rst": 0, "sig": 1}, {"pulse": 1}),
                                 ({"rst": 0, "sig": 0}, {"pulse": 0}),
                                 ({"rst": 0, "sig": 0}, {"pulse": 0}),
                                 ({"rst": 0, "sig": 1}, {"pulse": 1}),
                                 ({"rst": 0, "sig": 1}, {"pulse": 0})])
    return P("spec50-seq-020", "sequential",
             "Design a rising-edge detector. pulse goes high for exactly one clock "
             "cycle after a 0-to-1 transition on sig.",
             hdr, ref, [t1, t2], "timing")


# ===========================================================================
# 状态机（10 题）
# ===========================================================================

def fsm_001_seqdet1101():
    hdr = ("module seqdet1101 (input clk, input rst, input din, output reg det);")
    ref = ("module seqdet1101 (input clk, input rst, input din, output reg det);\n"
           "  reg [1:0] state;\n"
           "  localparam S0 = 2'd0, S1 = 2'd1, S2 = 2'd2, S3 = 2'd3;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin state <= S0; det <= 1'b0; end\n"
           "    else begin\n"
           "      case (state)\n"
           "        S0: state <= din ? S1 : S0;\n"
           "        S1: state <= din ? S2 : S0;\n"
           "        S2: state <= din ? S2 : S3;\n"
           "        S3: state <= din ? S2 : S0;\n"
           "      endcase\n"
           "      det <= (state == S3) && din;\n"
           "    end\n"
           "  end\n"
           "endmodule\n")

    def sim(bits):
        state, out = 0, []
        for b in bits:
            out.append(1 if (state == 3 and b) else 0)
            if state == 0:
                state = 1 if b else 0
            elif state == 1:
                state = 2 if b else 0
            elif state == 2:
                state = 2 if b else 3
            else:
                state = 2 if b else 0
        return out

    def mk(bits):
        outs = sim(bits)
        return st("t", [({"rst": 1, "din": 0}, {"det": 0})] +
                  [({"rst": 0, "din": b}, {"det": d}) for b, d in zip(bits, outs)])

    t1 = mk([1, 1, 0, 1]); t1["name"] = "t_detect"
    t2 = mk([1, 1, 0, 1, 1, 0, 1]); t2["name"] = "t_overlap"
    t3 = mk([1, 0, 1, 0, 1, 0]); t3["name"] = "t_none"
    t4 = mk([1, 1, 0, 1, 0, 0, 1, 1, 0, 1]); t4["name"] = "t_multi"
    return P("spec50-fsm-001", "fsm",
             "Design a sequence detector for the pattern 1101 with OVERLAPPING "
             "matches. det pulses high for one cycle whenever the pattern "
             "completes. Overlapping: the input 1101101 contains the pattern "
             "twice (positions 1-4 and 4-7).",
             hdr, ref, [t1, t2, t3, t4], "seq_detector")


def fsm_002_seqdet1011():
    hdr = ("module seqdet1011 (input clk, input rst, input din, output reg det);")
    ref = ("module seqdet1011 (input clk, input rst, input din, output reg det);\n"
           "  reg [2:0] state;\n"
           "  localparam S0 = 3'd0, S1 = 3'd1, S2 = 3'd2, S3 = 3'd3, S4 = 3'd4;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin state <= S0; det <= 1'b0; end\n"
           "    else begin\n"
           "      det <= 1'b0;\n"
           "      case (state)\n"
           "        S0: state <= din ? S1 : S0;\n"
           "        S1: state <= din ? S1 : S2;\n"
           "        S2: state <= din ? S3 : S0;\n"
           "        S3: state <= din ? S4 : S0;\n"
           "        S4: begin state <= din ? S1 : S0; det <= 1'b1; end\n"
           "      endcase\n"
           "    end\n"
           "  end\n"
           "endmodule\n")

    def sim(bits):
        state, out = 0, []
        for b in bits:
            out.append(1 if state == 4 else 0)
            if state == 0:
                state = 1 if b else 0
            elif state == 1:
                state = 1 if b else 2
            elif state == 2:
                state = 3 if b else 0
            elif state == 3:
                state = 4 if b else 0
            else:
                state = 1 if b else 0
        return out

    def mk(bits):
        outs = sim(bits)
        return st("t", [({"rst": 1, "din": 0}, {"det": 0})] +
                  [({"rst": 0, "din": b}, {"det": d}) for b, d in zip(bits, outs)])

    t1 = mk([1, 0, 1, 1, 0]); t1["name"] = "t_detect_moore"
    t2 = mk([1, 0, 1, 1, 0, 1, 1, 0]); t2["name"] = "t_nonoverlap"
    t3 = mk([1, 0, 1, 0, 1, 1, 0]); t3["name"] = "t_recover"
    return P("spec50-fsm-002", "fsm",
             "Design a Moore state machine that detects the pattern 1011 with "
             "NON-OVERLAPPING matches. det pulses for exactly one cycle after the "
             "4th bit of a match completes, and a new match can only start after "
             "that. Moore style: det depends only on the state.",
             hdr, ref, [t1, t2, t3], "seq_detector")


def fsm_003_traffic_light():
    hdr = ("module traffic_light (input clk, input rst, output reg [5:0] lights);")
    ref = ("module traffic_light (input clk, input rst, output reg [5:0] lights);\n"
           "  reg [1:0] phase;\n"
           "  reg [2:0] t;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin phase <= 2'd0; t <= 3'd0; end\n"
           "    else case (phase)\n"
           "      2'd0: if (t == 3'd3) begin phase <= 2'd1; t <= 3'd0; end else t <= t + 3'd1;\n"
           "      2'd1: if (t == 3'd1) begin phase <= 2'd2; t <= 3'd0; end else t <= t + 3'd1;\n"
           "      2'd2: if (t == 3'd3) begin phase <= 2'd3; t <= 3'd0; end else t <= t + 3'd1;\n"
           "      default: if (t == 3'd1) begin phase <= 2'd0; t <= 3'd0; end else t <= t + 3'd1;\n"
           "    endcase\n"
           "  end\n"
           "  always @(*) case (phase)\n"
           "    2'd0: lights = 6'b001100;  // NS green, EW red\n"
           "    2'd1: lights = 6'b010100;  // NS yellow, EW red\n"
           "    2'd2: lights = 6'b100001;  // NS red, EW green\n"
           "    default: lights = 6'b100010; // NS red, EW yellow\n"
           "  endcase\n"
           "endmodule\n")
    LIGHT = {0: 0b001100, 1: 0b010100, 2: 0b100001, 3: 0b100010}
    phase, t, lights = 0, 0, LIGHT[0]
    seq = [lights]
    for _ in range(24):
        nxt = {0: (1, 0) if t == 3 else (0, t + 1),
               1: (2, 0) if t == 1 else (1, t + 1),
               2: (3, 0) if t == 3 else (2, t + 1),
               3: (0, 0) if t == 1 else (3, t + 1)}[phase]
        phase, t = nxt
        seq.append(LIGHT[phase])
    t1 = st("t_cycle", [({"rst": 1}, {"lights": seq[0]})] +
            [({"rst": 0}, {"lights": v}) for v in seq[1:25]])
    t2 = st("t_rst_mid", [({"rst": 1}, {"lights": 0b001100}),
                          ({"rst": 0}, {"lights": 0b001100}),
                          ({"rst": 0}, {"lights": 0b001100}),
                          ({"rst": 1}, {"lights": 0b001100}),
                          ({"rst": 0}, {"lights": 0b001100})])
    return P("spec50-fsm-003", "fsm",
             "Design a two-way traffic light controller. lights is encoded as "
             "{ns_red, ns_yellow, ns_green, ew_red, ew_yellow, ew_green}. The "
             "cycle is: NS green for 4 cycles, NS yellow for 2, EW green for 4, "
             "EW yellow for 2, then repeat. The cross direction shows red whenever "
             "the other direction is green or yellow.",
             hdr, ref, [t1, t2], "controller")


def fsm_004_vending():
    hdr = ("module vending (input clk, input rst, input [2:0] coin, input cancel, "
           "output reg dispense, output reg [2:0] change);")
    ref = ("module vending (input clk, input rst, input [2:0] coin, input cancel, "
           "output reg dispense, output reg [2:0] change);\n"
           "  reg [2:0] sum;\n"
           "  always @(posedge clk) begin\n"
           "    dispense <= 1'b0;\n"
           "    change <= 3'd0;\n"
           "    if (rst) sum <= 3'd0;\n"
           "    else if (cancel) begin change <= sum; sum <= 3'd0; end\n"
           "    else if (coin != 3'd0) begin\n"
           "      case (coin)\n"
           "        3'b001: if (sum + 3'd1 >= 3'd5) begin dispense <= 1'b1; change <= sum + 3'd1 - 3'd5; sum <= 3'd0; end\n"
           "                else sum <= sum + 3'd1;\n"
           "        3'b010: if (sum + 3'd2 >= 3'd5) begin dispense <= 1'b1; change <= sum + 3'd2 - 3'd5; sum <= 3'd0; end\n"
           "                else sum <= sum + 3'd2;\n"
           "        3'b100: if (sum + 3'd5 >= 3'd5) begin dispense <= 1'b1; change <= sum + 3'd5 - 3'd5; sum <= 3'd0; end\n"
           "                else sum <= sum + 3'd5;\n"
           "        default: ;\n"
           "      endcase\n"
           "    end\n"
           "  end\n"
           "endmodule\n")
    VAL = {1: 1, 2: 2, 4: 5}

    def sim(ops):
        """ops = [(coin(0/1/2/4), cancel)] → 每步后 (dispense, change)"""
        sumv, out = 0, []
        for coin, cancel in ops:
            disp, chg = 0, 0
            if cancel:
                chg = sumv
                sumv = 0
            elif coin in VAL:
                v = VAL[coin]
                if sumv + v >= 5:
                    disp, chg, sumv = 1, sumv + v - 5, 0
                else:
                    sumv += v
            out.append((disp, chg))
        return out

    def mk(ops):
        outs = sim(ops)
        return st("t", [({"rst": 1, "coin": 0, "cancel": 0}, {"dispense": 0, "change": 0})] +
                  [({"rst": 0, "coin": c, "cancel": x},
                    {"dispense": d, "change": ch}) for (c, x), (d, ch) in zip(ops, outs)])

    t1 = mk([(1, 0), (1, 0), (1, 0), (2, 0), (0, 0)]); t1["name"] = "t_exact"
    t2 = mk([(2, 0), (2, 0), (2, 0), (0, 0)]); t2["name"] = "t_change"
    t3 = mk([(1, 0), (1, 0), (0, 1), (0, 0)]); t3["name"] = "t_cancel"
    t4 = mk([(4, 0), (0, 0), (1, 0)]); t4["name"] = "t_coin5"
    return P("spec50-fsm-004", "fsm",
             "Design a vending machine controller. Items cost 5. The coin input "
             "accepts 3'b001 (value 1), 3'b010 (value 2) or 3'b100 (value 5). "
             "When the accumulated sum reaches 5, dispense pulses high for one "
             "cycle and change returns the excess. cancel returns the accumulated "
             "sum as change and resets it.",
             hdr, ref, [t1, t2, t3, t4], "controller")


def fsm_005_gray_counter4():
    hdr = ("module gray_counter4 (input clk, input rst, input en, "
           "output reg [3:0] gray);")
    ref = ("module gray_counter4 (input clk, input rst, input en, "
           "output reg [3:0] gray);\n"
           "  reg [3:0] bin;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin bin <= 4'd0; gray <= 4'd0; end\n"
           "    else if (en) begin\n"
           "      bin <= bin + 4'd1;\n"
           "      gray <= (bin + 4'd1) ^ ((bin + 4'd1) >> 1);\n"
           "    end\n"
           "  end\n"
           "endmodule\n")
    seq = []
    bin_v = 0
    for _ in range(17):
        bin_v = (bin_v + 1) & 0xF
        seq.append(bin_v ^ (bin_v >> 1))
    t1 = st("t_cycle", [({"rst": 1, "en": 0}, {"gray": 0}),
                        ({"rst": 0, "en": 0}, {"gray": 0})] +
            [({"rst": 0, "en": 1}, {"gray": g}) for g in seq])
    t2 = st("t_gate", [({"rst": 1, "en": 0}, {"gray": 0}),
                       ({"rst": 0, "en": 1}, {"gray": 1}),
                       ({"rst": 0, "en": 0}, {"gray": 1}),
                       ({"rst": 0, "en": 0}, {"gray": 1}),
                       ({"rst": 0, "en": 1}, {"gray": 3})])
    return P("spec50-fsm-005", "fsm",
             "Design a 4-bit Gray-code counter. The output gray counts in Gray "
             "code order (exactly one bit changes per step): 0, 1, 3, 2, 6, 7, 5, "
             "4, 12, 13, 15, 14, 10, 11, 9, 8, then wraps.",
             hdr, ref, [t1, t2], "counter")


def fsm_006_arbiter_rr():
    hdr = ("module arbiter_rr (input clk, input rst, input [3:0] req, "
           "output reg [3:0] grant);")
    ref = ("module arbiter_rr (input clk, input rst, input [3:0] req, "
           "output reg [3:0] grant);\n"
           "  reg [1:0] last;\n"
           "  reg [3:0] g;\n"
           "  reg [1:0] ln;\n"
           "  reg found;\n"
           "  integer i;\n"
           "  always @(*) begin\n"
           "    g = 4'd0; ln = last; found = 1'b0;\n"
           "    for (i = 0; i < 4; i = i + 1) begin\n"
           "      if (req[(last + 2'd1 + i) % 4] && !found) begin\n"
           "        g = 4'b1 << ((last + 2'd1 + i) % 4);\n"
           "        ln = (last + 2'd1 + i) % 4;\n"
           "        found = 1'b1;\n"
           "      end\n"
           "    end\n"
           "  end\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin grant <= 4'd0; last <= 2'd0; end\n"
           "    else begin\n"
           "      grant <= g;\n"
           "      if (found) last <= ln;\n"
           "    end\n"
           "  end\n"
           "endmodule\n")

    def sim(reqs):
        last, out = 0, []
        for req in reqs:
            g, ln, found = 0, last, False
            for i in range(4):
                idx = (last + 1 + i) % 4
                if ((req >> idx) & 1) and not found:
                    g = 1 << idx
                    ln = idx
                    found = True
            out.append(g)
            if found:
                last = ln
        return out

    def mk(reqs):
        outs = sim(reqs)
        return st("t", [({"rst": 1, "req": 0}, {"grant": 0})] +
                  [({"rst": 0, "req": r}, {"grant": g}) for r, g in zip(reqs, outs)])

    t1 = mk([0b1111, 0b1111, 0b1111, 0b1111]); t1["name"] = "t_rotate"
    t2 = mk([0b1010, 0b1010, 0b1010, 0b1010]); t2["name"] = "t_priority"
    t3 = mk([0, 0, 0b0110, 0b0110]); t3["name"] = "t_none_then"
    t4 = mk([0b0110, 0b0110, 0b0110, 0b0110]); t4["name"] = "t_interleave"
    return P("spec50-fsm-006", "fsm",
             "Design a 4-requestor round-robin arbiter. grant is a one-hot signal "
             "selecting one requesting bit. Priority rotates: each cycle the "
             "search starts from the position AFTER the last granted requestor, "
             "so no requestor starves. When no request is active, grant is 0 and "
             "priority is unchanged.",
             hdr, ref, [t1, t2, t3, t4], "arbiter")


def fsm_007_uart_tx():
    hdr = ("module uart_tx (input clk, input rst, input send, input [7:0] data, "
           "output reg tx, output reg busy);")
    ref = ("module uart_tx (input clk, input rst, input send, input [7:0] data, "
           "output reg tx, output reg busy);\n"
           "  reg active;\n"
           "  reg [3:0] bit_cnt;\n"
           "  reg [3:0] bit_idx;\n"
           "  reg [7:0] sr;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin tx <= 1'b1; busy <= 1'b0; active <= 1'b0; bit_cnt <= 4'd0; bit_idx <= 4'd0; sr <= 8'd0; end\n"
           "    else if (!active) begin\n"
           "      if (send) begin active <= 1'b1; busy <= 1'b1; sr <= data; bit_idx <= 4'd0; bit_cnt <= 4'd0; tx <= 1'b0; end\n"
           "      else begin tx <= 1'b1; busy <= 1'b0; end\n"
           "    end else begin\n"
           "      if (bit_cnt == 4'd15) begin\n"
           "        bit_cnt <= 4'd0;\n"
           "        if (bit_idx == 4'd9) begin active <= 1'b0; busy <= 1'b0; tx <= 1'b1; end\n"
           "        else begin\n"
           "          if (bit_idx == 4'd8) tx <= 1'b1;\n"
           "          else tx <= sr[bit_idx];\n"
           "          bit_idx <= bit_idx + 4'd1;\n"
           "        end\n"
           "      end else bit_cnt <= bit_cnt + 4'd1;\n"
           "    end\n"
           "  end\n"
           "endmodule\n")

    def sim(byte, send_cycles):
        """send_cycles[i]=1 表示第 i 拍 send=1。返回每拍后 (tx, busy)。"""
        active = bit_cnt = bit_idx = 0
        tx, busy, sr = 1, 0, 0
        out = []
        for send in send_cycles:
            if not active:
                if send:
                    active, busy, sr = 1, 1, byte
                    bit_idx, bit_cnt, tx = 0, 0, 0
                else:
                    tx, busy = 1, 0
            else:
                if bit_cnt == 15:
                    bit_cnt = 0
                    if bit_idx == 9:
                        active, busy, tx = 0, 0, 1
                    else:
                        old = bit_idx
                        bit_idx += 1
                        tx = 1 if old == 8 else (sr >> old) & 1
                else:
                    bit_cnt += 1
            out.append((tx, busy))
        return out

    def mk(byte, hold_send=False):
        n = 164
        sends = [1] + [1 if hold_send else 0] * (n - 1)
        outs = sim(byte, sends)
        t = st("t", [({"rst": 1, "send": 0, "data": 0}, {"tx": 1, "busy": 0}),
                     ({"rst": 0, "send": 0, "data": byte}, {"tx": 1, "busy": 0})] +
                [({"rst": 0, "send": s, "data": byte}, {"tx": x, "busy": b})
                 for s, (x, b) in zip(sends, outs)])
        # 只保留关键拍 + 结尾，避免测试文件过大：全部保留（每拍都检查）
        return t

    t1 = mk(0xA5); t1["name"] = "t_send_a5"
    t2 = mk(0x00, hold_send=True); t2["name"] = "t_hold_send_ignored"
    t3 = mk(0xFF); t3["name"] = "t_send_ff"
    return P("spec50-fsm-007", "fsm",
             "Design a simplified UART transmitter with 16 clock cycles per bit. "
             "Protocol: idle tx=1. On send, transmit one start bit (0) for 16 "
             "cycles, then 8 data bits LSB-first (16 cycles each), then one stop "
             "bit (1) for 16 cycles, then return to idle. busy is high during the "
             "whole frame; send is ignored while busy.",
             hdr, ref, [t1, t2, t3], "serial_io")


def fsm_008_uart_rx():
    hdr = ("module uart_rx (input clk, input rst, input rx, output reg [7:0] data, "
           "output reg valid, output reg frame_err);")
    ref = ("module uart_rx (input clk, input rst, input rx, output reg [7:0] data, "
           "output reg valid, output reg frame_err);\n"
           "  localparam IDLE = 2'd0, START = 2'd1, DATA = 2'd2, STOP = 2'd3;\n"
           "  reg [1:0] state;\n"
           "  reg [3:0] cnt;\n"
           "  reg [2:0] idx;\n"
           "  always @(posedge clk) begin\n"
           "    valid <= 1'b0;\n"
           "    frame_err <= 1'b0;\n"
           "    if (rst) begin state <= IDLE; cnt <= 4'd0; idx <= 3'd0; data <= 8'd0; end\n"
           "    else case (state)\n"
           "      IDLE: begin\n"
           "        if (!rx) begin state <= START; cnt <= 4'd0; end\n"
           "      end\n"
           "      START: begin\n"
           "        if (cnt == 4'd7) begin\n"
           "          if (!rx) begin state <= DATA; cnt <= 4'd0; idx <= 3'd0; end\n"
           "          else state <= IDLE;\n"
           "        end else cnt <= cnt + 4'd1;\n"
           "      end\n"
           "      DATA: begin\n"
           "        if (cnt == 4'd15) begin\n"
           "          cnt <= 4'd0;\n"
           "          if (idx == 3'd7) state <= STOP;\n"
           "          else idx <= idx + 3'd1;\n"
           "        end else if (cnt == 4'd8) begin data[idx] <= rx; cnt <= cnt + 4'd1; end\n"
           "        else cnt <= cnt + 4'd1;\n"
           "      end\n"
           "      STOP: begin\n"
           "        if (cnt == 4'd15) begin state <= IDLE; cnt <= 4'd0; valid <= 1'b1; end\n"
           "        else begin\n"
           "          if (cnt == 4'd8) frame_err <= ~rx;\n"
           "          cnt <= cnt + 4'd1;\n"
           "        end\n"
           "      end\n"
           "    endcase\n"
           "  end\n"
           "endmodule\n")

    def sim(rx_seq):
        state = cnt = idx = 0
        data, out = 0, []
        for rx in rx_seq:
            valid, frame_err = 0, 0
            if state == 0:  # IDLE
                if rx == 0:
                    state, cnt = 1, 0
            elif state == 1:  # START
                if cnt == 7:
                    if rx == 0:
                        state, cnt, idx = 2, 0, 0
                    else:
                        state = 0
                else:
                    cnt += 1
            elif state == 2:  # DATA
                if cnt == 15:
                    cnt = 0
                    if idx == 7:
                        state = 3
                    else:
                        idx += 1
                elif cnt == 8:
                    data = (data & ~(1 << idx)) | (rx << idx)
                    cnt += 1
                else:
                    cnt += 1
            else:  # STOP
                if cnt == 15:
                    state, cnt, valid = 0, 0, 1
                else:
                    if cnt == 8:
                        frame_err = 1 - rx
                    cnt += 1
            out.append((data, valid, frame_err))
        return out

    def waveform(byte, idle_pre=3, stop_high=True, idle_post=4):
        rx = [1] * idle_pre + [0] * 16
        for k in range(8):
            rx += [(byte >> k) & 1] * 16
        rx += ([1] if stop_high else [0]) * 16
        rx += [1] * idle_post
        return rx

    def mk(byte, stop_high=True, false_start=False):
        if false_start:
            rx = [1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1]
            expect_data = 0
        else:
            rx = waveform(byte, stop_high=stop_high)
            expect_data = byte
        outs = sim(rx)
        steps = [({"rst": 1, "rx": 1}, {"data": 0, "valid": 0, "frame_err": 0})]
        steps += [({"rst": 0, "rx": r}, {"data": d, "valid": v, "frame_err": f})
                  for r, (d, v, f) in zip(rx, outs)]
        return st("t", steps)

    t1 = mk(0xA5); t1["name"] = "t_rx_a5"
    t2 = mk(0x5A); t2["name"] = "t_rx_5a"
    t3 = mk(0x00, stop_high=False); t3["name"] = "t_bad_stop"
    t4 = mk(0, false_start=True); t4["name"] = "t_false_start"
    return P("spec50-fsm-008", "fsm",
             "Design a simplified UART receiver with 16x oversampling. After a "
             "falling edge on rx, verify the start bit at half-bit time (7 ticks) "
             "to reject glitches; then sample each data bit at its midpoint "
             "(8 ticks into each 16-cycle bit window), LSB first; finally check "
             "the stop bit. valid pulses for one cycle when a frame completes; "
             "frame_err flags a bad stop bit.",
             hdr, ref, [t1, t2, t3, t4], "serial_io")


def fsm_009_spi_master():
    hdr = ("module spi_master (input clk, input rst, input send, input [7:0] data, "
           "output reg sck, output reg mosi, output reg cs, output reg busy);")
    ref = ("module spi_master (input clk, input rst, input send, input [7:0] data, "
           "output reg sck, output reg mosi, output reg cs, output reg busy);\n"
           "  reg active;\n"
           "  reg [3:0] idx;\n"
           "  reg sub;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin cs <= 1'b1; sck <= 1'b0; mosi <= 1'b0; busy <= 1'b0; active <= 1'b0; idx <= 4'd0; sub <= 1'b0; end\n"
           "    else if (!active) begin\n"
           "      if (send) begin active <= 1'b1; busy <= 1'b1; cs <= 1'b0; idx <= 4'd0; sub <= 1'b0; mosi <= data[7]; end\n"
           "      else begin cs <= 1'b1; sck <= 1'b0; end\n"
           "    end else begin\n"
           "      if (sub == 1'b0) begin sub <= 1'b1; sck <= 1'b1; end\n"
           "      else begin\n"
           "        sub <= 1'b0; sck <= 1'b0;\n"
           "        if (idx == 4'd7) begin active <= 1'b0; busy <= 1'b0; cs <= 1'b1; end\n"
           "        else begin idx <= idx + 4'd1; mosi <= data[7 - (idx + 4'd1)]; end\n"
           "      end\n"
           "    end\n"
           "  end\n"
           "endmodule\n")

    def sim(byte):
        active = idx = sub = 0
        sck, mosi, cs, busy = 0, 0, 1, 0
        out = []
        for c in range(18):
            send = 1 if c == 0 else 0
            if not active:
                if send:
                    active, busy, cs = 1, 1, 0
                    idx, sub, mosi = 0, 0, (byte >> 7) & 1
                else:
                    cs, sck = 1, 0
            else:
                if sub == 0:
                    sub, sck = 1, 1
                else:
                    sub, sck = 0, 0
                    if idx == 7:
                        active, busy, cs = 0, 0, 1
                    else:
                        idx += 1
                        mosi = (byte >> (7 - idx)) & 1
            out.append((mosi, sck, cs, busy))
        return out

    def mk(byte):
        outs = sim(byte)
        return st("t", [({"rst": 1, "send": 0, "data": 0},
                         {"mosi": 0, "sck": 0, "cs": 1, "busy": 0}),
                        ({"rst": 0, "send": 0, "data": byte},
                         {"mosi": 0, "sck": 0, "cs": 1, "busy": 0}),
                        ({"rst": 0, "send": 1, "data": byte},
                         {"mosi": (byte >> 7) & 1, "sck": 0, "cs": 0, "busy": 1})] +
                [({"rst": 0, "send": 0, "data": byte},
                  {"mosi": m, "sck": s, "cs": c, "busy": b})
                 for c_, (m, s, c, b) in zip(range(3, 19), outs[1:])])

    t1 = mk(0xB2); t1["name"] = "t_send_b2"
    t2 = mk(0x00); t2["name"] = "t_send_00"
    t3 = mk(0xFF); t3["name"] = "t_send_ff"
    return P("spec50-fsm-009", "fsm",
             "Design a simplified SPI master (2 clock cycles per bit, MSB first, "
             "mode 0). Idle: cs=1, sck=0. On send: cs goes low, each bit is "
             "presented on mosi while sck is low and then sck pulses high for one "
             "cycle. After 8 bits cs returns high and busy deasserts.",
             hdr, ref, [t1, t2, t3], "serial_io")


def fsm_010_digital_lock():
    hdr = ("module digital_lock (input clk, input rst, input [3:0] digit, "
           "input enter, output reg unlocked, output reg err);")
    ref = ("module digital_lock (input clk, input rst, input [3:0] digit, "
           "input enter, output reg unlocked, output reg err);\n"
           "  reg [1:0] matched;\n"
           "  always @(posedge clk) begin\n"
           "    err <= 1'b0;\n"
           "    if (rst) begin matched <= 2'd0; unlocked <= 1'b0; end\n"
           "    else if (enter) begin\n"
           "      if (unlocked) begin end\n"
           "      else case (matched)\n"
           "        2'd0: if (digit == 4'd1) matched <= 2'd1; else begin err <= 1'b1; matched <= 2'd0; end\n"
           "        2'd1: if (digit == 4'd2) matched <= 2'd2; else begin err <= 1'b1; matched <= 2'd0; end\n"
           "        2'd2: if (digit == 4'd3) begin unlocked <= 1'b1; matched <= 2'd3; end\n"
           "              else begin err <= 1'b1; matched <= 2'd0; end\n"
           "        default: ;\n"
           "      endcase\n"
           "    end\n"
           "  end\n"
           "endmodule\n")

    def sim(ops):
        """ops = [(digit, enter)] → 每步后 (unlocked, err)"""
        matched, unlocked, out = 0, 0, []
        for digit, enter in ops:
            err = 0
            if enter and not unlocked:
                if matched == 0:
                    matched = 1 if digit == 1 else 0
                    err = 0 if digit == 1 else 1
                elif matched == 1:
                    matched = 2 if digit == 2 else 0
                    err = 0 if digit == 2 else 1
                elif matched == 2:
                    if digit == 3:
                        unlocked, matched = 1, 3
                    else:
                        err, matched = 1, 0
            out.append((unlocked, err))
        return out

    def mk(ops):
        outs = sim(ops)
        return st("t", [({"rst": 1, "digit": 0, "enter": 0}, {"unlocked": 0, "err": 0})] +
                  [({"rst": 0, "digit": d, "enter": e},
                    {"unlocked": u, "err": x}) for (d, e), (u, x) in zip(ops, outs)])

    t1 = mk([(1, 1), (2, 1), (3, 1), (0, 0), (9, 1), (0, 0)]); t1["name"] = "t_correct"
    t2 = mk([(9, 1), (1, 1), (2, 1), (3, 1)]); t2["name"] = "t_wrong_then_correct"
    t3 = mk([(1, 1), (2, 1), (9, 1), (3, 1), (1, 1), (2, 1), (3, 1)])
    t3["name"] = "t_partial_reset"
    t4 = mk([(1, 0), (0, 0), (1, 1), (2, 1), (3, 1)]); t4["name"] = "t_enter_gate"
    return P("spec50-fsm-010", "fsm",
             "Design a digital combination lock. The unlock code is 1-2-3: the "
             "user enters digits one at a time with the enter input. Entering a "
             "wrong digit at any step pulses err for one cycle and resets the "
             "progress. After 1, 2, 3 are entered in order, unlocked goes high "
             "and stays high until reset. Enter is ignored while unlocked.",
             hdr, ref, [t1, t2, t3, t4], "controller")


def fsm_011_seqdet1001():
    """重叠序列检测器 1001（2026-09-21 补，评估集扩展题）。"""
    hdr = ("module seqdet1001 (input clk, input rst, input din, output reg det);")
    ref = ("module seqdet1001 (input clk, input rst, input din, output reg det);\n"
           "  reg [1:0] state;\n"
           "  localparam S0 = 2'd0, S1 = 2'd1, S2 = 2'd2, S3 = 2'd3;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin state <= S0; det <= 1'b0; end\n"
           "    else begin\n"
           "      case (state)\n"
           "        S0: state <= din ? S1 : S0;\n"
           "        S1: state <= din ? S1 : S2;\n"
           "        S2: state <= din ? S1 : S3;\n"
           "        S3: state <= din ? S1 : S0;\n"
           "      endcase\n"
           "      det <= (state == S3) && din;\n"
           "    end\n"
           "  end\n"
           "endmodule\n")

    def sim(bits):
        state, out = 0, []
        for b in bits:
            out.append(1 if (state == 3 and b) else 0)
            if state == 0:
                state = 1 if b else 0
            elif state == 1:
                state = 1 if b else 2
            elif state == 2:
                state = 1 if b else 3
            else:
                state = 1 if b else 0
        return out

    def mk(bits):
        outs = sim(bits)
        return st("t", [({"rst": 1, "din": 0}, {"det": 0})] +
                  [({"rst": 0, "din": b}, {"det": d}) for b, d in zip(bits, outs)])

    t1 = mk([1, 0, 0, 1]); t1["name"] = "t_detect"
    t2 = mk([1, 0, 0, 1, 0, 0, 1]); t2["name"] = "t_overlap"
    t3 = mk([1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1]); t3["name"] = "t_multi"
    t4 = mk([1, 0, 1, 0, 0, 1, 1]); t4["name"] = "t_recover"
    return P("spec50-fsm-011", "fsm",
             "Design a sequence detector for the pattern 1001 with OVERLAPPING "
             "matches. det pulses high for one cycle whenever the pattern "
             "completes (e.g. the input 1001001 contains the pattern twice).",
             hdr, ref, [t1, t2, t3, t4], "seq_detector")


def fsm_012_garage_counter():
    """停车场计数器（饱和计数 + full/empty 标志，2026-09-21 补）。"""
    hdr = ("module garage_counter (input clk, input rst, input car_enter, "
           "input car_exit, output reg [3:0] count, output full, output empty);")
    ref = ("module garage_counter (input clk, input rst, input car_enter, "
           "input car_exit, output reg [3:0] count, output full, output empty);\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) count <= 4'd0;\n"
           "    else begin\n"
           "      if (car_enter & ~car_exit & (count < 4'd15)) count <= count + 4'd1;\n"
           "      else if (car_exit & ~car_enter & (count > 4'd0)) count <= count - 4'd1;\n"
           "    end\n"
           "  end\n"
           "  assign full = (count == 4'd15);\n"
           "  assign empty = (count == 4'd0);\n"
           "endmodule\n")

    def sim(ops):
        cnt, out = 0, []
        for enter, exit_ in ops:
            if enter and not exit_ and cnt < 15:
                cnt += 1
            elif exit_ and not enter and cnt > 0:
                cnt -= 1
            out.append((cnt, int(cnt == 15), int(cnt == 0)))
        return out

    def mk(ops):
        outs = sim(ops)
        return st("t", [({"rst": 1, "car_enter": 0, "car_exit": 0},
                         {"count": 0, "full": 0, "empty": 1})] +
                  [({"rst": 0, "car_enter": e, "car_exit": x},
                    {"count": c, "full": f, "empty": em})
                   for (e, x), (c, f, em) in zip(ops, outs)])

    t1 = mk([(1, 0), (1, 0), (1, 0), (0, 1), (0, 1), (0, 0)])
    t1["name"] = "t_basic"
    t2 = mk([(1, 0)] * 16 + [(1, 0), (1, 0), (0, 1)])
    t2["name"] = "t_saturate_top"
    t3 = mk([(0, 1), (0, 1), (0, 1), (1, 0), (1, 0)])
    t3["name"] = "t_saturate_bottom"
    t4 = mk([(1, 1), (1, 0), (1, 1), (0, 1), (1, 1)])
    t4["name"] = "t_simultaneous"
    return P("spec50-fsm-012", "fsm",
             "Design a parking garage occupancy counter. car_enter and car_exit "
             "are one-cycle pulses. count increments on enter and decrements on "
             "exit, SATURATING at 15 (full) and 0 (empty). If enter and exit "
             "pulse in the same cycle, count does not change.",
             hdr, ref, [t1, t2, t3, t4], "controller")


def fsm_013_handshake():
    """二相握手协议 FSM（req/ack + 完成脉冲，2026-09-21 补）。"""
    hdr = ("module handshake (input clk, input rst, input req, output reg ack, "
           "output reg pulse);")
    ref = ("module handshake (input clk, input rst, input req, output reg ack, "
           "output reg pulse);\n"
           "  reg state;\n"
           "  localparam IDLE = 1'b0, ACK_HIGH = 1'b1;\n"
           "  always @(posedge clk) begin\n"
           "    pulse <= 1'b0;\n"
           "    if (rst) begin state <= IDLE; ack <= 1'b0; end\n"
           "    else case (state)\n"
           "      IDLE: if (req) begin state <= ACK_HIGH; ack <= 1'b1; end\n"
           "      ACK_HIGH: if (!req) begin state <= IDLE; ack <= 1'b0; pulse <= 1'b1; end\n"
           "    endcase\n"
           "  end\n"
           "endmodule\n")

    def sim(reqs):
        state, ack, out = 0, 0, []
        for req in reqs:
            pulse = 0
            if state == 0:
                if req:
                    state, ack = 1, 1
            else:
                if not req:
                    state, ack, pulse = 0, 0, 1
            out.append((ack, pulse))
        return out

    def mk(reqs):
        outs = sim(reqs)
        return st("t", [({"rst": 1, "req": 0}, {"ack": 0, "pulse": 0})] +
                  [({"rst": 0, "req": r}, {"ack": a, "pulse": p})
                   for r, (a, p) in zip(reqs, outs)])

    t1 = mk([0, 1, 1, 1, 0, 0]); t1["name"] = "t_full_handshake"
    t2 = mk([1, 0, 0, 1, 1, 0]); t2["name"] = "t_short_req"
    t3 = mk([0, 0, 1, 0, 0]); t3["name"] = "t_single_cycle_req"
    t4 = mk([1, 1, 1, 1, 0, 1, 0]); t4["name"] = "t_two_transactions"
    return P("spec50-fsm-013", "fsm",
             "Design a two-phase handshake controller. When req is asserted, "
             "ack goes high on the next clock edge and stays high until req is "
             "deasserted. When the handshake completes (req falls while ack is "
             "high), ack falls and pulse goes high for exactly one cycle "
             "marking the end of the transaction.",
             hdr, ref, [t1, t2, t3, t4], "handshake")


def fsm_014_debouncer4():
    """按键消抖（4 拍稳定判定，2026-09-21 补）。"""
    hdr = ("module debouncer4 (input clk, input rst, input btn, "
           "output reg stable);")
    ref = ("module debouncer4 (input clk, input rst, input btn, "
           "output reg stable);\n"
           "  reg [1:0] cnt;\n"
           "  reg prev;\n"
           "  always @(posedge clk) begin\n"
           "    if (rst) begin cnt <= 2'd0; prev <= 1'b0; stable <= 1'b0; end\n"
           "    else begin\n"
           "      prev <= btn;\n"
           "      if (btn != prev) cnt <= 2'd0;\n"
           "      else if (cnt < 2'd3) cnt <= cnt + 2'd1;\n"
           "      // 非阻塞语义：此处读到的是更新前的 cnt——旧值 2 表示\n"
           "      // 本拍是第 4 个连续相同电平（首拍 + 3 拍重复）\n"
           "      if (btn == prev && cnt == 2'd2) stable <= btn;\n"
           "    end\n"
           "  end\n"
           "endmodule\n")

    def sim(btns):
        prev, cnt, stable, out = 0, 0, 0, []
        for btn in btns:
            if btn != prev:
                cnt = 0
            elif cnt < 3:
                cnt += 1
            if btn == prev and cnt == 3:
                stable = btn
            prev = btn
            out.append(stable)
        return out

    def mk(btns):
        outs = sim(btns)
        return st("t", [({"rst": 1, "btn": 0}, {"stable": 0})] +
                  [({"rst": 0, "btn": b}, {"stable": s})
                   for b, s in zip(btns, outs)])

    t1 = mk([0, 1, 1, 1, 1, 1, 1]); t1["name"] = "t_press"
    t2 = mk([0, 1, 1, 0, 0, 0, 0]); t2["name"] = "t_glitch_rejected"
    t3 = mk([0, 1, 1, 1, 1, 0, 0, 0, 0, 0]); t3["name"] = "t_release"
    t4 = mk([1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1]); t4["name"] = "t_bounce"
    return P("spec50-fsm-014", "fsm",
             "Design a button debouncer. The stable output only follows btn "
             "after btn has held the same level for 4 consecutive clock cycles. "
             "Shorter pulses (glitches/bounces) are filtered out.",
             hdr, ref, [t1, t2, t3, t4], "timing")


# ===========================================================================
# 汇总与入口
# ===========================================================================

PROBLEMS = [
    comb_001_adder4(), comb_002_adder8(), comb_003_sub8(), comb_004_cmp8(),
    comb_005_mux2(), comb_006_mux4(), comb_007_prio(), comb_008_decoder38(),
    comb_009_parity8(), comb_010_alu4(), comb_011_barrel8(), comb_012_gray_enc(),
    comb_013_gray_dec(), comb_014_bcd_add(), comb_015_popcount16(), comb_016_therm3(),
    comb_017_neg8(), comb_018_mul4(), comb_019_absdiff8(), comb_020_maj3(),
    seq_001_counter8(), seq_002_load_counter8(), seq_003_bcd_counter(),
    seq_004_updown8(), seq_005_lfsr4(), seq_006_shifter8(), seq_007_piso8(),
    seq_008_sipo8(), seq_009_acc8(), seq_010_ram16x8(), seq_011_fifo8x8(),
    seq_012_clkdiv10(), seq_013_pulse_stretch4(), seq_014_counter8_tc(),
    seq_015_ring4(), seq_016_johnson4(), seq_017_counter4_arst(),
    seq_018_counter4_cout(), seq_019_sat_counter4(), seq_020_edge_detect(),
    fsm_001_seqdet1101(), fsm_002_seqdet1011(), fsm_003_traffic_light(),
    fsm_004_vending(), fsm_005_gray_counter4(), fsm_006_arbiter_rr(),
    fsm_007_uart_tx(), fsm_008_uart_rx(), fsm_009_spi_master(),
    fsm_010_digital_lock(),
    fsm_011_seqdet1001(), fsm_012_garage_counter(), fsm_013_handshake(),
    fsm_014_debouncer4(),
]


def generate(out_path):
    problems = []
    seen = set()
    for p in PROBLEMS:
        if p["task_id"] in seen:
            raise SystemExit(f"task_id 重复: {p['task_id']}")
        seen.add(p["task_id"])
        errs = rtl_common.validate_problem(p, "generated")
        if errs:
            raise SystemExit("生成的数据未通过校验:\n" + "\n".join(errs))
        problems.append(p)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for p in problems:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    n_eval = sum(1 for p in problems if p["split"] == "eval")
    tiers = {}
    for p in problems:
        tiers[p["tier"]] = tiers.get(p["tier"], 0) + 1
    print(f"已生成 {len(problems)} 题 → {out_path}")
    print(f"分档: {tiers} | eval 集 {n_eval} 题")
    print("提示: 在 Linux 上运行 --verify 用双闸自检参考实现（必须先全绿）")


def verify(path, workers=4):
    problems = rtl_common.load_problems(path)
    missing = rtl_common.check_tools()
    if missing:
        raise SystemExit("缺少工具: " + ", ".join(missing) +
                         "\n安装: sudo apt install -y yosys verilator build-essential")
    from concurrent.futures import ThreadPoolExecutor
    fails = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(rtl_common.evaluate_module, p["module"], p): p
                for p in problems}
        for fut, p in futs.items():
            r = fut.result()
            status = "PASS" if r["overall"] else "FAIL"
            print(f"[{status}] {p['task_id']:20s} {p['tier']:14s} "
                  f"tests {r['n_pass']}/{r['n_total']}"
                  + ("" if r["overall"] else f"  reason={r['reason'][:120]}"))
            if not r["overall"]:
                fails.append((p["task_id"], r))
    if fails:
        print(f"\n❌ {len(fails)} 题参考实现未通过自己的双闸 —— 数据集本身有 bug，"
              f"禁止开训。把本输出粘回给 AI 修复。")
        for tid, r in fails[:5]:
            print(f"\n--- {tid} ---\nsynth_log tail:\n{r['synth_log'][-400:]}")
            if r["sim_log"]:
                print(f"sim_log tail:\n{r['sim_log'][-400:]}")
        return 1
    print(f"\n✅ {len(problems)} 题参考实现全部通过双闸自检（综合 + 仿真）。可以开训。")
    return 0


def main():
    ap = argparse.ArgumentParser(description="自建 50 题 RTL spec 集")
    ap.add_argument("--out", default=OUT_DEFAULT, help="输出 jsonl 路径")
    ap.add_argument("--verify", action="store_true",
                    help="对参考实现跑双闸自检（需要 yosys/verilator，Linux）")
    ap.add_argument("--problems", default=None, help="--verify 时指定要验证的 jsonl")
    ap.add_argument("--workers", type=int, default=4, help="--verify 并行度")
    args = ap.parse_args()
    if args.verify:
        sys.exit(verify(args.problems or args.out, args.workers))
    generate(args.out)


if __name__ == "__main__":
    main()
