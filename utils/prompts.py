
def generate_test_prompt(inp):
    input_prompt_template = f"""
You are a talented query-item relevance evaluator.
We break down relevance into the following four classes which are used to
measure the relevance of items in the search results:

• Exact: the item is relevant for the query, and satisfies all the
query specifications (e.g., a water bottle matching all attributes
of a query “plastic water bottle 24oz”, such as material and size)
• Substitute: the item is somewhat relevant, i.e., it fails to fulfill
some aspects of the query but the item can be used as a functional
substitute (e.g., fleece for a “sweater” query)
• Complement: the item does not fulfill the query, but could
be used in combination with an exact item (e.g., track pants for
“running shoes” query)
• Irrelevant: the item is irrelevant, or it fails to fulfill a central
aspect of the query (e.g., socks for a “telescope” query, or a wheat
flour bread for a “gluten–free bread” query)

I will give you query, product_title, product_description, product_bullet_point, product_brand, product_color

query: {inp['query']},
product_title : {inp['product_title']},
product_description : {inp['product_description']},
product_bullet_point : {inp['product_bullet_point']},
product_brand : {inp['product_brand']},
product_color : {inp['product_color']}

Classify the query-product relevance label into Exact, Substitute, Complement, Irrelevant.
Do not return any other output than the label
The output should be a markdown code snippet formatted in the following schema, including the leading and trailing "\`\`\`json" and "\`\`\`":

```json
{{
	"Label": string  // This is the relevancy label
}}
```
""".strip()

    return input_prompt_template