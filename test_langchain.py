from langchain_core.prompts import PromptTemplate

import langchain
print("LangChain 版本:", langchain.__version__)

template = PromptTemplate.from_template(
    "你是一名金融研究助手。请回答关于研报的问题：{question}"
)
result = template.format(question="这家公司的主营业务是什么？")
print("模板渲染结果:", result)
