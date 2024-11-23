import getpass
import os
from bs4 import BeautifulSoup as Soup
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")


_set_env("OPENAI_API_KEY")



# LCEL docs
url = "https://dev.to/pierre/clean-javascript-code-1gc"
loader = RecursiveUrlLoader(
    url=url, max_depth=20, extractor=lambda x: Soup(x, "html.parser").text
)
docs = loader.load()

# Sort the list based on the URLs and get the text
d_sorted = sorted(docs, key=lambda x: x.metadata["source"])
d_reversed = list(reversed(d_sorted))
concatenated_content = "\n\n\n --- \n\n\n".join(
    [doc.page_content for doc in d_reversed]
)

code_gen_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """you are a programmer that is professional for making code more efficient given code file you will fix all the functions by reducing their complexity. NO EXPLANATİON ONLY THE MORE EFFICENT CODE OR DONT CHANGE Here is the file:""",
        ),
        ("placeholder", "{messages}"),
    ]
)


# Data model
class code(BaseModel):
    """Schema for code solutions to questions about LCEL."""

    prefix: str = Field(description="Description of the problem and approach")
    imports: str = Field(description="Code block import statements")
    code: str = Field(description="Code block not including import statements")


expt_llm = "gpt-4o-mini"
llm = ChatOpenAI(temperature=0, model=expt_llm)
code_gen_chain_oai = code_gen_prompt | llm.with_structured_output(code)
question = "def naive_matrix_multiply(A, B): n = len(A) result = [[0] * n for _ in range(n)] for i in range(n):  # Row of A for j in range(n):  # Column of B for k in range(n):  # Element of row A and column B result[i][j] += A[i][k] * B[k][j] return result"
solution = code_gen_chain_oai.invoke(
    {"context": concatenated_content, "messages": [("user", question)]}
)
solution