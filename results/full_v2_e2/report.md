# RTL 双闸评估报告

- 题目数: 98 | completion 数: 98

| 指标 | 值 |
|---|---|
| **pass@1（双闸全过）** | **0.3265** |
| 综合通过率 | 0.9388 |
| 仿真通过率 | 0.3265 |
| 仿真通过率（综合过者中） | 0.3478 |
| 格式达标率（<answer> 内解析出 module） | 0.9898 |

## 分档

| 档位 | 题数 | pass@1 | 综合率 | 仿真率 |
|---|---|---|---|---|
| combinational | 66 | 0.2879 | 0.9394 | 0.2879 |
| sequential | 32 | 0.4062 | 0.9375 | 0.4062 |

## 失败原因分布

| 原因 | 次数 |
|---|---|
| verilator_compile_error(cand) | 30 |
| synth_fail | 5 |
| gold_oracle_mismatch test=0 step=0 ports=['q'] | 5 |
| gold_oracle_mismatch test=1 step=0 ports=['out'] | 2 |
| gold_oracle_mismatch test=0 step=0 ports=['out'] | 2 |
| gold_oracle_mismatch test=2 step=0 ports=['out'] | 2 |
| gold_oracle_mismatch test=0 step=0 ports=['z'] | 2 |
| gold_oracle_mismatch test=0 step=1 ports=['z'] | 2 |
| gold_oracle_mismatch test=0 step=1 ports=['anyedge'] | 1 |
| gold_oracle_mismatch test=0 step=2 ports=['pedge'] | 1 |
| gold_oracle_mismatch test=0 step=15 ports=['Q'] | 1 |
| gold_oracle_mismatch test=0 step=2 ports=['Q'] | 1 |
| gold_oracle_mismatch test=0 step=1 ports=['out'] | 1 |
| gold_oracle_mismatch test=1 step=0 ports=['f'] | 1 |
| gold_oracle_mismatch test=0 step=12 ports=['q'] | 1 |
| gold_oracle_mismatch test=0 step=8 ports=['Z'] | 1 |
| gold_oracle_mismatch test=0 step=0 ports=['mux_in'] | 1 |
| gold_oracle_mismatch test=2 step=0 ports=['q'] | 1 |
| gold_oracle_mismatch test=3 step=0 ports=['q'] | 1 |
| gold_oracle_mismatch test=0 step=4 ports=['Q'] | 1 |
| gold_oracle_mismatch test=3 step=0 ports=['pos'] | 1 |
| gold_oracle_mismatch test=3 step=0 ports=['out'] | 1 |
| no_module_extracted | 1 |
| gold_oracle_mismatch test=0 step=0 ports=['g'] | 1 |

## 逐题明细

| task_id | tier | 综合 | 仿真 | 双闸 | 失败原因 |
|---|---|---|---|---|---|
| verilogeval-v2-Prob001 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob002 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob003 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob004 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob005 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob006 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=1 step=0 ports=['out'] |
| verilogeval-v2-Prob007 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob009 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob010 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob011 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob012 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['out'] |
| verilogeval-v2-Prob014 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob015 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob016 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob020 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob022 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob024 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob025 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob026 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob027 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob031 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob032 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob033 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob034 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob035 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob036 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob037 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob038 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob039 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob040 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob041 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob042 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob043 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob044 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob045 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=1 ports=['anyedge'] |
| verilogeval-v2-Prob046 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob047 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob050 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=2 step=0 ports=['out'] |
| verilogeval-v2-Prob051 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob054 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=2 ports=['pedge'] |
| verilogeval-v2-Prob056 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=15 ports=['Q'] |
| verilogeval-v2-Prob057 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['out'] |
| verilogeval-v2-Prob058 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob059 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob060 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob061 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=2 ports=['Q'] |
| verilogeval-v2-Prob062 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=2 step=0 ports=['out'] |
| verilogeval-v2-Prob063 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob064 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob065 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob066 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=1 ports=['out'] |
| verilogeval-v2-Prob067 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob069 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=1 step=0 ports=['f'] |
| verilogeval-v2-Prob070 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob071 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob072 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob073 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=12 ports=['q'] |
| verilogeval-v2-Prob074 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['z'] |
| verilogeval-v2-Prob076 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob077 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob078 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob079 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob081 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob083 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['z'] |
| verilogeval-v2-Prob084 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=8 ports=['Z'] |
| verilogeval-v2-Prob085 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob087 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob088 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=1 ports=['z'] |
| verilogeval-v2-Prob089 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=1 ports=['z'] |
| verilogeval-v2-Prob090 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob091 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob093 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['mux_in'] |
| verilogeval-v2-Prob094 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob098 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob099 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob101 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=2 step=0 ports=['q'] |
| verilogeval-v2-Prob102 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=3 step=0 ports=['q'] |
| verilogeval-v2-Prob103 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob104 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=4 ports=['Q'] |
| verilogeval-v2-Prob106 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob112 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=3 step=0 ports=['pos'] |
| verilogeval-v2-Prob114 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob115 | sequential | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob117 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob122 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=1 step=0 ports=['out'] |
| verilogeval-v2-Prob123 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob125 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=3 step=0 ports=['out'] |
| verilogeval-v2-Prob126 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob130 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob131 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob132 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob140 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob141 | sequential | ✗ | ✗ | ✗ | no_module_extracted |
| verilogeval-v2-Prob143 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob145 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob147 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob148 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['g'] |
| verilogeval-v2-Prob150 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
