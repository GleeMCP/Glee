from glee.types import ReviewSession, ReviewStatus


def test_review_session_creation():
    session = ReviewSession(
        review_id="test-123",
        files=["src/main.py"],
        project_path="/tmp/test",
    )
    assert session.review_id == "test-123"
    assert session.status == ReviewStatus.IN_PROGRESS
    assert session.iteration == 0
    assert session.max_iterations == 10


def test_review_status_values():
    assert ReviewStatus.IN_PROGRESS == "in_progress"
    assert ReviewStatus.APPROVED == "approved"
    assert ReviewStatus.MAX_ITERATIONS == "max_iterations"
