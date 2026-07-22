# GitHub CI 使用说明（给组员）

我们仓库已经配置了 GitHub Actions 自动检查，并保护了 `main` 分支。  
**请不要直接 push 到 `main`**，一律走 Pull Request（PR）。

---

## 1. 现在有哪些检查？

每次你开 PR（或往 PR 推新 commit）时，GitHub 会自动跑：

| Actions 里显示的名字 | 保护规则里的名字 | 检查什么 |
|---------------------|------------------|----------|
| Conflict Check | `check-conflict` | 是否和 `main` 有合并冲突；代码里是否还留着 `<<<<<<<` 等冲突标记 |
| Frontend CI | `build` | 前端能否安装依赖、通过 lint、成功 build |
| Backend CI | `check` | 后端依赖能否安装、Python 语法是否正常 |

三个都绿才能合并进 `main`（仓库已开启 Branch protection）。

工作流文件位置：

```text
.github/workflows/
  conflict-check.yml
  frontend.yml
  backend.yml
```

---

## 2. 日常开发正确流程

```bash
# 1) 更新本地 main
git checkout main
git pull origin main

# 2) 从最新 main 开自己的功能分支（名字自定）
git checkout -b feature/你的功能名

# 3) 正常改代码、提交
git add .
git commit -m "feat: 简短说明你做了什么"
git push -u origin feature/你的功能名
```

然后去 GitHub：

1. 打开仓库页面，点 **Compare & pull request**（或 Pull requests → New）
2. **base** 选 `main`，**compare** 选你的分支
3. 创建 PR，等 Actions 跑完（约 1～2 分钟）
4. 全绿后，点 **Merge pull request**

---

## 3. 在哪里看检查结果？

- **PR 页面底部**：会显示 checks 是否通过  
- 或点仓库顶栏 **Actions**：看每次运行的详情和日志  

绿勾 = 通过；红叉 = 失败（点进去看红色报错）。

---

## 4. 失败了怎么办？

### Conflict Check 红了
说明你的分支和 `main` 冲突了。在本地：

```bash
git checkout 你的分支
git fetch origin
git merge origin/main
# 在编辑器里解决冲突后：
git add .
git commit -m "chore: resolve merge conflicts with main"
git push
```

解决后**不要留下**冲突标记（Git 自动插入的那种三行标记）。
在编辑器里搜索：连续 7 个小于号、7 个等号、或 7 个大于号（即 conflict marker），确认文件里已经没有它们。

### Frontend CI 红了
多半是 lint 或 build 失败。本地复现：

```bash
cd frontend
npm ci
npm run lint
npm run build
```

修好再 `commit` + `push`，PR 会自动重跑。

### Backend CI 红了
本地复现：

```bash
cd backend
pip install -r requirements.txt
python -m compileall .
```

修好再推送。

---

## 5. 组员注意事项

1. **永远不要** `git push origin main`（会被拦 / 不符合规范）
2. 提交前先 `git pull origin main`，减少冲突
3. 前端改动请保证本地 `npm run lint` 和 `npm run build` 能过
4. 不要把 `.env`、密钥、大模型权重推进仓库
5. 一个 PR 尽量只做一件事，方便 review 和定位 CI 失败原因

---

## 6. 和 Dependabot 的关系

Actions 里可能还有 **Dependency Graph**（Dependabot）自动跑的任务，那是依赖扫描，**不是你们要管的 CI**。组员日常只关心上面三个检查即可。

---

有问题可以看 PR 的 Actions 日志，或问配置 CI 的同学。
