# Draft: OpenCode Agent Formatter 字段配置规范检索

## 研究目标
检索 opencode agent formatter 字段配置规范

## 检索策略
根据 skill 指令，需要执行以下 CLI 命令：
```bash
docrag \
  "opencodde agent formatter 字段配置规范" \
  --kb ~/project/md_docs_base \
  --threshold 3000 \
  --skip-keywords doc4llm/doc_rag/searcher/skiped_keywords.txt \
  --searcher-config '{
    "embedding_provider": "ms",
    "threshold_page_title": 3
  }'
```

## 研究范围
- OpenCode Agent Formatter 字段配置
- 字段配置规范和语法
- 实际使用示例和最佳实践

## 状态
待用户确认后执行
