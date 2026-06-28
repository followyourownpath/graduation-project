# 前端页面交互与逻辑设计文档 (Frontend Page Logic)

本文档基于业务需求及视觉设计稿，详细说明 AI 驱动的房贷合规评分系统 (Mortgage Scoring Engine) 的页面流转、状态管理以及前端组件选型规划。

## 1. 技术规范与 UI 组件库
- **基础框架**: Next.js App Router
- **样式引擎**: Tailwind CSS
- **UI 组件底层**: **Radix UI Primitives**（无样式、高可访问性的底层组件）
- **UI 封装**: 推荐基于 Radix UI 构建的 [shadcn/ui](https://ui.shadcn.com/) 方案，用于快速搭建企业级界面（如 Dialog, Select, Accordion, Tabs 等）。
- **图标**: Lucide React
- **状态管理**: Zustand（轻量级跨组件状态共享）或 React Context。

## 2. 核心路由设计
项目已搭建并包含以下核心路由 (基于 Next.js App Router):

- `/login` : 登录页面 (静态验证或 JWT Token 获取)
- `/dashboard` : 审查控制台主页 (概览数据、紧急待办)
- `/applications` : 申请列表管理页 (全量案卷查看、发起入口)
- `/applications/new` : 创建新的房贷申请，包含文件批量拖拽上传
- `/application/[id]` : 申请详情与审查校验页面 (分屏视图)

---

## 3. 页面逻辑与组件结构

### 3.1. 登录页 (`/login`)
- **UI 结构**: 
  - 左侧：品牌 Logo、产品愿景文案及抽象几何背景。
  - 右侧：登录表单卡片。
- **Radix UI 组件**: `Form`, `Label`, `Checkbox` (用于 Remember Me), `Button`.
- **交互逻辑**:
  1. 用户输入邮箱与密码，前端进行基础校验（非空、邮箱格式）。
  2. 点击登录触发 API 请求，处于 `isLoading` 状态时按钮显示加载动画。
  3. 成功：获取 JWT 并存入 HTTP-only Cookie 或 LocalStorage，跳转 `/dashboard`。
  4. 失败：展示错误提示 (Toast 提示)。

### 3.2. 控制台大盘页 (`/dashboard`)
- **UI 结构**:
  - 顶部/侧边导航栏 (Navigation Menu)。
  - 顶部数据统计卡片组。
  - 下方近期紧急申请数据表格。
- **Radix UI 组件**: `NavigationMenu`, `DropdownMenu` (用户头像菜单), `Card` (概览统计)。
- **交互逻辑**:
  1. 页面展示系统整体运行健康度和最需要人工干预的“高风险/待处理”清单。

### 3.3. 申请列表管理页 (`/applications`)
- **UI 结构**:
  - 顶部操作栏：包含标题以及醒目的主按钮 `+ New Application`。
  - 数据表格及过滤器。
- **Radix UI 组件**: `Select` (表格过滤), `Table`, `Badge` (风险标签)。
- **交互逻辑**:
  1. 表格支持按“状态”、“风险等级”、“贷款类型”进行过滤，触发状态变化并重新拉取数据。
  2. 风险评分动态变色：高风险(Red), 中等(Amber), 低风险(Green)。
  3. 点击 `+ New Application` 路由跳转至 `/applications/new`。
  4. 点击列表某行的 "Review" 按钮，携带对应的 application ID 路由跳转至 `/application/[id]`。

### 3.4. 新建申请与上传页 (`/applications/new`)
- **UI 结构**:
  - 顶部：申请人基础信息录入表单。
  - 中部：巨大的虚线框 Drag & Drop 拖拽上传区域。
  - 下部：已选择的文件队列及进度条展示区。
  - 底部：提交按钮。
- **交互逻辑**:
  1. **拖拽响应**：用户拖拽文件进入区域时，边框高亮。
  2. **上传动画**：前端拦截文件列表，并渲染到下方队列中。当前端触发上传时，动态增加各文件的进度条（百分比增加），上传中状态呈现蓝色 loading，完成后变为绿色对号。
  3. **完成提交**：只有当所有文件上传状态均为 completed 后，“Submit Application” 按钮才可点击，点击后跳转回 `/applications`。

### 3.5. 申请详情与审查页 (`/application/[id]`)
- **UI 结构 (双视窗布局)**:
  - 顶部条：申请人摘要、返回控制台按钮、整体申请状态。
  - 左半区：原始文件查看器 (PDF/图片渲染)。
  - 右半区：OCR 提取数据表单 + 跨文件校验预警面板。
- **Radix UI 组件**: `ScrollArea` (处理双边独立滚动), `Tabs` (切换不同文件如工资单、身份证), `Accordion` (折叠展示预警信息), `Dialog` (确认审批或拒绝弹窗), `Popover` (字段级别的不一致提示)。
- **交互逻辑**:
  1. **数据拉取**: 并行请求原始文件 URL 以及该文件对应的 OCR 提取结构化数据 (JSON) 和整体风控告警信息。
  2. **文件切换**: 左侧切换查看不同文件时，右侧的数据表单及预警列表同步切换到对应的上下文。
  3. **数据修正**: 审查员发现 OCR 提取有误时，可直接在右侧表单对应输入框进行手动覆盖修改。修改后字段标记为 `Edited` 状态。
  4. **预警处理**: 跨文件不一致性（如：工资单收入与银行流水不匹配）将在右侧面板以红色/黄色块醒目展示，审查员可点击 `Mark Resolved` 忽略或 `Add Note` 增加备注。
  5. **最终决策**: 点击底部的 "Approve" 或 "Reject" 会唤起 `Dialog` 弹窗，要求审查员二次确认并输入决断理由，最后提交给 Backend 完成业务流转。

## 4. API 交互与异常处理
- 对于涉及文件上传和 OCR 耗时较长的接口，前端需妥善处理进度条展示及长轮询 (Long-polling) 或 WebSocket 推送状态。
- 所有的错误（如 OCR 失败、文件损坏）需捕获并使用 Radix UI 的 `Toast` 统一反馈给用户。
