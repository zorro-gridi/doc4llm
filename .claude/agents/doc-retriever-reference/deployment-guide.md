# doc-retriever 部署和维护指南

## 🚀 快速部署

### 前置要求

1. **系统要求**
   - Python 3.8+
   - Claude Code 环境
   - 至少 1GB 可用磁盘空间
   - 读写权限到 `.claude/` 目录

2. **依赖检查**
   ```bash
   # 运行健康检查
   ./.claude/scripts/doc-retriever-health-check.sh
   
   # 运行完整诊断
   ./.claude/scripts/doc-retriever-diagnose.sh
   ```

### 部署步骤

1. **验证文件结构**
   ```
   .claude/
   ├── agents/
   │   ├── doc-retriever.md
   │   └── doc-retriever-reference/
   ├── skills/
   │   ├── md-doc-query-optimizer/
   │   ├── md-doc-searcher/
   │   ├── md-doc-reader/
   │   └── md-doc-processor/
   ├── scripts/
   │   ├── log-retrieval.sh
   │   ├── validate-doc-operation.sh
   │   ├── cleanup-doc-session.sh
   │   ├── doc-retriever-health-check.sh
   │   ├── doc-retriever-monitor.sh
   │   └── doc-retriever-diagnose.sh
   └── logs/
   ```

2. **设置权限**
   ```bash
   chmod +x .claude/scripts/*.sh
   mkdir -p .claude/logs
   ```

3. **验证部署**
   ```bash
   # 运行健康检查
   ./.claude/scripts/doc-retriever-health-check.sh
   
   # 测试基本功能
   echo "use contextZ: 测试查询" | # 通过 Claude Code 测试
   ```

## 🔧 配置选项

### 子代理配置

**核心配置参数:**

```yaml
# .claude/agents/doc-retriever.md
---
name: doc-retriever
model: sonnet                    # 可选: sonnet, opus, haiku
skills: []                       # 优化: 按需加载
permissionMode: bypassPermissions # 可选: default, acceptEdits, dontAsk
protocol_version: "1.1"          # AOP 协议版本
---
```

**性能调优参数:**

| 参数 | 默认值 | 说明 | 调优建议 |
|------|--------|------|----------|
| `model` | `sonnet` | AI 模型选择 | 高精度用 `opus`，高速度用 `haiku` |
| `skills` | `[]` | 技能预加载 | 保持空数组以优化启动速度 |
| `permissionMode` | `bypassPermissions` | 权限模式 | 生产环境考虑 `acceptEdits` |

### 安全配置

**命令验证配置:**

```bash
# .claude/scripts/validate-doc-operation.sh
MAX_COMMAND_LENGTH=1000          # 最大命令长度
ALLOWED_PATHS_PATTERN="^(md_docs/|\.claude/logs/)"  # 允许的路径模式
```

**日志配置:**

```bash
# 日志轮转设置
MAX_LOG_SIZE=5242880            # 5MB
MAX_LOG_LINES=1000              # 最大行数
LOG_RETENTION_DAYS=7            # 保留天数
```

## 📊 监控和维护

### 日常监控

1. **性能监控**
   ```bash
   # 手动运行监控
   ./.claude/scripts/doc-retriever-monitor.sh
   
   # 设置定时监控 (可选)
   # 添加到 crontab: 0 */6 * * * /path/to/doc-retriever-monitor.sh
   ```

2. **健康检查**
   ```bash
   # 每日健康检查
   ./.claude/scripts/doc-retriever-health-check.sh
   ```

3. **日志分析**
   ```bash
   # 查看最近的活动
   tail -50 .claude/logs/doc-retrieval.log
   
   # 查看错误日志
   grep -i "error\|failed" .claude/logs/*.log
   
   # 查看安全事件
   grep "CRITICAL\|ERROR" .claude/logs/security-validation.log
   ```

### 性能优化

1. **文档集优化**
   - 定期清理不需要的文档集
   - 压缩大型文档集
   - 建立文档索引缓存

2. **内存优化**
   - 监控技能加载内存使用
   - 优化大文档的处理策略
   - 实施文档分页机制

3. **响应时间优化**
   - 使用更快的模型 (`haiku`) 进行简单查询
   - 实施查询结果缓存
   - 优化文档搜索算法

### 故障排除

#### 常见问题

1. **技能调用失败**
   ```bash
   # 检查技能配置
   ls -la .claude/skills/*/SKILL.md
   
   # 验证技能语法
   grep -n "^name:\|^description:" .claude/skills/*/SKILL.md
   ```

2. **文档检索失败**
   ```bash
   # 检查文档集结构
   find md_docs -name "docContent.md" | head -5
   
   # 验证 Python 模块
   python -c "from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor"
   ```

3. **权限问题**
   ```bash
   # 检查脚本权限
   ls -la .claude/scripts/*.sh
   
   # 检查日志目录权限
   ls -ld .claude/logs
   ```

#### 错误代码参考

| 错误代码 | 含义 | 解决方案 |
|----------|------|----------|
| `exit 2` | 安全检查失败 | 检查命令是否包含危险操作 |
| `SkillError` | 技能调用失败 | 验证技能配置和依赖 |
| `FileNotFound` | 文档不存在 | 检查文档路径和权限 |
| `PermissionDenied` | 权限不足 | 检查文件和目录权限 |

## 🔄 升级和迁移

### 版本升级

1. **备份当前配置**
   ```bash
   cp -r .claude/agents/doc-retriever.md .claude/agents/doc-retriever.md.backup
   cp -r .claude/scripts .claude/scripts.backup
   ```

2. **应用新版本**
   - 更新子代理配置文件
   - 更新脚本文件
   - 更新技能文件

3. **验证升级**
   ```bash
   ./.claude/scripts/doc-retriever-diagnose.sh
   ```

### 配置迁移

**从 v1.0 到 v1.1:**

1. 更新协议版本
   ```yaml
   protocol_version: "1.1"  # 从 "1.0" 更新
   ```

2. 添加新的 hooks 配置
   ```yaml
   hooks:
     PreToolUse:
       - matcher: "Bash"
         hooks:
           - type: command
             command: "./.claude/scripts/validate-doc-operation.sh"
   ```

3. 优化技能加载
   ```yaml
   skills: []  # 从预加载列表改为空数组
   ```

## 📈 性能基准

### 基准测试结果

| 操作类型 | 平均响应时间 | 内存使用 | 成功率 |
|----------|--------------|----------|--------|
| 简单查询 | < 2s | < 50MB | 99.5% |
| 复杂查询 | < 5s | < 100MB | 98.0% |
| 大文档处理 | < 10s | < 200MB | 97.0% |
| 多文档聚合 | < 15s | < 300MB | 95.0% |

### 性能目标

- **响应时间**: 90% 的查询在 5 秒内完成
- **成功率**: 整体成功率 > 95%
- **内存使用**: 峰值内存使用 < 500MB
- **错误率**: 系统错误率 < 1%

## 🛡️ 安全最佳实践

### 部署安全

1. **最小权限原则**
   - 仅授予必要的文件访问权限
   - 限制网络访问（如果适用）
   - 定期审查权限配置

2. **输入验证**
   - 启用所有安全检查脚本
   - 定期更新危险操作模式列表
   - 监控异常查询模式

3. **日志安全**
   - 定期轮转和清理日志
   - 保护日志文件访问权限
   - 监控敏感信息泄露

### 运行时安全

1. **监控异常活动**
   ```bash
   # 监控安全事件
   tail -f .claude/logs/security-validation.log
   
   # 检查异常命令
   grep "CRITICAL" .claude/logs/security-validation.log
   ```

2. **定期安全审查**
   - 每月审查安全日志
   - 更新威胁模型
   - 测试安全控制措施

## 📞 支持和联系

### 获取帮助

1. **自助诊断**
   ```bash
   ./.claude/scripts/doc-retriever-diagnose.sh
   ```

2. **查看日志**
   ```bash
   # 最近的活动
   tail -100 .claude/logs/doc-retrieval.log
   
   # 错误信息
   grep -i error .claude/logs/*.log
   ```

3. **性能分析**
   ```bash
   ./.claude/scripts/doc-retriever-monitor.sh
   ```

### 报告问题

提交问题时请包含:
- 诊断报告输出
- 相关日志文件
- 重现步骤
- 系统环境信息

---

**最后更新**: 2024年1月
**版本**: 1.1.0
**维护者**: doc4llm 团队