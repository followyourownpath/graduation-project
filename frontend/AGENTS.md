<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# 👨‍💻 User Preferences & Reusable Instructions (Auto-generated from conversation)

## 1. 技术栈偏好 (Tech Stack Preferences)
- **前端框架**：如无特殊要求，默认采用 `React` + `Next.js (App Router)`。
- **UI/样式**：全面拥抱 `Tailwind CSS`。组件库偏好轻量、高可定制性的 `Radix UI` 配合 `shadcn/ui` 进行搭建，拒绝老旧臃肿组件库。
- **视觉标准**：要求极高。产出的页面必须具备现代化 SaaS 质感，色彩应用符合直觉（如风控审查场景中的红/黄/绿警示牌），拒绝简陋的原生 HTML 拼凑。

## 2. 协作与开发流程 (Collaboration Workflow)
- **设计前置**：在开发重要的全新功能页前，习惯让 AI 先通过工具 (`generate_image`) 生成 UI 视觉概念图，并在文档中写好开发计划 (`implementation_plan.md`)，确认无误后再动工。
- **文档语言**：倾向于使用**中文**阅读和维护项目核心架构文档（如：页面逻辑文档、功能进度报告）。
- **文档同步**：完成开发后，要求必须同步更新 `docs/` 目录下的相关文档，保持代码与设计文档100%一致。

## 3. 需求分析与 Git 习惯 (Requirements & Git Habits)
- **严格需求对齐**：规划新功能时，必须从项目的原始文档（Word、PDF、会议纪要等）中提取确切要求。对于在会议纪要中明确被标记为 **Out of Scope** 的功能（例如本次 MVP 中的 Audit Log 和复杂 RBAC 权限），不要过度设计和脑补。
- **整洁的 Git 记录**：在合并 PR 前，必须清理项目中多余的历史无用文件，保持干净的项目骨架。习惯在达成阶段性 Milestone（如完成 3 个核心页面）后，立即执行 `git commit` 与 `push` 操作。
