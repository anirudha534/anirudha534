"""Talks to Claude. One streaming call per teacher turn, one small call to grade a lesson."""
import json
import os
import re

import anthropic

from . import prompts

DEFAULT_MODEL = "claude-sonnet-5-5"


class TutorError(Exception):
    """A problem the student can act on (bad key, no network, ...)."""


class Tutor:
    def __init__(self, client=None, model=None, effort="medium", max_tokens=8000):
        self.client = client or anthropic.Anthropic()
        self.model = model or os.environ.get("TEACHER_MODEL", DEFAULT_MODEL)
        self.effort = effort
        self.max_tokens = max_tokens

    def system(self, config):
        # Cached: the same long prompt is sent on every turn of every lesson.
        return [{"type": "text", "text": prompts.build_system(config), "cache_control": {"type": "ephemeral"}}]

    def _call(self, fn):
        try:
            return fn()
        except anthropic.AuthenticationError:
            raise TutorError("The API key was rejected. Check ANTHROPIC_API_KEY.") from None
        except anthropic.RateLimitError:
            raise TutorError("Too many requests right now. Wait a minute and try again.") from None
        except anthropic.APIConnectionError:
            raise TutorError("Could not reach the Anthropic API. Check your internet connection.") from None
        except anthropic.APIStatusError as e:
            raise TutorError(f"The API returned an error ({e.status_code}). Try again in a moment.") from None
        except TypeError as e:  # the SDK raises this when no credentials are configured
            if "authentication" in str(e).lower():
                raise TutorError("No API key found. Set ANTHROPIC_API_KEY (see README).") from None
            raise

    def reply(self, config, messages, on_text=None):
        """Stream the teacher's next message; returns the full text."""
        def run():
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system(config),
                messages=messages,
                output_config={"effort": self.effort},
            ) as stream:
                for chunk in stream.text_stream:
                    if on_text:
                        on_text(chunk)
                return stream.get_final_message()

        final = self._call(run)
        if final.stop_reason == "refusal":
            raise TutorError("The model declined to answer that. Try rephrasing the question.")
        text = "".join(b.text for b in final.content if b.type == "text")
        if final.stop_reason == "max_tokens":
            text += "\n\n[My reply was cut off. Type /continue.]"
        return text

    def grade(self, config, messages):
        """Ask for an honest 0-3 mastery score. Returns a dict or None if unparseable."""
        def run():
            return self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=self.system(config),
                messages=messages + [{"role": "user", "content": prompts.GRADE}],
                output_config={"effort": "low"},
            )

        final = self._call(run)
        text = "".join(b.text for b in final.content if b.type == "text")
        return parse_grade(text)


def parse_grade(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        g = json.loads(m.group(0))
        mastery = int(g["mastery"])
    except (ValueError, KeyError, TypeError):
        return None
    if not 0 <= mastery <= 3:
        return None
    weak = [str(w)[:80] for w in g.get("weak", []) if w][:5]
    return {"mastery": mastery, "weak": weak, "notes": str(g.get("notes", ""))[:300]}
