import json

import anthropic
import httpx2
import pytest

from coursepilot.extraction import ExtractionError, LLMExtractor

API_KEY = "test-anthropic-key"


def tool_use_body(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-8",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "extract_course_items",
                "input": {"items": items},
            }
        ],
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }


def refusal_body() -> dict[str, object]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-8",
        "content": [],
        "stop_reason": "refusal",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 0},
    }


def make_extractor_with_body(
    body: dict[str, object],
) -> tuple[LLMExtractor, list[httpx2.Request]]:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json=body)

    http_client = httpx2.Client(transport=httpx2.MockTransport(handler))
    client = anthropic.Anthropic(api_key=API_KEY, http_client=http_client)
    return LLMExtractor(api_key=API_KEY, client=client), requests


def make_extractor(
    items: list[dict[str, object]],
) -> tuple[LLMExtractor, list[httpx2.Request]]:
    return make_extractor_with_body(tool_use_body(items))


def test_extract_maps_tool_use_input_to_extracted_items() -> None:
    extractor, _ = make_extractor(
        [
            {
                "title": "Homework 3",
                "item_type": "assignment",
                "due_date": "2026-09-15T23:59:00-07:00",
                "course": "CS 162",
                "extraction_confidence": "llm_high",
            }
        ]
    )

    items = extractor.extract("<html>Homework 3 due Sept 15</html>")

    assert len(items) == 1
    item = items[0]
    assert item.title == "Homework 3"
    assert item.item_type == "assignment"
    assert item.due_date == "2026-09-15T23:59:00-07:00"
    assert item.course == "CS 162"
    assert item.extraction_confidence == "llm_high"


def test_extract_returns_empty_list_when_no_items_found() -> None:
    extractor, _ = make_extractor([])

    items = extractor.extract("<html>no assignments here</html>")

    assert items == []


def test_extract_forces_the_extraction_tool_choice() -> None:
    extractor, requests = make_extractor([])

    extractor.extract("<html></html>")

    payload = json.loads(requests[-1].content)
    assert payload["tool_choice"] == {"type": "tool", "name": "extract_course_items"}
    assert payload["tools"][0]["name"] == "extract_course_items"


def test_extract_sends_the_html_as_the_user_message() -> None:
    extractor, requests = make_extractor([])

    extractor.extract("<html>page content</html>")

    payload = json.loads(requests[-1].content)
    assert payload["messages"] == [{"role": "user", "content": "<html>page content</html>"}]


def test_extract_defaults_a_field_missing_from_the_tool_response_instead_of_crashing() -> None:
    extractor, _ = make_extractor(
        [
            {
                "title": "Homework 3",
                "item_type": "assignment",
                "due_date": "2026-09-15T23:59:00-07:00",
                # "course" omitted entirely, unlike what the tool schema requires.
                "extraction_confidence": "llm_high",
            }
        ]
    )

    items = extractor.extract("<html>Homework 3 due Sept 15</html>")

    assert len(items) == 1
    assert items[0].course == ""


def test_extract_raises_a_clear_error_when_the_model_returns_no_tool_use() -> None:
    extractor, _ = make_extractor_with_body(refusal_body())

    with pytest.raises(ExtractionError, match="refusal"):
        extractor.extract("<html>page content</html>")
