# RTL 双闸评估报告

- 题目数: 46 | completion 数: 46

| 指标 | 值 |
|---|---|
| **pass@1（双闸全过）** | **0.6304** |
| 综合通过率 | 0.9783 |
| 仿真通过率 | 0.6304 |
| 仿真通过率（综合过者中） | 0.6444 |
| 格式达标率（<answer> 内解析出 module） | 1.0000 |

## 分档

| 档位 | 题数 | pass@1 | 综合率 | 仿真率 |
|---|---|---|---|---|
| combinational | 32 | 0.5938 | 1.0000 | 0.5938 |
| sequential | 12 | 0.7500 | 0.9167 | 0.7500 |
| fsm | 2 | 0.5000 | 1.0000 | 0.5000 |

## 失败原因分布

| 原因 | 次数 |
|---|---|
| verilator_compile_error(cand) | 9 |
| gold_oracle_mismatch test=0 step=0 ports=['out'] | 2 |
| FAIL t=0 step=3 port=cout expect=0 got=1 | 1 |
| FAIL t=0 step=19 port=sum expect=0 got=10 | 1 |
| synth_fail | 1 |
| FAIL t=0 step=2 port=stretched expect=1 got=0 | 1 |
| FAIL t=0 step=0 port=lights expect=12 got=0 | 1 |
| gold_oracle_mismatch test=0 step=0 ports=['anyedge'] | 1 |

## 逐题明细

| task_id | tier | 综合 | 仿真 | 双闸 | 失败原因 |
|---|---|---|---|---|---|
| spec50-comb-001 | combinational | ✓ | ✗ | ✗ | FAIL t=0 step=3 port=cout expect=0 got=1 |
| spec50-comb-010 | combinational | ✓ | ✓ | ✓ |  |
| spec50-comb-014 | combinational | ✓ | ✗ | ✗ | FAIL t=0 step=19 port=sum expect=0 got=10 |
| spec50-comb-019 | combinational | ✓ | ✓ | ✓ |  |
| spec50-fsm-001 | fsm | ✓ | ✓ | ✓ |  |
| spec50-fsm-003 | fsm | ✓ | ✗ | ✗ | FAIL t=0 step=0 port=lights expect=12 got=0 |
| spec50-seq-001 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-004 | sequential | ✓ | ✓ | ✓ |  |
| spec50-seq-011 | sequential | ✗ | ✗ | ✗ | synth_fail |
| spec50-seq-013 | sequential | ✓ | ✗ | ✗ | FAIL t=0 step=2 port=stretched expect=1 got=0 |
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
| verilogeval-v2-Prob046 | combinational | ✓ | ✓ | ✓ |  |
