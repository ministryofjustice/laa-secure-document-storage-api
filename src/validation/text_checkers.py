import re
from typing import Callable
from pydantic import BaseModel


class StringCheck(BaseModel):
    checker: Callable
    pattern: str | tuple
    message: str

    def check(self, line: str) -> tuple[int, str]:
        result = (200, "")
        if self.checker(self.pattern, line, flags=re.IGNORECASE):
            result = (400, self.message + line)
        return result


sql_injection_check = StringCheck(checker=re.search,
                                  pattern=r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b|\bOR\s+1=1\b|\bOR\s+'1'='1'",
                                  message="possible SQL injection found in: ")

html_tag_check = StringCheck(checker=re.search,
                             pattern=r"<[^>]+>",
                             message="possible HTML tag(s) found in: ")

javascript_url_check = StringCheck(checker=re.search,
                                   pattern=r"javascript\s*:",
                                   message="suspected javascript URL found in: ")

excel_char_check = StringCheck(checker=lambda substring, string, **kwargs: string.startswith(substring),
                               pattern=("=", "@", "+", "-"),
                               message="forbidden initial character found: ")
