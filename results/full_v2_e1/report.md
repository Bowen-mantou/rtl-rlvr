# RTL 双闸评估报告

- 题目数: 98 | completion 数: 98

| 指标 | 值 |
|---|---|
| **pass@1（双闸全过）** | **0.2041** |
| 综合通过率 | 0.7857 |
| 仿真通过率 | 0.2041 |
| 仿真通过率（综合过者中） | 0.2597 |
| 格式达标率（<answer> 内解析出 module） | 0.9694 |

## 分档

| 档位 | 题数 | pass@1 | 综合率 | 仿真率 |
|---|---|---|---|---|
| combinational | 66 | 0.1364 | 0.8030 | 0.1364 |
| sequential | 32 | 0.3438 | 0.7500 | 0.3438 |

## 失败原因分布

| 原因 | 次数 |
|---|---|
| verilator_compile_error(cand) | 38 |
| synth_fail | 19 |
| gold_oracle_mismatch test=0 step=0 ports=['q'] | 6 |
| gold_oracle_mismatch test=1 step=0 ports=['out'] | 3 |
| gold_oracle_mismatch test=0 step=0 ports=['out'] | 2 |
| no_module_extracted | 2 |
| gold_oracle_mismatch test=2 step=0 ports=['out'] | 1 |
| gold_oracle_mismatch test=49 step=0 ports=['sum'] | 1 |
| gold_oracle_mismatch test=128 step=0 ports=['out'] | 1 |
| gold_oracle_mismatch test=0 step=3 ports=['Q'] | 1 |
| gold_oracle_mismatch test=0 step=3 ports=['q'] | 1 |
| gold_oracle_mismatch test=0 step=12 ports=['Z'] | 1 |
| gold_oracle_mismatch test=3 step=0 ports=['q'] | 1 |
| gold_oracle_mismatch test=0 step=7 ports=['q'] | 1 |

## 逐题明细

| task_id | tier | 综合 | 仿真 | 双闸 | 失败原因 |
|---|---|---|---|---|---|
| verilogeval-v2-Prob001 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob002 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob003 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob004 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob005 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob006 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob007 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob009 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=2 step=0 ports=['out'] |
| verilogeval-v2-Prob010 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob011 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob012 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob014 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob015 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob016 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=49 step=0 ports=['sum'] |
| verilogeval-v2-Prob020 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob022 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob024 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob025 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob026 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob027 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob031 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob032 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob033 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob034 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob035 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob036 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob037 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob038 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob039 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob040 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob041 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob042 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=128 step=0 ports=['out'] |
| verilogeval-v2-Prob043 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob044 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob045 | sequential | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob046 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob047 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob050 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=1 step=0 ports=['out'] |
| verilogeval-v2-Prob051 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob054 | sequential | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob056 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob057 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['out'] |
| verilogeval-v2-Prob058 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob059 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob060 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob061 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=3 ports=['Q'] |
| verilogeval-v2-Prob062 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['out'] |
| verilogeval-v2-Prob063 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=3 ports=['q'] |
| verilogeval-v2-Prob064 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob065 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob066 | sequential | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob067 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob069 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob070 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob071 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob072 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob073 | sequential | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob074 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob076 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob077 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob078 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob079 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob081 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob083 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob084 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=12 ports=['Z'] |
| verilogeval-v2-Prob085 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob087 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob088 | sequential | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob089 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob090 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob091 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob093 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob094 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob098 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob099 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob101 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob102 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=3 step=0 ports=['q'] |
| verilogeval-v2-Prob103 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob104 | sequential | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob106 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob112 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob114 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob115 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=7 ports=['q'] |
| verilogeval-v2-Prob117 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob122 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=1 step=0 ports=['out'] |
| verilogeval-v2-Prob123 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob125 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=1 step=0 ports=['out'] |
| verilogeval-v2-Prob126 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob130 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob131 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob132 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob140 | sequential | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob141 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob143 | combinational | ✗ | ✗ | ✗ | no_module_extracted |
| verilogeval-v2-Prob145 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob147 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob148 | sequential | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob150 | combinational | ✗ | ✗ | ✗ | no_module_extracted |
