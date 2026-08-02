# 交叉比对规则字段核对反馈（Fact Find / ID / NOA）

> 日期：2026-07-31  
> 核对人：Jiawen（负责 Fact Find Sheet、ID、NOA 的 OCR / 字段抽取）  
> 对照文件：`SmartFINN文件字段交叉比对规则.xlsx`  
> 目的：按群内要求，核对自己负责部分的字段是否与规则表匹配；**不匹配项今天提出**，确认后再分工开发进系统。

---

## 1. 结论摘要

| 模块 | 与规则表对齐情况 | 是否可支撑相关规则 |
|------|------------------|--------------------|
| **ID（`id_100` / NSW 驾照）** | 字段键与表中 `ID.*` **完全一致** | ✅ 可支撑 FF-ID / ID-ID / ID-NOA |
| **NOA（`ato_notice`）** | 字段键与表中 `NOA.*` **完全一致** | ✅ 可支撑 FF-NOA / NOA-NOA / PS-NOA / BS-NOA / ID-NOA |
| **Fact Find** | **语义字段大多具备**，但存在 **命名约定、地址形态、DOB 缺失** 等问题 | ⚠️ 需先定映射 / 拼装规则后再开发比对引擎 |

**总体：** ID、NOA 侧无需因缺字段改 OCR；Fact Find 侧需与规则表作者对齐 4～5 个问题后再进入比对开发。

---

## 2. ID（驾照）核对

### 2.1 实现字段（9）

| 实际 `field_key` | 规则表 `ID.*` | 状态 |
|------------------|---------------|------|
| `document_type` | `ID.document_type` | ✅ |
| `jurisdiction` | `ID.jurisdiction` | ✅ |
| `full_legal_name` | `ID.full_legal_name` | ✅ |
| `residential_address` | `ID.residential_address` | ✅（整行地址） |
| `licence_number` | `ID.licence_number` | ✅ |
| `licence_class` | `ID.licence_class` | ✅ |
| `date_of_birth` | `ID.date_of_birth` | ✅ |
| `card_number` | `ID.card_number` | ✅ |
| `expiry_date` | `ID.expiry_date` | ✅ |

缺失 / 多余字段：**无**。

### 2.2 相关规则覆盖

| 规则 ID | 依赖字段 | 我们侧是否具备 |
|---------|----------|----------------|
| FF-ID-001 | `ID.full_legal_name` | ✅ |
| FF-ID-002 | `ID.residential_address` | ✅ |
| FF-ID-003 | `ID.expiry_date` | ✅（对端 ApplicationDate 见 §4） |
| FF-ID-004 | `ID.date_of_birth` | ✅（对端 FactFind DOB 见 §4） |
| ID-ID-005/006 | 多本证件姓名 / DOB 互比 | ✅ 字段具备；需运行时多文档实例 |
| ID-ID-007 | type/jurisdiction/licence/card + 登记 | ✅ 字段具备；登记服务属系统能力 |
| ID-ID-008 | expiry + file metadata / forensic | ⚠️ 字段有 expiry；**文件元数据 / 取证不在 OCR 字段层** |
| ID-NOA-011/012 | 姓名 / 地址 vs NOA | ✅ |

### 2.3 ID 侧需提出的点

1. **ID-ID-008**：规则依赖 `file_metadata` / forensic，当前 OCR 不产出；建议明确由存储/取证服务提供，或规则默认「无法取证 → 人工复核」（表中已倾向此语义，请确认写入实现说明）。  
2. 规则表前缀写作 `ID.xxx`，库内为扁平 `field_key`（无 `ID.` 前缀）——比对层需统一加命名空间或建映射表（见 §5）。

---

## 3. NOA 核对

### 3.1 实现字段（24，与表一致）

身份 / 期间：`taxpayer_name`, `taxpayer_address`, `tfn`, `ato_reference`, `year_ended`, `income_year`, `date_of_issue`  

税额组件：`taxable_income`, `tax_on_taxable_income`, `low_income_tax_offset`, `non_refundable_tax_offsets`, `assessed_tax_payable`, `medicare_levy`, `other_liabilities`, `tax_offset_refunds`, `payg_withholding_credits`, `payg_credits_and_entitlements`  

结果 / 退款：`result_of_notice_amount` + `result_of_notice_direction`, `outcome_amount` + `outcome_direction`, `refund_amount`, `refund_status`, `refund_reference`

缺失 / 多余：**无**。空抵免行会 **仍入库且值为 `null`**（符合表「空值语义」中 OCR 空 ≠ 真实零）。

### 3.2 相关规则

| 规则 ID | 状态 |
|---------|------|
| FF-NOA-001/002 | ✅ NOA 侧字段具备 |
| NOA-NOA-003～006 | ✅ 金额/方向/期间字段具备；`null` 不得当 0（我们已区分） |
| PS-NOA-007～009 | ✅ NOA 侧具备；工资单侧由 payslip 同学保障 YTD / period |
| BS-NOA-010 | ✅ NOA 退款字段具备；银行流水侧由 bank 同学保障 |
| ID-NOA-011/012 | ✅ |

### 3.3 NOA 侧需提出的点

1. **TFN**：表要求加密/仅格式与重复检查、跨文件不展示——产品/比对层需按敏感信息处理（OCR 已抽出 `tfn`）。  
2. 同样存在 `NOA.xxx` 逻辑名 vs 扁平 `field_key` 的命名空间问题（§5）。

---

## 4. Fact Find 核对（重点）

### 4.1 语义覆盖（相对「字段映射」Sheet）

| 规则表逻辑字段 | 我们实际 `field_key`（示例） | 状态 |
|----------------|------------------------------|------|
| `FactFind.Applicant.FullName` | `applicant_1_full_name` / `applicant_2_full_name`（另有 `cover_customer_name`） | ⚠️ **有字段，命名不同** |
| `FactFind.Applicant.CurrentAddress` | `applicant_*_current_address_{street,suburb,state,postcode,...}` | ⚠️ **有组件，无整段地址** |
| `FactFind.Applicant.PreviousAddress[]` | `applicant_*_previous_address_{1,2}_*` | ⚠️ 同上，拆字段 |
| `FactFind.Applicant.DateOfBirth` | — | ❌ **未抽取** |
| `FactFind.ApplicationDate` | 最接近：`cover_form_date` | ⚠️ **需确认是否等同** |
| `FactFind.Employment.EmployerName` | `applicant_*_current_employment_employer_name` 等 | ⚠️ 有，命名不同 |
| `FactFind.Employment.Type` | `…_employment_basis` | ⚠️ 有，键名是 basis 非 type |
| `FactFind.Employment.Position` | `…_position` | ⚠️ 有，命名不同 |
| `FactFind.Employment.StartDate/EndDate` | `…_start_date` / `…_end_date` | ⚠️ 有，命名不同 |
| `FactFind.Employment.EmployerAddress` | `…_employer_address_line1/line2` | ⚠️ 拆行，非单字段 |
| `FactFind.PreferredRepayment.AccountName/BSB/AccountNumber` | `repayment_account_name` / `_bsb` / `_number` | ⚠️ 有，命名不同 |
| `FactFind.Assets.SavingsTermDeposit.Value` | `savings_term_deposit_{1,2}_value` | ⚠️ 有，命名不同 |
| `FactFind.Liability[]` | `liability_*`（多类型多属性） | ⚠️ 有，结构更细 |
| `FactFind.MonthlyExpenditure[]` | `expense_*_monthly_amount` | ⚠️ 有，命名不同 |
| 申请人归属 | `applicant_number` = 1 / 2（部分 cover 字段为 null） | ⚠️ 基本具备；cover 级字段需规则约定 |

Fact Find 当前映射约 **264** 个 `field_key`，业务覆盖面足够，**主要矛盾是「逻辑名 / 形态」而非「完全没数据」**。

### 4.2 必须今天确认的问题（建议 Xiangyu 改表或我们补约定）

#### P0 — 必须拍板

1. **逻辑名 ↔ 实际 key 映射表**  
   规则写 `FactFind.Applicant.FullName`，实现是 `applicant_1_full_name`。  
   **建议：** 规则表增加一列「实现 field_key」，或单独维护映射 JSON；否则比对开发无法直接落地。

2. **地址：整段 vs 拆分**  
   - Fact Find：street / suburb / state / postcode  
   - ID / NOA：单行 `residential_address` / `taxpayer_address`  
   **建议：** 比对前由引擎将 FF 组件拼成标准化地址再比；或规定 ID/NOA 也拆地址（成本高，不推荐）。请确认采用「拼装后再 `address_norm`」。

3. **`DateOfBirth` 缺失**  
   规则 `FF-ID-004` 依赖 FactFind DOB。表中写 “if captured”。  
   **建议：** 明确标为 **不适用（N/A）**，直到 Fact Find 表单采集并抽取 DOB；不要因此判失败。

4. **`ApplicationDate` 定义**  
   `FF-ID-003` / `NOA-NOA-004` 等用申请日期。  
   **建议确认三选一：**  
   - A. `cover_form_date`（表单封面日期）  
   - B. 系统 `application.created_at`  
   - C. 另增字段  

#### P1 — 建议写清

5. **Employment.Type vs `employment_basis`**  
   枚举是否同一套（Full Time / Part Time / Casual…）？需要 `employment_type_map` 与我们 basis 枚举对齐。

6. **Liability / Expenditure 细粒度**  
   我们是扁平多 key（如 `liability_credit_card_1_creditor`），表是对象数组语义。  
   **建议：** 比对层按类型聚合，不要要求 OCR 改成嵌套 JSON。

7. **`FF-ALL-013` 申请人归属**  
   个人文档（工资单 / NOA / 驾照）不得串申请人。我们有 `applicant_number`，但上传文档与 applicant 的绑定是否在 intake 已强制？请产品/后端约定：`source_document` 是否必须带 `applicant_number`。

---

## 5. 命名空间建议（给规则作者 / 比对开发）

| 规则表写法 | 建议映射到实现 |
|------------|----------------|
| `ID.full_legal_name` | `document_type=id_100` → `field_key=full_legal_name` |
| `NOA.taxpayer_name` | `document_type=ato_notice` → `field_key=taxpayer_name` |
| `FactFind.Applicant.FullName`（申请人 1） | `field_key=applicant_1_full_name` |
| `FactFind.Applicant.CurrentAddress` | 拼接 `applicant_1_current_address_street` + suburb + state + postcode |
| `FactFind.ApplicationDate` | **待确认** → 暂建议 `cover_form_date` 或 `application.created_at` |
| `FactFind.PreferredRepayment.BSB` | `repayment_account_bsb` |

---

## 6. 跨组依赖（非我主责，但影响我侧规则）

以下字段在规则里出现，**不在我负责的 OCR 产出中**，需对应同学确认（避免联调时误以为是 FF/ID/NOA 缺字段）：

| 规则依赖 | 现状（据当前代码粗查） | 负责方 |
|----------|------------------------|--------|
| `BankStatement.customer_address` | 银行抽取 **未见** `customer_address` | 银行账单 |
| `BankStatement.total_credits/total_debits` | 映射里有 total credits；需确认稳定产出 | 银行账单 |
| `Payslip.employer_address` | 工资单 **未见** employer_address | 工资单 |
| `Payslip.ytd_*` | 有 YTD 抽取逻辑 | 工资单 |
| 字段级 `confidence` ≥ 0.85（ALL-ALL-014） | ID/NOA/FactFind 抽取行 **未写真实 OCR confidence**；Review API 有时用启发式占位 | 需统一：比对用 Azure confidence 还是放宽门控 |

---

## 7. 与「标准化规则 / 参数配置」的符合性

| 项 | 我们现状 | 说明 |
|----|----------|------|
| 日期 → `YYYY-MM-DD` | ✅ ID/NOA/FF 已用 `australian_date` | 与表一致 |
| 金额去 `$`/逗号 | ✅ `money()` | 与表一致 |
| 标识符去空格 | ✅ 驾照号/卡号/TFN/BSB 等 | 与表一致；BSB 模糊匹配表禁止——我们比对层需精确比 |
| 金额与 CR/DR 分开 | ✅ NOA 已拆 `*_amount` / `*_direction` | 与表一致 |
| OCR 空 ≠ 0 | ✅ NOA 空抵免为 `null` | 与表一致 |
| 姓名标准化（去称谓等） | ⚠️ OCR 保留 raw/normalised 原文；**深度 name_norm 应在比对层做** | 勿要求 OCR 删称谓后不可逆 |

---

## 8. 建议的群内反馈口径（可直接发）

> 已完成 Fact Find / ID / NOA 与《交叉比对规则》字段核对：  
> 1）**ID、NOA 字段与表一致，可支撑相关规则。**  
> 2）**Fact Find 业务字段基本都有**，但需要确认：  
> - 逻辑名（`FactFind.Applicant.*`）↔ 实际 key（如 `applicant_1_full_name`）映射表；  
> - 地址：FF 拆字段 vs ID/NOA 整行，是否比对前拼装；  
> - Fact Find **无 DOB**，`FF-ID-004` 是否标不适用；  
> - `ApplicationDate` 用 `cover_form_date` 还是系统创建时间。  
> 3）另：比对层所需的 `confidence` / 银行地址 / 工资单雇主地址属跨组项，请对应同学一并确认。  
> 以上定稿后即可按规则分工开发进系统。

---

## 9. 附录：我侧规则清单（便于分工）

**以我侧字段为端点的规则（开发比对时可认领 / 联调）：**

- 身份：`FF-ID-001`～`004`，`ID-ID-005`～`008`，`ID-NOA-011`～`012`  
- 税务：`FF-NOA-001`～`002`，`NOA-NOA-003`～`006`  
- 跨文件（我侧一端）：`PS-NOA-007`～`009`，`BS-NOA-010`  
- 总控：`FF-ALL-013`，`ALL-ALL-014`  

**Fact Find 作为来源、对端是银行/工资单的规则**（`FF-BS-*`、`FF-PS-*`）：我侧提供 Fact Find 字段即可，比对逻辑与银行/工资单同学共同联调。

---

## 10. 参考实现位置

| 类型 | 代码 |
|------|------|
| Fact Find | `backend/app/normalization/fact_find.py` / `fact_find_ocr.py` / `fact_find_mapping.json` |
| ID | `backend/app/normalization/id_100.py` |
| NOA | `backend/app/normalization/ato_notice.py` |
| 字段说明（组内） | `9900/ID_NOA_Field_Reference.md` |

分支：`feature/ocr-id-licence-ato-notice`（ID/NOA）；Fact Find 已在 `main` 相关合并中。
