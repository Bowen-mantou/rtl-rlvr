# RTL 双闸评估报告

- 题目数: 152 | completion 数: 152

| 指标 | 值 |
|---|---|
| **pass@1（双闸全过）** | **0.5724** |
| 综合通过率 | 0.9868 |
| 仿真通过率 | 0.5724 |
| 仿真通过率（综合过者中） | 0.5800 |
| 格式达标率（<answer> 内解析出 module） | 1.0000 |

## 分档

| 档位 | 题数 | pass@1 | 综合率 | 仿真率 |
|---|---|---|---|---|
| combinational | 86 | 0.5116 | 0.9884 | 0.5116 |
| sequential | 52 | 0.7885 | 0.9808 | 0.7885 |
| fsm | 14 | 0.1429 | 1.0000 | 0.1429 |

## 失败原因分布

| 原因 | 次数 |
|---|---|
| verilator_compile_error(cand) | 32 |
| gold_oracle_mismatch test=0 step=0 ports=['out'] | 3 |
| synth_fail | 2 |
| FAIL t=0 step=4 port=det expect=1 got=0 | 2 |
| gold_oracle_mismatch test=2 step=0 ports=['out'] | 2 |
| FAIL t=0 step=3 port=cout expect=0 got=1 | 1 |
| FAIL t=0 step=17 port=cout expect=0 got=1 | 1 |
| FAIL t=0 step=2 port=stretched expect=1 got=0 | 1 |
| FAIL t=0 step=0 port=lights expect=12 got=0 | 1 |
| FAIL t=0 step=4 port=dispense expect=1 got=0 | 1 |
| verilator_compile_error | 1 |
| FAIL t=0 step=0 port=busy expect=0 got=1 | 1 |
| sim_runtime_error | 1 |
| FAIL t=0 step=2 port=mosi expect=1 got=0 | 1 |
| FAIL t=0 step=1 port=err expect=0 got=1 | 1 |
| FAIL t=3 step=3 port=count expect=1 got=0 | 1 |
| FAIL t=0 step=5 port=ack expect=0 got=1 | 1 |
| FAIL t=0 step=4 port=stable expect=0 got=1 | 1 |
| gold_oracle_mismatch test=0 step=0 ports=['anyedge'] | 1 |
| gold_oracle_mismatch test=0 step=0 ports=['q'] | 1 |
| gold_oracle_mismatch test=0 step=1 ports=['out'] | 1 |
| gold_oracle_mismatch test=3 step=0 ports=['f'] | 1 |
| gold_oracle_mismatch test=0 step=13 ports=['z'] | 1 |
| gold_oracle_mismatch test=0 step=1 ports=['z'] | 1 |
| gold_oracle_mismatch test=0 step=0 ports=['mux_in'] | 1 |
| gold_oracle_mismatch test=1 step=0 ports=['q'] | 1 |
| gold_oracle_mismatch test=3 step=0 ports=['q'] | 1 |
| gold_oracle_mismatch test=0 step=1 ports=['q'] | 1 |
| gold_oracle_mismatch test=0 step=0 ports=['z'] | 1 |

## 逐题明细

| task_id | tier | 综合 | 仿真 | 双闸 | 失败原因 |
|---|---|---|---|---|---|
| spec50-comb-001 | combinational | ✓ | ✗ | ✗ | FAIL t=0 step=3 port=cout expect=0 got=1 |
| spec50-comb-002 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-003 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-004 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-005 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-006 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-007 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-008 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-009 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-010 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-011 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-012 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-013 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-014 | combinational | ✓ | ✗ | ✗ | FAIL t=0 step=17 port=cout expect=0 got=1 |
| spec50-comb-015 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-016 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-017 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-018 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-019 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-020 | combinational | ✓ | ✓ | ✓ |  |
| spec50-fsm-001 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=4 port=det expect=1 got=0 |
| spec50-fsm-002 | fsm | ✓ | ✓ | ✓ |  |
| spec50-fsm-003 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=0 port=lights expect=12 got=0 |
| spec50-fsm-004 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=4 port=dispense expect=1 got=0 |
| spec50-fsm-005 | fsm | ✓ | ✓ | ✓ |  |
| spec50-fsm-006 | fsm | ✓ | ✗ | ✗ | verilator_compile_error |
| spec50-fsm-007 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=0 port=busy expect=0 got=1 |
| spec50-fsm-008 | fsm | ✓ | ✗ | ✗ | sim_runtime_error |
| spec50-fsm-009 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=2 port=mosi expect=1 got=0 |
| spec50-fsm-010 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=1 port=err expect=0 got=1 |
| spec50-fsm-011 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=4 port=det expect=1 got=0 |
| spec50-fsm-012 | fsm | ✓ | ✗ | ✗ | FAIL t=3 step=3 port=count expect=1 got=0 |
| spec50-fsm-013 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=5 port=ack expect=0 got=1 |
| spec50-fsm-014 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=4 port=stable expect=0 got=1 |
| spec50-seq-001 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-002 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-003 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-004 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-005 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-006 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-007 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-008 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-009 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-010 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-011 | sequential | ✗ | ✗ | ✗ | synth_fail |
| spec50-seq-012 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-013 | sequential | ✓ | ✗ | ✗ | FAIL t=0 step=2 port=stretched expect=1 got=0 |
| spec50-seq-014 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-015 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-016 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-017 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-018 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-019 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-020 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob001 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob002 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob003 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob004 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob005 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob006 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['out'] |
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
| verilogeval-v2-Prob045 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['anyedge'] |
| verilogeval-v2-Prob046 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['q'] |
| verilogeval-v2-Prob047 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob050 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob051 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob054 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob056 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob057 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['out'] |
| verilogeval-v2-Prob058 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob059 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob060 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob061 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob062 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=2 step=0 ports=['out'] |
| verilogeval-v2-Prob063 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob064 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob065 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob066 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=1 ports=['out'] |
| verilogeval-v2-Prob067 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob069 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=3 step=0 ports=['f'] |
| verilogeval-v2-Prob070 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob071 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob072 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob073 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob074 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob076 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob077 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob078 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob079 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob081 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob083 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob084 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob085 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob087 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob088 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=13 ports=['z'] |
| verilogeval-v2-Prob089 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=1 ports=['z'] |
| verilogeval-v2-Prob090 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob091 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob093 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['mux_in'] |
| verilogeval-v2-Prob094 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob098 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob099 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob101 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=1 step=0 ports=['q'] |
| verilogeval-v2-Prob102 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=3 step=0 ports=['q'] |
| verilogeval-v2-Prob103 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob104 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob106 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob112 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob114 | combinational | ✗ | ✗ | ✗ | synth_fail |
| verilogeval-v2-Prob115 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob117 | sequential | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=1 ports=['q'] |
| verilogeval-v2-Prob122 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob123 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob125 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=2 step=0 ports=['out'] |
| verilogeval-v2-Prob126 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob130 | combinational | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob131 | combinational | ✓ | ✗ | ✗ | gold_oracle_mismatch test=0 step=0 ports=['z'] |
| verilogeval-v2-Prob132 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob140 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob141 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob143 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob145 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob147 | sequential | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
| verilogeval-v2-Prob148 | sequential | ✓ | ✓ | ✓ |  |
| verilogeval-v2-Prob150 | combinational | ✓ | ✗ | ✗ | verilator_compile_error(cand) |
