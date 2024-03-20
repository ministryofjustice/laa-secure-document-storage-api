from fastapi import APIRouter

router = APIRouter()


@router.get("/helloworld/")
async def hello_world():
    return {"Hello": "World"}


def complex_method(self, n):
    result = 0
    for i in range(n):
        if i % 2 == 0:
            result += i
        else:
            for j in range(i):
                if j % 2 == 0:
                    result -= j
                else:
                    for k in range(j):
                        if k % 2 == 0:
                            result += k
                        else:
                            for m in range(k):
                                if m % 2 == 0:
                                    result -= m
                                else:
                                    for p in range(m):
                                        if p % 2 == 0:
                                            result += p
                                        else:
                                            for q in range(p):
                                                if q % 2 == 0:
                                                    result -= q
                                                else:
                                                    result += q
    return result
