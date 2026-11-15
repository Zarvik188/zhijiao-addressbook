# 知交 · 通讯录

EE308FZ 极限编程作业的本地单用户实现，包含联系人增删改查、收藏、多条联系方式和真实 .xlsx 导入导出。由 Codex 辅助准备，需学生理解、验证并核对个人过程记录后提交。

## 运行

需要 Python 3.10+，依赖固定在 requirements.txt。

```powershell
python -m pip install -r requirements.txt
python server.py
```

打开 http://127.0.0.1:5188 。数据库 contacts.db 自动生成，刷新及重启后保留。默认没有真实联系人。

```powershell
python -m unittest discover -s tests -v
```

## Excel 格式

从页面下载模板；工作表名为“通讯录”。前四列固定为姓名、分组、收藏、备注。联系方式按类型编号，采用 `电话1_标签`、`电话1_值` 等成对列。收藏填“是”或“否”。电话号码和账号请按文本填写；Excel 已经丢失的前导零无法恢复。

导出全部联系人，每位一行，包含备注、收藏和全部联系方式；单元格按文本写出。导入整表校验后一次事务追加，不按同名自动覆盖，也不自动合并重复导入。文件不超过 5 MB，解压不超过 30 MB，最多 1000 位联系人，单人最多 50 条联系方式。

## 模块

- model.py：统一校验、UUID 标识、SQLite 持久化与事务。
- workbook.py：Excel 双向列映射和格式校验。
- server.py：HTTP API 与静态文件，只监听 127.0.0.1。
- static/：原生 HTML/CSS/JavaScript，动态联系方式表单、收藏筛选与搜索。
- tests/：临时数据库和工作簿测试。
- codestyle.md：代码规范。

## 演示边界

无云部署、账号系统和多人隔离。本机数据库保存明文联系人，不应公开监听或录入私人通讯录。示例数据均为虚构。当前没有 GitHub 发布、Release 或 PR；本地 Git 记录不能替代 GitHub 截图。
