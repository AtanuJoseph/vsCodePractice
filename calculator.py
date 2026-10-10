import ast
import math
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


STATIC_DIR = Path(__file__).parent / "static"
MAX_EXPRESSION_LENGTH = 256
MAX_EXPRESSION_NODES = 64

app = FastAPI(title="Calculator")


class CalculationRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=MAX_EXPRESSION_LENGTH)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def _evaluate(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        if isinstance(node.value, bool):
            raise ValueError("Only numeric values are allowed.")
        if isinstance(node.value, float) and not math.isfinite(node.value):
            raise ValueError("The result must be a finite number.")
        return node.value

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        operand = _evaluate(node.operand)
        result = operand if isinstance(node.op, ast.UAdd) else -operand
        return _ensure_finite(result)

    if isinstance(node, ast.BinOp):
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            result = left / right
        elif isinstance(node.op, ast.Mod):
            result = left % right
        else:
            raise ValueError("That operator is not supported.")
        return _ensure_finite(result)

    raise ValueError("Only basic arithmetic expressions are allowed.")


def _ensure_finite(result: int | float) -> int | float:
    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("The result must be a finite number.")
    return result


@app.post("/api/calc")
def calculate(request: CalculationRequest) -> dict[str, int | float]:
    try:
        tree = ast.parse(request.expression, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > MAX_EXPRESSION_NODES:
            raise ValueError("The expression is too complex.")
        result = _evaluate(tree.body)
    except SyntaxError as error:
        raise HTTPException(status_code=400, detail="Enter a valid arithmetic expression.") from error
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {"result": result}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
