# ID / NOA 字段说明（组员参考）

> Updated: 30 July 2026  
> 范围：本次交付的两个 OCR 类型 **`id_100`**（NSW 驾照）与 **`ato_notice`**（ATO Notice of Assessment）  
> 分支：`feature/ocr-id-licence-ato-notice`  
> 写法对齐现有 payslip / bank statement 字段表习惯（field_key / 含义 / 类型 / 标准化）

前端对接细节见：[`ID_NOA_Frontend_Handoff.md`](./ID_NOA_Frontend_Handoff.md)。

---

## 0. 与已有文档类型的关系（对照）

组里已有类似字段表，例如：

**Bank statement（`bank_statement_3m`）概要类：**  
`account_holder_name`, `bsb`, `account_number`, `statement_period`, `statement_period_start/end`, `opening_balance`, `closing_balance`, `total_credits`, `total_debits`  

**Bank statement 流水类（动态 N）：**  
`transaction_{N}_date` / `_description` / `_debit` / `_credit` / `_balance`

**Payslip（`payslip`）：**  
雇主周期：`employer_name`, `employer_abn`, `pay_date`, `pay_period_start/end`  
员工账户：`employee_name`, `job_title`, `employment_type`, `super_fund`, `super_member_id`, `bank_account`  
本期金额：`gross_income`, `tax_withheld`, `superannuation`, `net_income`  
YTD：`ytd_gross_income`, `ytd_tax_withheld`, `ytd_superannuation`, `ytd_net_income`  
金额标准化示例：`$8,735.25` → `8735.25`

下面两节是 **本次新增/重写** 的类型，入库表仍是 `extracted_field`，形态与上表一致。

---

## 1. `id_100` — NSW Driver Licence（9 个字段）

`document_type` 上传值：`id_100`  
`section_name`：`id_100`  
技术路线：Azure `prebuilt-layout` → `backend/app/normalization/id_100.py`  
说明：旧护照键值表 / `driver_licence_link*` **已删除**，请只使用下表。

### 1.1 字段表

| field_key | field_label | data_type | 说明 / 示例 | 标准化 |
|-----------|-------------|-----------|-------------|--------|
| `document_type` | Document Type | `text` | 证件类型 | 如 `Driver Licence` |
| `jurisdiction` | Jurisdiction | `text` | 签发州 / 辖区 | 如 `New South Wales, Australia` |
| `full_legal_name` | Full Legal Name | `text` | 姓名 | 空白压缩；映射 applicant.full_name |
| `residential_address` | Residential Address | `text` | 住址（**整行，不拆** street/suburb） | 如 `150 TODMAN AVE, KENSINGTON NSW 2033` |
| `licence_number` | Licence Number | `identifier` | Licence No. | 去空白数字，如 `11208313` |
| `licence_class` | Licence Class | `text` | 驾照类别 | 如 `C`（大写） |
| `date_of_birth` | Date of Birth | `date` | 出生日期 | `08 JAN 1992` → `1992-01-08` |
| `card_number` | Card Number | `identifier` | 卡号 | `2 042 604 436` → `2042604436` |
| `expiry_date` | Expiry Date | `date` | 有效期 | `12 DEC 2023` → `2023-12-12` |

### 1.2 样例核对（真实 Azure E2E）

| field_key | normalised_value |
|-----------|------------------|
| `document_type` | `Driver Licence` |
| `jurisdiction` | `New South Wales, Australia` |
| `full_legal_name` | `Junhong ZHONG` |
| `residential_address` | `150 TODMAN AVE, KENSINGTON NSW 2033` |
| `licence_number` | `11208313` |
| `licence_class` | `C` |
| `date_of_birth` | `1992-01-08` |
| `card_number` | `2042604436` |
| `expiry_date` | `2023-12-12` |

找不到的字段：**不会写入**该行（与 payslip 缺字段行为类似）。

---

## 2. `ato_notice` — Notice of Assessment（24 个字段）

`document_type` 上传值：`ato_notice`（前端文案多为 ATO Notice of Assessment）  
`section_name`：`ato_notice`  
技术路线：Azure `prebuilt-layout` → `backend/app/normalization/ato_notice.py`  

**重要：** 这 24 个 key **每次 OCR 都会入库**。样例中无单独金额的行，`raw_value` / `normalised_value` 为 **`null`**（方便前端固定表单占位）。

### 2.1 身份与概要

| field_key | field_label | data_type | 说明 / 示例 | 标准化 |
|-----------|-------------|-----------|-------------|--------|
| `taxpayer_name` | Taxpayer Name | `text` | 纳税人姓名 | 如 `MR DAVID R THOMPSON` |
| `taxpayer_address` | Taxpayer Address | `text` | 住址（整行） | 如 `45 WATTLE CRESCENT, PARRAMATTA NSW 2150` |
| `tfn` | Tax File Number | `identifier` | 税号（敏感） | `748 219 356` → `748219356` |
| `ato_reference` | ATO Reference | `identifier` | Our reference | 去空格数字 |
| `year_ended` | Year Ended | `date` | 财年截止日原文对应日期 | `30 June 2022` → `2022-06-30` |
| `income_year` | Income Year | `text` | 收入年度 | 由 year ended 推导，如 `2021–2022` |
| `date_of_issue` | Date of Issue | `date` | 签发日期 | `3 October 2022` → `2022-10-03` |

### 2.2 应税与抵免 / 负债金额

| field_key | field_label | data_type | 说明 / 示例 | 标准化 |
|-----------|-------------|-----------|-------------|--------|
| `taxable_income` | Taxable Income | `money` | 应税收入 | `85,321` → `85321.00` |
| `tax_on_taxable_income` | Tax on Taxable Income | `money` | 应税收入产生的税款 | `18742.15` |
| `low_income_tax_offset` | Low Income Tax Offset | `money` | 低收入税收抵免 | 样例常为 **`null`** |
| `non_refundable_tax_offsets` | Total Non-refundable Tax Offsets | `money` | 不可退还抵免合计 | 样例常为 **`null`** |
| `assessed_tax_payable` | Assessed Tax Payable | `money` | 评定应缴税款 | 可从 `$18,742.15 DR` 抽出金额 |
| `medicare_levy` | Medicare Levy | `money` | Medicare Levy | `1706.42` |
| `other_liabilities` | Total Other Liabilities | `money` | 其他负债合计 | 样例常为 **`null`** |
| `tax_offset_refunds` | Tax Offset Refunds | `money` | 税收抵免退款 | 可为 `0.00` |
| `payg_withholding_credits` | PAYG Withholding Credits | `money` | PAYG 预扣税抵免 | `21500.00` |
| `payg_credits_and_entitlements` | Total PAYG and Other Entitlements | `money` | PAYG 及其他权益合计 | 样例常为 **`null`** |

金额标准化与 payslip 相同：去掉 `$` 与千分位，保留两位小数字符串。

### 2.3 结果 / 退款（金额与方向拆分）

| field_key | field_label | data_type | 说明 / 示例 | 标准化 |
|-----------|-------------|-----------|-------------|--------|
| `result_of_notice_amount` | Result of This Notice Amount | `money` | 本通知结果金额 | `1051.43` |
| `result_of_notice_direction` | Result of This Notice Direction | `enum` | 方向 | `CR` 或 `DR` |
| `outcome_amount` | Outcome Amount | `money` | 最终结果金额 | 常与 result 相同 |
| `outcome_direction` | Outcome Direction | `enum` | 最终方向 | `CR` / `DR` |
| `refund_amount` | Refund Amount | `money` | 退款金额 | 退税场景下常等于 outcome |
| `refund_status` | Refund Status | `text` | 退款状态文案 | 如 forwarded to nominated financial institution |
| `refund_reference` | Refund Reference | `identifier` | 交易参考号 | 如 `ATO0007744921038562` |

`CR` = Credit（通常为退税）；`DR` = Debit（通常为欠税）。

### 2.4 样例核对（真实 Azure E2E，节选）

| field_key | normalised_value |
|-----------|------------------|
| `taxpayer_name` | `MR DAVID R THOMPSON` |
| `taxable_income` | `85321.00` |
| `result_of_notice_amount` | `1051.43` |
| `result_of_notice_direction` | `CR` |
| `refund_reference` | `ATO0007744921038562` |
| `low_income_tax_offset` | `null` |
| `non_refundable_tax_offsets` | `null` |
| `other_liabilities` | `null` |
| `payg_credits_and_entitlements` | `null` |

---

## 3. 实现位置速查

| 类型 | Mapper | Pipeline 条件 |
|------|--------|----------------|
| `id_100` | `normalization/id_100.py` → `extract_id_fields` | `document_type == "id_100"` |
| `ato_notice` | `normalization/ato_notice.py` → `extract_ato_notice_fields` | `document_type == "ato_notice"` |

测试：`backend/tests/test_normalization.py`  
离线 golden（仓库外）：`9900/1/ocr_id_noa_offline/expected/`

---

## 4. 给前端的注意点（简）

1. `id_100` 换键名后不要再绑旧 passport 字段。  
2. `ato_notice` 按 24 键固定渲染；`null` = 空槽，不是接口失败。  
3. Review API 的展示值目前在响应字段 `raw_value` 上（内部已优先用 normalised）。  
4. TFN 按敏感信息处理。
