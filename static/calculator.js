const expressionDisplay = document.querySelector("#expression");
const resultDisplay = document.querySelector("#result");
const keypad = document.querySelector(".keypad");

let expression = "";
let isShowingResult = false;

function render() {
  expressionDisplay.textContent = expression || "\u00a0";
  resultDisplay.classList.remove("error");
  if (!expression) {
    resultDisplay.textContent = "0";
  }
}

function appendValue(value) {
  if (isShowingResult && /[\d.(]/.test(value)) {
    expression = "";
  }
  expression += value;
  isShowingResult = false;
  render();
}

async function calculate() {
  if (!expression.trim()) {
    return;
  }

  try {
    const response = await fetch("/api/calc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expression }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Could not calculate this expression.");
    }

    expressionDisplay.textContent = expression;
    resultDisplay.textContent = String(data.result);
    resultDisplay.classList.remove("error");
    expression = String(data.result);
    isShowingResult = true;
  } catch (error) {
    resultDisplay.textContent =
      error instanceof Error ? error.message : "Could not calculate this expression.";
    resultDisplay.classList.add("error");
    isShowingResult = false;
  }
}

keypad.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) {
    return;
  }

  if (button.dataset.action === "clear") {
    expression = "";
    isShowingResult = false;
    render();
  } else if (button.dataset.action === "backspace") {
    expression = expression.slice(0, -1);
    isShowingResult = false;
    render();
  } else if (button.dataset.action === "calculate") {
    calculate();
  } else if (button.dataset.value) {
    appendValue(button.dataset.value);
  }
});

document.addEventListener("keydown", (event) => {
  if (/^[\d.+\-*/()%]$/.test(event.key)) {
    event.preventDefault();
    appendValue(event.key);
  } else if (event.key === "Enter" || event.key === "=") {
    event.preventDefault();
    calculate();
  } else if (event.key === "Backspace") {
    expression = expression.slice(0, -1);
    isShowingResult = false;
    render();
  } else if (event.key === "Escape") {
    expression = "";
    isShowingResult = false;
    render();
  }
});
