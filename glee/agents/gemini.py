"""Gemini CLI agent adapter."""

from typing import Any

from .base import AgentResult, BaseAgent


class GeminiAgent(BaseAgent):
    """Wrapper for Gemini CLI."""

    name = "gemini"
    command = "gemini"
    capabilities = ["code", "review"]

    def run(self, prompt: str, **kwargs: Any) -> AgentResult:
        """Run Gemini with a prompt.

        Uses: gemini -p "prompt"
        """
        args = [
            self.command,
            "-p", prompt,
        ]

        # Add sandbox mode if specified
        if kwargs.get("sandbox"):
            args.append("--sandbox")

        # Add yolo mode for auto-approval
        if kwargs.get("yolo"):
            args.append("--yolo")

        return self._run_subprocess(args, prompt=prompt, timeout=kwargs.get("timeout", 300))

    def run_review(self, files: list[str], focus: list[str] | None = None) -> AgentResult:
        """Run a code review with Gemini.

        Args:
            files: List of file paths to review
            focus: Optional focus areas (security, performance, etc.)
        """
        focus_str = ""
        if focus:
            focus_str = f"Focus on: {', '.join(focus)}. "

        files_str = ", ".join(files) if files else "the current codebase"

        prompt = f"""Review the following code: {files_str}

{focus_str}Provide structured feedback with:
1. Critical issues (must fix)
2. Warnings (should fix)
3. Suggestions (nice to have)

For each issue, specify:
- File and line number
- Description
- Suggested fix

End with APPROVED if no critical issues, or NEEDS_CHANGES if issues found."""

        return self.run(prompt, sandbox=True)

    def run_code(self, task: str, files: list[str] | None = None) -> AgentResult:
        """Run a coding task with Gemini.

        Args:
            task: Description of the coding task
            files: Optional list of files to focus on
        """
        context = ""
        if files:
            context = f"Focus on these files: {', '.join(files)}. "

        prompt = f"{context}{task}"

        return self.run(prompt, yolo=True)

    def run_judge(
        self,
        code_context: str,
        review_item: str,
        coder_objection: str,
    ) -> AgentResult:
        """Arbitrate a dispute between coder and reviewer.

        Args:
            code_context: The relevant code being disputed
            review_item: The reviewer's feedback (MUST or HIGH item)
            coder_objection: The coder's reasoning for disagreeing

        Returns:
            AgentResult with decision: ENFORCE, DISMISS, or ESCALATE
        """
        prompt = f"""You are an impartial judge arbitrating a dispute between a coder and a reviewer.

## Code Context
```
{code_context}
```

## Reviewer's Feedback (Disputed)
{review_item}

## Coder's Objection
{coder_objection}

## Your Task
Evaluate both perspectives objectively and make a decision:

1. **ENFORCE** - The reviewer is correct. The coder must implement the feedback.
2. **DISMISS** - The coder's objection is valid. The review item can be ignored.
3. **ESCALATE** - The situation is ambiguous and requires human judgment.

## Guidelines
- Focus on technical correctness, not preferences
- Consider: Does the review identify a real issue? Is the coder's objection factually accurate?
- ENFORCE if: The review catches a genuine bug, security issue, or violation of requirements
- DISMISS if: The review is based on a misunderstanding, or the suggestion would break functionality
- ESCALATE if: Both sides have valid points, or the decision requires domain knowledge you lack

## Response Format
Start your response with one of: ENFORCE, DISMISS, or ESCALATE

Then provide a brief explanation (2-3 sentences) justifying your decision."""

        return self.run(prompt, sandbox=True)
