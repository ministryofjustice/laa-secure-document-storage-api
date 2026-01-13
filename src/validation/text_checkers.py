import re
from typing import Callable
from pydantic import BaseModel


class StringCheck(BaseModel):
    "name attribute added to make it easier to identify check type in unit tests"
    checker: Callable
    pattern: str | tuple
    message: str
    name: str

    def check(self, line: str) -> tuple[int, str]:
        line_core = line.strip()
        result = (200, "")
        if self.checker(self.pattern, line, flags=re.IGNORECASE):
            result = (400, self.message + line_core)
        return result


text_checkers = {}
text_checkers["sql_injection_check"] = StringCheck(checker=re.search,
                                                   pattern=r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b|\bOR\s+1=1\b|\bOR\s+'1'='1'",  # noqa: 501
                                                   message="possible SQL injection found in: ",
                                                   name="sql_injection_check")

text_checkers["html_tag_check"] = StringCheck(checker=re.search,
                                              pattern=r"<[^>]+>",
                                              message="possible HTML tag(s) found in: ",
                                              name="html_tag_check")

text_checkers["javascript_url_check"] = StringCheck(checker=re.search,
                                                    pattern=r"javascript\s*:",
                                                    message="suspected javascript URL found in: ",
                                                    name="javascript_url_check")

text_checkers["excel_char_check"] = StringCheck(checker=lambda substring, string, **kwargs: string.strip().startswith(substring),  # noqa: 501
                                                pattern=("=", "@", "+", "-"),
                                                message="forbidden initial character found: ",
                                                name="excel_char_check")
