# 代码规范

- Python 使用四空格缩进，函数、变量使用 snake_case；JavaScript 使用两空格缩进和 camelCase。
- 联系人的业务校验集中在 model.py，Excel 列映射集中在 workbook.py；HTTP 层不重复实现规则。
- SQL 使用参数绑定；动态列名必须来自固定白名单。页面使用 textContent 输出用户输入。
- 联系方式保存为类型、标签和值三元组，禁止用单一分隔符拼接多值。
- 每次修改完成运行 python -m unittest discover -s tests -v。
- Git 按可验证的功能阶段提交，说明修改目的；不回填提交日期、不伪造贡献或测试结果。
- 演示只使用虚构联系人，不提交个人通讯录、数据库和凭据。
